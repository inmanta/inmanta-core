--
-- PostgreSQL database dump
--

-- Dumped from database version 13.14 (Ubuntu 13.14-1.pgdg20.04+1)
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
    exporter_plugin character varying,
    soft_delete boolean DEFAULT false NOT NULL
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
    undeployable character varying[] NOT NULL,
    skipped_for_undeployable character varying[] NOT NULL,
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
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	internal	2024-03-15 17:36:47.490133+01	f	738ef4da-b799-444d-a6f8-58590982209d	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	localhost	2024-03-15 17:36:48.611116+01	f	c8fe6b76-f1f9-494c-b773-2365045263fc	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	agent2	\N	f	\N	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
738ef4da-b799-444d-a6f8-58590982209d	37658a70-e2ea-11ee-bbf4-2385267413ef	internal	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4
c8fe6b76-f1f9-494c-b773-2365045263fc	37658a70-e2ea-11ee-bbf4-2385267413ef	localhost	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:36:47.490133+01	2024-03-15 17:37:55.558066+01	\N	37658a70-e2ea-11ee-bbf4-2385267413ef
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Service	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::File	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Directory	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Package	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Symlink	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::testing::NullResource	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::AgentConfig	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Service	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::File	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Directory	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Package	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Symlink	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::testing::NullResource	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::AgentConfig	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Service	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::File	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Directory	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Package	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Symlink	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::testing::NullResource	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::AgentConfig	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Service	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::File	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Directory	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Package	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Symlink	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::testing::NullResource	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::AgentConfig	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::AgentConfig	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Directory	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::File	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Package	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Service	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::Symlink	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	std::testing::NullResource	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, soft_delete) FROM stdin;
95bf6b1d-d458-4ffe-ad87-53cf36366726	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:36:21.016255+01	2024-03-15 17:36:46.974119+01	2024-03-15 17:36:21.008446+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	b616975c-4daf-4727-a0fc-f4a9b1126e30	t	\N	{"errors": []}	f	{}	\N	\N	\N	f
8b864bed-8e1b-4bf1-ae80-25216c9948d4	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:36:48.775784+01	2024-03-15 17:37:11.075283+01	2024-03-15 17:36:48.77194+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	2decac8b-31c0-4d8b-ab18-ec6056fb6193	t	\N	{"errors": []}	f	{}	\N	\N	\N	f
9c34ddc4-0295-4934-a443-dc9345d0d0c0	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:37:11.311078+01	2024-03-15 17:37:34.235228+01	2024-03-15 17:37:11.30723+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	3	3e60da3e-0249-4ff8-9c22-d24c4354da0b	t	\N	{"errors": []}	f	{}	\N	\N	\N	f
c18a3586-ac38-4b2e-a2cf-3c48f2d233cb	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:37:34.350975+01	2024-03-15 17:37:56.192633+01	2024-03-15 17:37:34.346122+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	4	021be8f8-bf41-4782-bb0f-5f532fda191e	t	\N	{"errors": []}	f	{}	\N	\N	\N	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles) FROM stdin;
1	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:36:46.845846+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
2	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:37:10.999998+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
3	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:37:34.161249+01	t	f	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
4	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:37:56.119778+01	f	f	pending	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
5	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2024-03-15 17:37:56.253118+01	f	f	pending	\N	3	{}	{}	4	t
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
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	dev-2	6515fe1b-deb1-4df6-9da2-d907f3f19b4a			{"auto_full_compile": ""}	0	f		
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	dev-1	6515fe1b-deb1-4df6-9da2-d907f3f19b4a			{"auto_deploy": false, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "autostart_agent_deploy_interval": "0", "autostart_agent_repair_interval": "600", "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0}	5	f		
\.


--
-- Data for Name: environmentmetricsgauge; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricsgauge (environment, metric_name, "timestamp", count, category) FROM stdin;
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	1	deployed
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	1	failed
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	skipped
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	0	skipped
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	dry
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	0	dry
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	deployed
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	failed
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	deploying
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	0	deploying
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	available
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	0	available
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	cancelled
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	0	cancelled
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	undefined
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	0	undefined
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	skipped_for_undefined
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.resource_count	2024-03-15 17:37:20.967009+01	0	unavailable
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	0	skipped_for_undefined
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.resource_count	2024-03-15 17:37:20.967009+01	0	unavailable
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.agent_count	2024-03-15 17:37:20.967009+01	0	down
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.agent_count	2024-03-15 17:37:20.967009+01	0	paused
7c9ac6b4-52e3-4ac2-b572-4ae6263122fa	resource.agent_count	2024-03-15 17:37:20.967009+01	0	up
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.agent_count	2024-03-15 17:37:20.967009+01	0	down
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.agent_count	2024-03-15 17:37:20.967009+01	0	paused
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	resource.agent_count	2024-03-15 17:37:20.967009+01	2	up
\.


--
-- Data for Name: environmentmetricstimer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricstimer (environment, metric_name, "timestamp", count, value, category) FROM stdin;
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	orchestrator.compile_waiting_time	2024-03-15 17:37:20.967009+01	3	0.015501	__None__
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	orchestrator.compile_time	2024-03-15 17:37:20.967009+01	2	48.257363	__None__
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
6515fe1b-deb1-4df6-9da2-d907f3f19b4a	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
9289fb50-b64e-456a-94d5-db21289cec7e	2024-03-15 17:36:21.016601+01	2024-03-15 17:36:21.017625+01		Init		Using extra environment variables during compile \n	0	95bf6b1d-d458-4ffe-ad87-53cf36366726
df8c2654-4f52-4568-b5b4-f35c7adadde0	2024-03-15 17:36:21.017895+01	2024-03-15 17:36:21.024581+01		Creating venv			0	95bf6b1d-d458-4ffe-ad87-53cf36366726
e8b13ebf-1ead-4179-b76f-d60bd5b1be0a	2024-03-15 17:36:21.028337+01	2024-03-15 17:36:21.35253+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	95bf6b1d-d458-4ffe-ad87-53cf36366726
92ec492d-daed-4154-8ef0-e82e92e17fb5	2024-03-15 17:37:55.575579+01	2024-03-15 17:37:56.191491+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m inmanta.app -vvv export -X -e 8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4 --server_address localhost --server_port 48717 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmph4zkxlto --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.115 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.1\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/codebatched/4\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=4 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=4 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.013 seconds\nexporter       DEBUG   The entire export command took 0.157 seconds\n	0	c18a3586-ac38-4b2e-a2cf-3c48f2d233cb
756e4b44-05b6-4d18-bf6c-a78533f97964	2024-03-15 17:36:21.354539+01	2024-03-15 17:36:46.280205+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 5.1.1 in /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 Jinja2<4,>=3.1 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.0.post1)\ninmanta.pip              DEBUG   Collecting email_validator<3,>=1.3\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/97d/882d174e2a657/email_validator-2.1.1-py3-none-any.whl (30 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Collecting Jinja2<4,>=3.1\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/7d6/d50dd97d52cbc/Jinja2-3.1.3-py3-none-any.whl (133 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (1.10.13)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Collecting build~=1.0 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/8ed/0851ee76e6e38/build-1.1.1-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.0)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/4dc/bb62368e2800c/colorlog-6.8.2-py3-none-any.whl (11 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Collecting cookiecutter<3,>=1 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/a54/a8e37995e4ed9/cookiecutter-2.6.0-py3-none-any.whl (39 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.0)\ninmanta.pip              DEBUG   Collecting importlib_metadata<8,>=4 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/f4b/c4c0c070c490a/importlib_metadata-7.0.2-py3-none-any.whl (24 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<11,>=8 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/686/b06abe565edfa/more_itertools-10.2.0-py3-none-any.whl (57 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Collecting packaging>=21.3 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/2dd/fb553fdf02fb7/packaging-24.0-py3-none-any.whl (53 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.3.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/ba0/d021a166865d2/pip-24.0-py3-none-any.whl (2.1 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/646/b2b12df4295b4/pydantic-1.10.14-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.2)\ninmanta.pip              DEBUG   Collecting python-dateutil~=2.0 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/a8b/2bc7bffae2822/python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.0.2)\ninmanta.pip              DEBUG   Collecting setuptools (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/c21/c49fb1042386d/setuptools-69.2.0-py3-none-any.whl (821 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.5)\ninmanta.pip              DEBUG   Collecting ruamel.yaml~=0.17 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/57b/53ba33def16c4/ruamel.yaml-0.18.6-py3-none-any.whl (117 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.14)\ninmanta.pip              DEBUG   Collecting types-python-dateutil>=2.8.10 (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/78a/a9124f360df90/types_python_dateutil-2.9.0.20240315-py3-none-any.whl (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: types-python-dateutil, setuptools, ruamel.yaml, python-dateutil, pydantic, pip, packaging, more-itertools, Jinja2, importlib_metadata, email_validator, colorlog, build, cookiecutter\ninmanta.pip              DEBUG   Attempting uninstall: types-python-dateutil\ninmanta.pip              DEBUG   Found existing installation: types-python-dateutil 2.8.19.14\ninmanta.pip              DEBUG   Not uninstalling types-python-dateutil at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'types-python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: setuptools\ninmanta.pip              DEBUG   Found existing installation: setuptools 69.0.2\ninmanta.pip              DEBUG   Not uninstalling setuptools at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'setuptools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: ruamel.yaml\ninmanta.pip              DEBUG   Found existing installation: ruamel.yaml 0.18.5\ninmanta.pip              DEBUG   Not uninstalling ruamel-yaml at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'ruamel.yaml'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-dateutil\ninmanta.pip              DEBUG   Found existing installation: python-dateutil 2.8.2\ninmanta.pip              DEBUG   Not uninstalling python-dateutil at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 1.10.13\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 23.3.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: packaging\ninmanta.pip              DEBUG   Found existing installation: packaging 23.2\ninmanta.pip              DEBUG   Not uninstalling packaging at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'packaging'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 10.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: Jinja2\ninmanta.pip              DEBUG   Found existing installation: Jinja2 3.1.2\ninmanta.pip              DEBUG   Not uninstalling jinja2 at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'Jinja2'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: importlib_metadata\ninmanta.pip              DEBUG   Found existing installation: importlib-metadata 7.0.0\ninmanta.pip              DEBUG   Not uninstalling importlib-metadata at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'importlib-metadata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: email_validator\ninmanta.pip              DEBUG   Found existing installation: email-validator 2.1.0.post1\ninmanta.pip              DEBUG   Not uninstalling email-validator at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'email-validator'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.8.0\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 1.0.3\ninmanta.pip              DEBUG   Not uninstalling build at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cookiecutter\ninmanta.pip              DEBUG   Found existing installation: cookiecutter 2.5.0\ninmanta.pip              DEBUG   Not uninstalling cookiecutter at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\ninmanta.pip              DEBUG   Can't uninstall 'cookiecutter'. No files were found to uninstall.\ninmanta.pip              DEBUG   Successfully installed Jinja2-3.1.3 build-1.1.1 colorlog-6.8.2 cookiecutter-2.6.0 email_validator-2.1.1 importlib_metadata-7.0.2 more-itertools-10.2.0 packaging-24.0 pip-24.0 pydantic-1.10.14 python-dateutil-2.9.0.post0 ruamel.yaml-0.18.6 setuptools-69.2.0 types-python-dateutil-2.9.0.20240315\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   [notice] A new release of pip is available: 23.3.1 -> 24.0\ninmanta.pip              DEBUG   [notice] To update, run: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade pip\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 2 misses (50%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 Jinja2<4,>=3.1 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in ./.env/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240315)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	95bf6b1d-d458-4ffe-ad87-53cf36366726
77fa37c1-0a96-4d8a-a685-9b36bd985cb3	2024-03-15 17:37:33.595208+01	2024-03-15 17:37:34.234187+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m inmanta.app -vvv export -X -e 8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4 --server_address localhost --server_port 48717 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpibicxe35 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.111 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.1\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/codebatched/3\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=3 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=3 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.015 seconds\nexporter       DEBUG   The entire export command took 0.155 seconds\n	0	9c34ddc4-0295-4934-a443-dc9345d0d0c0
b75922f9-df81-4083-8389-42aa30b98a3a	2024-03-15 17:36:46.281394+01	2024-03-15 17:36:46.972683+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m inmanta.app -vvv export -X -e 8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4 --server_address localhost --server_port 48717 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpe78n1sq3 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.121 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.1\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/file/23a9571ecf590d553a738634f7f1bfaca0a4bfb5\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/file/10d63b01c1ec8269f9b10edcb9740cf3519299dc\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/file/8840b9601481957a2f2d263f1603b89e6746156e\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/codebatched/1\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=1 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=1 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.033 seconds\nexporter       DEBUG   The entire export command took 0.182 seconds\n	0	95bf6b1d-d458-4ffe-ad87-53cf36366726
80c58791-363f-4c9b-ba0a-5098fc62f0c0	2024-03-15 17:37:11.31144+01	2024-03-15 17:37:11.312124+01		Init		Using extra environment variables during compile \n	0	9c34ddc4-0295-4934-a443-dc9345d0d0c0
58c06923-8b58-4b74-a2b1-32e51e23bda6	2024-03-15 17:36:48.776139+01	2024-03-15 17:36:48.777047+01		Init		Using extra environment variables during compile \n	0	8b864bed-8e1b-4bf1-ae80-25216c9948d4
c7862dd3-9344-4518-9be2-f3163b12c86f	2024-03-15 17:36:48.78142+01	2024-03-15 17:36:49.153068+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	8b864bed-8e1b-4bf1-ae80-25216c9948d4
6e1b31b1-25cd-4f74-9f08-ad93734d3cf2	2024-03-15 17:37:11.315832+01	2024-03-15 17:37:11.643868+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	9c34ddc4-0295-4934-a443-dc9345d0d0c0
c03f8df2-4b0b-492d-b550-0c75cbec1145	2024-03-15 17:36:49.154118+01	2024-03-15 17:37:10.462362+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in ./.env/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240315)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in ./.env/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240315)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	8b864bed-8e1b-4bf1-ae80-25216c9948d4
c0b4cd3a-6e69-489d-aa50-b7bc2680ee4b	2024-03-15 17:37:10.463484+01	2024-03-15 17:37:11.074349+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m inmanta.app -vvv export -X -e 8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4 --server_address localhost --server_port 48717 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpdh3eu2c2 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.110 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.1\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/codebatched/2\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:48717/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=2 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=2 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:48717/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.015 seconds\nexporter       DEBUG   The entire export command took 0.153 seconds\n	0	8b864bed-8e1b-4bf1-ae80-25216c9948d4
a6f2de38-7716-4eb1-b43a-f60f2d2d3976	2024-03-15 17:37:34.351296+01	2024-03-15 17:37:34.352038+01		Init		Using extra environment variables during compile \n	0	c18a3586-ac38-4b2e-a2cf-3c48f2d233cb
032fd55e-7afc-4499-984c-9ba1bc9e6863	2024-03-15 17:37:34.356268+01	2024-03-15 17:37:34.714145+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	c18a3586-ac38-4b2e-a2cf-3c48f2d233cb
9de7f79f-d8b6-4995-b251-e6b33fa17043	2024-03-15 17:37:11.644964+01	2024-03-15 17:37:33.594064+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in ./.env/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240315)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in ./.env/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240315)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	9c34ddc4-0295-4934-a443-dc9345d0d0c0
2109dd27-c7f9-43ad-b7af-053b45e8f1db	2024-03-15 17:37:34.715004+01	2024-03-15 17:37:55.574563+01	/tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 email_validator<3,>=1.3 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in ./.env/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240315)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp17b17ei0/server/environments/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 email_validator<3,>=1.3 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in ./.env/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240315)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	c18a3586-ac38-4b2e-a2cf-3c48f2d233cb
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set, last_success, last_produced_events) FROM stdin;
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1	std::AgentConfig[internal,agentname=localhost]	internal	2024-03-15 17:36:47.592573+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-03-15 17:36:47.541822+01	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1	std::File[localhost,path=/tmp/test]	localhost	2024-03-15 17:36:48.703018+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2	std::AgentConfig[internal,agentname=localhost]	internal	2024-03-15 17:37:11.233639+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-03-15 17:37:11.224751+01	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2	std::File[localhost,path=/tmp/test]	localhost	2024-03-15 17:37:11.236065+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	3	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	3	std::AgentConfig[internal,agentname=localhost]	internal	2024-03-15 17:37:34.333971+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-03-15 17:37:11.224751+01	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	4	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	4	std::AgentConfig[internal,agentname=localhost]	internal	\N	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	available	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	available	\N	\N	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	5	test::Resource[agent2,key=key2]	agent2	\N	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	available	{}	test::Resource	key2	available	set-a	\N	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	5	std::AgentConfig[internal,agentname=localhost]	internal	\N	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	available	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	available	\N	\N	\N
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	5	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
1b6e67b6-a572-4fdf-a796-9020035c3204	store	2024-03-15 17:36:46.845791+01	2024-03-15 17:36:46.853742+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2024-03-15T17:36:46.853754+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1	{"std::AgentConfig[internal,agentname=localhost],v=1","std::File[localhost,path=/tmp/test],v=1"}
51f43378-99cf-4371-81ea-cd58abb0bf4d	pull	2024-03-15 17:36:47.498205+01	2024-03-15 17:36:47.504168+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2024-03-15T17:36:47.504179+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
be62c429-524b-4377-a4e9-4bfcaff24edc	deploy	2024-03-15 17:36:47.541822+01	2024-03-15 17:36:47.592573+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2024-03-15 17:36:47+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2024-03-15 17:36:47+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"d8195d78-d0fe-4bf9-8775-e422788e5eb3\\"}, \\"timestamp\\": \\"2024-03-15T17:36:47.532617+01:00\\"}","{\\"msg\\": \\"Start deploy d8195d78-d0fe-4bf9-8775-e422788e5eb3 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"d8195d78-d0fe-4bf9-8775-e422788e5eb3\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2024-03-15T17:36:47.547448+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-15T17:36:47.549193+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-15T17:36:47.558174+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy d8195d78-d0fe-4bf9-8775-e422788e5eb3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"d8195d78-d0fe-4bf9-8775-e422788e5eb3\\"}, \\"timestamp\\": \\"2024-03-15T17:36:47.577357+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
40305a46-a91a-4908-8233-ec9d20ff08c7	pull	2024-03-15 17:36:48.631241+01	2024-03-15 17:36:48.636179+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2024-03-15T17:36:48.636207+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1	{"std::File[localhost,path=/tmp/test],v=1"}
02ed6e57-128c-41ba-91fb-08b889b656b9	deploy	2024-03-15 17:36:48.690294+01	2024-03-15 17:36:48.703018+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2024-03-15 17:36:48+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2024-03-15 17:36:48+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"92c9902a-d795-42a3-a60d-ad0a524e1a92\\"}, \\"timestamp\\": \\"2024-03-15T17:36:48.685065+01:00\\"}","{\\"msg\\": \\"Start deploy 92c9902a-d795-42a3-a60d-ad0a524e1a92 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"92c9902a-d795-42a3-a60d-ad0a524e1a92\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-03-15T17:36:48.693840+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-15T17:36:48.694999+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2024-03-15T17:36:48.698204+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp17b17ei0/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 609, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-03-15T17:36:48.698926+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 92c9902a-d795-42a3-a60d-ad0a524e1a92\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"92c9902a-d795-42a3-a60d-ad0a524e1a92\\"}, \\"timestamp\\": \\"2024-03-15T17:36:48.699245+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1	{"std::File[localhost,path=/tmp/test],v=1"}
72480059-cc87-4cb8-ba52-a807d21d6170	store	2024-03-15 17:37:10.999937+01	2024-03-15 17:37:11.001666+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2024-03-15T17:37:11.001676+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2	{"std::AgentConfig[internal,agentname=localhost],v=2","std::File[localhost,path=/tmp/test],v=2"}
011c1a7e-a961-49b1-9337-1630f16a6750	deploy	2024-03-15 17:37:11.181878+01	2024-03-15 17:37:11.181878+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2024-03-15T16:37:11.181878+00:00\\"}"}	deployed	\N	nochange	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
5f94f363-6d00-4847-a380-1ac5e08ee64d	pull	2024-03-15 17:37:11.211362+01	2024-03-15 17:37:11.212418+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2024-03-15T17:37:11.212426+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
d8b7e043-00a2-4df7-bfcf-800fede739b9	pull	2024-03-15 17:37:11.211833+01	2024-03-15 17:37:11.21323+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2024-03-15T17:37:11.213237+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2	{"std::File[localhost,path=/tmp/test],v=2"}
d7009302-9107-4a8b-a7ae-ef7ec620eadf	deploy	2024-03-15 17:37:11.224751+01	2024-03-15 17:37:11.233639+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"4839d61c-d3b7-4126-9c06-a1c34801b80d\\"}, \\"timestamp\\": \\"2024-03-15T17:37:11.221193+01:00\\"}","{\\"msg\\": \\"Start deploy 4839d61c-d3b7-4126-9c06-a1c34801b80d of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"4839d61c-d3b7-4126-9c06-a1c34801b80d\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2024-03-15T17:37:11.226765+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-15T17:37:11.227301+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy 4839d61c-d3b7-4126-9c06-a1c34801b80d\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"4839d61c-d3b7-4126-9c06-a1c34801b80d\\"}, \\"timestamp\\": \\"2024-03-15T17:37:11.230715+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
c6f7d18d-a8d6-463c-8ee6-c8c51a6ff512	store	2024-03-15 17:37:34.160765+01	2024-03-15 17:37:34.162829+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2024-03-15T17:37:34.162841+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	3	{"std::File[localhost,path=/tmp/test],v=3","std::AgentConfig[internal,agentname=localhost],v=3"}
6e911b6b-d8a5-4654-b071-92de307f26b6	deploy	2024-03-15 17:37:11.228951+01	2024-03-15 17:37:11.236065+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"1d9ec649-565e-460c-8c44-3afae79daa9b\\"}, \\"timestamp\\": \\"2024-03-15T17:37:11.226274+01:00\\"}","{\\"msg\\": \\"Start deploy 1d9ec649-565e-460c-8c44-3afae79daa9b of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"1d9ec649-565e-460c-8c44-3afae79daa9b\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-03-15T17:37:11.231351+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-15T17:37:11.231970+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2024-03-15T17:37:11.233498+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp17b17ei0/8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 609, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-03-15T17:37:11.233675+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 1d9ec649-565e-460c-8c44-3afae79daa9b\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"1d9ec649-565e-460c-8c44-3afae79daa9b\\"}, \\"timestamp\\": \\"2024-03-15T17:37:11.233837+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	2	{"std::File[localhost,path=/tmp/test],v=2"}
62d21b45-12ea-426a-ba68-07e96c5c94c4	deploy	2024-03-15 17:37:34.333971+01	2024-03-15 17:37:34.333971+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2024-03-15T16:37:34.333971+00:00\\"}"}	deployed	\N	nochange	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	3	{"std::AgentConfig[internal,agentname=localhost],v=3"}
c524fd3a-bcfc-492d-a069-0e5a98b4b7d5	store	2024-03-15 17:37:56.11972+01	2024-03-15 17:37:56.120954+01	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2024-03-15T17:37:56.120965+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	4	{"std::AgentConfig[internal,agentname=localhost],v=4","std::File[localhost,path=/tmp/test],v=4"}
b768a174-ce2a-46ea-80a2-061c78f4ce41	store	2024-03-15 17:37:56.253034+01	2024-03-15 17:37:56.255379+01	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2024-03-15T17:37:56.255387+01:00\\"}"}	\N	\N	\N	8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	5	{"std::AgentConfig[internal,agentname=localhost],v=5","test::Resource[agent2,key=key2],v=5","std::File[localhost,path=/tmp/test],v=5"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1b6e67b6-a572-4fdf-a796-9020035c3204	std::AgentConfig[internal,agentname=localhost]	1
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	1b6e67b6-a572-4fdf-a796-9020035c3204	std::File[localhost,path=/tmp/test]	1
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	51f43378-99cf-4371-81ea-cd58abb0bf4d	std::AgentConfig[internal,agentname=localhost]	1
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	be62c429-524b-4377-a4e9-4bfcaff24edc	std::AgentConfig[internal,agentname=localhost]	1
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	40305a46-a91a-4908-8233-ec9d20ff08c7	std::File[localhost,path=/tmp/test]	1
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	02ed6e57-128c-41ba-91fb-08b889b656b9	std::File[localhost,path=/tmp/test]	1
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	72480059-cc87-4cb8-ba52-a807d21d6170	std::AgentConfig[internal,agentname=localhost]	2
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	72480059-cc87-4cb8-ba52-a807d21d6170	std::File[localhost,path=/tmp/test]	2
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	011c1a7e-a961-49b1-9337-1630f16a6750	std::AgentConfig[internal,agentname=localhost]	2
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	5f94f363-6d00-4847-a380-1ac5e08ee64d	std::AgentConfig[internal,agentname=localhost]	2
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	d8b7e043-00a2-4df7-bfcf-800fede739b9	std::File[localhost,path=/tmp/test]	2
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	d7009302-9107-4a8b-a7ae-ef7ec620eadf	std::AgentConfig[internal,agentname=localhost]	2
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	6e911b6b-d8a5-4654-b071-92de307f26b6	std::File[localhost,path=/tmp/test]	2
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	c6f7d18d-a8d6-463c-8ee6-c8c51a6ff512	std::File[localhost,path=/tmp/test]	3
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	c6f7d18d-a8d6-463c-8ee6-c8c51a6ff512	std::AgentConfig[internal,agentname=localhost]	3
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	62d21b45-12ea-426a-ba68-07e96c5c94c4	std::AgentConfig[internal,agentname=localhost]	3
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	c524fd3a-bcfc-492d-a069-0e5a98b4b7d5	std::AgentConfig[internal,agentname=localhost]	4
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	c524fd3a-bcfc-492d-a069-0e5a98b4b7d5	std::File[localhost,path=/tmp/test]	4
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	b768a174-ce2a-46ea-80a2-061c78f4ce41	std::AgentConfig[internal,agentname=localhost]	5
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	b768a174-ce2a-46ea-80a2-061c78f4ce41	test::Resource[agent2,key=key2]	5
8936a55f-bc07-4fdb-ae09-a9bbe6c3d1d4	b768a174-ce2a-46ea-80a2-061c78f4ce41	std::File[localhost,path=/tmp/test]	5
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304070,202306060,202308010,202308020,202308100,202309130,202310040,202310090,202310180,202402130,202403120}
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

