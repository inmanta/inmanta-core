--
-- PostgreSQL database dump
--

-- Dumped from database version 10.12
-- Dumped by pg_dump version 10.12

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
    compile_data jsonb
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
    skipped_for_undeployable character varying[]
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
    resource_version_id character varying NOT NULL,
    agent character varying NOT NULL,
    last_deploy timestamp with time zone,
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
    started timestamp with time zone NOT NULL,
    finished timestamp with time zone,
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
b0549198-3d76-441a-aa3e-6cf1ea12020c	internal	2021-05-19 14:44:51.601054+02	f	68748f87-8040-4c5c-8fac-e720fcc38499	\N
b0549198-3d76-441a-aa3e-6cf1ea12020c	localhost	2021-05-19 14:44:54.00023+02	f	bda3a1ac-c416-4138-a288-c6078df4124f	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
68748f87-8040-4c5c-8fac-e720fcc38499	00fbd88a-b8a0-11eb-8693-e0d55ee746aa	internal	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c
bda3a1ac-c416-4138-a288-c6078df4124f	00fbd88a-b8a0-11eb-8693-e0d55ee746aa	localhost	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arthur	b0549198-3d76-441a-aa3e-6cf1ea12020c	2021-05-19 14:44:51.601054+02	2021-05-19 14:44:55.399839+02	\N	00fbd88a-b8a0-11eb-8693-e0d55ee746aa
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::Service	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::File	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::Directory	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::Package	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::Symlink	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::AgentConfig	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::Service	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::File	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::Directory	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::Package	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::Symlink	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
b0549198-3d76-441a-aa3e-6cf1ea12020c	std::AgentConfig	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
d7ddabf2-baa0-41ba-b5d3-cc4e08b8a926	b0549198-3d76-441a-aa3e-6cf1ea12020c	2021-05-19 14:44:48.991959+02	2021-05-19 14:44:51.728102+02	2021-05-19 14:44:48.986031+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	a84d70ad-d631-4142-8c59-08b8ea5d2fbb	t	\N	{"errors": []}
9d332ea9-7321-4c79-ae64-426b25241ba6	b0549198-3d76-441a-aa3e-6cf1ea12020c	2021-05-19 14:44:54.169166+02	2021-05-19 14:44:55.202389+02	2021-05-19 14:44:54.160294+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	747c2232-4ce6-43c6-baca-77a5abdd9d94	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	b0549198-3d76-441a-aa3e-6cf1ea12020c	2021-05-19 14:44:50.721884+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "arthur", "inmanta:compile:state": "success"}}	2	{}	{}
2	b0549198-3d76-441a-aa3e-6cf1ea12020c	2021-05-19 14:44:55.124085+02	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "arthur", "inmanta:compile:state": "success"}}	2	{}	{}
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
625412c9-935a-49e1-bfda-7f8cc67915d8	dev-2	069066a0-cc91-4a08-bfd5-bf64344a2ad9			{}	0	f
b0549198-3d76-441a-aa3e-6cf1ea12020c	dev-1	069066a0-cc91-4a08-bfd5-bf64344a2ad9			{"auto_deploy": true, "server_compile": true, "purge_on_delete": true, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
069066a0-cc91-4a08-bfd5-bf64344a2ad9	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
a929a6ba-7c77-4cd1-8835-9897c098b11a	2021-05-19 14:44:48.992546+02	2021-05-19 14:44:48.994059+02		Init		Using extra environment variables during compile \n	0	d7ddabf2-baa0-41ba-b5d3-cc4e08b8a926
bcdd903e-6da4-449f-b64e-f4cefdc228c9	2021-05-19 14:44:48.994589+02	2021-05-19 14:44:51.726961+02	/home/sander/.virtualenvs/inmanta-core36/bin/python -m inmanta.app -vvv export -X -e b0549198-3d76-441a-aa3e-6cf1ea12020c --server_address localhost --server_port 55075 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpa9g91xeo	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    Checking out 2.1.9 on /tmp/tmp8dzao9l9/server/environments/b0549198-3d76-441a-aa3e-6cf1ea12020c/libs/std\ninmanta.module           DEBUG   Parsing took 0.803271 seconds\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.004189)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002439)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000071)\ninmanta.execute.schedulerINFO    Total compilation time 0.006817\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55075/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55075/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55075/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55075/api/v1/file/4d9b69348bf390471ca4caeaf0295673154b25e9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55075/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55075/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55075/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55075/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	d7ddabf2-baa0-41ba-b5d3-cc4e08b8a926
75ed77a6-b5d3-4cfb-8d4b-c4e0dd676e4f	2021-05-19 14:44:54.170164+02	2021-05-19 14:44:54.172349+02		Init		Using extra environment variables during compile \n	0	9d332ea9-7321-4c79-ae64-426b25241ba6
7d7c6133-28f2-4c0a-ac82-cef0e3c2f51a	2021-05-19 14:44:54.173177+02	2021-05-19 14:44:55.201297+02	/home/sander/.virtualenvs/inmanta-core36/bin/python -m inmanta.app -vvv export -X -e b0549198-3d76-441a-aa3e-6cf1ea12020c --server_address localhost --server_port 55075 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpmz3fnc0e	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.018542 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003503)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002064)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000069)\ninmanta.execute.schedulerINFO    Total compilation time 0.005757\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55075/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55075/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55075/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55075/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55075/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	9d332ea9-7321-4c79-ae64-426b25241ba6
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type) FROM stdin;
b0549198-3d76-441a-aa3e-6cf1ea12020c	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2021-05-19 14:44:53.020928+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
b0549198-3d76-441a-aa3e-6cf1ea12020c	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2021-05-19 14:44:54.049749+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
b0549198-3d76-441a-aa3e-6cf1ea12020c	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2021-05-19 14:44:55.14288+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
b0549198-3d76-441a-aa3e-6cf1ea12020c	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2021-05-19 14:44:55.16183+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, send_event, environment, version, resource_version_ids) FROM stdin;
d52470c8-0c10-438f-95e1-e2ed186abbb0	store	2021-05-19 14:44:50.719659+02	2021-05-19 14:44:50.732008+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2021-05-19T14:44:50.732026+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
55835974-7287-4f80-86ff-ff7713cadcb7	pull	2021-05-19 14:44:51.612395+02	2021-05-19 14:44:51.619473+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-05-19T14:44:51.619491+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
a74dfcaf-1d72-402b-872e-3012589f2a22	pull	2021-05-19 14:44:52.949706+02	2021-05-19 14:44:52.951303+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-05-19T14:44:52.951329+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
818bdd21-bd92-4c65-991d-0687a715bd87	deploy	2021-05-19 14:44:52.945953+02	2021-05-19 14:44:52.964189+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2021-05-19 14:44:51+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2021-05-19 14:44:51+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"67ab7808-f31a-4c3a-9615-5aed4e319005\\"}, \\"timestamp\\": \\"2021-05-19T12:44:52.946024+00:00\\"}","{\\"msg\\": \\"Start deploy 67ab7808-f31a-4c3a-9615-5aed4e319005 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"67ab7808-f31a-4c3a-9615-5aed4e319005\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2021-05-19T12:44:52.946114+00:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-05-19T12:44:52.954575+00:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-05-19T12:44:52.960423+00:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 67ab7808-f31a-4c3a-9615-5aed4e319005\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"67ab7808-f31a-4c3a-9615-5aed4e319005\\"}, \\"timestamp\\": \\"2021-05-19T12:44:52.964145+00:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
067c68a3-bf22-44f7-919e-e6d76437f2dc	deploy	2021-05-19 14:44:52.984422+02	2021-05-19 14:44:52.993555+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"dc16bbf1-1f10-4fee-8b12-2e9b20d38a4e\\"}, \\"timestamp\\": \\"2021-05-19T12:44:52.984496+00:00\\"}","{\\"msg\\": \\"Start deploy dc16bbf1-1f10-4fee-8b12-2e9b20d38a4e of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"dc16bbf1-1f10-4fee-8b12-2e9b20d38a4e\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2021-05-19T12:44:52.984580+00:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-05-19T12:44:52.990058+00:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy dc16bbf1-1f10-4fee-8b12-2e9b20d38a4e\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"dc16bbf1-1f10-4fee-8b12-2e9b20d38a4e\\"}, \\"timestamp\\": \\"2021-05-19T12:44:52.993510+00:00\\"}"}	deployed	\N	nochange	f	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
ae401cff-922d-4f2a-92d1-a458353b1a6e	pull	2021-05-19 14:44:53.001719+02	2021-05-19 14:44:53.002855+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-05-19T14:44:53.002865+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
b3366982-7f88-4df1-a500-0fdb8f93bfdc	deploy	2021-05-19 14:44:53.010368+02	2021-05-19 14:44:53.020928+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2021-05-19 14:44:51+0200', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2021-05-19 14:44:51+0200', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"f0924bc9-e41e-43de-845a-0a24b1d14250\\"}, \\"timestamp\\": \\"2021-05-19T12:44:53.010422+00:00\\"}","{\\"msg\\": \\"Start deploy f0924bc9-e41e-43de-845a-0a24b1d14250 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"f0924bc9-e41e-43de-845a-0a24b1d14250\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2021-05-19T12:44:53.010482+00:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-05-19T12:44:53.016366+00:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy f0924bc9-e41e-43de-845a-0a24b1d14250\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"f0924bc9-e41e-43de-845a-0a24b1d14250\\"}, \\"timestamp\\": \\"2021-05-19T12:44:53.020873+00:00\\"}"}	deployed	\N	nochange	f	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
ac498296-2715-4a2e-b02c-9527de2d3088	pull	2021-05-19 14:44:54.015806+02	2021-05-19 14:44:54.02386+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-05-19T14:44:54.023878+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::File[localhost,path=/tmp/test],v=1"}
d3e1c7fb-ad42-4bb2-8597-d6f2ac331c0d	deploy	2021-05-19 14:44:54.037086+02	2021-05-19 14:44:54.049749+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2021-05-19 14:44:54+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2021-05-19 14:44:54+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"7348f508-41c4-44b5-8c86-a37e617743a1\\"}, \\"timestamp\\": \\"2021-05-19T12:44:54.037149+00:00\\"}","{\\"msg\\": \\"Start deploy 7348f508-41c4-44b5-8c86-a37e617743a1 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"7348f508-41c4-44b5-8c86-a37e617743a1\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2021-05-19T12:44:54.037219+00:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-05-19T12:44:54.043976+00:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-05-19T12:44:54.044138+00:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 906, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmp8dzao9l9/b0549198-3d76-441a-aa3e-6cf1ea12020c/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2021-05-19T12:44:54.049380+00:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 7348f508-41c4-44b5-8c86-a37e617743a1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"7348f508-41c4-44b5-8c86-a37e617743a1\\"}, \\"timestamp\\": \\"2021-05-19T12:44:54.049702+00:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	b0549198-3d76-441a-aa3e-6cf1ea12020c	1	{"std::File[localhost,path=/tmp/test],v=1"}
6873b04f-0dfb-40ad-9320-421a276acb6c	store	2021-05-19 14:44:55.122665+02	2021-05-19 14:44:55.126898+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2021-05-19T14:44:55.126910+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
90ec4798-2138-4826-8239-797eb2faf661	pull	2021-05-19 14:44:55.140213+02	2021-05-19 14:44:55.142731+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-05-19T14:44:55.143863+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	2	{"std::File[localhost,path=/tmp/test],v=2"}
9d4fa2e7-3543-4bf3-9a36-15eb38a2c381	deploy	2021-05-19 14:44:55.14288+02	2021-05-19 14:44:55.14288+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2021-05-19T12:44:55.142880+00:00\\"}"}	deployed	\N	nochange	f	b0549198-3d76-441a-aa3e-6cf1ea12020c	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
02276978-110e-42f5-9715-ca6e042e61dc	deploy	2021-05-19 14:44:55.15165+02	2021-05-19 14:44:55.16183+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"d3eb5220-06c7-4243-a368-f22783cbd24f\\"}, \\"timestamp\\": \\"2021-05-19T12:44:55.151715+00:00\\"}","{\\"msg\\": \\"Start deploy d3eb5220-06c7-4243-a368-f22783cbd24f of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"d3eb5220-06c7-4243-a368-f22783cbd24f\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2021-05-19T12:44:55.151782+00:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-05-19T12:44:55.158385+00:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2021-05-19T12:44:55.161197+00:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 913, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp8dzao9l9/b0549198-3d76-441a-aa3e-6cf1ea12020c/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2021-05-19T12:44:55.161472+00:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy d3eb5220-06c7-4243-a368-f22783cbd24f\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"d3eb5220-06c7-4243-a368-f22783cbd24f\\"}, \\"timestamp\\": \\"2021-05-19T12:44:55.161790+00:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"group": {"current": "sander", "desired": "root"}, "owner": {"current": "sander", "desired": "root"}}}	nochange	f	b0549198-3d76-441a-aa3e-6cf1ea12020c	2	{"std::File[localhost,path=/tmp/test],v=2"}
2c603cde-83d9-49fa-9c08-e6ed21a0e967	pull	2021-05-19 14:44:55.399428+02	2021-05-19 14:44:55.403751+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-05-19T14:44:55.403760+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	2	{"std::File[localhost,path=/tmp/test],v=2"}
9d1d6bc4-462e-4996-a58b-e179750f088c	pull	2021-05-19 14:44:55.398785+02	2021-05-19 14:44:55.403047+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-05-19T14:44:55.403059+02:00\\"}"}	\N	\N	\N	\N	b0549198-3d76-441a-aa3e-6cf1ea12020c	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170}
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

