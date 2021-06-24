--
-- PostgreSQL database dump
--

-- Dumped from database version 10.17 (Ubuntu 10.17-1.pgdg18.04+1)
-- Dumped by pg_dump version 12.7 (Ubuntu 12.7-1.pgdg18.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

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
    resource_type character varying NOT NULL,
    value character varying NOT NULL
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
a83a40d8-47bd-416f-8b92-ee17016b47bb	internal	2021-06-23 15:47:20.993384+02	f	7b498a9b-8105-4a39-a2dc-ad955a9eaa21	\N
a83a40d8-47bd-416f-8b92-ee17016b47bb	localhost	2021-06-23 15:47:23.039256+02	f	2d420bc8-771b-4cb6-b39c-6e99dea1acd7	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
7b498a9b-8105-4a39-a2dc-ad955a9eaa21	8840633e-d429-11eb-a3b3-50e0859bd318	internal	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb
2d420bc8-771b-4cb6-b39c-6e99dea1acd7	8840633e-d429-11eb-a3b3-50e0859bd318	localhost	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
andras-Latitude-5401	a83a40d8-47bd-416f-8b92-ee17016b47bb	2021-06-23 15:47:20.993384+02	2021-06-23 15:47:24.130354+02	\N	8840633e-d429-11eb-a3b3-50e0859bd318
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::Service	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::File	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::Directory	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::Package	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::Symlink	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::AgentConfig	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::Service	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::File	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::Directory	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::Package	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::Symlink	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
a83a40d8-47bd-416f-8b92-ee17016b47bb	std::AgentConfig	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
a72838b3-5c0f-43b4-a0d3-8123363420e5	a83a40d8-47bd-416f-8b92-ee17016b47bb	2021-06-23 15:47:18.837861+02	2021-06-23 15:47:21.143043+02	2021-06-23 15:47:18.831538+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	032ffc26-d4ca-46f3-aebe-0a5ac8185575	t	\N	{"errors": []}
1d949163-0c48-4896-99f7-7e83b1ae002d	a83a40d8-47bd-416f-8b92-ee17016b47bb	2021-06-23 15:47:23.253103+02	2021-06-23 15:47:24.034046+02	2021-06-23 15:47:23.243516+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	a5030c9c-26c9-4e34-8545-797f14bdc069	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	a83a40d8-47bd-416f-8b92-ee17016b47bb	2021-06-23 15:47:20.329099+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
2	a83a40d8-47bd-416f-8b92-ee17016b47bb	2021-06-23 15:47:23.948017+02	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
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
b63d2b84-51bb-4e13-9ce5-845bf8b42867	dev-2	c544e41b-af11-4998-8249-52c5b8dc7336			{}	0	f
a83a40d8-47bd-416f-8b92-ee17016b47bb	dev-1	c544e41b-af11-4998-8249-52c5b8dc7336			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
c544e41b-af11-4998-8249-52c5b8dc7336	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
f1135e21-fc44-48a1-8c2c-0108ec53c4fc	2021-06-23 15:47:18.838468+02	2021-06-23 15:47:18.840017+02		Init		Using extra environment variables during compile \n	0	a72838b3-5c0f-43b4-a0d3-8123363420e5
a75696a6-253e-4749-adc7-854f7ebdbd0b	2021-06-23 15:47:23.256983+02	2021-06-23 15:47:24.033174+02	/home/andras/git-repos/inmanta-core/.env6/bin/python -m inmanta.app -vvv export -X -e a83a40d8-47bd-416f-8b92-ee17016b47bb --server_address localhost --server_port 46545 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp6b_tggsj	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.015383 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002843)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001783)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000062)\ninmanta.execute.schedulerINFO    Total compilation time 0.004757\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46545/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46545/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46545/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46545/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46545/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	1d949163-0c48-4896-99f7-7e83b1ae002d
1ebfb842-7190-4646-badf-64f040f9c1a7	2021-06-23 15:47:18.840535+02	2021-06-23 15:47:21.141767+02	/home/andras/git-repos/inmanta-core/.env6/bin/python -m inmanta.app -vvv export -X -e a83a40d8-47bd-416f-8b92-ee17016b47bb --server_address localhost --server_port 46545 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpokw8t4l5	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    Checking out 3.0.2 on /tmp/tmp9hz0bz3v/server/environments/a83a40d8-47bd-416f-8b92-ee17016b47bb/libs/std\ninmanta.module           DEBUG   Parsing took 0.794655 seconds\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003219)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002145)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000065)\ninmanta.execute.schedulerINFO    Total compilation time 0.005507\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46545/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46545/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46545/api/v1/file/7f65552db2702d19fcc07c97d5cafac4431b094d\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46545/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46545/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46545/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46545/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46545/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	a72838b3-5c0f-43b4-a0d3-8123363420e5
4c8d6d5f-3c80-4d15-b673-bb803860bb93	2021-06-23 15:47:23.254034+02	2021-06-23 15:47:23.25619+02		Init		Using extra environment variables during compile \n	0	1d949163-0c48-4896-99f7-7e83b1ae002d
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, value) FROM stdin;
a83a40d8-47bd-416f-8b92-ee17016b47bb	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2021-06-23 15:47:22.065762+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost
a83a40d8-47bd-416f-8b92-ee17016b47bb	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2021-06-23 15:47:23.114421+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test
a83a40d8-47bd-416f-8b92-ee17016b47bb	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2021-06-23 15:47:23.966907+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deploying	{}	std::AgentConfig	localhost
a83a40d8-47bd-416f-8b92-ee17016b47bb	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2021-06-23 15:47:23.995274+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	deploying	{}	std::File	/tmp/test
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
a927e050-f70f-427a-89fe-d358fbf7077a	store	2021-06-23 15:47:20.328355+02	2021-06-23 15:47:20.339718+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2021-06-23T15:47:20.339732+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
55410648-ea11-42a3-a042-78ed23c7a95e	pull	2021-06-23 15:47:21.004862+02	2021-06-23 15:47:21.011154+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-23T15:47:21.011168+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
69bbffa5-04ba-4b00-b2c3-13c14a5f7367	pull	2021-06-23 15:47:21.999823+02	2021-06-23 15:47:22.001403+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-23T15:47:22.001411+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
5a944053-fa2e-43b0-ad70-d69338b2c1dc	deploy	2021-06-23 15:47:22.000942+02	2021-06-23 15:47:22.021128+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2021-06-23 15:47:20+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2021-06-23 15:47:20+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"2f13c9bb-da77-4073-a57e-95ed3a71ca5e\\"}, \\"timestamp\\": \\"2021-06-23T15:47:21.996445+02:00\\"}","{\\"msg\\": \\"Start deploy 2f13c9bb-da77-4073-a57e-95ed3a71ca5e of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"2f13c9bb-da77-4073-a57e-95ed3a71ca5e\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-23T15:47:22.003821+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-23T15:47:22.004414+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-23T15:47:22.009938+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 2f13c9bb-da77-4073-a57e-95ed3a71ca5e\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"2f13c9bb-da77-4073-a57e-95ed3a71ca5e\\"}, \\"timestamp\\": \\"2021-06-23T15:47:22.013633+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
2d7144aa-3c0e-4367-b797-449077257a11	deploy	2021-06-23 15:47:22.035214+02	2021-06-23 15:47:22.043509+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e43c0ff2-7f00-4e8d-851a-2b3fde2ccced\\"}, \\"timestamp\\": \\"2021-06-23T15:47:22.032482+02:00\\"}","{\\"msg\\": \\"Start deploy e43c0ff2-7f00-4e8d-851a-2b3fde2ccced of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e43c0ff2-7f00-4e8d-851a-2b3fde2ccced\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-23T15:47:22.037071+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-23T15:47:22.037352+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy e43c0ff2-7f00-4e8d-851a-2b3fde2ccced\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e43c0ff2-7f00-4e8d-851a-2b3fde2ccced\\"}, \\"timestamp\\": \\"2021-06-23T15:47:22.040751+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
23615e86-b77c-440c-b5f4-400fe0b2b8c4	pull	2021-06-23 15:47:22.048607+02	2021-06-23 15:47:22.04943+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-23T15:47:22.049436+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
419aab85-1256-4bf3-91f8-eee4af1d628f	deploy	2021-06-23 15:47:22.058245+02	2021-06-23 15:47:22.065762+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2021-06-23 15:47:20+0200', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2021-06-23 15:47:20+0200', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"6d811eef-8123-4088-883b-c59492b6183c\\"}, \\"timestamp\\": \\"2021-06-23T15:47:22.055942+02:00\\"}","{\\"msg\\": \\"Start deploy 6d811eef-8123-4088-883b-c59492b6183c of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"6d811eef-8123-4088-883b-c59492b6183c\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-23T15:47:22.059659+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-23T15:47:22.059975+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 6d811eef-8123-4088-883b-c59492b6183c\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"6d811eef-8123-4088-883b-c59492b6183c\\"}, \\"timestamp\\": \\"2021-06-23T15:47:22.063167+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1169e029-c61d-4cff-832f-66b77e185049	pull	2021-06-23 15:47:23.065724+02	2021-06-23 15:47:23.080289+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-23T15:47:23.080306+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::File[localhost,path=/tmp/test],v=1"}
d25e65f4-54f3-49e1-b494-edcc80b03e07	store	2021-06-23 15:47:23.947844+02	2021-06-23 15:47:23.950524+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2021-06-23T15:47:23.950534+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
6a68cc1c-23b5-4607-a3a1-3058c4819e16	deploy	2021-06-23 15:47:23.10215+02	2021-06-23 15:47:23.114421+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2021-06-23 15:47:23+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2021-06-23 15:47:23+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"362b711c-640c-42d9-8a38-df7ad7cd21a3\\"}, \\"timestamp\\": \\"2021-06-23T15:47:23.098316+02:00\\"}","{\\"msg\\": \\"Start deploy 362b711c-640c-42d9-8a38-df7ad7cd21a3 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"362b711c-640c-42d9-8a38-df7ad7cd21a3\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-23T15:47:23.104702+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-23T15:47:23.105410+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-23T15:47:23.105528+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 911, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmp9hz0bz3v/a83a40d8-47bd-416f-8b92-ee17016b47bb/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-23T15:47:23.109637+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 362b711c-640c-42d9-8a38-df7ad7cd21a3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"362b711c-640c-42d9-8a38-df7ad7cd21a3\\"}, \\"timestamp\\": \\"2021-06-23T15:47:23.110048+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	a83a40d8-47bd-416f-8b92-ee17016b47bb	1	{"std::File[localhost,path=/tmp/test],v=1"}
bb91b1b6-410a-4e9d-9402-a88548b36283	deploy	2021-06-23 15:47:23.966907+02	2021-06-23 15:47:23.966907+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2021-06-23T13:47:23.966907+00:00\\"}"}	deployed	\N	nochange	a83a40d8-47bd-416f-8b92-ee17016b47bb	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
59f843b6-f4a3-4760-a1a2-c863e6f7ef70	deploy	2021-06-23 15:47:23.985251+02	2021-06-23 15:47:23.995274+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"fc78cecd-1f6a-4c24-8aa8-4b668d36a1a4\\"}, \\"timestamp\\": \\"2021-06-23T15:47:23.981904+02:00\\"}","{\\"msg\\": \\"Start deploy fc78cecd-1f6a-4c24-8aa8-4b668d36a1a4 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"fc78cecd-1f6a-4c24-8aa8-4b668d36a1a4\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-23T15:47:23.986943+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-23T15:47:23.987408+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {}}, \\"timestamp\\": \\"2021-06-23T15:47:23.990053+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 918, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp9hz0bz3v/a83a40d8-47bd-416f-8b92-ee17016b47bb/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-23T15:47:23.990359+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy fc78cecd-1f6a-4c24-8aa8-4b668d36a1a4\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"fc78cecd-1f6a-4c24-8aa8-4b668d36a1a4\\"}, \\"timestamp\\": \\"2021-06-23T15:47:23.990730+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	a83a40d8-47bd-416f-8b92-ee17016b47bb	2	{"std::File[localhost,path=/tmp/test],v=2"}
6b9885aa-998c-4924-8c3a-32338bc7eb56	deploy	2021-06-23 15:47:24.15402+02	\N	\N	deploying	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
0e0fd93b-17d2-4b60-beea-a12dd9b3a55e	deploy	2021-06-23 15:47:24.163215+02	\N	\N	deploying	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	2	{"std::File[localhost,path=/tmp/test],v=2"}
5eb3b983-de0a-4ba2-a092-4d01d58e59a0	pull	2021-06-23 15:47:23.964558+02	2021-06-23 15:47:23.966804+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-23T15:47:23.968195+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	2	{"std::File[localhost,path=/tmp/test],v=2"}
41a6c6be-4f17-4036-af33-a676ba8e8768	pull	2021-06-23 15:47:24.130874+02	2021-06-23 15:47:24.13359+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-23T15:47:24.133598+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
d506831f-623f-45c7-95bb-8b397805ec08	pull	2021-06-23 15:47:24.131403+02	2021-06-23 15:47:24.143999+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-23T15:47:24.144016+02:00\\"}"}	\N	\N	\N	a83a40d8-47bd-416f-8b92-ee17016b47bb	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210}
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
-- Name: resource_environment_resource_value_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_value_index ON public.resource USING btree (environment, value);


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

