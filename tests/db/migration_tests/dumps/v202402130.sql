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
f015501d-e9e9-4016-914d-c7e214ae28bc	internal	2024-03-18 09:10:41.921685+01	f	109dda34-0f7f-4374-8128-fd8ac3c3f4f1	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	localhost	2024-03-18 09:10:43.074524+01	f	cc929a44-0df6-4089-9015-88a8dd0e1124	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	agent2	\N	f	\N	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
109dda34-0f7f-4374-8128-fd8ac3c3f4f1	0355ecd6-e4ff-11ee-baf7-4d4475d1b69e	internal	\N	f015501d-e9e9-4016-914d-c7e214ae28bc
cc929a44-0df6-4089-9015-88a8dd0e1124	0355ecd6-e4ff-11ee-baf7-4d4475d1b69e	localhost	\N	f015501d-e9e9-4016-914d-c7e214ae28bc
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:10:41.921685+01	2024-03-18 09:12:00.780071+01	\N	0355ecd6-e4ff-11ee-baf7-4d4475d1b69e
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Service	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::File	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Directory	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Package	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Symlink	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::testing::NullResource	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::AgentConfig	1	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Service	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::File	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Directory	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Package	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Symlink	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::testing::NullResource	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::AgentConfig	2	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Service	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::File	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Directory	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Package	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Symlink	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::testing::NullResource	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::AgentConfig	3	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Service	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::File	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Directory	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Package	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Symlink	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::testing::NullResource	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::AgentConfig	4	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::AgentConfig	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Directory	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::File	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Package	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Service	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::Symlink	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
f015501d-e9e9-4016-914d-c7e214ae28bc	std::testing::NullResource	5	{"10d63b01c1ec8269f9b10edcb9740cf3519299dc": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/types.py", "inmanta_plugins.std.types", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "23a9571ecf590d553a738634f7f1bfaca0a4bfb5": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "8840b9601481957a2f2d263f1603b89e6746156e": ["/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
e7265253-3331-47d9-8f57-1fff2d6f96d3	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:10:12.274202+01	2024-03-18 09:10:41.30971+01	2024-03-18 09:10:12.26947+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	05752c55-f82d-4432-bcce-e15f8bad7d0f	t	\N	{"errors": []}	f	{}	\N	\N	\N
ec402e66-196c-48de-b3a0-bce1bbc4ed78	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:10:43.200506+01	2024-03-18 09:11:10.283482+01	2024-03-18 09:10:43.195129+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	fdfd0820-0d4f-433c-b97f-3b4f3a9804d3	t	\N	{"errors": []}	f	{}	\N	\N	\N
6e015f0d-6e1f-444c-ac67-79b14d3e1b3b	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:11:10.566886+01	2024-03-18 09:11:36.388989+01	2024-03-18 09:11:10.563181+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	3	d210dcd3-9643-47db-aac2-93d655e34f96	t	\N	{"errors": []}	f	{}	\N	\N	\N
af289eeb-3e7d-42d1-9c6e-e8bea761d4af	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:11:36.542037+01	2024-03-18 09:12:00.795039+01	2024-03-18 09:11:36.538085+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	4	e4dfd16c-a5ed-4099-b396-65410cb68edf	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles) FROM stdin;
1	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:10:41.172852+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
2	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:11:10.16259+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
3	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:11:36.307349+01	t	f	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
4	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:12:00.663084+01	f	f	pending	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
5	f015501d-e9e9-4016-914d-c7e214ae28bc	2024-03-18 09:12:00.862205+01	f	f	pending	\N	3	{}	{}	4	t
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
73301adc-e537-4067-9654-2dec28b1f7ba	dev-2	72396b1e-41a1-41b9-b45e-0a6c457085a7			{"auto_full_compile": ""}	0	f		
f015501d-e9e9-4016-914d-c7e214ae28bc	dev-1	72396b1e-41a1-41b9-b45e-0a6c457085a7			{"auto_deploy": false, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "autostart_agent_deploy_interval": "0", "autostart_agent_repair_interval": "600", "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0}	5	t		
\.


--
-- Data for Name: environmentmetricsgauge; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricsgauge (environment, metric_name, "timestamp", count, category) FROM stdin;
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	1	deployed
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	1	failed
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	skipped
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	0	skipped
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	dry
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	0	dry
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	deployed
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	failed
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	deploying
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	0	deploying
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	available
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	0	available
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	cancelled
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	0	cancelled
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	undefined
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	0	undefined
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	skipped_for_undefined
73301adc-e537-4067-9654-2dec28b1f7ba	resource.resource_count	2024-03-18 09:11:12.196554+01	0	unavailable
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	0	skipped_for_undefined
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.resource_count	2024-03-18 09:11:12.196554+01	0	unavailable
73301adc-e537-4067-9654-2dec28b1f7ba	resource.agent_count	2024-03-18 09:11:12.196554+01	0	down
73301adc-e537-4067-9654-2dec28b1f7ba	resource.agent_count	2024-03-18 09:11:12.196554+01	0	paused
73301adc-e537-4067-9654-2dec28b1f7ba	resource.agent_count	2024-03-18 09:11:12.196554+01	0	up
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.agent_count	2024-03-18 09:11:12.196554+01	0	down
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.agent_count	2024-03-18 09:11:12.196554+01	0	paused
f015501d-e9e9-4016-914d-c7e214ae28bc	resource.agent_count	2024-03-18 09:11:12.196554+01	2	up
\.


--
-- Data for Name: environmentmetricstimer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricstimer (environment, metric_name, "timestamp", count, value, category) FROM stdin;
f015501d-e9e9-4016-914d-c7e214ae28bc	orchestrator.compile_waiting_time	2024-03-18 09:11:12.196554+01	3	0.013814	__None__
f015501d-e9e9-4016-914d-c7e214ae28bc	orchestrator.compile_time	2024-03-18 09:11:12.196554+01	2	56.118484	__None__
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
72396b1e-41a1-41b9-b45e-0a6c457085a7	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
b0e7a292-2243-44b6-8886-f7f504260b59	2024-03-18 09:10:12.274567+01	2024-03-18 09:10:12.275697+01		Init		Using extra environment variables during compile \n	0	e7265253-3331-47d9-8f57-1fff2d6f96d3
84954d21-009a-4a42-b819-3ddd91d4ebfa	2024-03-18 09:10:12.275972+01	2024-03-18 09:10:12.284642+01		Creating venv			0	e7265253-3331-47d9-8f57-1fff2d6f96d3
77fcb701-0869-44cb-997e-6487f484282c	2024-03-18 09:10:12.289436+01	2024-03-18 09:10:12.662061+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	e7265253-3331-47d9-8f57-1fff2d6f96d3
93eba776-46ff-4eaf-a155-5548f7662aaf	2024-03-18 09:10:12.663299+01	2024-03-18 09:10:40.544885+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 5.1.1 in /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (1.10.13)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Collecting Jinja2<4,>=3.1\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/7d6/d50dd97d52cbc/Jinja2-3.1.3-py3-none-any.whl (133 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.3)\ninmanta.pip              DEBUG   Collecting build~=1.0 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/8ed/0851ee76e6e38/build-1.1.1-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.0)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/4dc/bb62368e2800c/colorlog-6.8.2-py3-none-any.whl (11 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.5.0)\ninmanta.pip              DEBUG   Collecting cookiecutter<3,>=1 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/a54/a8e37995e4ed9/cookiecutter-2.6.0-py3-none-any.whl (39 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.0)\ninmanta.pip              DEBUG   Collecting importlib_metadata<8,>=4 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/f4b/c4c0c070c490a/importlib_metadata-7.0.2-py3-none-any.whl (24 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<11,>=8 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/686/b06abe565edfa/more_itertools-10.2.0-py3-none-any.whl (57 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.2)\ninmanta.pip              DEBUG   Collecting packaging>=21.3 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/2dd/fb553fdf02fb7/packaging-24.0-py3-none-any.whl (53 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (23.3.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/ba0/d021a166865d2/pip-24.0-py3-none-any.whl (2.1 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/646/b2b12df4295b4/pydantic-1.10.14-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.0.2)\ninmanta.pip              DEBUG   Collecting setuptools (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/c21/c49fb1042386d/setuptools-69.2.0-py3-none-any.whl (821 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.5)\ninmanta.pip              DEBUG   Collecting ruamel.yaml~=0.17 (from inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/57b/53ba33def16c4/ruamel.yaml-0.18.6-py3-none-any.whl (117 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.8.19.14)\ninmanta.pip              DEBUG   Collecting types-python-dateutil>=2.8.10 (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0)\ninmanta.pip              DEBUG   Downloading https://artifacts.internal.inmanta.com/root/pypi/%2Bf/6b8/cb66d960771ce/types_python_dateutil-2.9.0.20240316-py3-none-any.whl (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: types-python-dateutil, setuptools, ruamel.yaml, pydantic, pip, packaging, more-itertools, Jinja2, importlib_metadata, colorlog, build, cookiecutter\ninmanta.pip              DEBUG   Attempting uninstall: types-python-dateutil\ninmanta.pip              DEBUG   Found existing installation: types-python-dateutil 2.8.19.14\ninmanta.pip              DEBUG   Not uninstalling types-python-dateutil at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'types-python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: setuptools\ninmanta.pip              DEBUG   Found existing installation: setuptools 69.0.2\ninmanta.pip              DEBUG   Not uninstalling setuptools at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'setuptools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: ruamel.yaml\ninmanta.pip              DEBUG   Found existing installation: ruamel.yaml 0.18.5\ninmanta.pip              DEBUG   Not uninstalling ruamel-yaml at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'ruamel.yaml'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 1.10.13\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 23.3.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: packaging\ninmanta.pip              DEBUG   Found existing installation: packaging 23.2\ninmanta.pip              DEBUG   Not uninstalling packaging at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'packaging'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 10.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: Jinja2\ninmanta.pip              DEBUG   Found existing installation: Jinja2 3.1.2\ninmanta.pip              DEBUG   Not uninstalling jinja2 at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'Jinja2'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: importlib_metadata\ninmanta.pip              DEBUG   Found existing installation: importlib-metadata 7.0.0\ninmanta.pip              DEBUG   Not uninstalling importlib-metadata at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'importlib-metadata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.8.0\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 1.0.3\ninmanta.pip              DEBUG   Not uninstalling build at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cookiecutter\ninmanta.pip              DEBUG   Found existing installation: cookiecutter 2.5.0\ninmanta.pip              DEBUG   Not uninstalling cookiecutter at /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\ninmanta.pip              DEBUG   Can't uninstall 'cookiecutter'. No files were found to uninstall.\ninmanta.pip              DEBUG   Successfully installed Jinja2-3.1.3 build-1.1.1 colorlog-6.8.2 cookiecutter-2.6.0 importlib_metadata-7.0.2 more-itertools-10.2.0 packaging-24.0 pip-24.0 pydantic-1.10.14 ruamel.yaml-0.18.6 setuptools-69.2.0 types-python-dateutil-2.9.0.20240316\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   [notice] A new release of pip is available: 23.3.1 -> 24.0\ninmanta.pip              DEBUG   [notice] To update, run: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade pip\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 2 misses (50%)\ninmanta.module           INFO    Performing fetch on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240316)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	e7265253-3331-47d9-8f57-1fff2d6f96d3
632c1e32-2d18-4964-a8c8-e02ad7bae1b8	2024-03-18 09:10:43.207492+01	2024-03-18 09:10:43.589144+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	ec402e66-196c-48de-b3a0-bce1bbc4ed78
37f49046-13da-4f76-9b4f-82bf3678071c	2024-03-18 09:10:40.546109+01	2024-03-18 09:10:41.308556+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m inmanta.app -vvv export -X -e f015501d-e9e9-4016-914d-c7e214ae28bc --server_address localhost --server_port 57497 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpf9nwxflx --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.136 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.1\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/file/23a9571ecf590d553a738634f7f1bfaca0a4bfb5\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/file/10d63b01c1ec8269f9b10edcb9740cf3519299dc\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/file/8840b9601481957a2f2d263f1603b89e6746156e\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/codebatched/1\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=1 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=1 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.041 seconds\nexporter       DEBUG   The entire export command took 0.208 seconds\n	0	e7265253-3331-47d9-8f57-1fff2d6f96d3
7738b1a1-792a-40d1-a957-9e1691fecf0c	2024-03-18 09:10:43.201023+01	2024-03-18 09:10:43.202367+01		Init		Using extra environment variables during compile \n	0	ec402e66-196c-48de-b3a0-bce1bbc4ed78
c995da32-30a4-4929-8528-dbbe80a0d7d8	2024-03-18 09:11:10.567235+01	2024-03-18 09:11:10.567954+01		Init		Using extra environment variables during compile \n	0	6e015f0d-6e1f-444c-ac67-79b14d3e1b3b
71cec7b5-0b15-47e7-99b4-42eaba969831	2024-03-18 09:11:10.572405+01	2024-03-18 09:11:10.988564+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6e015f0d-6e1f-444c-ac67-79b14d3e1b3b
bfb1fb9e-7e35-4726-a88d-55cf7f30f0d7	2024-03-18 09:10:43.59037+01	2024-03-18 09:11:09.552171+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 email_validator<3,>=1.3 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240316)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 email_validator<3,>=1.3 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240316)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	ec402e66-196c-48de-b3a0-bce1bbc4ed78
93c354ff-9cfe-4565-83ad-7026677e9c48	2024-03-18 09:11:35.728567+01	2024-03-18 09:11:36.387899+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m inmanta.app -vvv export -X -e f015501d-e9e9-4016-914d-c7e214ae28bc --server_address localhost --server_port 57497 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpv90na5z4 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.119 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.1\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/codebatched/3\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=3 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=3 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.014 seconds\nexporter       DEBUG   The entire export command took 0.161 seconds\n	0	6e015f0d-6e1f-444c-ac67-79b14d3e1b3b
fc7c153f-81ff-4c1f-8a92-3426fb477f67	2024-03-18 09:11:36.542359+01	2024-03-18 09:11:36.5431+01		Init		Using extra environment variables during compile \n	0	af289eeb-3e7d-42d1-9c6e-e8bea761d4af
f70dce86-3442-402b-a7d5-3630f6a0557f	2024-03-18 09:11:36.547704+01	2024-03-18 09:11:36.908694+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.7.4.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	af289eeb-3e7d-42d1-9c6e-e8bea761d4af
d5f5a81b-8a92-43d3-9d4d-084a4ab998e4	2024-03-18 09:11:09.553389+01	2024-03-18 09:11:10.282178+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m inmanta.app -vvv export -X -e f015501d-e9e9-4016-914d-c7e214ae28bc --server_address localhost --server_port 57497 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp6tk8f_0l --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.125 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.1\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.005 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/codebatched/2\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=2 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=2 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.017 seconds\nexporter       DEBUG   The entire export command took 0.172 seconds\n	0	ec402e66-196c-48de-b3a0-bce1bbc4ed78
e7bddf05-2ddc-408d-abce-775e1f8dcb93	2024-03-18 09:11:10.989709+01	2024-03-18 09:11:35.727284+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240316)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240316)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	6e015f0d-6e1f-444c-ac67-79b14d3e1b3b
25c581ac-e2fd-4973-b88e-cef56305da68	2024-03-18 09:12:00.080138+01	2024-03-18 09:12:00.79386+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m inmanta.app -vvv export -X -e f015501d-e9e9-4016-914d-c7e214ae28bc --server_address localhost --server_port 57497 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmprc2xw3lk --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       DEBUG   Starting compile\ncompiler       WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ncompiler       INFO    verifying project\ncompiler       DEBUG   Loading module: inmanta_plugins.std\ncompiler       DEBUG   Plugin loading took 0.116 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V1 modules:\ncompiler       INFO      std: 5.1.1\ncompiler       WARNING TypeDeprecationWarning: Type 'number' is deprecated, use 'float' or 'int' instead\ncompiler       DEBUG   Compilation took 0.004 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v2/reserve_version\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       DEBUG   Start transport for client compiler\nexporter       INFO    Sending resources and handler source to server\nexporter       INFO    Uploading source files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v1/file\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/codebatched/4\nexporter       INFO    Uploading 1 files\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:57497/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::File[localhost,path=/tmp/test],v=4 not in any resource set\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=4 not in any resource set\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:57497/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.015 seconds\nexporter       DEBUG   The entire export command took 0.160 seconds\n	0	af289eeb-3e7d-42d1-9c6e-e8bea761d4af
fc686e49-2bbd-4e07-b790-410efe021a85	2024-03-18 09:11:36.91044+01	2024-03-18 09:12:00.078699+01	/tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 Jinja2<4,>=3.1 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240316)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.module           INFO    Checking out 5.1.1 on /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmph03hi3o7/server/environments/f015501d-e9e9-4016-914d-c7e214ae28bc/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 Jinja2<4,>=3.1 pydantic<3,>=1.10 inmanta-core==8.7.4.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in ./.env/lib/python3.9/site-packages (3.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.14)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/cc4/6fce866075808/pydantic-2.6.4-py3-none-any.whl (394 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.7.4.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.7.4.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.29.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (41.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<8,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (7.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (10.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (24.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (69.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions<4.10,>=4.8 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (4.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.18.6)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from inmanta-core==8.7.4.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.6)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.5)\ninmanta.pip              DEBUG   Requirement already satisfied: async-timeout>=4.0.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from asyncpg~=0.25->inmanta-core==8.7.4.dev0) (4.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from build~=1.0->inmanta-core==8.7.4.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (13.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from importlib_metadata<8,>=4->inmanta-core==8.7.4.dev0) (3.18.1)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.7.4.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.7.4.dev0) (0.2.8)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==8.7.4.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==8.7.4.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2024.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in ./.env/lib/python3.9/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.9.0.20240316)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (2.17.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core39/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==8.7.4.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\n	0	af289eeb-3e7d-42d1-9c6e-e8bea761d4af
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set, last_success, last_produced_events) FROM stdin;
f015501d-e9e9-4016-914d-c7e214ae28bc	1	std::AgentConfig[internal,agentname=localhost]	internal	2024-03-18 09:10:42.065276+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-03-18 09:10:42.000001+01	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	1	std::File[localhost,path=/tmp/test]	localhost	2024-03-18 09:10:43.124215+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	2	std::AgentConfig[internal,agentname=localhost]	internal	2024-03-18 09:11:10.508564+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-03-18 09:11:10.495067+01	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	2	std::File[localhost,path=/tmp/test]	localhost	2024-03-18 09:11:10.513162+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	3	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	3	std::AgentConfig[internal,agentname=localhost]	internal	2024-03-18 09:11:36.526347+01	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2024-03-18 09:11:10.495067+01	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	4	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	4	std::AgentConfig[internal,agentname=localhost]	internal	\N	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	available	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	available	\N	\N	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	5	test::Resource[agent2,key=key2]	agent2	\N	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	available	{}	test::Resource	key2	available	set-a	\N	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	5	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
f015501d-e9e9-4016-914d-c7e214ae28bc	5	std::AgentConfig[internal,agentname=localhost]	internal	\N	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	available	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	available	\N	\N	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
4297ec2b-f83e-4006-9d4e-f2cb3059fad2	store	2024-03-18 09:10:41.172793+01	2024-03-18 09:10:41.181753+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2024-03-18T09:10:41.181773+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	1	{"std::AgentConfig[internal,agentname=localhost],v=1","std::File[localhost,path=/tmp/test],v=1"}
d08d530b-0a06-46fa-8691-f1f828b84523	pull	2024-03-18 09:10:41.929536+01	2024-03-18 09:10:41.937585+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2024-03-18T09:10:41.937603+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1f933a9f-262f-42eb-9123-c451035b4427	deploy	2024-03-18 09:10:42.000001+01	2024-03-18 09:10:42.065276+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2024-03-18 09:10:41+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2024-03-18 09:10:41+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"a79905e6-25a1-43bd-8a88-fc32307defd7\\"}, \\"timestamp\\": \\"2024-03-18T09:10:41.990620+01:00\\"}","{\\"msg\\": \\"Start deploy a79905e6-25a1-43bd-8a88-fc32307defd7 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"a79905e6-25a1-43bd-8a88-fc32307defd7\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2024-03-18T09:10:42.023960+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-18T09:10:42.025825+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-18T09:10:42.036226+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy a79905e6-25a1-43bd-8a88-fc32307defd7\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"a79905e6-25a1-43bd-8a88-fc32307defd7\\"}, \\"timestamp\\": \\"2024-03-18T09:10:42.047356+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	f015501d-e9e9-4016-914d-c7e214ae28bc	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
fea64771-e2e7-4cba-bf46-67e51dc12a51	pull	2024-03-18 09:10:43.082475+01	2024-03-18 09:10:43.084176+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2024-03-18T09:10:43.084193+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	1	{"std::File[localhost,path=/tmp/test],v=1"}
f1fa6716-3e60-40d4-8a18-3bfac01396b4	deploy	2024-03-18 09:10:43.103576+01	2024-03-18 09:10:43.124215+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2024-03-18 09:10:43+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2024-03-18 09:10:43+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"351ca267-835e-4554-8350-9d0c5643c91b\\"}, \\"timestamp\\": \\"2024-03-18T09:10:43.100292+01:00\\"}","{\\"msg\\": \\"Start deploy 351ca267-835e-4554-8350-9d0c5643c91b of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"351ca267-835e-4554-8350-9d0c5643c91b\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-03-18T09:10:43.106980+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-18T09:10:43.107978+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-18T09:10:43.108170+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 902, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmph03hi3o7/f015501d-e9e9-4016-914d-c7e214ae28bc/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 220, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 609, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-03-18T09:10:43.119837+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 351ca267-835e-4554-8350-9d0c5643c91b\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"351ca267-835e-4554-8350-9d0c5643c91b\\"}, \\"timestamp\\": \\"2024-03-18T09:10:43.120262+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	f015501d-e9e9-4016-914d-c7e214ae28bc	1	{"std::File[localhost,path=/tmp/test],v=1"}
cfa7a648-97dd-4924-829f-d4c062de41f2	store	2024-03-18 09:11:10.162527+01	2024-03-18 09:11:10.164571+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2024-03-18T09:11:10.164587+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
0fc33e9e-bf5e-4b86-8399-b51dcf885713	deploy	2024-03-18 09:11:10.416987+01	2024-03-18 09:11:10.416987+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2024-03-18T08:11:10.416987+00:00\\"}"}	deployed	\N	nochange	f015501d-e9e9-4016-914d-c7e214ae28bc	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
d9377c24-501b-418a-ae1a-c8bd752a1757	pull	2024-03-18 09:11:10.470465+01	2024-03-18 09:11:10.474068+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2024-03-18T09:11:10.474091+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
0c5eb025-b668-4628-b75a-286db6ae61d7	pull	2024-03-18 09:11:10.47097+01	2024-03-18 09:11:10.476135+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2024-03-18T09:11:10.476155+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	2	{"std::File[localhost,path=/tmp/test],v=2"}
346cfa1d-a797-4bb1-9b49-8d86c4d370c8	deploy	2024-03-18 09:11:36.526347+01	2024-03-18 09:11:36.526347+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2024-03-18T08:11:36.526347+00:00\\"}"}	deployed	\N	nochange	f015501d-e9e9-4016-914d-c7e214ae28bc	3	{"std::AgentConfig[internal,agentname=localhost],v=3"}
18f72d17-7f7c-4a9e-bae8-ddc986e2fbb9	store	2024-03-18 09:12:00.66302+01	2024-03-18 09:12:00.664679+01	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2024-03-18T09:12:00.664691+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	4	{"std::File[localhost,path=/tmp/test],v=4","std::AgentConfig[internal,agentname=localhost],v=4"}
0b4673ad-592c-4359-b3b0-f16c444a33c5	store	2024-03-18 09:12:00.862107+01	2024-03-18 09:12:00.864357+01	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2024-03-18T09:12:00.864364+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	5	{"test::Resource[agent2,key=key2],v=5","std::AgentConfig[internal,agentname=localhost],v=5","std::File[localhost,path=/tmp/test],v=5"}
3c9327bb-2bcd-47b3-a268-ad4a4411b44a	deploy	2024-03-18 09:11:10.495067+01	2024-03-18 09:11:10.508564+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"f44e5a37-bda8-4378-bbaf-1ee0854ba686\\"}, \\"timestamp\\": \\"2024-03-18T09:11:10.491522+01:00\\"}","{\\"msg\\": \\"Start deploy f44e5a37-bda8-4378-bbaf-1ee0854ba686 of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"f44e5a37-bda8-4378-bbaf-1ee0854ba686\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2024-03-18T09:11:10.498312+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-18T09:11:10.498843+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy f44e5a37-bda8-4378-bbaf-1ee0854ba686\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"f44e5a37-bda8-4378-bbaf-1ee0854ba686\\"}, \\"timestamp\\": \\"2024-03-18T09:11:10.504109+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	f015501d-e9e9-4016-914d-c7e214ae28bc	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
b75de9d1-337e-4bb6-afdd-ac960781022a	deploy	2024-03-18 09:11:10.500805+01	2024-03-18 09:11:10.513162+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"9f222a68-92a6-4788-a5c5-9cef4e2898f2\\"}, \\"timestamp\\": \\"2024-03-18T09:11:10.496720+01:00\\"}","{\\"msg\\": \\"Start deploy 9f222a68-92a6-4788-a5c5-9cef4e2898f2 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"9f222a68-92a6-4788-a5c5-9cef4e2898f2\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-03-18T09:11:10.505676+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2024-03-18T09:11:10.506175+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2024-03-18T09:11:10.508660+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmph03hi3o7/f015501d-e9e9-4016-914d-c7e214ae28bc/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 609, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2024-03-18T09:11:10.509009+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 9f222a68-92a6-4788-a5c5-9cef4e2898f2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"9f222a68-92a6-4788-a5c5-9cef4e2898f2\\"}, \\"timestamp\\": \\"2024-03-18T09:11:10.509235+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	f015501d-e9e9-4016-914d-c7e214ae28bc	2	{"std::File[localhost,path=/tmp/test],v=2"}
cf81710f-af78-4308-8022-b24ba5ea7380	store	2024-03-18 09:11:36.307291+01	2024-03-18 09:11:36.308551+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2024-03-18T09:11:36.308562+01:00\\"}"}	\N	\N	\N	f015501d-e9e9-4016-914d-c7e214ae28bc	3	{"std::AgentConfig[internal,agentname=localhost],v=3","std::File[localhost,path=/tmp/test],v=3"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
f015501d-e9e9-4016-914d-c7e214ae28bc	4297ec2b-f83e-4006-9d4e-f2cb3059fad2	std::AgentConfig[internal,agentname=localhost]	1
f015501d-e9e9-4016-914d-c7e214ae28bc	4297ec2b-f83e-4006-9d4e-f2cb3059fad2	std::File[localhost,path=/tmp/test]	1
f015501d-e9e9-4016-914d-c7e214ae28bc	d08d530b-0a06-46fa-8691-f1f828b84523	std::AgentConfig[internal,agentname=localhost]	1
f015501d-e9e9-4016-914d-c7e214ae28bc	1f933a9f-262f-42eb-9123-c451035b4427	std::AgentConfig[internal,agentname=localhost]	1
f015501d-e9e9-4016-914d-c7e214ae28bc	fea64771-e2e7-4cba-bf46-67e51dc12a51	std::File[localhost,path=/tmp/test]	1
f015501d-e9e9-4016-914d-c7e214ae28bc	f1fa6716-3e60-40d4-8a18-3bfac01396b4	std::File[localhost,path=/tmp/test]	1
f015501d-e9e9-4016-914d-c7e214ae28bc	cfa7a648-97dd-4924-829f-d4c062de41f2	std::File[localhost,path=/tmp/test]	2
f015501d-e9e9-4016-914d-c7e214ae28bc	cfa7a648-97dd-4924-829f-d4c062de41f2	std::AgentConfig[internal,agentname=localhost]	2
f015501d-e9e9-4016-914d-c7e214ae28bc	0fc33e9e-bf5e-4b86-8399-b51dcf885713	std::AgentConfig[internal,agentname=localhost]	2
f015501d-e9e9-4016-914d-c7e214ae28bc	d9377c24-501b-418a-ae1a-c8bd752a1757	std::AgentConfig[internal,agentname=localhost]	2
f015501d-e9e9-4016-914d-c7e214ae28bc	0c5eb025-b668-4628-b75a-286db6ae61d7	std::File[localhost,path=/tmp/test]	2
f015501d-e9e9-4016-914d-c7e214ae28bc	3c9327bb-2bcd-47b3-a268-ad4a4411b44a	std::AgentConfig[internal,agentname=localhost]	2
f015501d-e9e9-4016-914d-c7e214ae28bc	b75de9d1-337e-4bb6-afdd-ac960781022a	std::File[localhost,path=/tmp/test]	2
f015501d-e9e9-4016-914d-c7e214ae28bc	cf81710f-af78-4308-8022-b24ba5ea7380	std::AgentConfig[internal,agentname=localhost]	3
f015501d-e9e9-4016-914d-c7e214ae28bc	cf81710f-af78-4308-8022-b24ba5ea7380	std::File[localhost,path=/tmp/test]	3
f015501d-e9e9-4016-914d-c7e214ae28bc	346cfa1d-a797-4bb1-9b49-8d86c4d370c8	std::AgentConfig[internal,agentname=localhost]	3
f015501d-e9e9-4016-914d-c7e214ae28bc	18f72d17-7f7c-4a9e-bae8-ddc986e2fbb9	std::File[localhost,path=/tmp/test]	4
f015501d-e9e9-4016-914d-c7e214ae28bc	18f72d17-7f7c-4a9e-bae8-ddc986e2fbb9	std::AgentConfig[internal,agentname=localhost]	4
f015501d-e9e9-4016-914d-c7e214ae28bc	0b4673ad-592c-4359-b3b0-f16c444a33c5	test::Resource[agent2,key=key2]	5
f015501d-e9e9-4016-914d-c7e214ae28bc	0b4673ad-592c-4359-b3b0-f16c444a33c5	std::AgentConfig[internal,agentname=localhost]	5
f015501d-e9e9-4016-914d-c7e214ae28bc	0b4673ad-592c-4359-b3b0-f16c444a33c5	std::File[localhost,path=/tmp/test]	5
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304070,202306060,202308010,202308020,202308100,202309130,202310040,202310090,202310180,202402130}
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

