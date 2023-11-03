--
-- PostgreSQL database dump
--

-- Dumped from database version 14.3
-- Dumped by pg_dump version 14.3

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
    partial_base integer,
    is_suitable_for_partial_compiles boolean NOT NULL
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
66988a20-8985-4870-96bb-9ea18fc4d931	localhost	2023-04-06 14:30:19.595683+02	f	204bf80c-db78-4801-8733-45192da167b7	\N
66988a20-8985-4870-96bb-9ea18fc4d931	internal	2023-04-06 14:30:21.03937+02	f	6e262b08-6067-4e11-9189-c4c29ec94ae4	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
6e262b08-6067-4e11-9189-c4c29ec94ae4	cb06f0ee-d476-11ed-93be-84144dfe5579	internal	\N	66988a20-8985-4870-96bb-9ea18fc4d931
204bf80c-db78-4801-8733-45192da167b7	cb06f0ee-d476-11ed-93be-84144dfe5579	localhost	\N	66988a20-8985-4870-96bb-9ea18fc4d931
a0ff73ad-2cbb-4a9a-a7f2-adc6043eca99	caaa06ea-d476-11ed-954d-84144dfe5579	internal	2023-04-06 14:30:21.03937+02	66988a20-8985-4870-96bb-9ea18fc4d931
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-inmanta-laptop	66988a20-8985-4870-96bb-9ea18fc4d931	2023-04-06 14:30:18.987245+02	2023-04-06 14:30:19.03889+02	2023-04-06 14:30:21.03937+02	caaa06ea-d476-11ed-954d-84144dfe5579
arnaud-inmanta-laptop	66988a20-8985-4870-96bb-9ea18fc4d931	2023-04-06 14:30:19.595683+02	2023-04-06 14:30:27.558354+02	\N	cb06f0ee-d476-11ed-93be-84144dfe5579
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
66988a20-8985-4870-96bb-9ea18fc4d931	std::Service	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::File	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::Directory	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::Package	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::Symlink	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::testing::NullResource	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::AgentConfig	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::Service	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::File	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::Directory	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::Package	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::Symlink	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::testing::NullResource	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
66988a20-8985-4870-96bb-9ea18fc4d931	std::AgentConfig	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
fae10175-4c98-482c-ab67-d70436b4d6da	66988a20-8985-4870-96bb-9ea18fc4d931	2023-04-06 14:30:10.25698+02	2023-04-06 14:30:19.069244+02	2023-04-06 14:30:10.248945+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	868994f2-e672-4796-b9f6-df7c9585e534	t	\N	{"errors": []}	f	{}	\N	\N	\N
049364cf-52bb-4485-905b-d0ef11277fa6	66988a20-8985-4870-96bb-9ea18fc4d931	2023-04-06 14:30:19.6716+02	2023-04-06 14:30:27.518079+02	2023-04-06 14:30:19.662084+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	5fb68ae3-288a-440e-b4c3-56a3f81e2d71	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles) FROM stdin;
1	66988a20-8985-4870-96bb-9ea18fc4d931	2023-04-06 14:30:18.56932+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
2	66988a20-8985-4870-96bb-9ea18fc4d931	2023-04-06 14:30:27.428927+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
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
46545d4a-3072-4b7f-bc41-9f3cb07d85cb	dev-2	43a7be05-b6f4-4bde-8c39-9def8356dc20			{"auto_full_compile": ""}	0	f		
66988a20-8985-4870-96bb-9ea18fc4d931	dev-1	43a7be05-b6f4-4bde-8c39-9def8356dc20			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
21372b34-fa49-4cd3-a767-687a9a6c599a	dev-3	43a7be05-b6f4-4bde-8c39-9def8356dc20			{"purge_on_delete": true, "auto_full_compile": ""}	0	f		
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
43a7be05-b6f4-4bde-8c39-9def8356dc20	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
c508ed94-8b84-40c7-95c3-c761402e5fc8	2023-04-06 14:30:10.257341+02	2023-04-06 14:30:10.258392+02		Init		Using extra environment variables during compile \n	0	fae10175-4c98-482c-ab67-d70436b4d6da
cf914630-2554-43f5-8849-72f168973d9c	2023-04-06 14:30:10.258676+02	2023-04-06 14:30:10.259591+02		Creating venv			0	fae10175-4c98-482c-ab67-d70436b4d6da
db083bc3-6566-478b-af44-c51a4bd40b17	2023-04-06 14:30:10.264317+02	2023-04-06 14:30:10.530199+02	/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.3.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	fae10175-4c98-482c-ab67-d70436b4d6da
7a7194f4-6e39-4731-8f9f-2bec7006cea3	2023-04-06 14:30:10.531345+02	2023-04-06 14:30:17.974813+02	/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.1.6 on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.1.6 in /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000127 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.module           INFO    Checking out 4.1.6 on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.7)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<41,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (40.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0\ninmanta.pip              DEBUG   Using cached python_slugify-8.0.1-py2.py3-none-any.whl (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<41,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<41,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.15)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   pyadr 0.19.0 requires python-slugify<7,>=6, but you have python-slugify 8.0.1 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed python-slugify-8.0.1\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000046 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.module           INFO    Checking out 4.1.6 on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.7)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<41,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (40.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<41,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<41,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.15)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	fae10175-4c98-482c-ab67-d70436b4d6da
2aa376cd-339e-4f83-a9e9-e80562a43c21	2023-04-06 14:30:17.976023+02	2023-04-06 14:30:19.06842+02	/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m inmanta.app -vvv export -X -e 66988a20-8985-4870-96bb-9ea18fc4d931 --server_address localhost --server_port 36333 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpedoek81o --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004623 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000094 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.6\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002486)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001759)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000246)\ninmanta.execute.schedulerINFO    Total compilation time 0.004674\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36333/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36333/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36333/api/v1/file/f20255abb8beb130e89ef3bdae958974f15163ed\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36333/api/v1/file/eed9c79c4b247a7a7452d795605e27a495863a9e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36333/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36333/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36333/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1 in resource set \ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1 in resource set \ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36333/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	fae10175-4c98-482c-ab67-d70436b4d6da
51c77a28-7fdf-41ac-90e8-35da002e863c	2023-04-06 14:30:19.67194+02	2023-04-06 14:30:19.672939+02		Init		Using extra environment variables during compile \n	0	049364cf-52bb-4485-905b-d0ef11277fa6
ddedc9be-cc54-45ac-bc8b-fdc81d0d11ed	2023-04-06 14:30:19.677874+02	2023-04-06 14:30:19.943825+02	/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.3.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	049364cf-52bb-4485-905b-d0ef11277fa6
36ef7198-b2f5-47ce-be63-03e5f0904c41	2023-04-06 14:30:19.944831+02	2023-04-06 14:30:26.869895+02	/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000072 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.module           INFO    Checking out 4.1.6 on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator~=1.3 Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.7)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<41,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (40.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<41,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<41,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.15)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.1.0)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000049 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.module           INFO    Checking out 4.1.6 on /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator~=1.3 Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" inmanta-core==8.3.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.7)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.3.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<41,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (40.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (23.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.3.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<41,>=36->inmanta-core==8.3.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.3.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.3.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.3.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<41,>=36->inmanta-core==8.3.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (1.26.15)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.3.0.dev0) (2022.12.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	049364cf-52bb-4485-905b-d0ef11277fa6
670d4df5-97ed-4c1c-8577-13594abdf15c	2023-04-06 14:30:26.870889+02	2023-04-06 14:30:27.516998+02	/tmp/tmp57pa8yad/server/environments/66988a20-8985-4870-96bb-9ea18fc4d931/.env/bin/python -m inmanta.app -vvv export -X -e 66988a20-8985-4870-96bb-9ea18fc4d931 --server_address localhost --server_port 36333 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp8wuz6dxv --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004399 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000089 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.6\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002352)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001611)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000240)\ninmanta.execute.schedulerINFO    Total compilation time 0.004353\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36333/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36333/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36333/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:36333/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2 in resource set \ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2 in resource set \ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:36333/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	049364cf-52bb-4485-905b-d0ef11277fa6
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
66988a20-8985-4870-96bb-9ea18fc4d931	1	std::File[localhost,path=/tmp/test]	localhost	2023-04-06 14:30:19.64104+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
66988a20-8985-4870-96bb-9ea18fc4d931	1	std::AgentConfig[internal,agentname=localhost]	internal	2023-04-06 14:30:21.068281+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
66988a20-8985-4870-96bb-9ea18fc4d931	2	std::File[localhost,path=/tmp/test]	localhost	2023-04-06 14:30:27.480964+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
66988a20-8985-4870-96bb-9ea18fc4d931	2	std::AgentConfig[internal,agentname=localhost]	internal	2023-04-06 14:30:27.54+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deploying	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
b8a786f3-7696-46f7-93da-f599a1ed061c	store	2023-04-06 14:30:18.569258+02	2023-04-06 14:30:18.575556+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2023-04-06T14:30:18.575568+02:00\\"}"}	\N	\N	\N	66988a20-8985-4870-96bb-9ea18fc4d931	1	{"std::AgentConfig[internal,agentname=localhost],v=1","std::File[localhost,path=/tmp/test],v=1"}
17d6db66-4b79-42d0-a40d-584e7893030b	pull	2023-04-06 14:30:18.994129+02	2023-04-06 14:30:18.997961+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-04-06T14:30:18.997980+02:00\\"}"}	\N	\N	\N	66988a20-8985-4870-96bb-9ea18fc4d931	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
ef3088ee-9413-417c-aa1b-ec20b62fe131	deploy	2023-04-06 14:30:19.023476+02	2023-04-06 14:30:19.038158+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-04-06 14:30:18+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-04-06 14:30:18+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b04c8b11-7c6b-446e-98a0-7b61de12a964\\"}, \\"timestamp\\": \\"2023-04-06T14:30:19.020413+02:00\\"}","{\\"msg\\": \\"Start deploy b04c8b11-7c6b-446e-98a0-7b61de12a964 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"b04c8b11-7c6b-446e-98a0-7b61de12a964\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-04-06T14:30:19.025348+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-04-06T14:30:19.026185+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-04-06T14:30:19.029577+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy b04c8b11-7c6b-446e-98a0-7b61de12a964\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b04c8b11-7c6b-446e-98a0-7b61de12a964\\"}, \\"timestamp\\": \\"2023-04-06T14:30:19.032833+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	66988a20-8985-4870-96bb-9ea18fc4d931	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
b60059e2-a4b4-418e-b2f3-e87c9f22e0f9	deploy	2023-04-06 14:30:19.161231+02	2023-04-06 14:30:19.161231+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-04-06T12:30:19.161231+00:00\\"}"}	deployed	\N	nochange	66988a20-8985-4870-96bb-9ea18fc4d931	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
e0248ea8-04a5-4c16-85c3-99f4671f8354	pull	2023-04-06 14:30:19.602819+02	2023-04-06 14:30:19.607928+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-04-06T14:30:19.607938+02:00\\"}"}	\N	\N	\N	66988a20-8985-4870-96bb-9ea18fc4d931	1	{"std::File[localhost,path=/tmp/test],v=1"}
49e9636e-b7a1-4a2b-b06f-b90120ae0df3	deploy	2023-04-06 14:30:19.632853+02	2023-04-06 14:30:19.64104+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2023-04-06 14:30:19+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2023-04-06 14:30:19+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"421119f0-5e00-48e5-bdae-c98f5b59dfac\\"}, \\"timestamp\\": \\"2023-04-06T14:30:19.630713+02:00\\"}","{\\"msg\\": \\"Start deploy 421119f0-5e00-48e5-bdae-c98f5b59dfac of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"421119f0-5e00-48e5-bdae-c98f5b59dfac\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-04-06T14:30:19.634746+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-04-06T14:30:19.635543+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-04-06T14:30:19.637980+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 935, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp57pa8yad/66988a20-8985-4870-96bb-9ea18fc4d931/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-04-06T14:30:19.638390+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 421119f0-5e00-48e5-bdae-c98f5b59dfac\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"421119f0-5e00-48e5-bdae-c98f5b59dfac\\"}, \\"timestamp\\": \\"2023-04-06T14:30:19.638565+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	66988a20-8985-4870-96bb-9ea18fc4d931	1	{"std::File[localhost,path=/tmp/test],v=1"}
5c8a6e23-b829-4fc5-ba5e-7b0bb0e012f9	pull	2023-04-06 14:30:21.048053+02	2023-04-06 14:30:21.049595+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-04-06T14:30:21.049606+02:00\\"}"}	\N	\N	\N	66988a20-8985-4870-96bb-9ea18fc4d931	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c774b080-5162-49b4-a21f-42ab03e60095	store	2023-04-06 14:30:27.428871+02	2023-04-06 14:30:27.430041+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2023-04-06T14:30:27.430049+02:00\\"}"}	\N	\N	\N	66988a20-8985-4870-96bb-9ea18fc4d931	2	{"std::AgentConfig[internal,agentname=localhost],v=2","std::File[localhost,path=/tmp/test],v=2"}
7352cb31-19bd-4d9a-ae71-782636842941	deploy	2023-04-06 14:30:27.431595+02	2023-04-06 14:30:27.431595+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-04-06T12:30:27.431595+00:00\\"}"}	deployed	\N	nochange	66988a20-8985-4870-96bb-9ea18fc4d931	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
81964250-f943-42ea-a951-f39c69ef10ae	deploy	2023-04-06 14:30:27.448838+02	2023-04-06 14:30:27.448838+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-04-06T12:30:27.448838+00:00\\"}"}	deployed	\N	nochange	66988a20-8985-4870-96bb-9ea18fc4d931	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
c6dfaf75-3836-4a80-a0a3-5cb65d64097f	pull	2023-04-06 14:30:27.558528+02	2023-04-06 14:30:27.55961+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-04-06T14:30:27.559617+02:00\\"}"}	\N	\N	\N	66988a20-8985-4870-96bb-9ea18fc4d931	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
a114bcf7-e610-4a6f-babf-d893e41342d7	deploy	2023-04-06 14:30:27.579124+02	\N	{"{\\"msg\\": \\"Resource deploy started on agent internal, setting status to deploying\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-04-06T14:30:27.579138+02:00\\"}"}	deploying	\N	\N	66988a20-8985-4870-96bb-9ea18fc4d931	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
162cfc1a-e372-461e-8805-0bdf57b027e2	deploy	2023-04-06 14:30:21.059232+02	2023-04-06 14:30:21.068281+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-04-06 14:30:21+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-04-06 14:30:21+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"c5c8bd14-005d-44de-9e11-81b79ee30ff8\\"}, \\"timestamp\\": \\"2023-04-06T14:30:21.056366+02:00\\"}","{\\"msg\\": \\"Start deploy c5c8bd14-005d-44de-9e11-81b79ee30ff8 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"c5c8bd14-005d-44de-9e11-81b79ee30ff8\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-04-06T14:30:21.060539+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-04-06T14:30:21.061797+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy c5c8bd14-005d-44de-9e11-81b79ee30ff8\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"c5c8bd14-005d-44de-9e11-81b79ee30ff8\\"}, \\"timestamp\\": \\"2023-04-06T14:30:21.065643+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	66988a20-8985-4870-96bb-9ea18fc4d931	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
de136ed7-561a-4f18-9c0c-59d0c0d005c2	pull	2023-04-06 14:30:27.448457+02	2023-04-06 14:30:27.449196+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-04-06T14:30:27.453496+02:00\\"}"}	\N	\N	\N	66988a20-8985-4870-96bb-9ea18fc4d931	2	{"std::File[localhost,path=/tmp/test],v=2"}
961f9d10-cf4d-4aa5-8849-2f8d557d7cf4	deploy	2023-04-06 14:30:27.473342+02	2023-04-06 14:30:27.480964+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"37cebb53-4c70-486b-adfd-1233cc857d44\\"}, \\"timestamp\\": \\"2023-04-06T14:30:27.470936+02:00\\"}","{\\"msg\\": \\"Start deploy 37cebb53-4c70-486b-adfd-1233cc857d44 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"37cebb53-4c70-486b-adfd-1233cc857d44\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-04-06T14:30:27.475127+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-04-06T14:30:27.475559+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-04-06T14:30:27.477816+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 935, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp57pa8yad/66988a20-8985-4870-96bb-9ea18fc4d931/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-04-06T14:30:27.478026+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 37cebb53-4c70-486b-adfd-1233cc857d44\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"37cebb53-4c70-486b-adfd-1233cc857d44\\"}, \\"timestamp\\": \\"2023-04-06T14:30:27.478201+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	66988a20-8985-4870-96bb-9ea18fc4d931	2	{"std::File[localhost,path=/tmp/test],v=2"}
2b18c79c-f99a-4037-bcf4-cc61394d3c0a	deploy	2023-04-06 14:30:27.54+02	2023-04-06 14:30:27.54+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-04-06T12:30:27.540000+00:00\\"}"}	deployed	\N	nochange	66988a20-8985-4870-96bb-9ea18fc4d931	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
66988a20-8985-4870-96bb-9ea18fc4d931	b8a786f3-7696-46f7-93da-f599a1ed061c	std::AgentConfig[internal,agentname=localhost]	1
66988a20-8985-4870-96bb-9ea18fc4d931	b8a786f3-7696-46f7-93da-f599a1ed061c	std::File[localhost,path=/tmp/test]	1
66988a20-8985-4870-96bb-9ea18fc4d931	17d6db66-4b79-42d0-a40d-584e7893030b	std::AgentConfig[internal,agentname=localhost]	1
66988a20-8985-4870-96bb-9ea18fc4d931	ef3088ee-9413-417c-aa1b-ec20b62fe131	std::AgentConfig[internal,agentname=localhost]	1
66988a20-8985-4870-96bb-9ea18fc4d931	b60059e2-a4b4-418e-b2f3-e87c9f22e0f9	std::AgentConfig[internal,agentname=localhost]	1
66988a20-8985-4870-96bb-9ea18fc4d931	e0248ea8-04a5-4c16-85c3-99f4671f8354	std::File[localhost,path=/tmp/test]	1
66988a20-8985-4870-96bb-9ea18fc4d931	49e9636e-b7a1-4a2b-b06f-b90120ae0df3	std::File[localhost,path=/tmp/test]	1
66988a20-8985-4870-96bb-9ea18fc4d931	5c8a6e23-b829-4fc5-ba5e-7b0bb0e012f9	std::AgentConfig[internal,agentname=localhost]	1
66988a20-8985-4870-96bb-9ea18fc4d931	162cfc1a-e372-461e-8805-0bdf57b027e2	std::AgentConfig[internal,agentname=localhost]	1
66988a20-8985-4870-96bb-9ea18fc4d931	c774b080-5162-49b4-a21f-42ab03e60095	std::AgentConfig[internal,agentname=localhost]	2
66988a20-8985-4870-96bb-9ea18fc4d931	c774b080-5162-49b4-a21f-42ab03e60095	std::File[localhost,path=/tmp/test]	2
66988a20-8985-4870-96bb-9ea18fc4d931	7352cb31-19bd-4d9a-ae71-782636842941	std::AgentConfig[internal,agentname=localhost]	2
66988a20-8985-4870-96bb-9ea18fc4d931	81964250-f943-42ea-a951-f39c69ef10ae	std::AgentConfig[internal,agentname=localhost]	2
66988a20-8985-4870-96bb-9ea18fc4d931	de136ed7-561a-4f18-9c0c-59d0c0d005c2	std::File[localhost,path=/tmp/test]	2
66988a20-8985-4870-96bb-9ea18fc4d931	961f9d10-cf4d-4aa5-8849-2f8d557d7cf4	std::File[localhost,path=/tmp/test]	2
66988a20-8985-4870-96bb-9ea18fc4d931	2b18c79c-f99a-4037-bcf4-cc61394d3c0a	std::AgentConfig[internal,agentname=localhost]	2
66988a20-8985-4870-96bb-9ea18fc4d931	c6dfaf75-3836-4a80-a0a3-5cb65d64097f	std::AgentConfig[internal,agentname=localhost]	2
66988a20-8985-4870-96bb-9ea18fc4d931	a114bcf7-e610-4a6f-babf-d893e41342d7	std::AgentConfig[internal,agentname=localhost]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071}
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

