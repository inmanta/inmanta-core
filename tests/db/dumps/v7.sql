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
-- SELECT pg_catalog.set_config('search_path', '', false);
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
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	internal	2020-10-26 16:09:49.551762	f	ea9dfe85-4f05-49eb-84c6-1085f6117890	\N
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	localhost	2020-10-26 16:09:52.314898	f	e22fb44e-d364-45e0-a499-aae5eef5a221	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
ea9dfe85-4f05-49eb-84c6-1085f6117890	49c13f3c-179d-11eb-802a-106530e9353d	internal	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a
e22fb44e-d364-45e0-a499-aae5eef5a221	49c13f3c-179d-11eb-802a-106530e9353d	localhost	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-laptop	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2020-10-26 16:09:49.551762	2020-10-26 16:09:53.419579	\N	49c13f3c-179d-11eb-802a-106530e9353d
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::Service	1	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::File	1	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::Directory	1	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::Package	1	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::Symlink	1	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::AgentConfig	1	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::Service	2	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::File	2	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::Directory	2	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::Package	2	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::Symlink	2	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	std::AgentConfig	2	{"2ab16878ca22887f47cc6ddb631c89984aa7fdc7": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
770f8330-568f-4131-88ab-0920ead8f4e4	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2020-10-26 16:09:43.240547	2020-10-26 16:09:49.635415	2020-10-26 16:09:43.233361	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	6f9f53c6-df64-43cb-8ca6-4e32e3dc6af8	t	\N	{"errors": []}
8beed2ba-f116-42c2-b9ae-6932868da18c	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2020-10-26 16:09:52.507078	2020-10-26 16:09:53.235565	2020-10-26 16:09:52.495407	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	ffef9b3c-5675-4d07-8a82-8f12b40938cf	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2020-10-26 16:09:47.411828	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
2	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2020-10-26 16:09:53.159583	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
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
48a026f2-8e78-4e43-9af1-43b873d7b621	dev-2	2f39dd5c-07a8-4b92-ba9c-0de2d37ac926			{}	0	f
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	dev-1	2f39dd5c-07a8-4b92-ba9c-0de2d37ac926			{"auto_deploy": true, "server_compile": true, "purge_on_delete": true, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
2f39dd5c-07a8-4b92-ba9c-0de2d37ac926	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
bbaf98c6-e10c-4955-8bf5-a50ab046dc01	2020-10-26 16:09:43.241286	2020-10-26 16:09:43.243497		Init		Using extra environment variables during compile \n	0	770f8330-568f-4131-88ab-0920ead8f4e4
cc17cc8a-be47-4be0-8bcc-aa35e75876bd	2020-10-26 16:09:52.508311	2020-10-26 16:09:52.511743		Init		Using extra environment variables during compile \n	0	8beed2ba-f116-42c2-b9ae-6932868da18c
fe38e7b1-24e8-41b9-9984-483accebaa6f	2020-10-26 16:09:43.244286	2020-10-26 16:09:49.63382	/home/arnaud/.virtualenvs/inmanta/bin/python -m inmanta.app -vvv export -X -e a21a4bdc-68f0-4c4e-a4f2-a6b42880661a --server_address localhost --server_port 48475 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpnqduc4mt	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    Checking out 2.0.7 on /tmp/tmphsbmvtgf/server/environments/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/libs/std\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003515)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002130)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000072)\ninmanta.execute.schedulerINFO    Total compilation time 0.005806\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48475/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48475/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48475/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48475/api/v1/file/2ab16878ca22887f47cc6ddb631c89984aa7fdc7\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48475/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48475/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48475/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48475/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	770f8330-568f-4131-88ab-0920ead8f4e4
56cc3fc3-190c-44a5-9043-18f06c92ec1c	2020-10-26 16:09:52.51273	2020-10-26 16:09:53.234176	/home/arnaud/.virtualenvs/inmanta/bin/python -m inmanta.app -vvv export -X -e a21a4bdc-68f0-4c4e-a4f2-a6b42880661a --server_address localhost --server_port 48475 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp_gpxf0_7	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003258)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002065)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000083)\ninmanta.execute.schedulerINFO    Total compilation time 0.005496\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48475/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48475/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48475/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48475/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48475/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	8beed2ba-f116-42c2-b9ae-6932868da18c
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type) FROM stdin;
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2020-10-26 16:09:51.355497	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2020-10-26 16:09:52.351507	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2020-10-26 16:09:53.181915	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2020-10-26 16:09:53.208033	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, send_event, environment, version, resource_version_ids) FROM stdin;
ffba1016-7ce9-4a10-8ef1-fe2aa33623b0	store	2020-10-26 16:09:47.408791	2020-10-26 16:09:47.426544	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2020-10-26T16:09:47.426553\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
7c3be789-4e00-463c-b467-c8e103ea7f03	pull	2020-10-26 16:09:49.568485	2020-10-26 16:09:49.577614	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-10-26T16:09:49.577622\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
502407b7-ce95-42f4-8d65-7ce6ef828529	pull	2020-10-26 16:09:51.260195	2020-10-26 16:09:51.263677	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-10-26T16:09:51.263683\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1453b53f-4d09-4113-a408-a085187fd42f	deploy	2020-10-26 16:09:53.181915	2020-10-26 16:09:53.181915	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2020-10-26T16:09:53.181915\\"}"}	deployed	\N	nochange	f	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
25069318-82a5-4532-ab19-c5398dfe29c7	deploy	2020-10-26 16:09:51.255938	2020-10-26 16:09:51.285613	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2020-10-26 16:09:49\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2020-10-26 16:09:49\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e963ee92-cb3b-405a-8f36-0b439c86e555\\"}, \\"timestamp\\": \\"2020-10-26T16:09:51.255983\\"}","{\\"msg\\": \\"Start deploy e963ee92-cb3b-405a-8f36-0b439c86e555 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e963ee92-cb3b-405a-8f36-0b439c86e555\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-10-26T16:09:51.256029\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-10-26T16:09:51.269968\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-10-26T16:09:51.277314\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy e963ee92-cb3b-405a-8f36-0b439c86e555\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e963ee92-cb3b-405a-8f36-0b439c86e555\\"}, \\"timestamp\\": \\"2020-10-26T16:09:51.285571\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
be0716e0-de4d-41e7-9101-9ebd111f9be9	deploy	2020-10-26 16:09:51.310692	2020-10-26 16:09:51.321856	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"1f69b91b-2e2b-4142-af5d-76edbb80e425\\"}, \\"timestamp\\": \\"2020-10-26T16:09:51.310730\\"}","{\\"msg\\": \\"Start deploy 1f69b91b-2e2b-4142-af5d-76edbb80e425 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"1f69b91b-2e2b-4142-af5d-76edbb80e425\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-10-26T16:09:51.310791\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-10-26T16:09:51.317685\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 1f69b91b-2e2b-4142-af5d-76edbb80e425\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"1f69b91b-2e2b-4142-af5d-76edbb80e425\\"}, \\"timestamp\\": \\"2020-10-26T16:09:51.321816\\"}"}	deployed	\N	nochange	f	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
b96d5fa3-1144-445c-83c7-df4bb243f9f2	pull	2020-10-26 16:09:51.331171	2020-10-26 16:09:51.332554	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-10-26T16:09:51.332558\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c7bb99c1-0b07-4d83-98ce-e9db70e0d0db	pull	2020-10-26 16:09:53.419514	2020-10-26 16:09:53.422039	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-10-26T16:09:53.422042\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2	{"std::File[localhost,path=/tmp/test],v=2"}
940bcb4f-53d0-4fdc-9f0f-01093c864ded	deploy	2020-10-26 16:09:51.345449	2020-10-26 16:09:51.355497	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2020-10-26 16:09:49', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2020-10-26 16:09:49', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"7c906f15-9d7a-4440-9695-a381b80a601e\\"}, \\"timestamp\\": \\"2020-10-26T16:09:51.345491\\"}","{\\"msg\\": \\"Start deploy 7c906f15-9d7a-4440-9695-a381b80a601e of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"7c906f15-9d7a-4440-9695-a381b80a601e\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-10-26T16:09:51.345524\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-10-26T16:09:51.351493\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 7c906f15-9d7a-4440-9695-a381b80a601e\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"7c906f15-9d7a-4440-9695-a381b80a601e\\"}, \\"timestamp\\": \\"2020-10-26T16:09:51.355459\\"}"}	deployed	\N	nochange	f	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
294475cf-f610-451f-8aa5-3f0ed1a9a0f2	pull	2020-10-26 16:09:52.324195	2020-10-26 16:09:52.326277	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-10-26T16:09:52.326280\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::File[localhost,path=/tmp/test],v=1"}
e38b7254-5813-4b62-a018-7172c31d735c	pull	2020-10-26 16:09:53.178907	2020-10-26 16:09:53.182055	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-10-26T16:09:53.183973\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2	{"std::File[localhost,path=/tmp/test],v=2"}
a6f6b0ea-cd43-4595-b5f3-0cdd76ec964d	deploy	2020-10-26 16:09:53.197803	2020-10-26 16:09:53.208033	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"ee4ad43d-bcec-462b-91b1-014a64b690f3\\"}, \\"timestamp\\": \\"2020-10-26T16:09:53.197829\\"}","{\\"msg\\": \\"Start deploy ee4ad43d-bcec-462b-91b1-014a64b690f3 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"ee4ad43d-bcec-462b-91b1-014a64b690f3\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-10-26T16:09:53.197864\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-10-26T16:09:53.204553\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2020-10-26T16:09:53.207531\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 888, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmphsbmvtgf/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 594, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-10-26T16:09:53.207770\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy ee4ad43d-bcec-462b-91b1-014a64b690f3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"ee4ad43d-bcec-462b-91b1-014a64b690f3\\"}, \\"timestamp\\": \\"2020-10-26T16:09:53.207999\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"group": {"current": "arnaud", "desired": "root"}, "owner": {"current": "arnaud", "desired": "root"}}}	nochange	f	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2	{"std::File[localhost,path=/tmp/test],v=2"}
2191dcc0-23e4-4195-90b1-7a3191aafc2d	deploy	2020-10-26 16:09:52.341059	2020-10-26 16:09:52.351507	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2020-10-26 16:09:52\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2020-10-26 16:09:52\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"48ecc31d-daab-45fd-9bb5-b9e1b2343878\\"}, \\"timestamp\\": \\"2020-10-26T16:09:52.341084\\"}","{\\"msg\\": \\"Start deploy 48ecc31d-daab-45fd-9bb5-b9e1b2343878 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"48ecc31d-daab-45fd-9bb5-b9e1b2343878\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-10-26T16:09:52.341119\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-10-26T16:09:52.348015\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-10-26T16:09:52.348149\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 881, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmphsbmvtgf/a21a4bdc-68f0-4c4e-a4f2-a6b42880661a/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 594, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-10-26T16:09:52.351204\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 48ecc31d-daab-45fd-9bb5-b9e1b2343878\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"48ecc31d-daab-45fd-9bb5-b9e1b2343878\\"}, \\"timestamp\\": \\"2020-10-26T16:09:52.351459\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	1	{"std::File[localhost,path=/tmp/test],v=1"}
6770c00a-f043-4189-b264-c9ed2c13fa46	store	2020-10-26 16:09:53.158057	2020-10-26 16:09:53.163331	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2020-10-26T16:09:53.163342\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
79d2331a-a650-4774-a1b2-5fb577bced51	pull	2020-10-26 16:09:53.419283	2020-10-26 16:09:53.421626	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-10-26T16:09:53.421629\\"}"}	\N	\N	\N	\N	a21a4bdc-68f0-4c4e-a4f2-a6b42880661a	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, current_version) FROM stdin;
core	7
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
-- Name: resourceaction_environment_version_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_environment_version_started_index ON public.resourceaction USING btree (environment, version, started DESC);


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
    ADD CONSTRAINT compile_substitute_compile_id_fkey FOREIGN KEY (substitute_compile_id) REFERENCES public.compile(id) ON DELETE CASCADE;


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

