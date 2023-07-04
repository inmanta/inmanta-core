--
-- PostgreSQL database dump
--

-- Dumped from database version 14.8 (Ubuntu 14.8-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.8 (Ubuntu 14.8-0ubuntu0.22.04.1)

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
    discovered_at timestamp without time zone NOT NULL
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
27b02950-b8a4-4950-809c-9339a76f802c	internal	2023-06-08 17:32:49.39491+02	f	08835270-5b64-4c3c-afc5-3e9278e9e58a	\N
27b02950-b8a4-4950-809c-9339a76f802c	localhost	2023-06-08 17:32:51.766264+02	f	1b5ea026-7985-4cbc-8b1d-48ad3478cb09	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
08835270-5b64-4c3c-afc5-3e9278e9e58a	b9a3bcb6-0611-11ee-984e-7d381e717513	internal	\N	27b02950-b8a4-4950-809c-9339a76f802c
1b5ea026-7985-4cbc-8b1d-48ad3478cb09	b9a3bcb6-0611-11ee-984e-7d381e717513	localhost	\N	27b02950-b8a4-4950-809c-9339a76f802c
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
florent-Hydra-Pro-70	27b02950-b8a4-4950-809c-9339a76f802c	2023-06-08 17:32:49.39491+02	2023-06-08 17:33:07.569468+02	\N	b9a3bcb6-0611-11ee-984e-7d381e717513
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
27b02950-b8a4-4950-809c-9339a76f802c	std::Service	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::File	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::Directory	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::Package	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::Symlink	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::testing::NullResource	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::AgentConfig	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::Service	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::File	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::Directory	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::Package	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::Symlink	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::testing::NullResource	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
27b02950-b8a4-4950-809c-9339a76f802c	std::AgentConfig	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
6d4c8c18-b6ce-47f3-af59-5bc530c54ea8	27b02950-b8a4-4950-809c-9339a76f802c	2023-06-08 17:32:30.247852+02	2023-06-08 17:32:49.464858+02	2023-06-08 17:32:30.238177+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	d9434a70-1bd1-404f-906a-e114bc30db7b	t	\N	{"errors": []}	f	{}	\N	\N	\N
44fa9306-5a66-4c1e-b5f1-facdf241736f	27b02950-b8a4-4950-809c-9339a76f802c	2023-06-08 17:32:52.272193+02	2023-06-08 17:33:07.488685+02	2023-06-08 17:32:52.269847+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	ca4e6da9-8157-46db-bb96-a14b13da17c8	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles) FROM stdin;
1	27b02950-b8a4-4950-809c-9339a76f802c	2023-06-08 17:32:47.253879+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Hydra-Pro-70", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
2	27b02950-b8a4-4950-809c-9339a76f802c	2023-06-08 17:33:07.388614+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Hydra-Pro-70", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
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
08636991-fdc5-49b9-9146-b957ec7e52f1	dev-2	e1187acc-793f-46ac-b3a9-6eb8e301b0cf			{"auto_full_compile": ""}	0	f		
27b02950-b8a4-4950-809c-9339a76f802c	dev-1	e1187acc-793f-46ac-b3a9-6eb8e301b0cf			{"auto_deploy": true, "server_compile": true, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
e1187acc-793f-46ac-b3a9-6eb8e301b0cf	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
945ee02a-6728-4af1-84f6-a4b66741508a	2023-06-08 17:32:30.248254+02	2023-06-08 17:32:30.249358+02		Init		Using extra environment variables during compile \n	0	6d4c8c18-b6ce-47f3-af59-5bc530c54ea8
0d4025b4-34de-4f5b-86f1-b630a655862d	2023-06-08 17:32:30.24961+02	2023-06-08 17:32:30.256197+02		Creating venv			0	6d4c8c18-b6ce-47f3-af59-5bc530c54ea8
c52d5abc-acc8-430a-92d8-c9138a2ab4da	2023-06-08 17:32:30.259232+02	2023-06-08 17:32:30.475912+02	/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.1.0.dev0\nNot uninstalling inmanta-core at /home/florent/Desktop/Inmanta/inmanta-core/src, outside environment /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6d4c8c18-b6ce-47f3-af59-5bc530c54ea8
bff11838-0622-4a81-901b-a069c72cb1ad	2023-06-08 17:32:30.476535+02	2023-06-08 17:32:46.864051+02	/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.1.7 on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.1.7 in /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000062 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.module           INFO    Checking out 4.1.7 on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 pydantic<2,>=1.10 Jinja2<4,>=3.1 inmanta-core==9.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (1.10.8)\ninmanta.pip              DEBUG   Collecting pydantic<2,>=1.10\ninmanta.pip              DEBUG   Downloading https://artifacts.internal.inmanta.com/root/pypi/%2Bf/83f/cff3c7df7adff/pydantic-1.10.9-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.2 MB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.2/3.2 MB 5.1 MB/s eta 0:00:00\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.1.0.dev0 in /home/florent/Desktop/Inmanta/inmanta-core/src (9.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (41.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (23.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.17.31)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.6.3)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.1.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/70c/a6ea68fe63ecc/python_slugify-8.0.1-py2.py3-none-any.whl (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.1.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.1.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.1.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.1.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2023.5.7)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, pydantic\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 1.10.8\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   pyadr 0.19.0 requires python-slugify<7,>=6, but you have python-slugify 8.0.1 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed pydantic-1.10.9 python-slugify-8.0.1\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000032 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.module           INFO    Checking out 4.1.7 on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 pydantic<2,>=1.10 Jinja2<4,>=3.1 inmanta-core==9.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.9)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.1.0.dev0 in /home/florent/Desktop/Inmanta/inmanta-core/src (9.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (41.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (23.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.17.31)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.6.3)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.1.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.1.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.1.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.1.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.1.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2023.5.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	6d4c8c18-b6ce-47f3-af59-5bc530c54ea8
ae6f7f65-6420-445d-9f76-18e3c63b5302	2023-06-08 17:32:46.86491+02	2023-06-08 17:32:49.463319+02	/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m inmanta.app -vvv export -X -e 27b02950-b8a4-4950-809c-9339a76f802c --server_address localhost --server_port 49729 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpad123ode --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.002919 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000066 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.7\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001510)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001091)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000163)\ninmanta.execute.schedulerINFO    Total compilation time 0.002861\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:49729/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:49729/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:49729/api/v1/file/eed9c79c4b247a7a7452d795605e27a495863a9e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:49729/api/v1/file/f20255abb8beb130e89ef3bdae958974f15163ed\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:49729/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:49729/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:49729/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1 in resource set \ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1 in resource set \ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:49729/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	6d4c8c18-b6ce-47f3-af59-5bc530c54ea8
bb5d94a9-e3ca-4289-bb93-a3213dacad2c	2023-06-08 17:32:52.272443+02	2023-06-08 17:32:52.272887+02		Init		Using extra environment variables during compile \n	0	44fa9306-5a66-4c1e-b5f1-facdf241736f
2f6529e3-6519-44fb-b2e0-c499699c5c19	2023-06-08 17:32:52.275318+02	2023-06-08 17:32:52.488871+02	/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.1.0.dev0\nNot uninstalling inmanta-core at /home/florent/Desktop/Inmanta/inmanta-core/src, outside environment /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	44fa9306-5a66-4c1e-b5f1-facdf241736f
d0b3b7f3-f5ed-47f8-b329-d1cf2b128f31	2023-06-08 17:32:52.489356+02	2023-06-08 17:33:07.002142+02	/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000052 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.module           INFO    Checking out 4.1.7 on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 pydantic<2,>=1.10 email_validator<3,>=1.3 inmanta-core==9.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.9)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.1.0.dev0 in /home/florent/Desktop/Inmanta/inmanta-core/src (9.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (41.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (23.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.17.31)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.6.3)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.1.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.1.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.1.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.1.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.1.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2023.5.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000029 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.module           INFO    Checking out 4.1.7 on /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 pydantic<2,>=1.10 email_validator<3,>=1.3 inmanta-core==9.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in ./.env/lib/python3.9/site-packages (1.10.9)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.1.0.dev0 in /home/florent/Desktop/Inmanta/inmanta-core/src (9.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (41.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (9.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (23.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.17.31)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==9.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.6.3)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.1.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.1.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.1.0.dev0) (3.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.1.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.1.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (3.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.1.0.dev0) (2023.5.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	44fa9306-5a66-4c1e-b5f1-facdf241736f
f7e85b91-aaf7-4e08-9e3c-1eab7390aaf2	2023-06-08 17:33:07.002852+02	2023-06-08 17:33:07.488371+02	/tmp/tmpx6dpins3/server/environments/27b02950-b8a4-4950-809c-9339a76f802c/.env/bin/python -m inmanta.app -vvv export -X -e 27b02950-b8a4-4950-809c-9339a76f802c --server_address localhost --server_port 49729 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpfsvdl2sb --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.002972 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000086 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.7\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001584)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001151)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000163)\ninmanta.execute.schedulerINFO    Total compilation time 0.002992\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:49729/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:49729/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:49729/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:49729/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2 in resource set \ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2 in resource set \ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:49729/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	44fa9306-5a66-4c1e-b5f1-facdf241736f
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
27b02950-b8a4-4950-809c-9339a76f802c	1	std::AgentConfig[internal,agentname=localhost]	internal	2023-06-08 17:32:50.763262+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
27b02950-b8a4-4950-809c-9339a76f802c	1	std::File[localhost,path=/tmp/test]	localhost	2023-06-08 17:32:51.781762+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
27b02950-b8a4-4950-809c-9339a76f802c	2	std::AgentConfig[internal,agentname=localhost]	internal	2023-06-08 17:33:07.562584+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
27b02950-b8a4-4950-809c-9339a76f802c	2	std::File[localhost,path=/tmp/test]	localhost	2023-06-08 17:33:07.931129+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
ebb86d65-943e-40e6-9f93-424c50d82164	store	2023-06-08 17:32:47.253837+02	2023-06-08 17:32:48.229431+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2023-06-08T17:32:48.229446+02:00\\"}"}	\N	\N	\N	27b02950-b8a4-4950-809c-9339a76f802c	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
2f6e2371-f6d4-4c74-af41-a36c86a98865	pull	2023-06-08 17:32:49.400064+02	2023-06-08 17:32:49.870342+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-06-08T17:32:49.870357+02:00\\"}"}	\N	\N	\N	27b02950-b8a4-4950-809c-9339a76f802c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
96b647e4-3d9c-47ab-8928-21a7b3e1c6c0	deploy	2023-06-08 17:32:50.755936+02	2023-06-08 17:32:50.763262+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-06-08 17:32:49+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-06-08 17:32:49+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"5b76d8ea-713f-469c-addc-83ad30a1caca\\"}, \\"timestamp\\": \\"2023-06-08T17:32:50.754626+02:00\\"}","{\\"msg\\": \\"Start deploy 5b76d8ea-713f-469c-addc-83ad30a1caca of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"5b76d8ea-713f-469c-addc-83ad30a1caca\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-06-08T17:32:50.756935+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-06-08T17:32:50.757367+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-06-08T17:32:50.759024+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 5b76d8ea-713f-469c-addc-83ad30a1caca\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"5b76d8ea-713f-469c-addc-83ad30a1caca\\"}, \\"timestamp\\": \\"2023-06-08T17:32:50.760596+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	27b02950-b8a4-4950-809c-9339a76f802c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1bb55884-807e-40cb-95c2-9f9bbefba565	pull	2023-06-08 17:32:51.769704+02	2023-06-08 17:32:51.770501+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-06-08T17:32:51.770505+02:00\\"}"}	\N	\N	\N	27b02950-b8a4-4950-809c-9339a76f802c	1	{"std::File[localhost,path=/tmp/test],v=1"}
e60f2f96-9cc1-4faf-b994-ce2cab14bcbb	deploy	2023-06-08 17:32:51.777176+02	2023-06-08 17:32:51.781762+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2023-06-08 17:32:51+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2023-06-08 17:32:51+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"956734b4-4e3a-47d9-9f1c-2cf65575496f\\"}, \\"timestamp\\": \\"2023-06-08T17:32:51.776055+02:00\\"}","{\\"msg\\": \\"Start deploy 956734b4-4e3a-47d9-9f1c-2cf65575496f of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"956734b4-4e3a-47d9-9f1c-2cf65575496f\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-06-08T17:32:51.778273+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-06-08T17:32:51.778700+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-06-08T17:32:51.778862+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 899, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpx6dpins3/27b02950-b8a4-4950-809c-9339a76f802c/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 220, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-06-08T17:32:51.780160+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 956734b4-4e3a-47d9-9f1c-2cf65575496f\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"956734b4-4e3a-47d9-9f1c-2cf65575496f\\"}, \\"timestamp\\": \\"2023-06-08T17:32:51.780296+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	27b02950-b8a4-4950-809c-9339a76f802c	1	{"std::File[localhost,path=/tmp/test],v=1"}
80a15c03-537a-411f-8dba-614d7889afd5	store	2023-06-08 17:33:07.388579+02	2023-06-08 17:33:07.389377+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2023-06-08T17:33:07.389383+02:00\\"}"}	\N	\N	\N	27b02950-b8a4-4950-809c-9339a76f802c	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
ac452851-f52b-477a-b2c8-a9ccf7cae4ad	deploy	2023-06-08 17:33:07.390201+02	2023-06-08 17:33:07.390201+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-06-08T15:33:07.390201+00:00\\"}"}	deployed	\N	nochange	27b02950-b8a4-4950-809c-9339a76f802c	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
895d7fdb-09c2-4fa2-b7b8-cc91e40379ff	deploy	2023-06-08 17:33:07.441913+02	2023-06-08 17:33:07.441913+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-06-08T15:33:07.441913+00:00\\"}"}	deployed	\N	nochange	27b02950-b8a4-4950-809c-9339a76f802c	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
489d05d8-ae04-40c6-9a86-ce46028afcf7	deploy	2023-06-08 17:33:07.562584+02	2023-06-08 17:33:07.562584+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-06-08T15:33:07.562584+00:00\\"}"}	deployed	\N	nochange	27b02950-b8a4-4950-809c-9339a76f802c	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
4db6d9b0-8876-4c95-b689-4bfcd9a21315	pull	2023-06-08 17:33:07.441723+02	2023-06-08 17:33:07.442096+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-06-08T17:33:07.442588+02:00\\"}"}	\N	\N	\N	27b02950-b8a4-4950-809c-9339a76f802c	2	{"std::File[localhost,path=/tmp/test],v=2"}
d2fe54ae-2211-40b6-a47b-de1b64e0a945	deploy	2023-06-08 17:33:07.92716+02	2023-06-08 17:33:07.931129+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"d1e2e141-a9bb-41f3-81ed-20cc5aa26710\\"}, \\"timestamp\\": \\"2023-06-08T17:33:07.925994+02:00\\"}","{\\"msg\\": \\"Start deploy d1e2e141-a9bb-41f3-81ed-20cc5aa26710 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"d1e2e141-a9bb-41f3-81ed-20cc5aa26710\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-06-08T17:33:07.928291+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-06-08T17:33:07.928538+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-06-08T17:33:07.929503+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 906, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpx6dpins3/27b02950-b8a4-4950-809c-9339a76f802c/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-06-08T17:33:07.929646+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy d1e2e141-a9bb-41f3-81ed-20cc5aa26710\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"d1e2e141-a9bb-41f3-81ed-20cc5aa26710\\"}, \\"timestamp\\": \\"2023-06-08T17:33:07.929756+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	27b02950-b8a4-4950-809c-9339a76f802c	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
27b02950-b8a4-4950-809c-9339a76f802c	ebb86d65-943e-40e6-9f93-424c50d82164	std::File[localhost,path=/tmp/test]	1
27b02950-b8a4-4950-809c-9339a76f802c	ebb86d65-943e-40e6-9f93-424c50d82164	std::AgentConfig[internal,agentname=localhost]	1
27b02950-b8a4-4950-809c-9339a76f802c	2f6e2371-f6d4-4c74-af41-a36c86a98865	std::AgentConfig[internal,agentname=localhost]	1
27b02950-b8a4-4950-809c-9339a76f802c	96b647e4-3d9c-47ab-8928-21a7b3e1c6c0	std::AgentConfig[internal,agentname=localhost]	1
27b02950-b8a4-4950-809c-9339a76f802c	1bb55884-807e-40cb-95c2-9f9bbefba565	std::File[localhost,path=/tmp/test]	1
27b02950-b8a4-4950-809c-9339a76f802c	e60f2f96-9cc1-4faf-b994-ce2cab14bcbb	std::File[localhost,path=/tmp/test]	1
27b02950-b8a4-4950-809c-9339a76f802c	80a15c03-537a-411f-8dba-614d7889afd5	std::File[localhost,path=/tmp/test]	2
27b02950-b8a4-4950-809c-9339a76f802c	80a15c03-537a-411f-8dba-614d7889afd5	std::AgentConfig[internal,agentname=localhost]	2
27b02950-b8a4-4950-809c-9339a76f802c	ac452851-f52b-477a-b2c8-a9ccf7cae4ad	std::AgentConfig[internal,agentname=localhost]	2
27b02950-b8a4-4950-809c-9339a76f802c	895d7fdb-09c2-4fa2-b7b8-cc91e40379ff	std::AgentConfig[internal,agentname=localhost]	2
27b02950-b8a4-4950-809c-9339a76f802c	489d05d8-ae04-40c6-9a86-ce46028afcf7	std::AgentConfig[internal,agentname=localhost]	2
27b02950-b8a4-4950-809c-9339a76f802c	4db6d9b0-8876-4c95-b689-4bfcd9a21315	std::File[localhost,path=/tmp/test]	2
27b02950-b8a4-4950-809c-9339a76f802c	d2fe54ae-2211-40b6-a47b-de1b64e0a945	std::File[localhost,path=/tmp/test]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060}
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
-- Name: discoveredresource unmanagedresource_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discoveredresource
    ADD CONSTRAINT unmanagedresource_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

