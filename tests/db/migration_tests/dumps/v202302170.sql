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
cdb78cac-aed9-43ca-a545-5a3ed9247314	localhost	2023-02-17 10:13:02.32948+01	f	7a2fa59e-3d39-4fab-a8cf-243ca7507d5a	\N
cdb78cac-aed9-43ca-a545-5a3ed9247314	internal	2023-02-17 10:13:03.820055+01	f	88fe13d5-c5d2-4e98-bc3a-5c084071caf4	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
88fe13d5-c5d2-4e98-bc3a-5c084071caf4	47a38e40-aea3-11ed-9986-84144dfe5579	internal	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314
7a2fa59e-3d39-4fab-a8cf-243ca7507d5a	47a38e40-aea3-11ed-9986-84144dfe5579	localhost	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314
662d728b-d7c8-4f28-b23d-ccb60de04010	474d1a1a-aea3-11ed-b5cb-84144dfe5579	internal	2023-02-17 10:13:03.820055+01	cdb78cac-aed9-43ca-a545-5a3ed9247314
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-inmanta-laptop	cdb78cac-aed9-43ca-a545-5a3ed9247314	2023-02-17 10:13:01.764386+01	2023-02-17 10:13:01.819658+01	2023-02-17 10:13:03.820055+01	474d1a1a-aea3-11ed-b5cb-84144dfe5579
arnaud-inmanta-laptop	cdb78cac-aed9-43ca-a545-5a3ed9247314	2023-02-17 10:13:02.32948+01	2023-02-17 10:13:09.816501+01	\N	47a38e40-aea3-11ed-9986-84144dfe5579
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::Service	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::File	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::Directory	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::Package	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::Symlink	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::AgentConfig	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::Service	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::File	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::Directory	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::Package	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::Symlink	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
cdb78cac-aed9-43ca-a545-5a3ed9247314	std::AgentConfig	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
24bb4e6d-1608-413b-bedb-ff29fa0f730c	cdb78cac-aed9-43ca-a545-5a3ed9247314	2023-02-17 10:12:53.312721+01	2023-02-17 10:13:01.85545+01	2023-02-17 10:12:53.305139+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	2db46169-f3cd-4b29-b9ee-449d895726a8	t	\N	{"errors": []}	f	{}	\N	\N	\N
27c05e1c-028e-4313-b987-bfac4948fde0	cdb78cac-aed9-43ca-a545-5a3ed9247314	2023-02-17 10:13:02.445357+01	2023-02-17 10:13:09.756046+01	2023-02-17 10:13:02.439701+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	5710e2ba-0587-44cc-a1fc-1f3433d28ffd	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	cdb78cac-aed9-43ca-a545-5a3ed9247314	2023-02-17 10:13:01.364897+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	cdb78cac-aed9-43ca-a545-5a3ed9247314	2023-02-17 10:13:09.674549+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
bab6d7ef-0dc2-496e-a256-f67e8240d8b5	dev-2	1bede093-eb98-481c-852c-e7e32811f367			{"auto_full_compile": ""}	0	f		
cdb78cac-aed9-43ca-a545-5a3ed9247314	dev-1	1bede093-eb98-481c-852c-e7e32811f367			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
1bede093-eb98-481c-852c-e7e32811f367	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
bca81f73-da92-4276-b2a9-52f3e35e8389	2023-02-17 10:12:53.313078+01	2023-02-17 10:12:53.31415+01		Init		Using extra environment variables during compile \n	0	24bb4e6d-1608-413b-bedb-ff29fa0f730c
dd7220c6-da99-4084-bad2-73730db23426	2023-02-17 10:12:53.314421+01	2023-02-17 10:12:53.315274+01		Creating venv			0	24bb4e6d-1608-413b-bedb-ff29fa0f730c
de39c2e2-bf49-4c86-8bb2-7d081b6b4ccf	2023-02-17 10:12:53.319455+01	2023-02-17 10:12:53.572212+01	/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.3.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	24bb4e6d-1608-413b-bedb-ff29fa0f730c
aea65734-9b05-4ea4-9eb2-0e09459dcd76	2023-02-17 10:12:53.572901+01	2023-02-17 10:13:00.809626+01	/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.1.3 on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.1.3 in /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000107 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.module           INFO    Checking out 4.1.3 on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 dataclasses~=0.7; python_version < "3.7" pydantic~=1.10 email_validator~=1.3 inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Collecting pydantic~=1.10\ninmanta.pip              DEBUG   Using cached pydantic-1.10.5-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (39.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0\ninmanta.pip              DEBUG   Using cached python_slugify-8.0.0-py2.py3-none-any.whl (9.5 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.0.1)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, pydantic\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 1.10.4\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages, outside environment /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   pyadr 0.19.0 requires python-slugify<7,>=6, but you have python-slugify 8.0.0 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed pydantic-1.10.5 python-slugify-8.0.0\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.0 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000045 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.module           INFO    Checking out 4.1.3 on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 dataclasses~=0.7; python_version < "3.7" pydantic~=1.10 email_validator~=1.3 inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (39.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.0.1)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.0 (from pyadr)\n	0	24bb4e6d-1608-413b-bedb-ff29fa0f730c
8cb95813-9afa-4a06-ad8a-869a794bfc44	2023-02-17 10:13:00.810471+01	2023-02-17 10:13:01.854341+01	/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m inmanta.app -vvv export -X -e cdb78cac-aed9-43ca-a545-5a3ed9247314 --server_address localhost --server_port 36299 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpgmeaerbu --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004187 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.0 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000089 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.3\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002160)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001598)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000233)\ninmanta.execute.schedulerINFO    Total compilation time 0.004131\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36299/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36299/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36299/api/v1/file/e13ad6e395f94b178f8627cbe0b8125d46e7abf0\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36299/api/v1/file/db0b95ee005147666e020669ad62de99f657791b\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36299/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36299/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36299/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36299/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	24bb4e6d-1608-413b-bedb-ff29fa0f730c
e9b4e9cf-0f51-4bcc-8612-2c578d260da9	2023-02-17 10:13:02.445826+01	2023-02-17 10:13:02.44697+01		Init		Using extra environment variables during compile \n	0	27c05e1c-028e-4313-b987-bfac4948fde0
c4eab3d1-8c91-4a7e-943b-f1a3c9ddafa0	2023-02-17 10:13:02.452132+01	2023-02-17 10:13:02.714144+01	/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.3.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	27c05e1c-028e-4313-b987-bfac4948fde0
4b01f197-5937-4b93-927d-a35a61dffba4	2023-02-17 10:13:02.714974+01	2023-02-17 10:13:09.109283+01	/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000071 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.module           INFO    Checking out 4.1.3 on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator~=1.3 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (39.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.0.1)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.0 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000043 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.module           INFO    Checking out 4.1.3 on /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator~=1.3 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (39.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.0 (from pyadr)\n	0	27c05e1c-028e-4313-b987-bfac4948fde0
67a3da7a-a8d0-4302-9cf4-b8bc319b43b3	2023-02-17 10:13:09.110266+01	2023-02-17 10:13:09.755297+01	/tmp/tmp9tq6gnyi/server/environments/cdb78cac-aed9-43ca-a545-5a3ed9247314/.env/bin/python -m inmanta.app -vvv export -X -e cdb78cac-aed9-43ca-a545-5a3ed9247314 --server_address localhost --server_port 36299 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpbxpc4std --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004448 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.0 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000091 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.3\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002272)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001724)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000248)\ninmanta.execute.schedulerINFO    Total compilation time 0.004390\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36299/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36299/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36299/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36299/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36299/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	27c05e1c-028e-4313-b987-bfac4948fde0
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
cdb78cac-aed9-43ca-a545-5a3ed9247314	2	std::AgentConfig[internal,agentname=localhost]	internal	2023-02-17 10:13:09.80599+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
cdb78cac-aed9-43ca-a545-5a3ed9247314	1	std::File[localhost,path=/tmp/test]	localhost	2023-02-17 10:13:02.456816+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
cdb78cac-aed9-43ca-a545-5a3ed9247314	1	std::AgentConfig[internal,agentname=localhost]	internal	2023-02-17 10:13:03.844185+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
cdb78cac-aed9-43ca-a545-5a3ed9247314	2	std::File[localhost,path=/tmp/test]	localhost	2023-02-17 10:13:09.715703+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
447ec3b5-6478-4428-8546-35710860b754	store	2023-02-17 10:13:01.364438+01	2023-02-17 10:13:01.369984+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2023-02-17T10:13:01.369994+01:00\\"}"}	\N	\N	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
61cd5801-864b-419d-9e24-4e1d221eadd0	pull	2023-02-17 10:13:01.773241+01	2023-02-17 10:13:01.778849+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-02-17T10:13:01.778861+01:00\\"}"}	\N	\N	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
dff9b766-a160-4a23-9e95-42414b07b4a9	deploy	2023-02-17 10:13:01.806111+01	2023-02-17 10:13:01.81919+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-02-17 10:13:01+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-02-17 10:13:01+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b45a60c4-79ec-4be1-a103-057f9c28f0f3\\"}, \\"timestamp\\": \\"2023-02-17T10:13:01.803088+01:00\\"}","{\\"msg\\": \\"Start deploy b45a60c4-79ec-4be1-a103-057f9c28f0f3 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"b45a60c4-79ec-4be1-a103-057f9c28f0f3\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-02-17T10:13:01.807659+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-02-17T10:13:01.808371+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-02-17T10:13:01.811427+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy b45a60c4-79ec-4be1-a103-057f9c28f0f3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b45a60c4-79ec-4be1-a103-057f9c28f0f3\\"}, \\"timestamp\\": \\"2023-02-17T10:13:01.814336+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
0310f1b4-afb0-4b9d-86ef-3b9bcd0c8734	deploy	2023-02-17 10:13:01.934122+01	2023-02-17 10:13:01.934122+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-02-17T09:13:01.934122+00:00\\"}"}	deployed	\N	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
136578d3-d20a-4ff0-9fa9-d0068f390080	pull	2023-02-17 10:13:02.336077+01	2023-02-17 10:13:02.3387+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-02-17T10:13:02.338718+01:00\\"}"}	\N	\N	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::File[localhost,path=/tmp/test],v=1"}
a2528c6a-3c93-4c10-80fb-8f647d75a7a3	deploy	2023-02-17 10:13:02.360851+01	2023-02-17 10:13:02.368954+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2023-02-17 10:13:02+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2023-02-17 10:13:02+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"22d9a372-ffad-4b0c-9f74-2ab9049c4d55\\"}, \\"timestamp\\": \\"2023-02-17T10:13:02.359002+01:00\\"}","{\\"msg\\": \\"Start deploy 22d9a372-ffad-4b0c-9f74-2ab9049c4d55 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"22d9a372-ffad-4b0c-9f74-2ab9049c4d55\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-02-17T10:13:02.363724+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-02-17T10:13:02.364640+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-02-17T10:13:02.364750+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 928, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmp9tq6gnyi/cdb78cac-aed9-43ca-a545-5a3ed9247314/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-02-17T10:13:02.366791+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 22d9a372-ffad-4b0c-9f74-2ab9049c4d55\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"22d9a372-ffad-4b0c-9f74-2ab9049c4d55\\"}, \\"timestamp\\": \\"2023-02-17T10:13:02.366968+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::File[localhost,path=/tmp/test],v=1"}
615f8117-3188-4647-a8d0-d93fe1fa6a0b	pull	2023-02-17 10:13:02.432177+01	2023-02-17 10:13:02.434338+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-02-17T10:13:02.434350+01:00\\"}"}	\N	\N	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::File[localhost,path=/tmp/test],v=1"}
a6b241af-8035-4907-b4b5-b4a3f499bbe8	pull	2023-02-17 10:13:03.829248+01	2023-02-17 10:13:03.830213+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-02-17T10:13:03.830224+01:00\\"}"}	\N	\N	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
10753041-2ac1-4eda-9b64-19a9330e3771	deploy	2023-02-17 10:13:03.837856+01	2023-02-17 10:13:03.844185+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-02-17 10:13:03+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-02-17 10:13:03+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b6d49264-7a0c-4c35-be36-aa01bb8bbcf1\\"}, \\"timestamp\\": \\"2023-02-17T10:13:03.835794+01:00\\"}","{\\"msg\\": \\"Start deploy b6d49264-7a0c-4c35-be36-aa01bb8bbcf1 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"b6d49264-7a0c-4c35-be36-aa01bb8bbcf1\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-02-17T10:13:03.838959+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-02-17T10:13:03.839600+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy b6d49264-7a0c-4c35-be36-aa01bb8bbcf1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b6d49264-7a0c-4c35-be36-aa01bb8bbcf1\\"}, \\"timestamp\\": \\"2023-02-17T10:13:03.842377+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
2cff3ee5-9559-4a42-9969-6c97490f2463	deploy	2023-02-17 10:13:02.445117+01	2023-02-17 10:13:02.456816+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"cdd3c811-fb48-4658-8ad8-c9821bac8daf\\"}, \\"timestamp\\": \\"2023-02-17T10:13:02.441716+01:00\\"}","{\\"msg\\": \\"Start deploy cdd3c811-fb48-4658-8ad8-c9821bac8daf of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"cdd3c811-fb48-4658-8ad8-c9821bac8daf\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-02-17T10:13:02.446534+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-02-17T10:13:02.447063+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-02-17T10:13:02.451981+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 935, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp9tq6gnyi/cdb78cac-aed9-43ca-a545-5a3ed9247314/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-02-17T10:13:02.452155+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy cdd3c811-fb48-4658-8ad8-c9821bac8daf\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"cdd3c811-fb48-4658-8ad8-c9821bac8daf\\"}, \\"timestamp\\": \\"2023-02-17T10:13:02.452329+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	1	{"std::File[localhost,path=/tmp/test],v=1"}
d45f927c-85fa-42d3-bf8a-087eb37e4e7f	store	2023-02-17 10:13:09.674516+01	2023-02-17 10:13:09.675957+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2023-02-17T10:13:09.675967+01:00\\"}"}	\N	\N	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
036b344f-c93e-4e3a-aed8-82f230319b76	deploy	2023-02-17 10:13:09.67721+01	2023-02-17 10:13:09.67721+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-02-17T09:13:09.677210+00:00\\"}"}	deployed	\N	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
1bc76596-418f-4fdb-9ea6-3727ac21fa46	deploy	2023-02-17 10:13:09.692642+01	2023-02-17 10:13:09.692642+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-02-17T09:13:09.692642+00:00\\"}"}	deployed	\N	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
32fd3e35-39f1-4f21-81dc-c8fb7ef8e83c	pull	2023-02-17 10:13:09.691793+01	2023-02-17 10:13:09.692458+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-02-17T10:13:09.693629+01:00\\"}"}	\N	\N	\N	cdb78cac-aed9-43ca-a545-5a3ed9247314	2	{"std::File[localhost,path=/tmp/test],v=2"}
cd4b7ed5-a7a1-4cd9-aaaa-bbccc9d43ad6	deploy	2023-02-17 10:13:09.708536+01	2023-02-17 10:13:09.715703+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"fab0414b-1cb6-4871-9e32-116d9c596cba\\"}, \\"timestamp\\": \\"2023-02-17T10:13:09.706402+01:00\\"}","{\\"msg\\": \\"Start deploy fab0414b-1cb6-4871-9e32-116d9c596cba of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"fab0414b-1cb6-4871-9e32-116d9c596cba\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-02-17T10:13:09.710396+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-02-17T10:13:09.710837+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-02-17T10:13:09.712969+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 935, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp9tq6gnyi/cdb78cac-aed9-43ca-a545-5a3ed9247314/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-02-17T10:13:09.713151+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy fab0414b-1cb6-4871-9e32-116d9c596cba\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"fab0414b-1cb6-4871-9e32-116d9c596cba\\"}, \\"timestamp\\": \\"2023-02-17T10:13:09.713342+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	2	{"std::File[localhost,path=/tmp/test],v=2"}
19273755-8111-40fa-8a68-367770c2c869	deploy	2023-02-17 10:13:09.80599+01	2023-02-17 10:13:09.80599+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-02-17T09:13:09.805990+00:00\\"}"}	deployed	\N	nochange	cdb78cac-aed9-43ca-a545-5a3ed9247314	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
cdb78cac-aed9-43ca-a545-5a3ed9247314	447ec3b5-6478-4428-8546-35710860b754	std::File[localhost,path=/tmp/test]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	447ec3b5-6478-4428-8546-35710860b754	std::AgentConfig[internal,agentname=localhost]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	61cd5801-864b-419d-9e24-4e1d221eadd0	std::AgentConfig[internal,agentname=localhost]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	dff9b766-a160-4a23-9e95-42414b07b4a9	std::AgentConfig[internal,agentname=localhost]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	0310f1b4-afb0-4b9d-86ef-3b9bcd0c8734	std::AgentConfig[internal,agentname=localhost]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	136578d3-d20a-4ff0-9fa9-d0068f390080	std::File[localhost,path=/tmp/test]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	a2528c6a-3c93-4c10-80fb-8f647d75a7a3	std::File[localhost,path=/tmp/test]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	615f8117-3188-4647-a8d0-d93fe1fa6a0b	std::File[localhost,path=/tmp/test]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	2cff3ee5-9559-4a42-9969-6c97490f2463	std::File[localhost,path=/tmp/test]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	a6b241af-8035-4907-b4b5-b4a3f499bbe8	std::AgentConfig[internal,agentname=localhost]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	10753041-2ac1-4eda-9b64-19a9330e3771	std::AgentConfig[internal,agentname=localhost]	1
cdb78cac-aed9-43ca-a545-5a3ed9247314	d45f927c-85fa-42d3-bf8a-087eb37e4e7f	std::File[localhost,path=/tmp/test]	2
cdb78cac-aed9-43ca-a545-5a3ed9247314	d45f927c-85fa-42d3-bf8a-087eb37e4e7f	std::AgentConfig[internal,agentname=localhost]	2
cdb78cac-aed9-43ca-a545-5a3ed9247314	036b344f-c93e-4e3a-aed8-82f230319b76	std::AgentConfig[internal,agentname=localhost]	2
cdb78cac-aed9-43ca-a545-5a3ed9247314	32fd3e35-39f1-4f21-81dc-c8fb7ef8e83c	std::File[localhost,path=/tmp/test]	2
cdb78cac-aed9-43ca-a545-5a3ed9247314	1bc76596-418f-4fdb-9ea6-3727ac21fa46	std::AgentConfig[internal,agentname=localhost]	2
cdb78cac-aed9-43ca-a545-5a3ed9247314	cd4b7ed5-a7a1-4cd9-aaaa-bbccc9d43ad6	std::File[localhost,path=/tmp/test]	2
cdb78cac-aed9-43ca-a545-5a3ed9247314	19273755-8111-40fa-8a68-367770c2c869	std::AgentConfig[internal,agentname=localhost]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302170}
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
-- Name: resource_environment_model_resource_set_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_model_resource_set_idx ON public.resource USING btree (environment, model, resource_set);


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

