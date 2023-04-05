--
-- PostgreSQL database dump
--

-- Dumped from database version 13.6 (Ubuntu 13.6-0ubuntu0.21.10.1)
-- Dumped by pg_dump version 14.7 (Ubuntu 14.7-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
--  SELECT pg_catalog.set_config('search_path', '', false);
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

-- SET default_table_access_method = heap;

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
-- Name: inmanta_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inmanta_user (
    id uuid NOT NULL,
    username character varying NOT NULL,
    password_hash character varying NOT NULL,
    auth_method public.auth_method NOT NULL
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
c6b2570c-c115-4931-9f63-a83972769724	internal	2023-03-07 10:49:23.414801+01	f	e1b31850-8994-475c-ba06-d60fdd7f3432	\N
c6b2570c-c115-4931-9f63-a83972769724	localhost	2023-03-07 10:49:26.111569+01	f	dcfd905a-008c-4740-9983-474c176fa924	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
e1b31850-8994-475c-ba06-d60fdd7f3432	57191358-bccd-11ed-86be-990e02844d04	internal	\N	c6b2570c-c115-4931-9f63-a83972769724
dcfd905a-008c-4740-9983-474c176fa924	57191358-bccd-11ed-86be-990e02844d04	localhost	\N	c6b2570c-c115-4931-9f63-a83972769724
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
florent-Latitude-5421	c6b2570c-c115-4931-9f63-a83972769724	2023-03-07 10:49:23.414801+01	2023-03-07 10:49:34.354196+01	\N	57191358-bccd-11ed-86be-990e02844d04
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
c6b2570c-c115-4931-9f63-a83972769724	std::Service	1	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::File	1	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::Directory	1	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::Package	1	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::Symlink	1	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::testing::NullResource	1	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::AgentConfig	1	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::Service	2	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::File	2	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::Directory	2	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::Package	2	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::Symlink	2	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::testing::NullResource	2	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c6b2570c-c115-4931-9f63-a83972769724	std::AgentConfig	2	{"8075baf6360169f7ea8e2bfe877789a37de43617": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
aa3df1f3-6a35-4ad2-9009-e804e54d1d40	c6b2570c-c115-4931-9f63-a83972769724	2023-03-07 10:49:12.305244+01	2023-03-07 10:49:23.534459+01	2023-03-07 10:49:12.250005+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	2998fb5a-4ad0-47d9-bff4-96d27b3b7347	t	\N	{"errors": []}	f	{}	\N	\N	\N
e4d550d0-b2d1-4606-a953-69503e61764b	c6b2570c-c115-4931-9f63-a83972769724	2023-03-07 10:49:26.277499+01	2023-03-07 10:49:34.178384+01	2023-03-07 10:49:26.273467+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	7bf685d1-ebbc-4a9b-bd7b-61915163c23a	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	c6b2570c-c115-4931-9f63-a83972769724	2023-03-07 10:49:21.44991+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	c6b2570c-c115-4931-9f63-a83972769724	2023-03-07 10:49:33.996516+01	t	t	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
9d007807-af23-4f30-8c23-9cb56990b254	dev-2	8fd0f067-722a-4d14-9f6e-40f2a87a23fe			{"auto_full_compile": ""}	0	f		
c6b2570c-c115-4931-9f63-a83972769724	dev-1	8fd0f067-722a-4d14-9f6e-40f2a87a23fe			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
-- Data for Name: inmanta_user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inmanta_user (id, username, password_hash, auth_method) FROM stdin;
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
8fd0f067-722a-4d14-9f6e-40f2a87a23fe	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
21a9eb1c-454b-43dd-a4c7-88eb29efca9d	2023-03-07 10:49:12.30558+01	2023-03-07 10:49:12.306777+01		Init		Using extra environment variables during compile \n	0	aa3df1f3-6a35-4ad2-9009-e804e54d1d40
f799d9fe-0b67-40e5-93c5-271e087f6bad	2023-03-07 10:49:12.307094+01	2023-03-07 10:49:12.31396+01		Creating venv			0	aa3df1f3-6a35-4ad2-9009-e804e54d1d40
fda991db-2b12-4349-963f-ad051780b252	2023-03-07 10:49:12.320323+01	2023-03-07 10:49:12.597869+01	/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.3.0.dev0\nNot uninstalling inmanta-core at /home/florent/Desktop/inmanta-core/src, outside environment /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	aa3df1f3-6a35-4ad2-9009-e804e54d1d40
0d489f69-93e2-442d-9a9c-d4693a4c3a7a	2023-03-07 10:49:12.599167+01	2023-03-07 10:49:20.946363+01	/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.1.4 on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.1.4 in /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000078 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.module           INFO    Checking out 4.1.4 on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator~=1.3 Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (1.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/florent/Desktop/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (39.0.1)\ninmanta.pip              DEBUG   Collecting cryptography<40,>=36\ninmanta.pip              DEBUG   Using cached cryptography-39.0.2-cp36-abi3-manylinux_2_28_x86_64.whl (4.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Collecting more-itertools<10,>=8\ninmanta.pip              DEBUG   Using cached more_itertools-9.1.0-py3-none-any.whl (54 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Collecting pip>=21.3\ninmanta.pip              DEBUG   Using cached pip-23.0.1-py3-none-any.whl (2.1 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0\ninmanta.pip              DEBUG   Using cached python_slugify-8.0.1-py2.py3-none-any.whl (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.14.0)\ninmanta.pip              DEBUG   Collecting zipp>=0.5\ninmanta.pip              DEBUG   Using cached zipp-3.15.0-py3-none-any.whl (6.8 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.0.1)\ninmanta.pip              DEBUG   Collecting charset-normalizer<4,>=2\ninmanta.pip              DEBUG   Using cached charset_normalizer-3.1.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (199 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Installing collected packages: zipp, python-slugify, pip, more-itertools, charset-normalizer, cryptography\ninmanta.pip              DEBUG   Attempting uninstall: zipp\ninmanta.pip              DEBUG   Found existing installation: zipp 3.14.0\ninmanta.pip              DEBUG   Not uninstalling zipp at /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages, outside environment /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env\ninmanta.pip              DEBUG   Can't uninstall 'zipp'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages, outside environment /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 23.0\ninmanta.pip              DEBUG   Not uninstalling pip at /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages, outside environment /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 9.0.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages, outside environment /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: charset-normalizer\ninmanta.pip              DEBUG   Found existing installation: charset-normalizer 3.0.1\ninmanta.pip              DEBUG   Not uninstalling charset-normalizer at /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages, outside environment /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env\ninmanta.pip              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cryptography\ninmanta.pip              DEBUG   Found existing installation: cryptography 39.0.1\ninmanta.pip              DEBUG   Not uninstalling cryptography at /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages, outside environment /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env\ninmanta.pip              DEBUG   Can't uninstall 'cryptography'. No files were found to uninstall.\ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   pyadr 0.19.0 requires python-slugify<7,>=6, but you have python-slugify 8.0.1 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed charset-normalizer-3.1.0 cryptography-39.0.2 more-itertools-9.1.0 pip-23.0.1 python-slugify-8.0.1 zipp-3.15.0\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   [notice] A new release of pip is available: 23.0 -> 23.0.1\ninmanta.pip              DEBUG   [notice] To update, run: /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m pip install --upgrade pip\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000043 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.module           INFO    Checking out 4.1.4 on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator~=1.3 Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (1.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/florent/Desktop/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (39.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	aa3df1f3-6a35-4ad2-9009-e804e54d1d40
7b54381a-68e4-4090-9c8b-ae816a78cfa6	2023-03-07 10:49:20.947819+01	2023-03-07 10:49:23.532644+01	/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m inmanta.app -vvv export -X -e c6b2570c-c115-4931-9f63-a83972769724 --server_address localhost --server_port 40701 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpegp9qn4q --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004124 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000089 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001998)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001585)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000236)\ninmanta.execute.schedulerINFO    Total compilation time 0.003970\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40701/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40701/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40701/api/v1/file/eed9c79c4b247a7a7452d795605e27a495863a9e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40701/api/v1/file/8075baf6360169f7ea8e2bfe877789a37de43617\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40701/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40701/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40701/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40701/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	aa3df1f3-6a35-4ad2-9009-e804e54d1d40
03d91dd3-7c47-4672-aeee-a45f0b96c7df	2023-03-07 10:49:26.277875+01	2023-03-07 10:49:26.278825+01		Init		Using extra environment variables during compile \n	0	e4d550d0-b2d1-4606-a953-69503e61764b
0393ea4d-05cb-4c37-a7c0-1cc147bfa765	2023-03-07 10:49:26.284144+01	2023-03-07 10:49:26.57984+01	/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.3.0.dev0\nNot uninstalling inmanta-core at /home/florent/Desktop/inmanta-core/src, outside environment /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	e4d550d0-b2d1-4606-a953-69503e61764b
1a0dc7e9-c44d-4b4a-a7ac-11f78c3bdcc7	2023-03-07 10:49:26.58082+01	2023-03-07 10:49:33.4932+01	/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000067 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.module           INFO    Checking out 4.1.4 on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator~=1.3 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (1.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/florent/Desktop/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (39.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.1.0)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000046 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.module           INFO    Checking out 4.1.4 on /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator~=1.3 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (1.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/florent/Desktop/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (39.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/my-new-core-venv/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.14)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	e4d550d0-b2d1-4606-a953-69503e61764b
b587e3ab-928c-41f1-8b00-6347f6bdb3e7	2023-03-07 10:49:33.494428+01	2023-03-07 10:49:34.17769+01	/tmp/tmptuotattk/server/environments/c6b2570c-c115-4931-9f63-a83972769724/.env/bin/python -m inmanta.app -vvv export -X -e c6b2570c-c115-4931-9f63-a83972769724 --server_address localhost --server_port 40701 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpyull19im --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004121 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000116 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002100)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001537)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000217)\ninmanta.execute.schedulerINFO    Total compilation time 0.003989\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40701/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40701/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40701/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40701/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40701/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	e4d550d0-b2d1-4606-a953-69503e61764b
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
c6b2570c-c115-4931-9f63-a83972769724	1	std::AgentConfig[internal,agentname=localhost]	internal	2023-03-07 10:49:25.106517+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
c6b2570c-c115-4931-9f63-a83972769724	1	std::File[localhost,path=/tmp/test]	localhost	2023-03-07 10:49:26.174553+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
c6b2570c-c115-4931-9f63-a83972769724	2	std::AgentConfig[internal,agentname=localhost]	internal	2023-03-07 10:49:34.289173+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
c6b2570c-c115-4931-9f63-a83972769724	2	std::File[localhost,path=/tmp/test]	localhost	2023-03-07 10:49:34.1293+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	deploying	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
c6bb9f21-9eec-4033-9530-fcc97818f34d	store	2023-03-07 10:49:21.44882+01	2023-03-07 10:49:22.511593+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2023-03-07T10:49:22.511614+01:00\\"}"}	\N	\N	\N	c6b2570c-c115-4931-9f63-a83972769724	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
aca12f08-8a47-428c-b1b7-1cc5788f0705	pull	2023-03-07 10:49:23.423238+01	2023-03-07 10:49:23.969393+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-03-07T10:49:23.969412+01:00\\"}"}	\N	\N	\N	c6b2570c-c115-4931-9f63-a83972769724	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
dbdd3db3-cf2f-4f0c-afc9-c07ce5970858	pull	2023-03-07 10:49:26.116801+01	2023-03-07 10:49:26.117988+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-03-07T10:49:26.117996+01:00\\"}"}	\N	\N	\N	c6b2570c-c115-4931-9f63-a83972769724	1	{"std::File[localhost,path=/tmp/test],v=1"}
699d8616-3595-46dc-8576-ff0610b6a737	deploy	2023-03-07 10:49:24.549873+01	2023-03-07 10:49:25.106517+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-03-07 10:49:23+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-03-07 10:49:23+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"bdfbd02c-48e4-4064-8ccc-0689b083e073\\"}, \\"timestamp\\": \\"2023-03-07T10:49:24.547091+01:00\\"}","{\\"msg\\": \\"Start deploy bdfbd02c-48e4-4064-8ccc-0689b083e073 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"bdfbd02c-48e4-4064-8ccc-0689b083e073\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-03-07T10:49:25.092357+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-03-07T10:49:25.093615+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-03-07T10:49:25.098015+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy bdfbd02c-48e4-4064-8ccc-0689b083e073\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"bdfbd02c-48e4-4064-8ccc-0689b083e073\\"}, \\"timestamp\\": \\"2023-03-07T10:49:25.102552+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	c6b2570c-c115-4931-9f63-a83972769724	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
530932a8-6874-4774-948d-031bdcd40031	deploy	2023-03-07 10:49:26.165075+01	2023-03-07 10:49:26.174553+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2023-03-07 10:49:26+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2023-03-07 10:49:26+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"a1d3b671-abcd-40f1-852f-c78bde58769c\\"}, \\"timestamp\\": \\"2023-03-07T10:49:26.159211+01:00\\"}","{\\"msg\\": \\"Start deploy a1d3b671-abcd-40f1-852f-c78bde58769c of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"a1d3b671-abcd-40f1-852f-c78bde58769c\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-03-07T10:49:26.168251+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-03-07T10:49:26.168995+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-03-07T10:49:26.171199+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 935, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmptuotattk/c6b2570c-c115-4931-9f63-a83972769724/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-03-07T10:49:26.171768+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy a1d3b671-abcd-40f1-852f-c78bde58769c\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"a1d3b671-abcd-40f1-852f-c78bde58769c\\"}, \\"timestamp\\": \\"2023-03-07T10:49:26.172071+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	c6b2570c-c115-4931-9f63-a83972769724	1	{"std::File[localhost,path=/tmp/test],v=1"}
4a98582e-af0f-4963-8a12-a3925ffc3c91	store	2023-03-07 10:49:33.996324+01	2023-03-07 10:49:33.997943+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2023-03-07T10:49:33.997952+01:00\\"}"}	\N	\N	\N	c6b2570c-c115-4931-9f63-a83972769724	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
683c6ffe-e04a-4cf8-8a71-8111efeb4b70	deploy	2023-03-07 10:49:34.044714+01	2023-03-07 10:49:34.044714+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-03-07T09:49:34.044714+00:00\\"}"}	deployed	\N	nochange	c6b2570c-c115-4931-9f63-a83972769724	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
b1f3b62a-7d32-4f0c-ba66-c1f5c8731974	pull	2023-03-07 10:49:34.105853+01	2023-03-07 10:49:34.106243+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-03-07T10:49:34.107180+01:00\\"}"}	\N	\N	\N	c6b2570c-c115-4931-9f63-a83972769724	2	{"std::File[localhost,path=/tmp/test],v=2"}
8e2f6564-1cbe-426c-a8d2-bbeb246a0cff	deploy	2023-03-07 10:49:34.106422+01	2023-03-07 10:49:34.106422+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-03-07T09:49:34.106422+00:00\\"}"}	deployed	\N	nochange	c6b2570c-c115-4931-9f63-a83972769724	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
24053d91-6f35-4894-b0c0-a0c1c7a439ae	deploy	2023-03-07 10:49:34.289173+01	2023-03-07 10:49:34.289173+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-03-07T09:49:34.289173+00:00\\"}"}	deployed	\N	nochange	c6b2570c-c115-4931-9f63-a83972769724	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
22df6dce-baed-4d77-9cf2-00d678eaf6d6	pull	2023-03-07 10:49:34.354519+01	2023-03-07 10:49:34.355595+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-03-07T10:49:34.355606+01:00\\"}"}	\N	\N	\N	c6b2570c-c115-4931-9f63-a83972769724	2	{"std::File[localhost,path=/tmp/test],v=2"}
4addf09a-79dd-47aa-9777-a62b99089c31	deploy	2023-03-07 10:49:34.363431+01	\N	{"{\\"msg\\": \\"Resource deploy started on agent localhost, setting status to deploying\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-03-07T10:49:34.363440+01:00\\"}"}	deploying	\N	\N	c6b2570c-c115-4931-9f63-a83972769724	2	{"std::File[localhost,path=/tmp/test],v=2"}
9065ec5b-0b89-4a27-9786-0ae2a1bcb5a9	deploy	2023-03-07 10:49:34.121276+01	2023-03-07 10:49:34.1293+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"ef721845-af7e-416e-b65c-201016dfdd58\\"}, \\"timestamp\\": \\"2023-03-07T10:49:34.119073+01:00\\"}","{\\"msg\\": \\"Start deploy ef721845-af7e-416e-b65c-201016dfdd58 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"ef721845-af7e-416e-b65c-201016dfdd58\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-03-07T10:49:34.122884+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-03-07T10:49:34.123732+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-03-07T10:49:34.125897+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 935, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmptuotattk/c6b2570c-c115-4931-9f63-a83972769724/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-03-07T10:49:34.126130+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy ef721845-af7e-416e-b65c-201016dfdd58\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"ef721845-af7e-416e-b65c-201016dfdd58\\"}, \\"timestamp\\": \\"2023-03-07T10:49:34.126371+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	c6b2570c-c115-4931-9f63-a83972769724	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
c6b2570c-c115-4931-9f63-a83972769724	c6bb9f21-9eec-4033-9530-fcc97818f34d	std::File[localhost,path=/tmp/test]	1
c6b2570c-c115-4931-9f63-a83972769724	c6bb9f21-9eec-4033-9530-fcc97818f34d	std::AgentConfig[internal,agentname=localhost]	1
c6b2570c-c115-4931-9f63-a83972769724	aca12f08-8a47-428c-b1b7-1cc5788f0705	std::AgentConfig[internal,agentname=localhost]	1
c6b2570c-c115-4931-9f63-a83972769724	699d8616-3595-46dc-8576-ff0610b6a737	std::AgentConfig[internal,agentname=localhost]	1
c6b2570c-c115-4931-9f63-a83972769724	dbdd3db3-cf2f-4f0c-afc9-c07ce5970858	std::File[localhost,path=/tmp/test]	1
c6b2570c-c115-4931-9f63-a83972769724	530932a8-6874-4774-948d-031bdcd40031	std::File[localhost,path=/tmp/test]	1
c6b2570c-c115-4931-9f63-a83972769724	4a98582e-af0f-4963-8a12-a3925ffc3c91	std::File[localhost,path=/tmp/test]	2
c6b2570c-c115-4931-9f63-a83972769724	4a98582e-af0f-4963-8a12-a3925ffc3c91	std::AgentConfig[internal,agentname=localhost]	2
c6b2570c-c115-4931-9f63-a83972769724	683c6ffe-e04a-4cf8-8a71-8111efeb4b70	std::AgentConfig[internal,agentname=localhost]	2
c6b2570c-c115-4931-9f63-a83972769724	b1f3b62a-7d32-4f0c-ba66-c1f5c8731974	std::File[localhost,path=/tmp/test]	2
c6b2570c-c115-4931-9f63-a83972769724	9065ec5b-0b89-4a27-9786-0ae2a1bcb5a9	std::File[localhost,path=/tmp/test]	2
c6b2570c-c115-4931-9f63-a83972769724	8e2f6564-1cbe-426c-a8d2-bbeb246a0cff	std::AgentConfig[internal,agentname=localhost]	2
c6b2570c-c115-4931-9f63-a83972769724	24053d91-6f35-4894-b0c0-a0c1c7a439ae	std::AgentConfig[internal,agentname=localhost]	2
c6b2570c-c115-4931-9f63-a83972769724	22df6dce-baed-4d77-9cf2-00d678eaf6d6	std::File[localhost,path=/tmp/test]	2
c6b2570c-c115-4931-9f63-a83972769724	4addf09a-79dd-47aa-9777-a62b99089c31	std::File[localhost,path=/tmp/test]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070}
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
-- Name: resource_environment_agent_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_agent_idx ON public.resource USING btree (environment, agent);


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

