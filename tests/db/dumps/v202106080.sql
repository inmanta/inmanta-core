--
-- PostgreSQL database dump
--

-- Dumped from database version 10.17
-- Dumped by pg_dump version 10.17

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
5659aecb-8a48-43c2-be64-bc12cd228e6d	internal	2021-06-09 09:14:15.988197+02	f	3ed35cd6-be7d-44d2-a0f5-ba5a8424aaef	\N
5659aecb-8a48-43c2-be64-bc12cd228e6d	localhost	2021-06-09 09:14:18.079065+02	f	6bdd1857-7337-4835-8737-2bf1e07c3847	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
3ed35cd6-be7d-44d2-a0f5-ba5a8424aaef	4cb5fcb2-c8f2-11eb-9c8d-106530e13c0b	internal	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d
6bdd1857-7337-4835-8737-2bf1e07c3847	4cb5fcb2-c8f2-11eb-9c8d-106530e13c0b	localhost	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-laptop	5659aecb-8a48-43c2-be64-bc12cd228e6d	2021-06-09 09:14:15.988197+02	2021-06-09 09:14:19.144997+02	\N	4cb5fcb2-c8f2-11eb-9c8d-106530e13c0b
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::Service	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::File	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::Directory	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::Package	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::Symlink	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::AgentConfig	1	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::Service	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::File	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::Directory	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::Package	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::Symlink	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
5659aecb-8a48-43c2-be64-bc12cd228e6d	std::AgentConfig	2	{"4d9b69348bf390471ca4caeaf0295673154b25e9": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
d535bc55-7956-4a02-9e31-6e3820a13fdf	5659aecb-8a48-43c2-be64-bc12cd228e6d	2021-06-09 09:14:13.13636+02	2021-06-09 09:14:16.176463+02	2021-06-09 09:14:13.12897+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	59d6a4f9-5c6d-42ca-88e6-cd7b5751a243	t	\N	{"errors": []}
ca8235e6-766a-4032-8cf0-3cfdd6b25758	5659aecb-8a48-43c2-be64-bc12cd228e6d	2021-06-09 09:14:18.257837+02	2021-06-09 09:14:19.036375+02	2021-06-09 09:14:18.249173+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	45de3746-36e4-49f2-8b94-e5a26f32fdf7	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	5659aecb-8a48-43c2-be64-bc12cd228e6d	2021-06-09 09:14:15.354443+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
2	5659aecb-8a48-43c2-be64-bc12cd228e6d	2021-06-09 09:14:18.946561+02	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
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
d558d982-9201-4388-8a5b-3feaa736e50f	dev-2	cb94f149-9bbd-4cef-ba3d-5d8470933541			{}	0	f
5659aecb-8a48-43c2-be64-bc12cd228e6d	dev-1	cb94f149-9bbd-4cef-ba3d-5d8470933541			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
cb94f149-9bbd-4cef-ba3d-5d8470933541	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
199f249b-f54b-4371-a7f8-6d812637ea5e	2021-06-09 09:14:13.137288+02	2021-06-09 09:14:13.140113+02		Init		Using extra environment variables during compile \n	0	d535bc55-7956-4a02-9e31-6e3820a13fdf
2704c29b-1930-4f71-998b-9feeff63f44d	2021-06-09 09:14:13.140992+02	2021-06-09 09:14:16.175001+02	/home/arnaud/.virtualenvs/inmanta-core/bin/python -m inmanta.app -vvv export -X -e 5659aecb-8a48-43c2-be64-bc12cd228e6d --server_address localhost --server_port 45705 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpm54c12u6	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    Checking out 3.0.1 on /tmp/tmpf2fwbsi9/server/environments/5659aecb-8a48-43c2-be64-bc12cd228e6d/libs/std\ninmanta.module           DEBUG   Parsing took 1.541705 seconds\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.004004)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002200)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000073)\ninmanta.execute.schedulerINFO    Total compilation time 0.006371\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:45705/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:45705/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:45705/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:45705/api/v1/file/4d9b69348bf390471ca4caeaf0295673154b25e9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:45705/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:45705/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:45705/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:45705/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	d535bc55-7956-4a02-9e31-6e3820a13fdf
4fd12ad9-dc6a-4247-9082-cb80094d5f11	2021-06-09 09:14:18.258845+02	2021-06-09 09:14:18.261155+02		Init		Using extra environment variables during compile \n	0	ca8235e6-766a-4032-8cf0-3cfdd6b25758
2a649d14-473d-449e-a5f8-0596179e6a4d	2021-06-09 09:14:18.26192+02	2021-06-09 09:14:19.035139+02	/home/arnaud/.virtualenvs/inmanta-core/bin/python -m inmanta.app -vvv export -X -e 5659aecb-8a48-43c2-be64-bc12cd228e6d --server_address localhost --server_port 45705 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpyxsqc47k	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.019195 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003646)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002103)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000073)\ninmanta.execute.schedulerINFO    Total compilation time 0.005912\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:45705/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:45705/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:45705/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:45705/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:45705/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	ca8235e6-766a-4032-8cf0-3cfdd6b25758
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type) FROM stdin;
5659aecb-8a48-43c2-be64-bc12cd228e6d	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2021-06-09 09:14:17.110096+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig
5659aecb-8a48-43c2-be64-bc12cd228e6d	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2021-06-09 09:14:18.13529+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
5659aecb-8a48-43c2-be64-bc12cd228e6d	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2021-06-09 09:14:18.967959+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig
5659aecb-8a48-43c2-be64-bc12cd228e6d	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2021-06-09 09:14:18.997692+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
c5591255-b5b9-48dc-a637-46fcfe11f19d	store	2021-06-09 09:14:15.3537+02	2021-06-09 09:14:15.365942+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2021-06-09T09:14:15.365959+02:00\\"}"}	\N	\N	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
7ed79e3f-f36a-448a-8d5d-9ae107ea438e	pull	2021-06-09 09:14:16.00077+02	2021-06-09 09:14:16.009509+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-09T09:14:16.009528+02:00\\"}"}	\N	\N	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
2462a1e0-b0ec-4281-aa12-ab4c237e6225	pull	2021-06-09 09:14:17.029933+02	2021-06-09 09:14:17.031342+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-09T09:14:17.031349+02:00\\"}"}	\N	\N	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
967b5619-4702-480c-8106-73ef9a4bb85b	deploy	2021-06-09 09:14:17.031056+02	2021-06-09 09:14:17.055616+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2021-06-09 09:14:15+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2021-06-09 09:14:15+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"0f5fb781-8bbb-47db-a732-084f1d02cc44\\"}, \\"timestamp\\": \\"2021-06-09T09:14:17.026435+02:00\\"}","{\\"msg\\": \\"Start deploy 0f5fb781-8bbb-47db-a732-084f1d02cc44 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"0f5fb781-8bbb-47db-a732-084f1d02cc44\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:17.034539+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-09T09:14:17.035159+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-09T09:14:17.042024+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 0f5fb781-8bbb-47db-a732-084f1d02cc44\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"0f5fb781-8bbb-47db-a732-084f1d02cc44\\"}, \\"timestamp\\": \\"2021-06-09T09:14:17.046263+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c2c632c3-369a-4981-8fd4-ba3ab03b8a44	deploy	2021-06-09 09:14:17.067876+02	2021-06-09 09:14:17.078648+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"92ba821e-56de-41f0-9e37-bdedd918654c\\"}, \\"timestamp\\": \\"2021-06-09T09:14:17.064633+02:00\\"}","{\\"msg\\": \\"Start deploy 92ba821e-56de-41f0-9e37-bdedd918654c of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"92ba821e-56de-41f0-9e37-bdedd918654c\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:17.070303+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-09T09:14:17.070768+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 92ba821e-56de-41f0-9e37-bdedd918654c\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"92ba821e-56de-41f0-9e37-bdedd918654c\\"}, \\"timestamp\\": \\"2021-06-09T09:14:17.075282+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
d3572c65-f384-46d2-83a0-b2aa56f723e9	pull	2021-06-09 09:14:17.084826+02	2021-06-09 09:14:17.085877+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-09T09:14:17.085885+02:00\\"}"}	\N	\N	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
74191552-9e9f-41c3-9b45-d6a04f454bde	deploy	2021-06-09 09:14:17.097985+02	2021-06-09 09:14:17.110096+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2021-06-09 09:14:15+0200', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2021-06-09 09:14:15+0200', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e50219b7-7b54-4625-90b6-8d8df20a4c6c\\"}, \\"timestamp\\": \\"2021-06-09T09:14:17.094774+02:00\\"}","{\\"msg\\": \\"Start deploy e50219b7-7b54-4625-90b6-8d8df20a4c6c of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e50219b7-7b54-4625-90b6-8d8df20a4c6c\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:17.099720+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-09T09:14:17.100139+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy e50219b7-7b54-4625-90b6-8d8df20a4c6c\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e50219b7-7b54-4625-90b6-8d8df20a4c6c\\"}, \\"timestamp\\": \\"2021-06-09T09:14:17.104869+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
8a7d679f-f72c-44a2-a80f-dc581df09679	pull	2021-06-09 09:14:18.10602+02	2021-06-09 09:14:18.108606+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-09T09:14:18.108623+02:00\\"}"}	\N	\N	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::File[localhost,path=/tmp/test],v=1"}
7766fdeb-7c26-45c9-adbf-15e2e19e5a3c	pull	2021-06-09 09:14:18.965153+02	2021-06-09 09:14:18.968124+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-09T09:14:18.970413+02:00\\"}"}	\N	\N	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d	2	{"std::File[localhost,path=/tmp/test],v=2"}
f6c1562a-4b52-494d-a603-b4c8fa5bd5ac	deploy	2021-06-09 09:14:18.124445+02	2021-06-09 09:14:18.13529+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2021-06-09 09:14:18+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2021-06-09 09:14:18+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"e2342e46-0573-4aa6-b507-aa9522c34689\\"}, \\"timestamp\\": \\"2021-06-09T09:14:18.120551+02:00\\"}","{\\"msg\\": \\"Start deploy e2342e46-0573-4aa6-b507-aa9522c34689 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e2342e46-0573-4aa6-b507-aa9522c34689\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:18.126476+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-09T09:14:18.127140+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:18.129945+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 898, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpf2fwbsi9/5659aecb-8a48-43c2-be64-bc12cd228e6d/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:18.130586+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy e2342e46-0573-4aa6-b507-aa9522c34689\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"e2342e46-0573-4aa6-b507-aa9522c34689\\"}, \\"timestamp\\": \\"2021-06-09T09:14:18.130878+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	5659aecb-8a48-43c2-be64-bc12cd228e6d	1	{"std::File[localhost,path=/tmp/test],v=1"}
7ba7130f-1703-4b57-ad2c-d13f26fa27fa	store	2021-06-09 09:14:18.946346+02	2021-06-09 09:14:18.950011+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2021-06-09T09:14:18.950024+02:00\\"}"}	\N	\N	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
0056455d-378c-4aaf-9118-5e069e2bc833	deploy	2021-06-09 09:14:18.967959+02	2021-06-09 09:14:18.967959+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2021-06-09T07:14:18.967959+00:00\\"}"}	deployed	\N	nochange	5659aecb-8a48-43c2-be64-bc12cd228e6d	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
384ba8da-b016-4e37-bc8f-6d091c0109a1	deploy	2021-06-09 09:14:18.986856+02	2021-06-09 09:14:18.997692+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"bef3b10d-c449-4df8-b02b-b1515aab5947\\"}, \\"timestamp\\": \\"2021-06-09T09:14:18.979685+02:00\\"}","{\\"msg\\": \\"Start deploy bef3b10d-c449-4df8-b02b-b1515aab5947 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"bef3b10d-c449-4df8-b02b-b1515aab5947\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:18.989576+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-09T09:14:18.990094+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:18.992900+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 898, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpf2fwbsi9/5659aecb-8a48-43c2-be64-bc12cd228e6d/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-09T09:14:18.993198+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy bef3b10d-c449-4df8-b02b-b1515aab5947\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"bef3b10d-c449-4df8-b02b-b1515aab5947\\"}, \\"timestamp\\": \\"2021-06-09T09:14:18.993499+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	5659aecb-8a48-43c2-be64-bc12cd228e6d	2	{"std::File[localhost,path=/tmp/test],v=2"}
3b2731c8-a630-46ab-9706-51b1a05c61c8	pull	2021-06-09 09:14:19.145616+02	2021-06-09 09:14:19.14878+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-09T09:14:19.148789+02:00\\"}"}	\N	\N	\N	5659aecb-8a48-43c2-be64-bc12cd228e6d	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080}
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

