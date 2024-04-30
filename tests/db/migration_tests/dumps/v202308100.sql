--
-- PostgreSQL database dump
--

-- Dumped from database version 15.1
-- Dumped by pg_dump version 15.1

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
    last_success timestamp with time zone
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
b2de1039-78a2-4938-83e7-5faf6a4ea183	internal	2023-08-10 16:01:13.638848+02	f	6d915403-fc9c-4250-b6f9-1afe8aa29dc4	\N
b2de1039-78a2-4938-83e7-5faf6a4ea183	localhost	2023-08-10 16:01:13.715594+02	f	64d6620f-45cf-4b91-8146-1ea21e0101ad	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
6d915403-fc9c-4250-b6f9-1afe8aa29dc4	5df0540a-3786-11ee-b4e8-84144dfe5579	internal	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183
64d6620f-45cf-4b91-8146-1ea21e0101ad	5df0540a-3786-11ee-b4e8-84144dfe5579	localhost	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-inmanta-laptop	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:13.638848+02	2023-08-10 16:01:37.436491+02	\N	5df0540a-3786-11ee-b4e8-84144dfe5579
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Service	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::File	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Directory	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Package	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Symlink	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::testing::NullResource	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::AgentConfig	1	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Service	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::File	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Directory	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Package	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Symlink	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::testing::NullResource	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::AgentConfig	2	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Service	3	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::File	3	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Directory	3	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Package	3	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Symlink	3	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::testing::NullResource	3	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::AgentConfig	3	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Service	4	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::File	4	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Directory	4	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Package	4	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::Symlink	4	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::testing::NullResource	4	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
b2de1039-78a2-4938-83e7-5faf6a4ea183	std::AgentConfig	4	{"eed9c79c4b247a7a7452d795605e27a495863a9e": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]], "f20255abb8beb130e89ef3bdae958974f15163ed": ["/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "pydantic>=1.10,<2"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
a956a7b3-c3f6-4c15-8725-f0540791d0fc	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:02.359977+02	2023-08-10 16:01:13.075418+02	2023-08-10 16:01:02.355048+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	f3faebb4-42a2-454c-9349-2e5357ea594e	t	\N	{"errors": []}	f	{}	\N	\N	\N
e80fc392-46f0-4c50-adb9-7bc327138f34	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:13.828517+02	2023-08-10 16:01:22.174607+02	2023-08-10 16:01:13.824822+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	f20582d9-5800-4f03-9bc6-43931df5a903	t	\N	{"errors": []}	f	{}	\N	\N	\N
025ec17e-cb73-46d8-ac4f-c8815f3005ed	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:22.399904+02	2023-08-10 16:01:30.280325+02	2023-08-10 16:01:22.391216+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	3	6544128c-7e5f-49fb-818a-59315e6106ad	t	\N	{"errors": []}	f	{}	\N	\N	\N
59e481b0-cfc9-464f-85a0-64787e3122cc	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:30.405567+02	2023-08-10 16:01:38.322762+02	2023-08-10 16:01:30.401688+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	4	3238d9de-2821-4f1c-bf68-0c120a70a1ce	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles) FROM stdin;
1	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:12.992241+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
2	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:22.085198+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
3	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:30.20936+02	t	f	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
4	b2de1039-78a2-4938-83e7-5faf6a4ea183	2023-08-10 16:01:38.247293+02	f	f	pending	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t
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
c9337aca-4ddf-4475-b510-3427a91b7e66	dev-2	83adf095-f382-48d4-8fd0-87566642c1e2			{"auto_full_compile": ""}	0	f		
b2de1039-78a2-4938-83e7-5faf6a4ea183	dev-1	83adf095-f382-48d4-8fd0-87566642c1e2			{"auto_deploy": false, "server_compile": true, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0}	4	f		
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
83adf095-f382-48d4-8fd0-87566642c1e2	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
2e54d968-9790-46b2-bab3-ac14db56daec	2023-08-10 16:01:02.360329+02	2023-08-10 16:01:02.361449+02		Init		Using extra environment variables during compile \n	0	a956a7b3-c3f6-4c15-8725-f0540791d0fc
f356764e-14f4-4dbf-bda6-8536d6d5174b	2023-08-10 16:01:02.361731+02	2023-08-10 16:01:02.363079+02		Creating venv			0	a956a7b3-c3f6-4c15-8725-f0540791d0fc
58fae1d2-d39c-48bc-a790-9ea648302b37	2023-08-10 16:01:02.367058+02	2023-08-10 16:01:02.637994+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.3.1.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	a956a7b3-c3f6-4c15-8725-f0540791d0fc
d79e8109-777e-4396-878e-7c90e6819c0f	2023-08-10 16:01:02.638758+02	2023-08-10 16:01:12.390322+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.1.8 in /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000079 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<2,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==9.3.1.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.12)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.3.1.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (9.3.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (8.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.4.1)\ninmanta.pip              DEBUG   Collecting dnspython>=2.0.0 (from email_validator<3,>=1.3)\ninmanta.pip              DEBUG   Obtaining dependency information for dnspython>=2.0.0 from https://files.pythonhosted.org/packages/f6/b4/0a9bee52c50f226a3cbfb54263d02bb421c7f2adc136520729c2c689c1e5/dnspython-2.4.2-py3-none-any.whl.metadata\ninmanta.pip              DEBUG   Downloading dnspython-2.4.2-py3-none-any.whl.metadata (4.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-8.0.1-py2.py3-none-any.whl (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.3.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.3.1.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.3.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.3.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.3.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.1.2)\ninmanta.pip              DEBUG   Downloading dnspython-2.4.2-py3-none-any.whl (300 kB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 300.4/300.4 kB 9.7 MB/s eta 0:00:00\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, dnspython\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: dnspython\ninmanta.pip              DEBUG   Found existing installation: dnspython 2.4.1\ninmanta.pip              DEBUG   Not uninstalling dnspython at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env\ninmanta.pip              DEBUG   Can't uninstall 'dnspython'. No files were found to uninstall.\ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   pyadr 0.19.0 requires python-slugify<7,>=6, but you have python-slugify 8.0.1 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed dnspython-2.4.2 python-slugify-8.0.1\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000057 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic<2,>=1.10 email_validator<3,>=1.3 Jinja2<4,>=3.1 inmanta-core==9.3.1.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.12)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.3.1.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (9.3.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (8.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.3.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.3.1.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.3.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.3.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.3.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	a956a7b3-c3f6-4c15-8725-f0540791d0fc
03adc3d6-6587-410e-889d-a25d317d395c	2023-08-10 16:01:12.391399+02	2023-08-10 16:01:13.07453+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m inmanta.app -vvv export -X -e b2de1039-78a2-4938-83e7-5faf6a4ea183 --server_address localhost --server_port 55623 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpgp91qi4z --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004411 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000092 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.8\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002298)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001579)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000234)\ninmanta.execute.schedulerINFO    Total compilation time 0.004256\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/file/f20255abb8beb130e89ef3bdae958974f15163ed\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/file/eed9c79c4b247a7a7452d795605e27a495863a9e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1 not in any resource set\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1 not in any resource set\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	a956a7b3-c3f6-4c15-8725-f0540791d0fc
cd38c020-249b-4634-b286-9957f729251c	2023-08-10 16:01:13.828799+02	2023-08-10 16:01:13.829525+02		Init		Using extra environment variables during compile \n	0	e80fc392-46f0-4c50-adb9-7bc327138f34
4fe65d8f-cf80-4694-88aa-267b665c403b	2023-08-10 16:01:13.833048+02	2023-08-10 16:01:14.079301+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.3.1.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	e80fc392-46f0-4c50-adb9-7bc327138f34
f8b13ae3-5ca4-4562-befc-403d10394fd8	2023-08-10 16:01:14.080254+02	2023-08-10 16:01:21.468678+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000069 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 pydantic<2,>=1.10 email_validator<3,>=1.3 inmanta-core==9.3.1.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.12)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.3.1.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (9.3.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (8.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.3.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.3.1.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.3.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.3.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.3.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000053 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2<4,>=3.1 pydantic<2,>=1.10 email_validator<3,>=1.3 inmanta-core==9.3.1.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.12)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.3.1.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (9.3.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (8.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.3.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.3.1.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.3.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.3.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.3.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	e80fc392-46f0-4c50-adb9-7bc327138f34
c2397090-2e86-41ab-bdf8-4ac9097eb275	2023-08-10 16:01:21.469752+02	2023-08-10 16:01:22.173793+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m inmanta.app -vvv export -X -e b2de1039-78a2-4938-83e7-5faf6a4ea183 --server_address localhost --server_port 55623 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp2lcpcp9h --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004584 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000099 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.8\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002602)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001808)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000243)\ninmanta.execute.schedulerINFO    Total compilation time 0.004831\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2 not in any resource set\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2 not in any resource set\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	e80fc392-46f0-4c50-adb9-7bc327138f34
5569546c-88cd-4fb4-994c-00cc458a82f7	2023-08-10 16:01:22.405185+02	2023-08-10 16:01:22.652437+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.3.1.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	025ec17e-cb73-46d8-ac4f-c8815f3005ed
33d7c645-355b-4fc1-bcab-242cde7fe84c	2023-08-10 16:01:22.400323+02	2023-08-10 16:01:22.401565+02		Init		Using extra environment variables during compile \n	0	025ec17e-cb73-46d8-ac4f-c8815f3005ed
4a7c903b-9523-46e5-9372-50da6145ca56	2023-08-10 16:01:22.653242+02	2023-08-10 16:01:29.636399+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000068 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 pydantic<2,>=1.10 Jinja2<4,>=3.1 inmanta-core==9.3.1.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.12)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.3.1.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (9.3.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (8.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.3.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.3.1.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.3.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.3.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.3.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000053 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 pydantic<2,>=1.10 Jinja2<4,>=3.1 inmanta-core==9.3.1.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.12)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.3.1.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (9.3.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (8.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.3.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.3.1.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.3.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.3.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.3.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	025ec17e-cb73-46d8-ac4f-c8815f3005ed
f9593db9-296f-4add-a5ff-182a96591462	2023-08-10 16:01:29.637199+02	2023-08-10 16:01:30.279585+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m inmanta.app -vvv export -X -e b2de1039-78a2-4938-83e7-5faf6a4ea183 --server_address localhost --server_port 55623 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp6yniiifv --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004254 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000093 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.8\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002269)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001611)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000229)\ninmanta.execute.schedulerINFO    Total compilation time 0.004255\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/codebatched/3\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=3 not in any resource set\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=3 not in any resource set\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/version\ninmanta.export           INFO    Committed resources with version 3\n	0	025ec17e-cb73-46d8-ac4f-c8815f3005ed
9140d0ae-681d-4376-bc40-fa0b90150800	2023-08-10 16:01:30.405862+02	2023-08-10 16:01:30.40657+02		Init		Using extra environment variables during compile \n	0	59e481b0-cfc9-464f-85a0-64787e3122cc
4ef37334-6715-43ed-b7c0-abd8b72ff6de	2023-08-10 16:01:30.410354+02	2023-08-10 16:01:30.663114+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 9.3.1.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	59e481b0-cfc9-464f-85a0-64787e3122cc
719050e2-7083-4357-a080-9a6322d5499a	2023-08-10 16:01:30.664066+02	2023-08-10 16:01:37.673502+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000067 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 Jinja2<4,>=3.1 pydantic<2,>=1.10 inmanta-core==9.3.1.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.12)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.3.1.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (9.3.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (8.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.3.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.3.1.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.3.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.3.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.3.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000056 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.module           INFO    Checking out 4.1.8 on /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m pip install --upgrade --upgrade-strategy eager email_validator<3,>=1.3 Jinja2<4,>=3.1 pydantic<2,>=1.10 inmanta-core==9.3.1.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator<3,>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (2.0.0.post2)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2<4,>=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic<2,>=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.12)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==9.3.1.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (9.3.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.28.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (8.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<42,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (41.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet<2,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (10.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (23.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (6.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.17.32)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==9.3.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator<3,>=1.3) (2.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator<3,>=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2<4,>=3.1) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic<2,>=1.10) (4.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==9.3.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (8.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (13.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<42,>=36->inmanta-core==9.3.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==9.3.1.dev0) (3.16.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==9.3.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==9.3.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.9->inmanta-core==9.3.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<42,>=36->inmanta-core==9.3.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2023.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (2.16.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==9.3.1.dev0) (0.1.2)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\n	0	59e481b0-cfc9-464f-85a0-64787e3122cc
2f9a065c-fa33-4437-87d6-8dda18cd0126	2023-08-10 16:01:37.674502+02	2023-08-10 16:01:38.321952+02	/tmp/tmp5rs_itxm/server/environments/b2de1039-78a2-4938-83e7-5faf6a4ea183/.env/bin/python -m inmanta.app -vvv export -X -e b2de1039-78a2-4938-83e7-5faf6a4ea183 --server_address localhost --server_port 55623 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpfxvyoul3 --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004376 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 8.0.1 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000085 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.8\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002212)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001597)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000233)\ninmanta.execute.schedulerINFO    Total compilation time 0.004186\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/codebatched/4\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55623/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=4 not in any resource set\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=4 not in any resource set\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55623/api/v1/version\ninmanta.export           INFO    Committed resources with version 4\n	0	59e481b0-cfc9-464f-85a0-64787e3122cc
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set, last_success) FROM stdin;
b2de1039-78a2-4938-83e7-5faf6a4ea183	1	std::AgentConfig[internal,agentname=localhost]	internal	2023-08-10 16:01:13.7391+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2023-08-10 16:01:13.727352+02
b2de1039-78a2-4938-83e7-5faf6a4ea183	1	std::File[localhost,path=/tmp/test]	localhost	2023-08-10 16:01:13.747904+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N
b2de1039-78a2-4938-83e7-5faf6a4ea183	2	std::AgentConfig[internal,agentname=localhost]	internal	2023-08-10 16:01:22.294191+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2023-08-10 16:01:22.286028+02
b2de1039-78a2-4938-83e7-5faf6a4ea183	2	std::File[localhost,path=/tmp/test]	localhost	2023-08-10 16:01:22.298185+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N	\N
b2de1039-78a2-4938-83e7-5faf6a4ea183	3	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N
b2de1039-78a2-4938-83e7-5faf6a4ea183	3	std::AgentConfig[internal,agentname=localhost]	internal	2023-08-10 16:01:30.389394+02	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N	2023-08-10 16:01:22.286028+02
b2de1039-78a2-4938-83e7-5faf6a4ea183	4	std::File[localhost,path=/tmp/test]	localhost	\N	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	available	{}	std::File	/tmp/test	available	\N	\N
b2de1039-78a2-4938-83e7-5faf6a4ea183	4	std::AgentConfig[internal,agentname=localhost]	internal	\N	{"uri": "local:", "purged": false, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	available	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	available	\N	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
2fd5e7a8-869c-4adb-a707-e73c24e9cc74	store	2023-08-10 16:01:12.992175+02	2023-08-10 16:01:12.999007+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2023-08-10T16:01:12.999020+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
b38a35bc-9715-4bda-b14d-c49edeb6590b	pull	2023-08-10 16:01:13.645964+02	2023-08-10 16:01:13.650002+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.650011+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
f8649b20-4822-4b43-9c6a-4ce574a79480	deploy	2023-08-10 16:01:13.674632+02	2023-08-10 16:01:13.686661+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-08-10 16:01:13+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-08-10 16:01:13+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"2de3786d-4971-4f68-8ab8-58883ee9e0f9\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.672692+02:00\\"}","{\\"msg\\": \\"Start deploy 2de3786d-4971-4f68-8ab8-58883ee9e0f9 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"2de3786d-4971-4f68-8ab8-58883ee9e0f9\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-08-10T16:01:13.675939+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-08-10T16:01:13.676612+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-08-10T16:01:13.679129+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 2de3786d-4971-4f68-8ab8-58883ee9e0f9\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"2de3786d-4971-4f68-8ab8-58883ee9e0f9\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.681456+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	b2de1039-78a2-4938-83e7-5faf6a4ea183	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
d449a6f1-af98-4cc0-94f8-f8d3c6f5d45c	pull	2023-08-10 16:01:13.714561+02	2023-08-10 16:01:13.716425+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.716432+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
d423b8bf-01a3-47cb-aea1-cb10dd324f20	pull	2023-08-10 16:01:13.721292+02	2023-08-10 16:01:13.722531+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.722537+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	1	{"std::File[localhost,path=/tmp/test],v=1"}
6c042e7b-5ded-4096-9975-357238076720	deploy	2023-08-10 16:01:13.727352+02	2023-08-10 16:01:13.7391+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"17b1e8e8-ff70-4cc8-8f66-00a5786e4bd5\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.718861+02:00\\"}","{\\"msg\\": \\"Start deploy 17b1e8e8-ff70-4cc8-8f66-00a5786e4bd5 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"17b1e8e8-ff70-4cc8-8f66-00a5786e4bd5\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-08-10T16:01:13.733479+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-08-10T16:01:13.733924+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 17b1e8e8-ff70-4cc8-8f66-00a5786e4bd5\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"17b1e8e8-ff70-4cc8-8f66-00a5786e4bd5\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.737087+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	b2de1039-78a2-4938-83e7-5faf6a4ea183	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
33fd81c5-fe08-4304-a2f1-ef792d108560	deploy	2023-08-10 16:01:13.732813+02	2023-08-10 16:01:13.747904+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2023-08-10 16:01:13+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2023-08-10 16:01:13+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"1f5a6506-ee1c-40c5-aa26-f142eb70a535\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.730844+02:00\\"}","{\\"msg\\": \\"Start deploy 1f5a6506-ee1c-40c5-aa26-f142eb70a535 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"1f5a6506-ee1c-40c5-aa26-f142eb70a535\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-08-10T16:01:13.734496+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-08-10T16:01:13.735037+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-08-10T16:01:13.735205+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 898, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmp5rs_itxm/b2de1039-78a2-4938-83e7-5faf6a4ea183/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 220, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-08-10T16:01:13.745538+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 1f5a6506-ee1c-40c5-aa26-f142eb70a535\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"1f5a6506-ee1c-40c5-aa26-f142eb70a535\\"}, \\"timestamp\\": \\"2023-08-10T16:01:13.745796+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	b2de1039-78a2-4938-83e7-5faf6a4ea183	1	{"std::File[localhost,path=/tmp/test],v=1"}
68d69db8-6e26-4dd6-a7fe-dd070e1707f9	store	2023-08-10 16:01:22.085129+02	2023-08-10 16:01:22.088975+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2023-08-10T16:01:22.088985+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	2	{"std::AgentConfig[internal,agentname=localhost],v=2","std::File[localhost,path=/tmp/test],v=2"}
9e03ecdf-acba-4838-8a37-5ade54fe95f9	deploy	2023-08-10 16:01:22.253375+02	2023-08-10 16:01:22.253375+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-08-10T14:01:22.253375+00:00\\"}"}	deployed	\N	nochange	b2de1039-78a2-4938-83e7-5faf6a4ea183	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
c5c303b0-be22-48c2-b388-6a610444381d	pull	2023-08-10 16:01:22.27323+02	2023-08-10 16:01:22.274777+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-08-10T16:01:22.274785+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
f325688f-e26b-464d-a8b6-4c7f6e7171ed	deploy	2023-08-10 16:01:22.286028+02	2023-08-10 16:01:22.294191+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"7e501786-03cd-4f4e-b3e6-708f6ff60afe\\"}, \\"timestamp\\": \\"2023-08-10T16:01:22.281369+02:00\\"}","{\\"msg\\": \\"Start deploy 7e501786-03cd-4f4e-b3e6-708f6ff60afe of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"7e501786-03cd-4f4e-b3e6-708f6ff60afe\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-08-10T16:01:22.288048+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-08-10T16:01:22.288516+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy 7e501786-03cd-4f4e-b3e6-708f6ff60afe\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"7e501786-03cd-4f4e-b3e6-708f6ff60afe\\"}, \\"timestamp\\": \\"2023-08-10T16:01:22.291978+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	b2de1039-78a2-4938-83e7-5faf6a4ea183	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
07ef44cc-0e12-4a83-893a-192a5584bc3b	deploy	2023-08-10 16:01:22.290429+02	2023-08-10 16:01:22.298185+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"99dcf430-733e-4017-ab1f-daba3149c7b8\\"}, \\"timestamp\\": \\"2023-08-10T16:01:22.287543+02:00\\"}","{\\"msg\\": \\"Start deploy 99dcf430-733e-4017-ab1f-daba3149c7b8 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"99dcf430-733e-4017-ab1f-daba3149c7b8\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-08-10T16:01:22.292913+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-08-10T16:01:22.293378+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-08-10T16:01:22.295126+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 905, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp5rs_itxm/b2de1039-78a2-4938-83e7-5faf6a4ea183/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 248, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-08-10T16:01:22.295313+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 99dcf430-733e-4017-ab1f-daba3149c7b8\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"99dcf430-733e-4017-ab1f-daba3149c7b8\\"}, \\"timestamp\\": \\"2023-08-10T16:01:22.295478+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	b2de1039-78a2-4938-83e7-5faf6a4ea183	2	{"std::File[localhost,path=/tmp/test],v=2"}
0a3d7b9a-5a62-4b8e-938e-c8f42fe3ba46	pull	2023-08-10 16:01:22.27356+02	2023-08-10 16:01:22.275176+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-08-10T16:01:22.275189+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	2	{"std::File[localhost,path=/tmp/test],v=2"}
d2aec8cf-9234-40ba-b8e5-8859cb18ec39	store	2023-08-10 16:01:30.209305+02	2023-08-10 16:01:30.210787+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2023-08-10T16:01:30.210795+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	3	{"std::File[localhost,path=/tmp/test],v=3","std::AgentConfig[internal,agentname=localhost],v=3"}
511f679d-207a-47ec-94ac-184a071e2911	deploy	2023-08-10 16:01:30.389394+02	2023-08-10 16:01:30.389394+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-08-10T14:01:30.389394+00:00\\"}"}	deployed	\N	nochange	b2de1039-78a2-4938-83e7-5faf6a4ea183	3	{"std::AgentConfig[internal,agentname=localhost],v=3"}
90c57558-d7bb-455a-8085-fe5de7f3373f	store	2023-08-10 16:01:38.247087+02	2023-08-10 16:01:38.249256+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2023-08-10T16:01:38.249273+02:00\\"}"}	\N	\N	\N	b2de1039-78a2-4938-83e7-5faf6a4ea183	4	{"std::File[localhost,path=/tmp/test],v=4","std::AgentConfig[internal,agentname=localhost],v=4"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
b2de1039-78a2-4938-83e7-5faf6a4ea183	2fd5e7a8-869c-4adb-a707-e73c24e9cc74	std::File[localhost,path=/tmp/test]	1
b2de1039-78a2-4938-83e7-5faf6a4ea183	2fd5e7a8-869c-4adb-a707-e73c24e9cc74	std::AgentConfig[internal,agentname=localhost]	1
b2de1039-78a2-4938-83e7-5faf6a4ea183	b38a35bc-9715-4bda-b14d-c49edeb6590b	std::AgentConfig[internal,agentname=localhost]	1
b2de1039-78a2-4938-83e7-5faf6a4ea183	f8649b20-4822-4b43-9c6a-4ce574a79480	std::AgentConfig[internal,agentname=localhost]	1
b2de1039-78a2-4938-83e7-5faf6a4ea183	d449a6f1-af98-4cc0-94f8-f8d3c6f5d45c	std::AgentConfig[internal,agentname=localhost]	1
b2de1039-78a2-4938-83e7-5faf6a4ea183	d423b8bf-01a3-47cb-aea1-cb10dd324f20	std::File[localhost,path=/tmp/test]	1
b2de1039-78a2-4938-83e7-5faf6a4ea183	6c042e7b-5ded-4096-9975-357238076720	std::AgentConfig[internal,agentname=localhost]	1
b2de1039-78a2-4938-83e7-5faf6a4ea183	33fd81c5-fe08-4304-a2f1-ef792d108560	std::File[localhost,path=/tmp/test]	1
b2de1039-78a2-4938-83e7-5faf6a4ea183	68d69db8-6e26-4dd6-a7fe-dd070e1707f9	std::AgentConfig[internal,agentname=localhost]	2
b2de1039-78a2-4938-83e7-5faf6a4ea183	68d69db8-6e26-4dd6-a7fe-dd070e1707f9	std::File[localhost,path=/tmp/test]	2
b2de1039-78a2-4938-83e7-5faf6a4ea183	9e03ecdf-acba-4838-8a37-5ade54fe95f9	std::AgentConfig[internal,agentname=localhost]	2
b2de1039-78a2-4938-83e7-5faf6a4ea183	c5c303b0-be22-48c2-b388-6a610444381d	std::AgentConfig[internal,agentname=localhost]	2
b2de1039-78a2-4938-83e7-5faf6a4ea183	0a3d7b9a-5a62-4b8e-938e-c8f42fe3ba46	std::File[localhost,path=/tmp/test]	2
b2de1039-78a2-4938-83e7-5faf6a4ea183	f325688f-e26b-464d-a8b6-4c7f6e7171ed	std::AgentConfig[internal,agentname=localhost]	2
b2de1039-78a2-4938-83e7-5faf6a4ea183	07ef44cc-0e12-4a83-893a-192a5584bc3b	std::File[localhost,path=/tmp/test]	2
b2de1039-78a2-4938-83e7-5faf6a4ea183	d2aec8cf-9234-40ba-b8e5-8859cb18ec39	std::File[localhost,path=/tmp/test]	3
b2de1039-78a2-4938-83e7-5faf6a4ea183	d2aec8cf-9234-40ba-b8e5-8859cb18ec39	std::AgentConfig[internal,agentname=localhost]	3
b2de1039-78a2-4938-83e7-5faf6a4ea183	511f679d-207a-47ec-94ac-184a071e2911	std::AgentConfig[internal,agentname=localhost]	3
b2de1039-78a2-4938-83e7-5faf6a4ea183	90c57558-d7bb-455a-8085-fe5de7f3373f	std::File[localhost,path=/tmp/test]	4
b2de1039-78a2-4938-83e7-5faf6a4ea183	90c57558-d7bb-455a-8085-fe5de7f3373f	std::AgentConfig[internal,agentname=localhost]	4
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100}
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

