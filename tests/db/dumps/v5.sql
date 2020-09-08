--
-- PostgreSQL database dump
--

-- Dumped from database version 10.14
-- Dumped by pg_dump version 10.14

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
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


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
    'skipped_for_undefined',
    'processing_events'
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

SET default_with_oids = false;

--
-- Name: agent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent (
    environment uuid NOT NULL,
    name character varying NOT NULL,
    last_failover timestamp without time zone,
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
    expired timestamp without time zone,
    tid uuid NOT NULL
);


--
-- Name: agentprocess; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agentprocess (
    hostname character varying NOT NULL,
    environment uuid NOT NULL,
    first_seen timestamp without time zone,
    last_seen timestamp without time zone,
    expired timestamp without time zone,
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
    started timestamp without time zone,
    completed timestamp without time zone,
    requested timestamp without time zone,
    metadata jsonb,
    environment_variables jsonb,
    do_export boolean,
    force_update boolean,
    success boolean,
    version integer,
    remote_id uuid,
    handled boolean,
    substitute_compile_id uuid,
    compile_data jsonb
);


--
-- Name: configurationmodel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configurationmodel (
    version integer NOT NULL,
    environment uuid NOT NULL,
    date timestamp without time zone,
    released boolean DEFAULT false,
    deployed boolean DEFAULT false,
    result public.versionstate DEFAULT 'pending'::public.versionstate,
    version_info jsonb,
    total integer DEFAULT 0,
    undeployable character varying[],
    skipped_for_undeployable character varying[]
);


--
-- Name: dryrun; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dryrun (
    id uuid NOT NULL,
    environment uuid NOT NULL,
    model integer NOT NULL,
    date timestamp without time zone,
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
    halted boolean DEFAULT false NOT NULL
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
    updated timestamp without time zone,
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
    started timestamp without time zone NOT NULL,
    completed timestamp without time zone,
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
    resource_version_id character varying NOT NULL,
    agent character varying NOT NULL,
    last_deploy timestamp without time zone,
    attributes jsonb,
    attribute_hash character varying,
    status public.resourcestate DEFAULT 'available'::public.resourcestate,
    provides character varying[] DEFAULT ARRAY[]::character varying[],
    resource_type character varying NOT NULL
);


--
-- Name: resourceaction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resourceaction (
    action_id uuid NOT NULL,
    action public.resourceaction_type NOT NULL,
    started timestamp without time zone NOT NULL,
    finished timestamp without time zone,
    messages jsonb[],
    status public.resourcestate,
    changes jsonb DEFAULT '{}'::jsonb,
    change public.change,
    send_event boolean,
    environment uuid NOT NULL,
    version integer NOT NULL,
    resource_version_ids character varying[] NOT NULL
);


--
-- Name: schemamanager; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schemamanager (
    name character varying NOT NULL,
    current_version integer NOT NULL
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
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	internal	2020-09-08 09:08:12.671106	f	19cb8104-fffc-4261-8767-19be7f9dc0a3	\N
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	localhost	2020-09-08 09:08:15.50886	f	66ba11aa-6115-489b-bb42-de2fc8b6f973	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
19cb8104-fffc-4261-8767-19be7f9dc0a3	0dec2ae2-f1a2-11ea-8b56-106530e9353d	internal	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f
66ba11aa-6115-489b-bb42-de2fc8b6f973	0dec2ae2-f1a2-11ea-8b56-106530e9353d	localhost	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-laptop	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2020-09-08 09:08:12.671106	2020-09-08 09:08:16.592457	\N	0dec2ae2-f1a2-11ea-8b56-106530e9353d
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::Service	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::File	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::Directory	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::Package	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::Symlink	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::AgentConfig	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::Service	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::File	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::Directory	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::Package	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::Symlink	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	std::AgentConfig	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
785274ad-c222-42a2-8026-9d01666cc430	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2020-09-08 09:08:05.82809	2020-09-08 09:08:12.809434	2020-09-08 09:08:05.819512	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	b5679e7b-1800-48f8-8412-7e3a52548764	t	\N	{"errors": []}
9616d4b2-5123-4a71-924e-d4fcc673ff3f	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2020-09-08 09:08:15.721718	2020-09-08 09:08:16.520778	2020-09-08 09:08:15.709738	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	2dbfe038-f8d8-4c09-8439-f5eda7459bb1	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2020-09-08 09:08:10.177458	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
2	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2020-09-08 09:08:16.445106	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted) FROM stdin;
f18d7eb8-0d60-4e66-8d93-16f9813504fb	dev-2	e7337cba-f2c5-4a09-807d-88d56b47beb7			{}	0	f
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	dev-1	e7337cba-f2c5-4a09-807d-88d56b47beb7			{"auto_deploy": true, "server_compile": true, "purge_on_delete": true, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
e7337cba-f2c5-4a09-807d-88d56b47beb7	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
770ba7ba-8daa-4c17-8555-9a4fb00e0f06	2020-09-08 09:08:05.82884	2020-09-08 09:08:05.831357		Init		Using extra environment variables during compile \n	0	785274ad-c222-42a2-8026-9d01666cc430
f12fd5cf-d0f2-4a53-be1f-622232b7a475	2020-09-08 09:08:05.832277	2020-09-08 09:08:12.807778	/home/arnaud/.virtualenvs/inmanta/bin/python -m inmanta.app -vvv export -X -e 35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f --server_address localhost --server_port 47773 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp_c58wunk	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    Checking out 2.0.6 on /tmp/tmp0fv1ljeq/server/environments/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/libs/std\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003896)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002231)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000073)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:47773/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:47773/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:47773/api/v1/file/967cda255497c4742364e7a35dc381dd70d6fa13\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:47773/api/v1/file/82ed41381f2512462ae3bb9e514f84d8cd2d0772\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:47773/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:47773/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:47773/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:47773/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	785274ad-c222-42a2-8026-9d01666cc430
c7b98baf-b6aa-4f65-a734-2a4ecc08b1a8	2020-09-08 09:08:15.722894	2020-09-08 09:08:15.725841		Init		Using extra environment variables during compile \n	0	9616d4b2-5123-4a71-924e-d4fcc673ff3f
effe4a0c-5788-4f0c-88cf-0c86f1e71126	2020-09-08 09:08:15.727144	2020-09-08 09:08:16.519744	/home/arnaud/.virtualenvs/inmanta/bin/python -m inmanta.app -vvv export -X -e 35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f --server_address localhost --server_port 47773 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpur6sh1sz	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003709)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002272)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000077)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:47773/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:47773/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:47773/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:47773/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:47773/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	9616d4b2-5123-4a71-924e-d4fcc673ff3f
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type) FROM stdin;
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2020-09-08 09:08:14.567991	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2020-09-08 09:08:15.544143	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2020-09-08 09:08:16.467396	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2020-09-08 09:08:16.494888	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, send_event, environment, version, resource_version_ids) FROM stdin;
499936c8-2a37-49d1-a820-a708300edcf8	store	2020-09-08 09:08:10.174812	2020-09-08 09:08:10.192392	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2020-09-08T09:08:10.192400\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
f9d8c87b-9dae-47f4-b0b9-9708381235d3	pull	2020-09-08 09:08:12.68345	2020-09-08 09:08:12.691344	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-09-08T09:08:12.691354\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1bab58c6-69a2-4af5-b5ca-5bf87110cf17	pull	2020-09-08 09:08:14.472945	2020-09-08 09:08:14.474707	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-09-08T09:08:14.474710\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
049746f4-2a37-41e6-94f9-bbe96d9defcf	deploy	2020-09-08 09:08:14.468936	2020-09-08 09:08:14.493869	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2020-09-08 09:08:12\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2020-09-08 09:08:12\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"3aeefe4a-153e-444c-9da1-4407d4a0abaf\\"}, \\"timestamp\\": \\"2020-09-08T09:08:14.468984\\"}","{\\"msg\\": \\"Start deploy 3aeefe4a-153e-444c-9da1-4407d4a0abaf of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"3aeefe4a-153e-444c-9da1-4407d4a0abaf\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-09-08T09:08:14.469035\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-08T09:08:14.478090\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-08T09:08:14.488945\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 3aeefe4a-153e-444c-9da1-4407d4a0abaf\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"3aeefe4a-153e-444c-9da1-4407d4a0abaf\\"}, \\"timestamp\\": \\"2020-09-08T09:08:14.493822\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
4ea7bb45-0eff-4c79-9a86-c6da7b3a45e8	deploy	2020-09-08 09:08:14.513286	2020-09-08 09:08:14.528831	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"3e0b8a14-3f16-414e-bac4-5ac0baf4f5fa\\"}, \\"timestamp\\": \\"2020-09-08T09:08:14.513323\\"}","{\\"msg\\": \\"Start deploy 3e0b8a14-3f16-414e-bac4-5ac0baf4f5fa of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"3e0b8a14-3f16-414e-bac4-5ac0baf4f5fa\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-09-08T09:08:14.513384\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-08T09:08:14.524693\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 3e0b8a14-3f16-414e-bac4-5ac0baf4f5fa\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"3e0b8a14-3f16-414e-bac4-5ac0baf4f5fa\\"}, \\"timestamp\\": \\"2020-09-08T09:08:14.528787\\"}"}	deployed	\N	nochange	f	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1ce11e3e-35ef-4e6f-9fdf-c63bca9723b5	pull	2020-09-08 09:08:14.54203	2020-09-08 09:08:14.543684	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-09-08T09:08:14.543688\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
bdee761f-4595-4d3b-b410-7ebb0201b2c6	deploy	2020-09-08 09:08:14.557627	2020-09-08 09:08:14.567991	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2020-09-08 09:08:12', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2020-09-08 09:08:12', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"9e2df0fc-dce9-44f2-b49c-eee5ba7f93d2\\"}, \\"timestamp\\": \\"2020-09-08T09:08:14.557652\\"}","{\\"msg\\": \\"Start deploy 9e2df0fc-dce9-44f2-b49c-eee5ba7f93d2 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"9e2df0fc-dce9-44f2-b49c-eee5ba7f93d2\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-09-08T09:08:14.557688\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-08T09:08:14.563868\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 9e2df0fc-dce9-44f2-b49c-eee5ba7f93d2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"9e2df0fc-dce9-44f2-b49c-eee5ba7f93d2\\"}, \\"timestamp\\": \\"2020-09-08T09:08:14.567948\\"}"}	deployed	\N	nochange	f	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
4fd872b3-863c-476a-93fd-a10de3d626cd	pull	2020-09-08 09:08:15.516297	2020-09-08 09:08:15.517741	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-09-08T09:08:15.517745\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::File[localhost,path=/tmp/test],v=1"}
51d92912-5bbc-42ea-aac8-8c0d6a0f8fb7	deploy	2020-09-08 09:08:15.530831	2020-09-08 09:08:15.544143	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2020-09-08 09:08:15\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2020-09-08 09:08:15\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"73f61cf6-d8e1-479e-a326-cf37244beaa5\\"}, \\"timestamp\\": \\"2020-09-08T09:08:15.530855\\"}","{\\"msg\\": \\"Start deploy 73f61cf6-d8e1-479e-a326-cf37244beaa5 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"73f61cf6-d8e1-479e-a326-cf37244beaa5\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-09-08T09:08:15.530889\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-08T09:08:15.537089\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-08T09:08:15.537241\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 881, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmp0fv1ljeq/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 594, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-09-08T09:08:15.543691\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 73f61cf6-d8e1-479e-a326-cf37244beaa5\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"73f61cf6-d8e1-479e-a326-cf37244beaa5\\"}, \\"timestamp\\": \\"2020-09-08T09:08:15.544099\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	1	{"std::File[localhost,path=/tmp/test],v=1"}
3627acc4-ff79-4b60-b7c5-9585bd4746f4	deploy	2020-09-08 09:08:16.467396	2020-09-08 09:08:16.467396	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2020-09-08T09:08:16.467396\\"}"}	deployed	\N	nochange	f	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
6b0a6178-7242-416f-8d1e-fecdc3195e62	store	2020-09-08 09:08:16.443698	2020-09-08 09:08:16.448308	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2020-09-08T09:08:16.448313\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
98250066-92a6-484e-b4fe-e89cb890a258	pull	2020-09-08 09:08:16.463927	2020-09-08 09:08:16.467545	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-09-08T09:08:16.469194\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2	{"std::File[localhost,path=/tmp/test],v=2"}
75c86d38-2ccb-4ee8-bf2e-2c3f1c69e0c1	deploy	2020-09-08 09:08:16.484184	2020-09-08 09:08:16.494888	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"785ce1de-d089-4c36-b4f8-f382f42c0c33\\"}, \\"timestamp\\": \\"2020-09-08T09:08:16.484210\\"}","{\\"msg\\": \\"Start deploy 785ce1de-d089-4c36-b4f8-f382f42c0c33 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"785ce1de-d089-4c36-b4f8-f382f42c0c33\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-09-08T09:08:16.484245\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-08T09:08:16.491236\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2020-09-08T09:08:16.494327\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 888, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp0fv1ljeq/35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 594, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-09-08T09:08:16.494570\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 785ce1de-d089-4c36-b4f8-f382f42c0c33\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"785ce1de-d089-4c36-b4f8-f382f42c0c33\\"}, \\"timestamp\\": \\"2020-09-08T09:08:16.494849\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"group": {"current": "arnaud", "desired": "root"}, "owner": {"current": "arnaud", "desired": "root"}}}	nochange	f	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2	{"std::File[localhost,path=/tmp/test],v=2"}
9d9e3122-f59f-451c-a17c-f95e1a251ee4	pull	2020-09-08 09:08:16.59181	2020-09-08 09:08:16.594438	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-09-08T09:08:16.594441\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2	{"std::File[localhost,path=/tmp/test],v=2"}
995d2837-5cd4-4f62-b8e6-df6cad53acd9	pull	2020-09-08 09:08:16.592177	2020-09-08 09:08:16.595124	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-09-08T09:08:16.595127\\"}"}	\N	\N	\N	\N	35c42f3f-93ba-4c9f-8cf8-4dd4b2b9b50f	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, current_version) FROM stdin;
core	5
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
    ADD CONSTRAINT resource_pkey PRIMARY KEY (environment, resource_version_id);


--
-- Name: resourceaction resourceaction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction
    ADD CONSTRAINT resourceaction_pkey PRIMARY KEY (action_id);


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
-- Name: agentprocess_sid_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX agentprocess_sid_expired_index ON public.agentprocess USING btree (sid, expired);


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

CREATE INDEX resource_env_resourceid_index ON public.resource USING btree (environment, resource_id, model DESC);


--
-- Name: resource_environment_resource_type_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_type_index ON public.resource USING btree (environment, resource_type);


--
-- Name: resourceaction_environment_action_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_environment_action_started_index ON public.resourceaction USING btree (environment, action, started DESC);


--
-- Name: resourceaction_resource_version_ids_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_resource_version_ids_index ON public.resourceaction USING gin (resource_version_ids);


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
    ADD CONSTRAINT agent_id_primary_fkey FOREIGN KEY (id_primary) REFERENCES public.agentinstance(id) ON DELETE CASCADE;


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
    ADD CONSTRAINT compile_substitute_compile_id_fkey FOREIGN KEY (substitute_compile_id) REFERENCES public.compile(id);


--
-- Name: configurationmodel configurationmodel_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel
    ADD CONSTRAINT configurationmodel_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: dryrun dryrun_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun
    ADD CONSTRAINT dryrun_environment_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: environment environment_project_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment
    ADD CONSTRAINT environment_project_fkey FOREIGN KEY (project) REFERENCES public.project(id) ON DELETE CASCADE;


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
-- Name: resource resource_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_environment_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: resourceaction resourceaction_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction
    ADD CONSTRAINT resourceaction_environment_fkey FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_fkey1 FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

