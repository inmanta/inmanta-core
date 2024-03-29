--
-- PostgreSQL database dump
--

-- Dumped from database version 13.11 (Ubuntu 13.11-1.pgdg20.04+1)
-- Dumped by pg_dump version 15.3 (Ubuntu 15.3-1.pgdg20.04+1)

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
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


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
-- Name: discoveredresource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discoveredresource (
    environment uuid NOT NULL,
    discovered_resource_id character varying NOT NULL,
    "values" jsonb NOT NULL,
    discovered_at timestamp with time zone NOT NULL
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
    resource_set character varying,
    last_success timestamp with time zone,
    last_produced_events timestamp with time zone
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
35707199-1500-4ff4-a853-51413de9e736	internal	2024-02-13 17:10:39.229635+01	f	83e8f272-35c7-45dd-a34e-ac729620f5f7	\N
35707199-1500-4ff4-a853-51413de9e736	localhost	2024-02-13 17:10:39.33642+01	f	739bfd0c-e35d-44c9-9cef-7217f1cb55fe	\N
35707199-1500-4ff4-a853-51413de9e736	agent2	\N	f	\N	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
83e8f272-35c7-45dd-a34e-ac729620f5f7	6dd5aacc-ca8a-11ee-b4ae-07906a822e36	internal	\N	35707199-1500-4ff4-a853-51413de9e736
739bfd0c-e35d-44c9-9cef-7217f1cb55fe	6dd5aacc-ca8a-11ee-b4ae-07906a822e36	localhost	\N	35707199-1500-4ff4-a853-51413de9e736
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:10:39.229635+01	2024-02-13 17:11:50.230396+01	\N	6dd5aacc-ca8a-11ee-b4ae-07906a822e36
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
35707199-1500-4ff4-a853-51413de9e736	std::Service	1	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::File	1	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Directory	1	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Package	1	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Symlink	1	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::testing::NullResource	1	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::AgentConfig	1	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Service	2	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::File	2	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Directory	2	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Package	2	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Symlink	2	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::testing::NullResource	2	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::AgentConfig	2	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Service	3	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::File	3	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Directory	3	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Package	3	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Symlink	3	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::testing::NullResource	3	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::AgentConfig	3	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Service	4	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::File	4	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Directory	4	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Package	4	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Symlink	4	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::testing::NullResource	4	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::AgentConfig	4	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::AgentConfig	5	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Directory	5	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::File	5	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Package	5	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Service	5	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::Symlink	5	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
35707199-1500-4ff4-a853-51413de9e736	std::testing::NullResource	5	{"2d9352edf3df574cbad78d9fa84bba6dbababf71": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "ece02f87d39aba7e8bd2d22f9439b50a92df1f7a": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
e151800c-383b-4522-b305-4ad903bcc76b	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:10:13.073133+01	2024-02-13 17:10:38.71573+01	2024-02-13 17:10:13.062754+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	ca00af9b-418e-4c84-add7-335986aef2be	t	\N	{"errors": []}	f	{}	\N	\N	\N
033fdf52-baaf-4699-bb3f-16801514b648	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:10:39.496932+01	2024-02-13 17:11:03.819944+01	2024-02-13 17:10:39.481315+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	0e041b06-7517-49fb-af07-caec5ad81fa4	t	\N	{"errors": []}	f	{}	\N	\N	\N
6b42437b-6d19-4824-aef6-1a50c24aabae	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:11:04.045439+01	2024-02-13 17:11:27.914814+01	2024-02-13 17:11:04.031252+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	3	0b8488d5-bbbf-474e-9169-4ba039a5011e	t	\N	{"errors": []}	f	{}	\N	\N	\N
62bf001f-db2a-4c23-a608-6de67bd6bf8d	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:11:28.034504+01	2024-02-13 17:11:50.682157+01	2024-02-13 17:11:28.029699+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	4	f62588e6-b87b-43a1-9569-993e6b31cea9	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles) FROM stdin;
1	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:10:38.637091+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
2	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:11:03.744064+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
3	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:11:27.839981+01	t	f	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
4	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:11:50.599445+01	f	f	pending	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
5	35707199-1500-4ff4-a853-51413de9e736	2024-02-13 17:11:50.802341+01	f	f	pending	\N	3	\N	\N	4	t
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at) FROM stdin;
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
2f6ffc72-7a13-4d4e-b766-42455a65acad	dev-2	94cdd49a-b124-438d-80b5-a6927320552c			{"auto_full_compile": ""}	0	f		
35707199-1500-4ff4-a853-51413de9e736	dev-1	94cdd49a-b124-438d-80b5-a6927320552c			{"auto_deploy": false, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "autostart_agent_deploy_interval": "0", "autostart_agent_repair_interval": "600", "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0}	5	f		
\.


--
-- Data for Name: environmentmetricsgauge; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricsgauge (environment, metric_name, "timestamp", count, category) FROM stdin;
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	1	deployed
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	1	failed
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	skipped
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	0	skipped
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	dry
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	0	dry
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	deployed
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	failed
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	deploying
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	0	deploying
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	available
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	0	available
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	cancelled
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	0	cancelled
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	undefined
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	0	undefined
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	skipped_for_undefined
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.resource_count	2024-02-13 17:11:13.025092+01	0	unavailable
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	0	skipped_for_undefined
35707199-1500-4ff4-a853-51413de9e736	resource.resource_count	2024-02-13 17:11:13.025092+01	0	unavailable
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.agent_count	2024-02-13 17:11:13.025092+01	0	down
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.agent_count	2024-02-13 17:11:13.025092+01	0	paused
2f6ffc72-7a13-4d4e-b766-42455a65acad	resource.agent_count	2024-02-13 17:11:13.025092+01	0	up
35707199-1500-4ff4-a853-51413de9e736	resource.agent_count	2024-02-13 17:11:13.025092+01	0	down
35707199-1500-4ff4-a853-51413de9e736	resource.agent_count	2024-02-13 17:11:13.025092+01	0	paused
35707199-1500-4ff4-a853-51413de9e736	resource.agent_count	2024-02-13 17:11:13.025092+01	2	up
\.


--
-- Data for Name: environmentmetricstimer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricstimer (environment, metric_name, "timestamp", count, value, category) FROM stdin;
35707199-1500-4ff4-a853-51413de9e736	orchestrator.compile_waiting_time	2024-02-13 17:11:13.025092+01	3	0.040183	__None__
35707199-1500-4ff4-a853-51413de9e736	orchestrator.compile_time	2024-02-13 17:11:13.025092+01	2	49.965609	__None__
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
94cdd49a-b124-438d-80b5-a6927320552c	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
a4c8399f-6efa-47ab-937e-8a9d30b95402	2024-02-13 17:10:13.073554+01	2024-02-13 17:10:13.074852+01		Init		Using extra environment variables during compile \n	0	e151800c-383b-4522-b305-4ad903bcc76b
2bd65b5e-1014-4e3a-a13f-c3801e3ab14f	2024-02-13 17:10:13.075188+01	2024-02-13 17:10:13.081965+01		Creating venv			0	e151800c-383b-4522-b305-4ad903bcc76b
1ae560b6-026e-48c2-b894-6fe537745bab	2024-02-13 17:10:13.086288+01	2024-02-13 17:10:13.425497+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	e151800c-383b-4522-b305-4ad903bcc76b
a5b55d56-5f12-4d3c-836a-6087e2ce7388	2024-02-13 17:11:50.060566+01	2024-02-13 17:11:50.68108+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m inmanta.app -vvv export -X -e 35707199-1500-4ff4-a853-51413de9e736 --server_address localhost --server_port 39061 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpq8chz0hn --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.109 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.0\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.005 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/codebatched/4\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=4 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=4 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.015 seconds\nexporter       DEBUG   The entire export command took 0.153 seconds\n	0	62bf001f-db2a-4c23-a608-6de67bd6bf8d
79b5d6d5-45cb-4637-a173-cc6ac7df40b3	2024-02-13 17:10:13.426518+01	2024-02-13 17:10:38.061275+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 5.1.0 in /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 pydantic<3,>=1.10 Jinja2<4,>=3.1 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (1.10.13)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0b6/a909df3192245/pydantic-2.6.1-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Collecting Jinja2<4,>=3.1\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/7d6/d50dd97d52cbc/Jinja2-3.1.3-py3-none-any.whl (133 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.0)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/4dc/bb62368e2800c/colorlog-6.8.2-py3-none-any.whl (11 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.0)\ninmanta.pip              DEBUG   Collecting importlib_metadata<8,>=4 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/480/5911c3a4ec7c3/importlib_metadata-7.0.1-py3-none-any.whl (23 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<11,>=8 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/686/b06abe565edfa/more_itertools-10.2.0-py3-none-any.whl (57 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.3.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/ba0/d021a166865d2/pip-24.0-py3-none-any.whl (2.1 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/646/b2b12df4295b4/pydantic-1.10.14-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.0.2)\ninmanta.pip              DEBUG   Collecting setuptools (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/c05/4629b81b946d6/setuptools-69.1.0-py3-none-any.whl (819 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.5)\ninmanta.pip              DEBUG   Collecting ruamel.yaml~=0.17 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/57b/53ba33def16c4/ruamel.yaml-0.18.6-py3-none-any.whl (117 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.14)\ninmanta.pip              DEBUG   Collecting types-python-dateutil>=2.8.10 (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/efb/bdc54590d0f16/types_python_dateutil-2.8.19.20240106-py3-none-any.whl (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: types-python-dateutil, setuptools, ruamel.yaml, pydantic, pip, more-itertools, Jinja2, importlib_metadata, colorlog\ninmanta.pip              DEBUG   Attempting uninstall: types-python-dateutil\ninmanta.pip              DEBUG   Found existing installation: types-python-dateutil 2.8.19.14\ninmanta.pip              DEBUG   Not uninstalling types-python-dateutil at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'types-python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: setuptools\ninmanta.pip              DEBUG   Found existing installation: setuptools 69.0.2\ninmanta.pip              DEBUG   Not uninstalling setuptools at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'setuptools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: ruamel.yaml\ninmanta.pip              DEBUG   Found existing installation: ruamel.yaml 0.18.5\ninmanta.pip              DEBUG   Not uninstalling ruamel-yaml at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'ruamel.yaml'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 1.10.13\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 23.3.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 10.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: Jinja2\ninmanta.pip              DEBUG   Found existing installation: Jinja2 3.1.2\ninmanta.pip              DEBUG   Not uninstalling jinja2 at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'Jinja2'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: importlib_metadata\ninmanta.pip              DEBUG   Found existing installation: importlib-metadata 7.0.0\ninmanta.pip              DEBUG   Not uninstalling importlib-metadata at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'importlib-metadata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.8.0\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   Successfully installed Jinja2-3.1.3 colorlog-6.8.2 importlib_metadata-7.0.1 more-itertools-10.2.0 pip-24.0 pydantic-1.10.14 ruamel.yaml-0.18.6 setuptools-69.1.0 types-python-dateutil-2.8.19.20240106\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   [notice] A new release of pip is available: 23.3.1 -> 24.0\ninmanta.pip              DEBUG   [notice] To update, run: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade pip\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 2 misses (50%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 pydantic<3,>=1.10 Jinja2<4,>=3.1 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0b6/a909df3192245/pydantic-2.6.1-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.20240106)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	e151800c-383b-4522-b305-4ad903bcc76b
5aa1f3be-07cf-4299-b56e-2217e3ea5cac	2024-02-13 17:10:38.062461+01	2024-02-13 17:10:38.714576+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m inmanta.app -vvv export -X -e 35707199-1500-4ff4-a853-51413de9e736 --server_address localhost --server_port 39061 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpdyyvqlnj --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.111 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.0\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/file/f20255abb8beb130e89ef3bdae958974f15163ed\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/file/ece02f87d39aba7e8bd2d22f9439b50a92df1f7a\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/file/2d9352edf3df574cbad78d9fa84bba6dbababf71\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/codebatched/1\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=1 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=1 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.035 seconds\nexporter       DEBUG   The entire export command took 0.176 seconds\n	0	e151800c-383b-4522-b305-4ad903bcc76b
4e9cfae6-3e02-4311-bb18-6e473b4e7e7b	2024-02-13 17:10:39.498077+01	2024-02-13 17:10:39.501043+01		Init		Using extra environment variables during compile \n	0	033fdf52-baaf-4699-bb3f-16801514b648
70434b8f-9ba1-4e71-bbc0-c77a3d0479ec	2024-02-13 17:11:04.053325+01	2024-02-13 17:11:04.37968+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6b42437b-6d19-4824-aef6-1a50c24aabae
c82c0979-793d-48c0-807c-bc3c83674fbb	2024-02-13 17:10:39.508405+01	2024-02-13 17:10:39.784849+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	033fdf52-baaf-4699-bb3f-16801514b648
36aeb0f4-c712-4951-8b73-064ddde4bcc6	2024-02-13 17:11:03.178787+01	2024-02-13 17:11:03.819103+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m inmanta.app -vvv export -X -e 35707199-1500-4ff4-a853-51413de9e736 --server_address localhost --server_port 39061 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpp4nf1a_l --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.110 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.0\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/codebatched/2\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=2 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=2 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.015 seconds\nexporter       DEBUG   The entire export command took 0.154 seconds\n	0	033fdf52-baaf-4699-bb3f-16801514b648
903efbf1-02b1-4a50-83d9-352f0a3192f9	2024-02-13 17:11:04.046741+01	2024-02-13 17:11:04.049833+01		Init		Using extra environment variables during compile \n	0	6b42437b-6d19-4824-aef6-1a50c24aabae
3b6cf42b-83a5-4062-8a2d-ae4d7ccd9a7d	2024-02-13 17:10:39.785695+01	2024-02-13 17:11:03.177617+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0b6/a909df3192245/pydantic-2.6.1-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.20240106)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0b6/a909df3192245/pydantic-2.6.1-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.20240106)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	033fdf52-baaf-4699-bb3f-16801514b648
1a356404-6e76-452d-9150-82c1d012fd1d	2024-02-13 17:11:28.040108+01	2024-02-13 17:11:28.334182+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	62bf001f-db2a-4c23-a608-6de67bd6bf8d
3ee375f6-8f7c-4c41-916f-5b04096ebafa	2024-02-13 17:11:04.380726+01	2024-02-13 17:11:27.278886+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0b6/a909df3192245/pydantic-2.6.1-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.20240106)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0b6/a909df3192245/pydantic-2.6.1-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.20240106)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	6b42437b-6d19-4824-aef6-1a50c24aabae
5a3f2fd8-f23b-41b4-818d-d19f0b4fafa7	2024-02-13 17:11:27.279886+01	2024-02-13 17:11:27.913845+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m inmanta.app -vvv export -X -e 35707199-1500-4ff4-a853-51413de9e736 --server_address localhost --server_port 39061 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpyf3y1l3f --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.108 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.0\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/codebatched/3\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39061/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=3 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=3 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39061/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.016 seconds\nexporter       DEBUG   The entire export command took 0.153 seconds\n	0	6b42437b-6d19-4824-aef6-1a50c24aabae
b2cfa3b9-6dd1-49f5-bdba-5b56eee6ee8e	2024-02-13 17:11:28.03488+01	2024-02-13 17:11:28.035585+01		Init		Using extra environment variables during compile \n	0	62bf001f-db2a-4c23-a608-6de67bd6bf8d
3d976914-645e-47bb-9221-5eccff35c395	2024-02-13 17:11:28.334981+01	2024-02-13 17:11:50.059352+01	/tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 email_validator<3,>=1.3 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0b6/a909df3192245/pydantic-2.6.1-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.20240106)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.module           INFO    Checking out 5.1.0 on /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpm0pqlhls/server/environments/35707199-1500-4ff4-a853-51413de9e736/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 email_validator<3,>=1.3 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0b6/a909df3192245/pydantic-2.6.1-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.20240106)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/inmanta-core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	62bf001f-db2a-4c23-a608-6de67bd6bf8d
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set, last_success, last_produced_events) FROM stdin;
35707199-1500-4ff4-a853-51413de9e736	1	std::AgentConfig[internal,agentname=localhost]	internal	2024-02-13 17:10:39.284862+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-02-13 17:10:39.27063+01	\N
35707199-1500-4ff4-a853-51413de9e736	1	std::File[localhost,path=/tmp/test]	localhost	2024-02-13 17:10:39.381623+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N	\N
35707199-1500-4ff4-a853-51413de9e736	2	std::AgentConfig[internal,agentname=localhost]	internal	2024-02-13 17:11:03.937036+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-02-13 17:11:03.928333+01	\N
35707199-1500-4ff4-a853-51413de9e736	2	std::File[localhost,path=/tmp/test]	localhost	2024-02-13 17:11:03.95063+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N	\N
35707199-1500-4ff4-a853-51413de9e736	3	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
35707199-1500-4ff4-a853-51413de9e736	3	std::AgentConfig[internal,agentname=localhost]	internal	2024-02-13 17:11:28.014181+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-02-13 17:11:03.928333+01	\N
35707199-1500-4ff4-a853-51413de9e736	4	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
35707199-1500-4ff4-a853-51413de9e736	4	std::AgentConfig[internal,agentname=localhost]	internal	\N	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	available	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	available	\N	\N	\N
35707199-1500-4ff4-a853-51413de9e736	5	test::Resource[agent2,key=key2]	agent2	\N	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	available	{}	test::Resource	key2	available	set-a	\N	\N
35707199-1500-4ff4-a853-51413de9e736	5	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
35707199-1500-4ff4-a853-51413de9e736	5	std::AgentConfig[internal,agentname=localhost]	internal	\N	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	available	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	available	\N	\N	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
a7e4e613-fbb7-474d-844f-a8a946ab7810	store	2024-02-13 17:10:38.63703+01	2024-02-13 17:10:38.643323+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2024-02-13T17:10:38.643334+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
729d8c8b-9cc1-403d-8e40-9e9929e7d2b6	pull	2024-02-13 17:10:39.23671+01	2024-02-13 17:10:39.243178+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2024-02-13T17:10:39.243188+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
cadddee5-f225-4918-9182-f89a9b9f426f	deploy	2024-02-13 17:10:39.27063+01	2024-02-13 17:10:39.284862+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2024-02-13 17:10:39+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2024-02-13 17:10:39+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"97525714-d206-494e-bfc5-17d821708640\\"}, \\"timestamp\\": \\"2024-02-13T17:10:39.266859+01:00\\"}","{\\"msg\\": \\"Start deploy 97525714-d206-494e-bfc5-17d821708640 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"97525714-d206-494e-bfc5-17d821708640\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2024-02-13T17:10:39.272887+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-02-13T17:10:39.273693+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-02-13T17:10:39.277131+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 97525714-d206-494e-bfc5-17d821708640\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"97525714-d206-494e-bfc5-17d821708640\\"}, \\"timestamp\\": \\"2024-02-13T17:10:39.280489+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	35707199-1500-4ff4-a853-51413de9e736	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1e13d86a-e4d0-4eff-89c0-857ded69661e	pull	2024-02-13 17:10:39.355169+01	2024-02-13 17:10:39.36171+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2024-02-13T17:10:39.361720+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	1	{"std::File[localhost,path=/tmp/test],v=1"}
f438592c-3b71-4fc2-a8f7-a9e97ecabdbe	deploy	2024-02-13 17:10:39.375705+01	2024-02-13 17:10:39.381623+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2024-02-13 17:10:39+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2024-02-13 17:10:39+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"c2240895-bc44-4ca9-90a0-6827735f69b8\\"}, \\"timestamp\\": \\"2024-02-13T17:10:39.373939+01:00\\"}","{\\"msg\\": \\"Start deploy c2240895-bc44-4ca9-90a0-6827735f69b8 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"c2240895-bc44-4ca9-90a0-6827735f69b8\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-02-13T17:10:39.377116+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-02-13T17:10:39.377784+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2024-02-13T17:10:39.379185+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpm0pqlhls/35707199-1500-4ff4-a853-51413de9e736/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 609, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-02-13T17:10:39.379543+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy c2240895-bc44-4ca9-90a0-6827735f69b8\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"c2240895-bc44-4ca9-90a0-6827735f69b8\\"}, \\"timestamp\\": \\"2024-02-13T17:10:39.379727+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	35707199-1500-4ff4-a853-51413de9e736	1	{"std::File[localhost,path=/tmp/test],v=1"}
1d717f24-741e-4696-a197-923097c5c694	store	2024-02-13 17:11:03.743986+01	2024-02-13 17:11:03.745549+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2024-02-13T17:11:03.745560+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	2	{"std::AgentConfig[internal,agentname=localhost],v=2","std::File[localhost,path=/tmp/test],v=2"}
3c59192e-2112-4e35-a7c4-81d8054c71ed	deploy	2024-02-13 17:11:03.890692+01	2024-02-13 17:11:03.890692+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2024-02-13T16:11:03.890692+00:00\\"}"}	deployed	\N	nochange	35707199-1500-4ff4-a853-51413de9e736	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
ca90895f-83fe-4877-a4e9-5859196a78e2	pull	2024-02-13 17:11:03.91613+01	2024-02-13 17:11:03.917814+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2024-02-13T17:11:03.917820+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
a005a620-cc68-4652-9615-7270b043eb62	pull	2024-02-13 17:11:03.916265+01	2024-02-13 17:11:03.91741+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2024-02-13T17:11:03.917418+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	2	{"std::File[localhost,path=/tmp/test],v=2"}
5fda01c5-664d-4de4-b944-4144a47242f8	deploy	2024-02-13 17:11:03.928333+01	2024-02-13 17:11:03.937036+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"5f389246-cb5b-42c4-913d-8bb29570fd11\\"}, \\"timestamp\\": \\"2024-02-13T17:11:03.923729+01:00\\"}","{\\"msg\\": \\"Start deploy 5f389246-cb5b-42c4-913d-8bb29570fd11 of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"5f389246-cb5b-42c4-913d-8bb29570fd11\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2024-02-13T17:11:03.930594+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-02-13T17:11:03.931163+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy 5f389246-cb5b-42c4-913d-8bb29570fd11\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"5f389246-cb5b-42c4-913d-8bb29570fd11\\"}, \\"timestamp\\": \\"2024-02-13T17:11:03.934705+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	35707199-1500-4ff4-a853-51413de9e736	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
ed90505c-fc5a-4b8f-a3f5-15a749e038e4	deploy	2024-02-13 17:11:28.014181+01	2024-02-13 17:11:28.014181+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2024-02-13T16:11:28.014181+00:00\\"}"}	deployed	\N	nochange	35707199-1500-4ff4-a853-51413de9e736	3	{"std::AgentConfig[internal,agentname=localhost],v=3"}
96119c68-d9b0-45ea-af27-9d18a8c37a7e	store	2024-02-13 17:11:50.599385+01	2024-02-13 17:11:50.600982+01	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2024-02-13T17:11:50.600994+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	4	{"std::File[localhost,path=/tmp/test],v=4","std::AgentConfig[internal,agentname=localhost],v=4"}
0341316d-4a12-4019-837b-baf79fbb3fd7	deploy	2024-02-13 17:11:03.944188+01	2024-02-13 17:11:03.95063+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"2d74cf58-5c9e-4450-bd8b-4e4e4fcc1268\\"}, \\"timestamp\\": \\"2024-02-13T17:11:03.940788+01:00\\"}","{\\"msg\\": \\"Start deploy 2d74cf58-5c9e-4450-bd8b-4e4e4fcc1268 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"2d74cf58-5c9e-4450-bd8b-4e4e4fcc1268\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-02-13T17:11:03.945801+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-02-13T17:11:03.946255+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2024-02-13T17:11:03.948027+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpm0pqlhls/35707199-1500-4ff4-a853-51413de9e736/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 609, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-02-13T17:11:03.948251+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 2d74cf58-5c9e-4450-bd8b-4e4e4fcc1268\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"2d74cf58-5c9e-4450-bd8b-4e4e4fcc1268\\"}, \\"timestamp\\": \\"2024-02-13T17:11:03.948432+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	35707199-1500-4ff4-a853-51413de9e736	2	{"std::File[localhost,path=/tmp/test],v=2"}
43b2ac32-f4d6-4314-a2a6-6d1d9586b231	store	2024-02-13 17:11:27.839912+01	2024-02-13 17:11:27.842889+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2024-02-13T17:11:27.842900+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	3	{"std::File[localhost,path=/tmp/test],v=3","std::AgentConfig[internal,agentname=localhost],v=3"}
280a7ce1-b6ad-46c2-88bf-38247bdf149b	store	2024-02-13 17:11:50.802236+01	2024-02-13 17:11:50.805192+01	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2024-02-13T17:11:50.805204+01:00\\"}"}	\N	\N	\N	35707199-1500-4ff4-a853-51413de9e736	5	{"std::File[localhost,path=/tmp/test],v=5","test::Resource[agent2,key=key2],v=5","std::AgentConfig[internal,agentname=localhost],v=5"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
35707199-1500-4ff4-a853-51413de9e736	a7e4e613-fbb7-474d-844f-a8a946ab7810	std::File[localhost,path=/tmp/test]	1
35707199-1500-4ff4-a853-51413de9e736	a7e4e613-fbb7-474d-844f-a8a946ab7810	std::AgentConfig[internal,agentname=localhost]	1
35707199-1500-4ff4-a853-51413de9e736	729d8c8b-9cc1-403d-8e40-9e9929e7d2b6	std::AgentConfig[internal,agentname=localhost]	1
35707199-1500-4ff4-a853-51413de9e736	cadddee5-f225-4918-9182-f89a9b9f426f	std::AgentConfig[internal,agentname=localhost]	1
35707199-1500-4ff4-a853-51413de9e736	1e13d86a-e4d0-4eff-89c0-857ded69661e	std::File[localhost,path=/tmp/test]	1
35707199-1500-4ff4-a853-51413de9e736	f438592c-3b71-4fc2-a8f7-a9e97ecabdbe	std::File[localhost,path=/tmp/test]	1
35707199-1500-4ff4-a853-51413de9e736	1d717f24-741e-4696-a197-923097c5c694	std::AgentConfig[internal,agentname=localhost]	2
35707199-1500-4ff4-a853-51413de9e736	1d717f24-741e-4696-a197-923097c5c694	std::File[localhost,path=/tmp/test]	2
35707199-1500-4ff4-a853-51413de9e736	3c59192e-2112-4e35-a7c4-81d8054c71ed	std::AgentConfig[internal,agentname=localhost]	2
35707199-1500-4ff4-a853-51413de9e736	ca90895f-83fe-4877-a4e9-5859196a78e2	std::AgentConfig[internal,agentname=localhost]	2
35707199-1500-4ff4-a853-51413de9e736	a005a620-cc68-4652-9615-7270b043eb62	std::File[localhost,path=/tmp/test]	2
35707199-1500-4ff4-a853-51413de9e736	5fda01c5-664d-4de4-b944-4144a47242f8	std::AgentConfig[internal,agentname=localhost]	2
35707199-1500-4ff4-a853-51413de9e736	0341316d-4a12-4019-837b-baf79fbb3fd7	std::File[localhost,path=/tmp/test]	2
35707199-1500-4ff4-a853-51413de9e736	43b2ac32-f4d6-4314-a2a6-6d1d9586b231	std::File[localhost,path=/tmp/test]	3
35707199-1500-4ff4-a853-51413de9e736	43b2ac32-f4d6-4314-a2a6-6d1d9586b231	std::AgentConfig[internal,agentname=localhost]	3
35707199-1500-4ff4-a853-51413de9e736	ed90505c-fc5a-4b8f-a3f5-15a749e038e4	std::AgentConfig[internal,agentname=localhost]	3
35707199-1500-4ff4-a853-51413de9e736	96119c68-d9b0-45ea-af27-9d18a8c37a7e	std::File[localhost,path=/tmp/test]	4
35707199-1500-4ff4-a853-51413de9e736	96119c68-d9b0-45ea-af27-9d18a8c37a7e	std::AgentConfig[internal,agentname=localhost]	4
35707199-1500-4ff4-a853-51413de9e736	280a7ce1-b6ad-46c2-88bf-38247bdf149b	std::File[localhost,path=/tmp/test]	5
35707199-1500-4ff4-a853-51413de9e736	280a7ce1-b6ad-46c2-88bf-38247bdf149b	test::Resource[agent2,key=key2]	5
35707199-1500-4ff4-a853-51413de9e736	280a7ce1-b6ad-46c2-88bf-38247bdf149b	std::AgentConfig[internal,agentname=localhost]	5
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304070,202306060,202308010,202308020,202308100,202309130,202310040,202310090,202310180}
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

CREATE INDEX agent_id_primary_index ON public.agent USING btree (id_primary);


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
-- Name: resource_environment_model_resource_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_model_resource_type_idx ON public.resource USING btree (environment, model, resource_type);


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
-- Name: resource_resource_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_resource_id_index ON public.resource USING btree (resource_id);


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
-- Name: discoveredresource unmanagedresource_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discoveredresource
    ADD CONSTRAINT unmanagedresource_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: -
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

