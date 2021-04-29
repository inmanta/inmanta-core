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
5c1d2de2-d403-4812-9c0c-a52d0324fd45	internal	2021-04-29 15:50:29.450454	f	9218cc8e-4be6-40e2-b534-839e1328abb4	\N
5c1d2de2-d403-4812-9c0c-a52d0324fd45	localhost	2021-04-29 15:50:32.387422	f	5b0ed48e-dd0a-43f1-9638-cb9f06146305	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
9218cc8e-4be6-40e2-b534-839e1328abb4	dbde7caa-a8f1-11eb-a55a-e0d55ee746aa	internal	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45
5b0ed48e-dd0a-43f1-9638-cb9f06146305	dbde7caa-a8f1-11eb-a55a-e0d55ee746aa	localhost	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arthur	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2021-04-29 15:50:29.450454	2021-04-29 15:50:33.584808	\N	dbde7caa-a8f1-11eb-a55a-e0d55ee746aa
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::Service	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::File	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::Directory	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::Package	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::Symlink	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::AgentConfig	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::Service	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::File	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::Directory	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::Package	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::Symlink	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5c1d2de2-d403-4812-9c0c-a52d0324fd45	std::AgentConfig	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
7f98eb87-c82c-474b-bc25-c0262b97988f	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2021-04-29 15:50:26.946376	2021-04-29 15:50:29.567963	2021-04-29 15:50:26.938999	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	00cc127d-bc03-4599-8d1a-b885203cd4ea	t	\N	{"errors": []}
d702b48f-3628-44e8-85dc-143ca798c4c0	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2021-04-29 15:50:32.625631	2021-04-29 15:50:33.524048	2021-04-29 15:50:32.602949	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	8e371caa-f4a4-4e65-bbc1-2209b28c9876	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2021-04-29 15:50:28.676457	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "arthur", "inmanta:compile:state": "success"}}	2	{}	{}
2	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2021-04-29 15:50:33.456821	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "arthur", "inmanta:compile:state": "success"}}	2	{}	{}
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
4f9f3526-1e86-4d46-b94c-8ab1bc5f2aeb	dev-2	0b7d4889-4ff2-4b15-aa56-ba5947487d3e			{}	0	f
5c1d2de2-d403-4812-9c0c-a52d0324fd45	dev-1	0b7d4889-4ff2-4b15-aa56-ba5947487d3e			{"auto_deploy": true, "server_compile": true, "purge_on_delete": true, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
0b7d4889-4ff2-4b15-aa56-ba5947487d3e	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
ea220493-e2b0-41a9-8191-54b368d6f94e	2021-04-29 15:50:26.946951	2021-04-29 15:50:26.948887		Init		Using extra environment variables during compile \n	0	7f98eb87-c82c-474b-bc25-c0262b97988f
3576cebf-5807-43c4-b8e5-8122fbb6ccd6	2021-04-29 15:50:26.949492	2021-04-29 15:50:29.566765	/home/sander/.virtualenvs/iso3/bin/python -m inmanta.app -vvv export -X -e 5c1d2de2-d403-4812-9c0c-a52d0324fd45 --server_address localhost --server_port 46227 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp_5mgowzs	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    Checking out 2.1.8 on /tmp/tmpfk4jnety/server/environments/5c1d2de2-d403-4812-9c0c-a52d0324fd45/libs/std\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003434)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002367)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000174)\ninmanta.execute.schedulerINFO    Total compilation time 0.006203\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46227/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46227/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46227/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46227/api/v1/file/4d9b69348bf390471ca4caeaf0295673154b25e9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46227/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46227/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46227/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46227/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	7f98eb87-c82c-474b-bc25-c0262b97988f
2d320c26-ce58-4550-95f1-ef23bec98e83	2021-04-29 15:50:32.627665	2021-04-29 15:50:32.632477		Init		Using extra environment variables during compile \n	0	d702b48f-3628-44e8-85dc-143ca798c4c0
443cf39c-1e9f-4916-b501-d8b5703ae003	2021-04-29 15:50:32.634048	2021-04-29 15:50:33.523	/home/sander/.virtualenvs/iso3/bin/python -m inmanta.app -vvv export -X -e 5c1d2de2-d403-4812-9c0c-a52d0324fd45 --server_address localhost --server_port 46227 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpq9ty1ipd	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003355)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002218)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000071)\ninmanta.execute.schedulerINFO    Total compilation time 0.005733\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46227/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46227/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46227/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46227/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46227/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	d702b48f-3628-44e8-85dc-143ca798c4c0
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type) FROM stdin;
5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2021-04-29 15:50:31.413451	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2021-04-29 15:50:32.448809	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
5c1d2de2-d403-4812-9c0c-a52d0324fd45	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2021-04-29 15:50:33.476681	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
5c1d2de2-d403-4812-9c0c-a52d0324fd45	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2021-04-29 15:50:33.495911	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, send_event, environment, version, resource_version_ids) FROM stdin;
1a0a9461-d416-40c5-a090-ed504794f622	store	2021-04-29 15:50:28.673668	2021-04-29 15:50:28.689373	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2021-04-29T15:50:28.689380\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
e1d1e623-47ad-4102-859f-062ad452c32d	pull	2021-04-29 15:50:29.462544	2021-04-29 15:50:29.469036	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-04-29T15:50:29.469044\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
56ddf946-3578-47fe-bfe3-07dc3fc3c21a	pull	2021-04-29 15:50:31.339112	2021-04-29 15:50:31.340478	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-04-29T15:50:31.340482\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
827a2d16-1f49-40a7-b9be-f09b4e481fe1	deploy	2021-04-29 15:50:33.476681	2021-04-29 15:50:33.476681	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2021-04-29T15:50:33.476681\\"}"}	deployed	\N	nochange	f	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
d9098462-5465-463b-ba32-e862230e5880	deploy	2021-04-29 15:50:31.335257	2021-04-29 15:50:31.357191	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2021-04-29 15:50:29\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2021-04-29 15:50:29\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e8e17f1f-3758-4b8e-86b4-4dd8bf64812e\\"}, \\"timestamp\\": \\"2021-04-29T15:50:31.335296\\"}","{\\"msg\\": \\"Start deploy e8e17f1f-3758-4b8e-86b4-4dd8bf64812e of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e8e17f1f-3758-4b8e-86b4-4dd8bf64812e\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2021-04-29T15:50:31.335340\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-04-29T15:50:31.348596\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-04-29T15:50:31.353091\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy e8e17f1f-3758-4b8e-86b4-4dd8bf64812e\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e8e17f1f-3758-4b8e-86b4-4dd8bf64812e\\"}, \\"timestamp\\": \\"2021-04-29T15:50:31.357148\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
49b8b00a-eb02-4035-bc4e-899f1dc037d2	deploy	2021-04-29 15:50:31.37588	2021-04-29 15:50:31.384207	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"f6527873-a040-42a5-be84-c55e72c8b7e5\\"}, \\"timestamp\\": \\"2021-04-29T15:50:31.375913\\"}","{\\"msg\\": \\"Start deploy f6527873-a040-42a5-be84-c55e72c8b7e5 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"f6527873-a040-42a5-be84-c55e72c8b7e5\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2021-04-29T15:50:31.375968\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-04-29T15:50:31.380760\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy f6527873-a040-42a5-be84-c55e72c8b7e5\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"f6527873-a040-42a5-be84-c55e72c8b7e5\\"}, \\"timestamp\\": \\"2021-04-29T15:50:31.384166\\"}"}	deployed	\N	nochange	f	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
15072e8d-8ef5-4d14-a679-09c5b9a3d9dc	pull	2021-04-29 15:50:31.392237	2021-04-29 15:50:31.393485	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-04-29T15:50:31.393488\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
998db25f-bc80-41bf-95f7-3606f8a21ba8	deploy	2021-04-29 15:50:31.401134	2021-04-29 15:50:31.413451	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2021-04-29 15:50:29', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2021-04-29 15:50:29', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"d6b667e8-475f-4726-8816-cc4d59d46009\\"}, \\"timestamp\\": \\"2021-04-29T15:50:31.401157\\"}","{\\"msg\\": \\"Start deploy d6b667e8-475f-4726-8816-cc4d59d46009 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"d6b667e8-475f-4726-8816-cc4d59d46009\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2021-04-29T15:50:31.401191\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-04-29T15:50:31.409543\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy d6b667e8-475f-4726-8816-cc4d59d46009\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"d6b667e8-475f-4726-8816-cc4d59d46009\\"}, \\"timestamp\\": \\"2021-04-29T15:50:31.413409\\"}"}	deployed	\N	nochange	f	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
ca8bfef0-f082-4510-a408-8812440e6318	pull	2021-04-29 15:50:32.418272	2021-04-29 15:50:32.421504	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-04-29T15:50:32.421511\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::File[localhost,path=/tmp/test],v=1"}
1df5413a-ed6e-444b-84e0-12d692dec33f	deploy	2021-04-29 15:50:32.434323	2021-04-29 15:50:32.448809	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2021-04-29 15:50:32\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2021-04-29 15:50:32\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"a045e224-a3ee-4247-b383-5e44bcec5cd5\\"}, \\"timestamp\\": \\"2021-04-29T15:50:32.434353\\"}","{\\"msg\\": \\"Start deploy a045e224-a3ee-4247-b383-5e44bcec5cd5 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"a045e224-a3ee-4247-b383-5e44bcec5cd5\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2021-04-29T15:50:32.434396\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-04-29T15:50:32.445108\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-04-29T15:50:32.445255\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 881, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpfk4jnety/5c1d2de2-d403-4812-9c0c-a52d0324fd45/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 603, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2021-04-29T15:50:32.448502\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy a045e224-a3ee-4247-b383-5e44bcec5cd5\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"a045e224-a3ee-4247-b383-5e44bcec5cd5\\"}, \\"timestamp\\": \\"2021-04-29T15:50:32.448774\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	5c1d2de2-d403-4812-9c0c-a52d0324fd45	1	{"std::File[localhost,path=/tmp/test],v=1"}
a1af7256-8398-4184-ae2c-96dfcbae6f9a	store	2021-04-29 15:50:33.455153	2021-04-29 15:50:33.459898	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2021-04-29T15:50:33.459904\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
60518acc-cbaf-4fa6-aa45-84a61273d56f	pull	2021-04-29 15:50:33.58506	2021-04-29 15:50:33.588304	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-04-29T15:50:33.588308\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2	{"std::File[localhost,path=/tmp/test],v=2"}
f927bf2a-8ba9-4de7-999a-47bd7619e93f	pull	2021-04-29 15:50:33.473692	2021-04-29 15:50:33.476551	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-04-29T15:50:33.477681\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2	{"std::File[localhost,path=/tmp/test],v=2"}
67b54c20-5f41-4a14-8228-dc88e2e75f74	pull	2021-04-29 15:50:33.584955	2021-04-29 15:50:33.588758	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-04-29T15:50:33.588760\\"}"}	\N	\N	\N	\N	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
0d75b37b-96b2-4419-9001-4aa6fe121826	deploy	2021-04-29 15:50:33.486208	2021-04-29 15:50:33.495911	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"a266118c-7010-4254-8493-8fcb90cfda76\\"}, \\"timestamp\\": \\"2021-04-29T15:50:33.486233\\"}","{\\"msg\\": \\"Start deploy a266118c-7010-4254-8493-8fcb90cfda76 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"a266118c-7010-4254-8493-8fcb90cfda76\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2021-04-29T15:50:33.486265\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-04-29T15:50:33.492416\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2021-04-29T15:50:33.495424\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 888, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpfk4jnety/5c1d2de2-d403-4812-9c0c-a52d0324fd45/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 603, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2021-04-29T15:50:33.495629\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy a266118c-7010-4254-8493-8fcb90cfda76\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"a266118c-7010-4254-8493-8fcb90cfda76\\"}, \\"timestamp\\": \\"2021-04-29T15:50:33.495876\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"group": {"current": "sander", "desired": "root"}, "owner": {"current": "sander", "desired": "root"}}}	nochange	f	5c1d2de2-d403-4812-9c0c-a52d0324fd45	2	{"std::File[localhost,path=/tmp/test],v=2"}
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

