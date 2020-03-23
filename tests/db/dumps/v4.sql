--
-- PostgreSQL database dump
--

-- Dumped from database version 10.12
-- Dumped by pg_dump version 12.1

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
    last_failover timestamp without time zone,
    paused boolean DEFAULT false,
    id_primary uuid
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
    handled boolean
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
    last_version integer DEFAULT 0
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

COPY public.agent (environment, name, last_failover, paused, id_primary) FROM stdin;
00db6be2-0d1b-48e3-852c-9ae41d65adb1	localhost	2020-03-23 11:37:17.730676	f	2361fc11-422f-4ec3-bc4a-a477f6c3b27c
00db6be2-0d1b-48e3-852c-9ae41d65adb1	internal	2020-03-23 11:37:18.197805	f	d0b4001d-95ef-4d64-a533-254937b4462d
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
d0b4001d-95ef-4d64-a533-254937b4462d	4495dcbc-6cf2-11ea-8e52-50e0859bd318	internal	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1
2361fc11-422f-4ec3-bc4a-a477f6c3b27c	4495dcbc-6cf2-11ea-8e52-50e0859bd318	localhost	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1
3ad12976-3272-4756-817d-f71d8eb99dd6	42493d3c-6cf2-11ea-8e52-50e0859bd318	internal	2020-03-23 11:37:18.188858	00db6be2-0d1b-48e3-852c-9ae41d65adb1
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
andras-Latitude-5401	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2020-03-23 11:37:14.980843	2020-03-23 11:37:16.188006	2020-03-23 11:37:18.188858	42493d3c-6cf2-11ea-8e52-50e0859bd318
andras-Latitude-5401	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2020-03-23 11:37:17.722217	2020-03-23 11:37:20.601992	\N	4495dcbc-6cf2-11ea-8e52-50e0859bd318
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::Service	1	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::File	1	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::Directory	1	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::Package	1	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::Symlink	1	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::AgentConfig	1	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::Service	2	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::File	2	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::Directory	2	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::Package	2	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::Symlink	2	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
00db6be2-0d1b-48e3-852c-9ae41d65adb1	std::AgentConfig	2	{"cfbfe093a9c308d519cadb13ab4adddfbba4ef3f": ["/tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.11.0", "email_validator==1.0.5", "pydantic==1.4"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled) FROM stdin;
447f20c9-fc75-43e2-9d94-bf89318e5b74	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2020-03-23 11:37:09.681254	2020-03-23 11:37:15.07643	2020-03-23 11:37:09.676076	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	fe0a3884-f043-43bd-bdb4-26a22e502b4e	t
745de827-52cf-420d-847e-6d3384fce993	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2020-03-23 11:37:19.928057	2020-03-23 11:37:20.538101	2020-03-23 11:37:19.922375	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	05f1df99-3222-4405-b0b4-ab42994ce40e	t
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2020-03-23 11:37:13.358379	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
2	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2020-03-23 11:37:20.471032	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version) FROM stdin;
69157995-7eaa-4043-b1d8-2d682b344ee3	dev-2	fba81cc2-56b7-40b5-a9dd-24c77121f5af			{}	0
00db6be2-0d1b-48e3-852c-9ae41d65adb1	dev-1	fba81cc2-56b7-40b5-a9dd-24c77121f5af			{"auto_deploy": true, "server_compile": true, "purge_on_delete": true, "autostart_on_start": true, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2
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
fba81cc2-56b7-40b5-a9dd-24c77121f5af	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
afabc91d-63de-4b64-8ae5-9d9e4caa636a	2020-03-23 11:37:09.682231	2020-03-23 11:37:09.684799		Init		Using extra environment variables during compile \n	0	447f20c9-fc75-43e2-9d94-bf89318e5b74
65f77779-6a13-45c2-bfa4-6da0231bf43a	2020-03-23 11:37:19.93039	2020-03-23 11:37:19.933731		Init		Using extra environment variables during compile \n	0	745de827-52cf-420d-847e-6d3384fce993
49e2428c-1ed5-439a-a11b-a5cec459d3b4	2020-03-23 11:37:09.685794	2020-03-23 11:37:15.074435	/home/andras/git-repos/inmanta/venv/bin/python -m inmanta.app -vvv export -X -e 00db6be2-0d1b-48e3-852c-9ae41d65adb1 --server_address localhost --server_port 33551 --metadata {"type": "api", "message": "Recompile trigger through API call"}	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           WARNING collecting requirements on project that has not been loaded completely\ninmanta.module           INFO    Checking out 1.4.0 on /tmp/tmpkbkn9cml/server/environments/00db6be2-0d1b-48e3-852c-9ae41d65adb1/libs/std\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002652)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001808)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000053)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33551/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33551/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33551/api/v1/file/cfbfe093a9c308d519cadb13ab4adddfbba4ef3f\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33551/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33551/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33551/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33551/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	447f20c9-fc75-43e2-9d94-bf89318e5b74
9cac190b-bff3-47f5-b250-2631285a708b	2020-03-23 11:37:19.934927	2020-03-23 11:37:20.537334	/home/andras/git-repos/inmanta/venv/bin/python -m inmanta.app -vvv export -X -e 00db6be2-0d1b-48e3-852c-9ae41d65adb1 --server_address localhost --server_port 33551 --metadata {"type": "api", "message": "Recompile trigger through API call"}	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002712)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002003)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000051)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33551/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33551/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33551/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33551/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33551/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	745de827-52cf-420d-847e-6d3384fce993
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type) FROM stdin;
00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2020-03-23 11:37:19.813984	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2020-03-23 11:37:19.833187	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
00db6be2-0d1b-48e3-852c-9ae41d65adb1	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2020-03-23 11:37:20.493917	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
00db6be2-0d1b-48e3-852c-9ae41d65adb1	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2020-03-23 11:37:20.530355	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, send_event, environment, version, resource_version_ids) FROM stdin;
a919e1f2-53d4-43f6-b510-07359dbb7722	store	2020-03-23 11:37:13.355031	2020-03-23 11:37:13.379876	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2020-03-23T11:37:13.379887\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
6b499f9c-e18c-42ee-9de1-57a0fc54fa5f	pull	2020-03-23 11:37:14.998797	2020-03-23 11:37:15.006781	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-03-23T11:37:15.006786\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
bda76090-933a-4b56-9c88-a45d8e744f2c	pull	2020-03-23 11:37:17.046545	2020-03-23 11:37:17.060738	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-03-23T11:37:17.060743\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
0b152a8d-2969-487f-8b16-d385a17124db	deploy	2020-03-23 11:37:17.071658	2020-03-23 11:37:17.098213	{"{\\"msg\\": \\"Failed to load handler code or install handler code dependencies. Check the agent log for details.\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-03-23T11:37:17.098054\\"}"}	unavailable	{}	\N	f	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
5e7394f0-5b75-4beb-a221-5862f1c80c22	deploy	2020-03-23 11:37:17.036875	2020-03-23 11:37:17.08698	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2020-03-23 11:37:14\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2020-03-23 11:37:14\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e329c6cf-efc7-49e1-be50-192749231949\\"}, \\"timestamp\\": \\"2020-03-23T11:37:17.036976\\"}","{\\"msg\\": \\"Start deploy e329c6cf-efc7-49e1-be50-192749231949 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e329c6cf-efc7-49e1-be50-192749231949\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-03-23T11:37:17.037074\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-03-23T11:37:17.066769\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-03-23T11:37:17.074622\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy e329c6cf-efc7-49e1-be50-192749231949\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"e329c6cf-efc7-49e1-be50-192749231949\\"}, \\"timestamp\\": \\"2020-03-23T11:37:17.086863\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c82b733e-7ffd-4b1f-9bf4-ca663f9a3606	pull	2020-03-23 11:37:17.745746	2020-03-23 11:37:17.75002	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-03-23T11:37:17.750046\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::File[localhost,path=/tmp/test],v=1"}
244b4c52-70fd-462a-bf2c-22aa7a60364f	pull	2020-03-23 11:37:18.208829	2020-03-23 11:37:18.211368	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-03-23T11:37:18.211372\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
5ef49790-8097-4f3e-8561-c856df4b6246	deploy	2020-03-23 11:37:20.516702	2020-03-23 11:37:20.530355	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"04959852-bb55-4d90-ad9c-3c68ed9e8bcd\\"}, \\"timestamp\\": \\"2020-03-23T11:37:20.516723\\"}","{\\"msg\\": \\"Start deploy 04959852-bb55-4d90-ad9c-3c68ed9e8bcd of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"04959852-bb55-4d90-ad9c-3c68ed9e8bcd\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-03-23T11:37:20.516751\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-03-23T11:37:20.526465\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2020-03-23T11:37:20.529800\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/handler.py\\\\\\", line 865, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpkbkn9cml/00db6be2-0d1b-48e3-852c-9ae41d65adb1/agent/code/modules/inmanta_plugins.std.resources.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 594, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-03-23T11:37:20.530081\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 04959852-bb55-4d90-ad9c-3c68ed9e8bcd\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"04959852-bb55-4d90-ad9c-3c68ed9e8bcd\\"}, \\"timestamp\\": \\"2020-03-23T11:37:20.530328\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"group": {"current": "andras", "desired": "root"}, "owner": {"current": "andras", "desired": "root"}}}	nochange	f	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2	{"std::File[localhost,path=/tmp/test],v=2"}
0b521043-6772-4478-be8c-74d72f6fcca3	deploy	2020-03-23 11:37:19.798748	2020-03-23 11:37:19.813984	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2020-03-23 11:37:17\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2020-03-23 11:37:17\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"a94e7ca7-efb6-4c22-a739-7bc5078ce0c7\\"}, \\"timestamp\\": \\"2020-03-23T11:37:19.798788\\"}","{\\"msg\\": \\"Start deploy a94e7ca7-efb6-4c22-a739-7bc5078ce0c7 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"a94e7ca7-efb6-4c22-a739-7bc5078ce0c7\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-03-23T11:37:19.798829\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-03-23T11:37:19.808382\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-03-23T11:37:19.808871\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/handler.py\\\\\\", line 858, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpkbkn9cml/00db6be2-0d1b-48e3-852c-9ae41d65adb1/agent/code/modules/inmanta_plugins.std.resources.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 594, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-03-23T11:37:19.813525\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy a94e7ca7-efb6-4c22-a739-7bc5078ce0c7\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"a94e7ca7-efb6-4c22-a739-7bc5078ce0c7\\"}, \\"timestamp\\": \\"2020-03-23T11:37:19.813931\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::File[localhost,path=/tmp/test],v=1"}
3ca62f22-7fe7-484e-9d8b-eeea900140ec	pull	2020-03-23 11:37:20.490404	2020-03-23 11:37:20.494087	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-03-23T11:37:20.495921\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2	{"std::File[localhost,path=/tmp/test],v=2"}
20c1e77b-40f3-46b3-b5b1-4358d5035e2b	deploy	2020-03-23 11:37:19.820037	2020-03-23 11:37:19.833187	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2020-03-23 11:37:18\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2020-03-23 11:37:18\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"2db666aa-ebd4-4556-9b67-6be7d0f008ef\\"}, \\"timestamp\\": \\"2020-03-23T11:37:19.820062\\"}","{\\"msg\\": \\"Start deploy 2db666aa-ebd4-4556-9b67-6be7d0f008ef of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"2db666aa-ebd4-4556-9b67-6be7d0f008ef\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-03-23T11:37:19.820099\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-03-23T11:37:19.828915\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 2db666aa-ebd4-4556-9b67-6be7d0f008ef\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"2db666aa-ebd4-4556-9b67-6be7d0f008ef\\"}, \\"timestamp\\": \\"2020-03-23T11:37:19.833144\\"}"}	deployed	{}	nochange	f	00db6be2-0d1b-48e3-852c-9ae41d65adb1	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
d4473231-19b6-4170-a503-234824f42b83	store	2020-03-23 11:37:20.468618	2020-03-23 11:37:20.474332	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2020-03-23T11:37:20.474338\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
9b95390c-6310-413d-9806-89872c213a87	deploy	2020-03-23 11:37:20.493917	2020-03-23 11:37:20.493917	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2020-03-23T11:37:20.493917\\"}"}	deployed	{}	nochange	f	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
f0129170-f926-4179-81e9-132effa6b9be	pull	2020-03-23 11:37:20.603171	2020-03-23 11:37:20.6075	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-03-23T11:37:20.607505\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
02efde30-bfba-4845-935e-eb5ee5dfdee1	pull	2020-03-23 11:37:20.604191	2020-03-23 11:37:20.627935	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-03-23T11:37:20.627964\\"}"}	\N	{}	\N	\N	00db6be2-0d1b-48e3-852c-9ae41d65adb1	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, current_version) FROM stdin;
core	4
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

