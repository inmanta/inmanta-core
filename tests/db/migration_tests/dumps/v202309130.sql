--
-- PostgreSQL database dump
--

-- Dumped from database version 15.4
-- Dumped by pg_dump version 15.4

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
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	internal	2023-09-15 13:28:03.702971+02	f	9ecbc0d3-6127-414f-b55e-d963fa88e650	\N
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	localhost	2023-09-15 13:28:04.801912+02	f	1e63e909-1ad1-4ea0-978d-83a9fceee5ae	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
9ecbc0d3-6127-414f-b55e-d963fa88e650	ef2e43aa-53ba-11ee-94e0-58ce2a79a3a6	internal	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72
1e63e909-1ad1-4ea0-978d-83a9fceee5ae	ef2e43aa-53ba-11ee-94e0-58ce2a79a3a6	localhost	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
sentinella	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:28:03.702971+02	2023-09-15 13:28:54.65057+02	\N	ef2e43aa-53ba-11ee-94e0-58ce2a79a3a6
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Service	1	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::File	1	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Directory	1	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Package	1	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Symlink	1	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::testing::NullResource	1	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::AgentConfig	1	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Service	2	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::File	2	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Directory	2	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Package	2	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Symlink	2	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::testing::NullResource	2	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::AgentConfig	2	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Service	3	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::File	3	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Directory	3	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Package	3	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Symlink	3	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::testing::NullResource	3	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::AgentConfig	3	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Service	4	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::File	4	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Directory	4	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Package	4	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::Symlink	4	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::testing::NullResource	4	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	std::AgentConfig	4	{"5dacd13a846cb6171754e26365f939b509fb151e": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<3"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
41ec4be4-570e-4a18-99d4-8726abe34537	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:27:45.578234+02	2023-09-15 13:28:03.289981+02	2023-09-15 13:27:45.572775+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	e372c757-3b3f-43c4-8df0-b4216f7f3138	t	\N	{"errors": []}	f	{}	\N	\N	\N
a7ae39eb-ef5b-42f1-a02c-1cfefb3a87b1	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:28:04.908417+02	2023-09-15 13:28:21.002344+02	2023-09-15 13:28:04.903758+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	b7a14647-cd3c-42b8-9a49-ed5f71da4aca	t	\N	{"errors": []}	f	{}	\N	\N	\N
7eb643b0-7935-4dab-887a-ab5bde2482a8	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:28:21.163325+02	2023-09-15 13:28:37.48341+02	2023-09-15 13:28:21.157355+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	3	2e96df28-a261-4178-87a9-e67703782312	t	\N	{"errors": []}	f	{}	\N	\N	\N
41674c1e-d041-46fd-83ea-3d7586a3cdee	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:28:37.58704+02	2023-09-15 13:28:54.647181+02	2023-09-15 13:28:37.553855+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	4	f94f55c9-4c11-4132-be3a-3902350bf51f	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles) FROM stdin;
1	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:28:03.197069+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "wouter", "hostname": "sentinella", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
2	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:28:20.911724+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "wouter", "hostname": "sentinella", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
3	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:28:37.397238+02	t	f	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "wouter", "hostname": "sentinella", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
4	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2023-09-15 13:28:54.519715+02	f	f	pending	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "wouter", "hostname": "sentinella", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
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
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	dev-2	7750ca4b-4cde-4d86-bc2e-0976a34e7591			{"auto_full_compile": ""}	0	f		
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	dev-1	7750ca4b-4cde-4d86-bc2e-0976a34e7591			{"auto_deploy": false, "server_compile": true, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0}	4	f		
\.


--
-- Data for Name: environmentmetricsgauge; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricsgauge (environment, metric_name, "timestamp", count, category) FROM stdin;
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	1	deployed
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	1	available
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	skipped
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	0	skipped
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	dry
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	0	dry
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	deployed
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	failed
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	0	failed
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	deploying
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	0	deploying
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	available
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	cancelled
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	0	cancelled
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	undefined
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	0	undefined
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	skipped_for_undefined
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.resource_count	2023-09-15 13:28:45.529401+02	0	unavailable
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	0	skipped_for_undefined
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.resource_count	2023-09-15 13:28:45.529401+02	0	unavailable
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.agent_count	2023-09-15 13:28:45.529401+02	0	down
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.agent_count	2023-09-15 13:28:45.529401+02	0	paused
06e5ca33-4020-4bac-b9a6-0cff862bbfe0	resource.agent_count	2023-09-15 13:28:45.529401+02	0	up
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.agent_count	2023-09-15 13:28:45.529401+02	0	down
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.agent_count	2023-09-15 13:28:45.529401+02	0	paused
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	resource.agent_count	2023-09-15 13:28:45.529401+02	2	up
\.


--
-- Data for Name: environmentmetricstimer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricstimer (environment, metric_name, "timestamp", count, value, category) FROM stdin;
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	orchestrator.compile_waiting_time	2023-09-15 13:28:45.529401+02	4	0.049273	__None__
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	orchestrator.compile_time	2023-09-15 13:28:45.529401+02	3	50.125759	__None__
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
7750ca4b-4cde-4d86-bc2e-0976a34e7591	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
f07d97e6-ed86-4e9a-a7ed-6ff875f9c488	2023-09-15 13:27:45.578748+02	2023-09-15 13:27:45.580309+02		Init		Using extra environment variables during compile \n	0	41ec4be4-570e-4a18-99d4-8726abe34537
f7d015a6-06a5-41a3-911a-08aa9a4df5ae	2023-09-15 13:27:45.580738+02	2023-09-15 13:27:45.581841+02		Creating venv			0	41ec4be4-570e-4a18-99d4-8726abe34537
8ef2550d-dd29-4206-8c46-6c23c103e407	2023-09-15 13:27:45.583446+02	2023-09-15 13:27:45.88833+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.4.0.dev0\nNot uninstalling inmanta-core at /home/wouter/projects/inmanta/src, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	41ec4be4-570e-4a18-99d4-8726abe34537
ea7d3196-78ce-49a6-85d3-e33dc5bc9f33	2023-09-15 13:28:36.831747+02	2023-09-15 13:28:37.482557+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m inmanta.app -vvv export -X -e 7c7e012d-33d9-44b7-9efa-4c3b1efe9e72 --server_address localhost --server_port 51597 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp66i0l69s --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004071 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000093 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.2.0\ninmanta.execute.schedulerINFO    Total compilation time 0.003094\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/codebatched/3\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=3 not in any resource set\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=3 not in any resource set\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/version\ninmanta.export           INFO    Committed resources with version 3\n	0	7eb643b0-7935-4dab-887a-ab5bde2482a8
c1b9aa1a-62ca-48d1-bf8e-6f23958327f9	2023-09-15 13:28:37.593477+02	2023-09-15 13:28:37.830464+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.4.0.dev0\nNot uninstalling inmanta-core at /home/wouter/projects/inmanta/src, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	41674c1e-d041-46fd-83ea-3d7586a3cdee
5d50cee0-43b6-4e66-beb9-efc46c3e1ed9	2023-09-15 13:28:37.588511+02	2023-09-15 13:28:37.591158+02		Init		Using extra environment variables during compile \n	0	41674c1e-d041-46fd-83ea-3d7586a3cdee
950f9054-cf7d-4728-b87a-df420b84eceb	2023-09-15 13:27:45.889409+02	2023-09-15 13:28:02.634107+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.2.0 in /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000082 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==9.4.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.12)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/45b/5e446c6dfaad9/pydantic-2.3.0-py3-none-any.whl (374 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.4.0.dev0 in /home/wouter/projects/inmanta/src (9.4.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pydantic<3,>=1.10) (4.5.0)\ninmanta.pip              DEBUG   Collecting typing-extensions>=4.2.0 (from pydantic<3,>=1.10)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/440/d5dd3af93b060/typing_extensions-4.7.1-py3-none-any.whl (33 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (2.3.0)\ninmanta.pip              DEBUG   Collecting dnspython>=2.0.0 (from email_validator<3,>=1.3)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/57c/6fbaaeaaf39c8/dnspython-2.4.2-py3-none-any.whl (300 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from Jinja2<4,>=3.1) (2.1.2)\ninmanta.pip              DEBUG   Collecting MarkupSafe>=2.0 (from Jinja2<4,>=3.1)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/65c/1a9bcdadc6c28/MarkupSafe-2.1.3-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (25 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/70c/a6ea68fe63ecc/python_slugify-8.0.1-py2.py3-none-any.whl (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<42,>=36->inmanta-core==9.4.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Collecting zipp>=0.5 (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/679/e51dd4403591b/zipp-3.16.2-py3-none-any.whl (7.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==9.4.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.4.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.9->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Collecting chardet>=3.0.2 (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/e1c/f59446890a001/chardet-5.2.0-py3-none-any.whl (199 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.4.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Collecting charset-normalizer<4,>=2 (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/193/cbc708ea3aca4/charset_normalizer-3.2.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (201 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.26.15)\ninmanta.pip              DEBUG   Collecting urllib3<3,>=1.21.1 (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/de7/df1803967d2c2/urllib3-2.0.4-py3-none-any.whl (123 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Collecting certifi>=2017.4.17 (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/92d/6037539857d82/certifi-2023.7.22-py3-none-any.whl (158 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: zipp, urllib3, typing-extensions, python-slugify, MarkupSafe, dnspython, charset-normalizer, chardet, certifi\ninmanta.pip              DEBUG   Attempting uninstall: zipp\ninmanta.pip              DEBUG   Found existing installation: zipp 3.15.0\ninmanta.pip              DEBUG   Not uninstalling zipp at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'zipp'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: urllib3\ninmanta.pip              DEBUG   Found existing installation: urllib3 1.26.15\ninmanta.pip              DEBUG   Not uninstalling urllib3 at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: typing-extensions\ninmanta.pip              DEBUG   Found existing installation: typing_extensions 4.5.0\ninmanta.pip              DEBUG   Not uninstalling typing-extensions at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'typing_extensions'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: MarkupSafe\ninmanta.pip              DEBUG   Found existing installation: MarkupSafe 2.1.2\ninmanta.pip              DEBUG   Not uninstalling markupsafe at /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'MarkupSafe'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: dnspython\ninmanta.pip              DEBUG   Found existing installation: dnspython 2.3.0\ninmanta.pip              DEBUG   Not uninstalling dnspython at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'dnspython'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: charset-normalizer\ninmanta.pip              DEBUG   Found existing installation: charset-normalizer 3.1.0\ninmanta.pip              DEBUG   Not uninstalling charset-normalizer at /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: chardet\ninmanta.pip              DEBUG   Found existing installation: chardet 5.1.0\ninmanta.pip              DEBUG   Not uninstalling chardet at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'chardet'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: certifi\ninmanta.pip              DEBUG   Found existing installation: certifi 2022.12.7\ninmanta.pip              DEBUG   Not uninstalling certifi at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\ninmanta.pip              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   botocore 1.29.161 requires urllib3<1.27,>=1.25.4, but you have urllib3 2.0.4 which is incompatible.\ninmanta.pip              DEBUG   google-auth 2.21.0 requires urllib3<2.0, but you have urllib3 2.0.4 which is incompatible.\ninmanta.pip              DEBUG   pyadr 0.19.0 requires python-slugify<7,>=6, but you have python-slugify 8.0.1 which is incompatible.\ninmanta.pip              DEBUG   sphinx-rtd-theme 1.1.1 requires docutils<0.18, but you have docutils 0.19 which is incompatible.\ninmanta.pip              DEBUG   sphinx-rtd-theme 1.1.1 requires sphinx<6,>=1.6, but you have sphinx 7.2.6 which is incompatible.\ninmanta.pip              DEBUG   sphinx-tabs 3.3.1 requires docutils~=0.17.0, but you have docutils 0.19 which is incompatible.\ninmanta.pip              DEBUG   sphinx-tabs 3.3.1 requires sphinx<5,>=2, but you have sphinx 7.2.6 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed MarkupSafe-2.1.3 certifi-2023.7.22 chardet-5.2.0 charset-normalizer-3.2.0 dnspython-2.4.2 python-slugify-8.0.1 typing-extensions-4.7.1 urllib3-2.0.4 zipp-3.16.2\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000037 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==9.4.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.12)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/45b/5e446c6dfaad9/pydantic-2.3.0-py3-none-any.whl (374 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.4.0.dev0 in /home/wouter/projects/inmanta/src (9.4.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in ./.env/lib/python3.10/site-packages (from pydantic<3,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.10/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.10/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<42,>=36->inmanta-core==9.4.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==9.4.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.4.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.9->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.4.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\n	0	41ec4be4-570e-4a18-99d4-8726abe34537
973d1b3a-d7d2-4fe4-b5be-8976280f0db6	2023-09-15 13:28:04.908841+02	2023-09-15 13:28:04.909882+02		Init		Using extra environment variables during compile \n	0	a7ae39eb-ef5b-42f1-a02c-1cfefb3a87b1
639e5c1a-a176-495a-a91e-3783cde6dac5	2023-09-15 13:28:02.634993+02	2023-09-15 13:28:03.289265+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m inmanta.app -vvv export -X -e 7c7e012d-33d9-44b7-9efa-4c3b1efe9e72 --server_address localhost --server_port 51597 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpv7s7ynz8 --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004189 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000079 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.2.0\ninmanta.execute.schedulerINFO    Total compilation time 0.003202\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/file/f20255abb8beb130e89ef3bdae958974f15163ed\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/file/5dacd13a846cb6171754e26365f939b509fb151e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1 not in any resource set\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1 not in any resource set\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	41ec4be4-570e-4a18-99d4-8726abe34537
26e68da7-3b9f-4793-a02b-148504eeb801	2023-09-15 13:28:04.911718+02	2023-09-15 13:28:05.156551+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.4.0.dev0\nNot uninstalling inmanta-core at /home/wouter/projects/inmanta/src, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	a7ae39eb-ef5b-42f1-a02c-1cfefb3a87b1
2fe1a68c-e31a-40cd-92fe-b7a87acaf91d	2023-09-15 13:28:05.157775+02	2023-09-15 13:28:20.330302+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000065 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 email_validator<3,>=1.3 pydantic<3,>=1.10 inmanta-core==9.4.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.12)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/45b/5e446c6dfaad9/pydantic-2.3.0-py3-none-any.whl (374 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.4.0.dev0 in /home/wouter/projects/inmanta/src (9.4.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.10/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.10/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in ./.env/lib/python3.10/site-packages (from pydantic<3,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<42,>=36->inmanta-core==9.4.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==9.4.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.4.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.9->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.4.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000038 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 email_validator<3,>=1.3 pydantic<3,>=1.10 inmanta-core==9.4.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.12)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/45b/5e446c6dfaad9/pydantic-2.3.0-py3-none-any.whl (374 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.4.0.dev0 in /home/wouter/projects/inmanta/src (9.4.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.10/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.10/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in ./.env/lib/python3.10/site-packages (from pydantic<3,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<42,>=36->inmanta-core==9.4.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==9.4.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.4.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.9->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.4.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\n	0	a7ae39eb-ef5b-42f1-a02c-1cfefb3a87b1
c7e56a0f-a6fd-4982-bfc8-19216d8d22a8	2023-09-15 13:28:20.331382+02	2023-09-15 13:28:21.001469+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m inmanta.app -vvv export -X -e 7c7e012d-33d9-44b7-9efa-4c3b1efe9e72 --server_address localhost --server_port 51597 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp_y80rbh2 --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.003961 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000100 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.2.0\ninmanta.execute.schedulerINFO    Total compilation time 0.003193\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2 not in any resource set\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2 not in any resource set\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	a7ae39eb-ef5b-42f1-a02c-1cfefb3a87b1
29111741-7ca5-49f7-875a-cd6c15004b0a	2023-09-15 13:28:21.163711+02	2023-09-15 13:28:21.164379+02		Init		Using extra environment variables during compile \n	0	7eb643b0-7935-4dab-887a-ab5bde2482a8
0a49b1e6-3175-40dc-9bef-5f4e405ccda1	2023-09-15 13:28:21.165912+02	2023-09-15 13:28:21.40118+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.4.0.dev0\nNot uninstalling inmanta-core at /home/wouter/projects/inmanta/src, outside environment /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	7eb643b0-7935-4dab-887a-ab5bde2482a8
b2269db5-ffb8-429f-af42-3d1555046ed6	2023-09-15 13:28:21.402066+02	2023-09-15 13:28:36.830753+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000061 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==9.4.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.12)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/45b/5e446c6dfaad9/pydantic-2.3.0-py3-none-any.whl (374 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.4.0.dev0 in /home/wouter/projects/inmanta/src (9.4.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in ./.env/lib/python3.10/site-packages (from pydantic<3,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.10/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.10/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<42,>=36->inmanta-core==9.4.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==9.4.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.4.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.9->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.4.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000038 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==9.4.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.12)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/45b/5e446c6dfaad9/pydantic-2.3.0-py3-none-any.whl (374 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.4.0.dev0 in /home/wouter/projects/inmanta/src (9.4.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in ./.env/lib/python3.10/site-packages (from pydantic<3,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.10/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.10/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<42,>=36->inmanta-core==9.4.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==9.4.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.4.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.9->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.4.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\n	0	7eb643b0-7935-4dab-887a-ab5bde2482a8
de620a7b-0449-4805-a817-d77713a22b75	2023-09-15 13:28:37.831243+02	2023-09-15 13:28:53.956305+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000061 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==9.4.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.12)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/45b/5e446c6dfaad9/pydantic-2.3.0-py3-none-any.whl (374 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.4.0.dev0 in /home/wouter/projects/inmanta/src (9.4.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in ./.env/lib/python3.10/site-packages (from pydantic<3,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.10/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.10/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<42,>=36->inmanta-core==9.4.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==9.4.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.4.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.9->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.4.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000041 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.module           INFO    Checking out 4.2.0 on /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<3,>=1.10 Jinja2<4,>=3.1 email_validator<3,>=1.3 inmanta-core==9.4.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<3,>=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.12)\ninmanta.pip              DEBUG   Collecting pydantic<3,>=1.10\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/45b/5e446c6dfaad9/pydantic-2.3.0-py3-none-any.whl (374 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.4.0.dev0 in /home/wouter/projects/inmanta/src (9.4.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (8.1.7)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (6.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==9.4.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in ./.env/lib/python3.10/site-packages (from pydantic<3,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.10/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.10/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=1.0->inmanta-core==9.4.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<42,>=36->inmanta-core==9.4.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.4.0.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==9.4.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.4.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.9->inmanta-core==9.4.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.4.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.4.0.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\n	0	41674c1e-d041-46fd-83ea-3d7586a3cdee
f547f394-ff92-4677-a9c2-e7a3cda5f31a	2023-09-15 13:28:53.957303+02	2023-09-15 13:28:54.646148+02	/tmp/tmp2c55dop3/server/environments/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/.env/bin/python -m inmanta.app -vvv export -X -e 7c7e012d-33d9-44b7-9efa-4c3b1efe9e72 --server_address localhost --server_port 51597 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpt7cv_kov --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004102 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint sphinx<5,>=2 and installed version 7.2.6 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint urllib3<2.0 and installed version 2.0.4 (from google-auth)\ninmanta.env              WARNING Incompatibility between constraint docutils<0.18 and installed version 0.19 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint docutils~=0.17.0 and installed version 0.19 (from sphinx-tabs)\ninmanta.env              WARNING Incompatibility between constraint sphinx<6,>=1.6 and installed version 7.2.6 (from sphinx-rtd-theme)\ninmanta.env              WARNING Incompatibility between constraint urllib3<1.27,>=1.25.4 and installed version 2.0.4 (from botocore)\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000113 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.2.0\ninmanta.execute.schedulerINFO    Total compilation time 0.003106\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/codebatched/4\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:51597/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=4 not in any resource set\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=4 not in any resource set\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:51597/api/v1/version\ninmanta.export           INFO    Committed resources with version 4\n	0	41674c1e-d041-46fd-83ea-3d7586a3cdee
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set, last_success, last_produced_events) FROM stdin;
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	1	std::AgentConfig[internal,agentname=localhost]	internal	2023-09-15 13:28:03.792976+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2023-09-15 13:28:03.78005+02	\N
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	1	std::File[localhost,path=/tmp/test]	localhost	2023-09-15 13:28:04.840799+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N	\N
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2	std::AgentConfig[internal,agentname=localhost]	internal	2023-09-15 13:28:21.073486+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2023-09-15 13:28:21.0642+02	\N
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2	std::File[localhost,path=/tmp/test]	localhost	2023-09-15 13:28:21.078496+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N	\N
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	3	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	3	std::AgentConfig[internal,agentname=localhost]	internal	2023-09-15 13:28:37.544361+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2023-09-15 13:28:21.0642+02	\N
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	4	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N	\N
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	4	std::AgentConfig[internal,agentname=localhost]	internal	\N	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	available	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	available	\N	\N	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
9302e557-fa32-422a-9066-a4a369c76fc1	store	2023-09-15 13:28:03.196974+02	2023-09-15 13:28:03.203738+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2023-09-15T13:28:03.203746+02:00\\"}"}	\N	\N	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
65b8ca58-4f5c-4e2e-a4f5-1bb3baa8ada7	pull	2023-09-15 13:28:03.712582+02	2023-09-15 13:28:03.719461+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-09-15T13:28:03.719471+02:00\\"}"}	\N	\N	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
396ab377-05c1-4b3e-ae2e-f396700bc386	deploy	2023-09-15 13:28:03.78005+02	2023-09-15 13:28:03.792976+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-09-15 13:28:03+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-09-15 13:28:03+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"4e295fde-dfd6-4b13-9ab3-908cc70be3cf\\"}, \\"timestamp\\": \\"2023-09-15T13:28:03.777041+02:00\\"}","{\\"msg\\": \\"Start deploy 4e295fde-dfd6-4b13-9ab3-908cc70be3cf of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"4e295fde-dfd6-4b13-9ab3-908cc70be3cf\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-09-15T13:28:03.781540+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-09-15T13:28:03.782197+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-09-15T13:28:03.784949+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 4e295fde-dfd6-4b13-9ab3-908cc70be3cf\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"4e295fde-dfd6-4b13-9ab3-908cc70be3cf\\"}, \\"timestamp\\": \\"2023-09-15T13:28:03.787673+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
42aceab4-18d8-44d7-9e46-ce056dd0d97b	pull	2023-09-15 13:28:04.809742+02	2023-09-15 13:28:04.815531+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-09-15T13:28:04.815542+02:00\\"}"}	\N	\N	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	1	{"std::File[localhost,path=/tmp/test],v=1"}
7ab5ccbd-f8e6-4d24-847c-b01ac84d4891	deploy	2023-09-15 13:28:04.833468+02	2023-09-15 13:28:04.840799+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2023-09-15 13:28:04+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2023-09-15 13:28:04+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"3de69e66-8710-40b5-88df-5647aeae2225\\"}, \\"timestamp\\": \\"2023-09-15T13:28:04.831064+02:00\\"}","{\\"msg\\": \\"Start deploy 3de69e66-8710-40b5-88df-5647aeae2225 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"3de69e66-8710-40b5-88df-5647aeae2225\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-09-15T13:28:04.835090+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-09-15T13:28:04.835774+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-09-15T13:28:04.835908+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 934, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmp2c55dop3/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 220, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-09-15T13:28:04.838191+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 3de69e66-8710-40b5-88df-5647aeae2225\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"3de69e66-8710-40b5-88df-5647aeae2225\\"}, \\"timestamp\\": \\"2023-09-15T13:28:04.838399+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	1	{"std::File[localhost,path=/tmp/test],v=1"}
29bc9be2-5ecd-4573-a1a2-dde70497de74	store	2023-09-15 13:28:20.91167+02	2023-09-15 13:28:20.913597+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2023-09-15T13:28:20.913605+02:00\\"}"}	\N	\N	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
1f3cc843-425f-45ff-8ec9-637a24a3b09a	deploy	2023-09-15 13:28:21.027037+02	2023-09-15 13:28:21.027037+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-09-15T11:28:21.027037+00:00\\"}"}	deployed	\N	nochange	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
5f12f05a-d9e3-4bd2-8419-ac48c66d2c19	pull	2023-09-15 13:28:21.04921+02	2023-09-15 13:28:21.050185+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-09-15T13:28:21.050191+02:00\\"}"}	\N	\N	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
b3ca2aeb-4373-467c-9e60-f88be54ef603	pull	2023-09-15 13:28:21.049106+02	2023-09-15 13:28:21.050463+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-09-15T13:28:21.050468+02:00\\"}"}	\N	\N	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2	{"std::File[localhost,path=/tmp/test],v=2"}
9b134073-c1ab-4199-8a1f-f58cef14426a	deploy	2023-09-15 13:28:21.071023+02	2023-09-15 13:28:21.078496+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"48ba82eb-10b0-4c98-aa9f-cd7c908e8d3f\\"}, \\"timestamp\\": \\"2023-09-15T13:28:21.066025+02:00\\"}","{\\"msg\\": \\"Start deploy 48ba82eb-10b0-4c98-aa9f-cd7c908e8d3f of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"48ba82eb-10b0-4c98-aa9f-cd7c908e8d3f\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-09-15T13:28:21.072471+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-09-15T13:28:21.072850+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"wouter\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"wouter\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-09-15T13:28:21.074825+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 941, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp2c55dop3/7c7e012d-33d9-44b7-9efa-4c3b1efe9e72/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-09-15T13:28:21.075087+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 48ba82eb-10b0-4c98-aa9f-cd7c908e8d3f\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"48ba82eb-10b0-4c98-aa9f-cd7c908e8d3f\\"}, \\"timestamp\\": \\"2023-09-15T13:28:21.075313+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2	{"std::File[localhost,path=/tmp/test],v=2"}
b19be623-c8e0-4830-aab5-7f846d21ad06	deploy	2023-09-15 13:28:21.0642+02	2023-09-15 13:28:21.073486+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"4d1e65cc-298e-423a-8a37-e23d340b2edd\\"}, \\"timestamp\\": \\"2023-09-15T13:28:21.058259+02:00\\"}","{\\"msg\\": \\"Start deploy 4d1e65cc-298e-423a-8a37-e23d340b2edd of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"4d1e65cc-298e-423a-8a37-e23d340b2edd\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-09-15T13:28:21.066793+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-09-15T13:28:21.067408+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy 4d1e65cc-298e-423a-8a37-e23d340b2edd\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"4d1e65cc-298e-423a-8a37-e23d340b2edd\\"}, \\"timestamp\\": \\"2023-09-15T13:28:21.071139+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
0c2b8c56-8e6c-4207-a1ce-537e826f6972	store	2023-09-15 13:28:37.397182+02	2023-09-15 13:28:37.398294+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2023-09-15T13:28:37.398300+02:00\\"}"}	\N	\N	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	3	{"std::AgentConfig[internal,agentname=localhost],v=3","std::File[localhost,path=/tmp/test],v=3"}
17c4092c-e44c-4472-b7d4-0a26a2e6affe	deploy	2023-09-15 13:28:37.544361+02	2023-09-15 13:28:37.544361+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-09-15T11:28:37.544361+00:00\\"}"}	deployed	\N	nochange	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	3	{"std::AgentConfig[internal,agentname=localhost],v=3"}
83c3fb8c-a16f-40c9-a743-d32cab8a8575	store	2023-09-15 13:28:54.519657+02	2023-09-15 13:28:54.522356+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2023-09-15T13:28:54.522369+02:00\\"}"}	\N	\N	\N	7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	4	{"std::AgentConfig[internal,agentname=localhost],v=4","std::File[localhost,path=/tmp/test],v=4"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	9302e557-fa32-422a-9066-a4a369c76fc1	std::File[localhost,path=/tmp/test]	1
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	9302e557-fa32-422a-9066-a4a369c76fc1	std::AgentConfig[internal,agentname=localhost]	1
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	65b8ca58-4f5c-4e2e-a4f5-1bb3baa8ada7	std::AgentConfig[internal,agentname=localhost]	1
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	396ab377-05c1-4b3e-ae2e-f396700bc386	std::AgentConfig[internal,agentname=localhost]	1
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	42aceab4-18d8-44d7-9e46-ce056dd0d97b	std::File[localhost,path=/tmp/test]	1
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	7ab5ccbd-f8e6-4d24-847c-b01ac84d4891	std::File[localhost,path=/tmp/test]	1
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	29bc9be2-5ecd-4573-a1a2-dde70497de74	std::File[localhost,path=/tmp/test]	2
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	29bc9be2-5ecd-4573-a1a2-dde70497de74	std::AgentConfig[internal,agentname=localhost]	2
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	1f3cc843-425f-45ff-8ec9-637a24a3b09a	std::AgentConfig[internal,agentname=localhost]	2
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	5f12f05a-d9e3-4bd2-8419-ac48c66d2c19	std::AgentConfig[internal,agentname=localhost]	2
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	b3ca2aeb-4373-467c-9e60-f88be54ef603	std::File[localhost,path=/tmp/test]	2
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	b19be623-c8e0-4830-aab5-7f846d21ad06	std::AgentConfig[internal,agentname=localhost]	2
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	9b134073-c1ab-4199-8a1f-f58cef14426a	std::File[localhost,path=/tmp/test]	2
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	0c2b8c56-8e6c-4207-a1ce-537e826f6972	std::AgentConfig[internal,agentname=localhost]	3
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	0c2b8c56-8e6c-4207-a1ce-537e826f6972	std::File[localhost,path=/tmp/test]	3
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	17c4092c-e44c-4472-b7d4-0a26a2e6affe	std::AgentConfig[internal,agentname=localhost]	3
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	83c3fb8c-a16f-40c9-a743-d32cab8a8575	std::AgentConfig[internal,agentname=localhost]	4
7c7e012d-33d9-44b7-9efa-4c3b1efe9e72	83c3fb8c-a16f-40c9-a743-d32cab8a8575	std::File[localhost,path=/tmp/test]	4
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309130}
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
-- PostgreSQL database dump complete
--

