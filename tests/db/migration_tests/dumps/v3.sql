--
-- PostgreSQL database dump
--

-- Dumped from database version 11.6
-- Dumped by pg_dump version 12.1

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
-- Name: form; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.form (
    environment uuid NOT NULL,
    form_type character varying NOT NULL,
    options jsonb,
    fields jsonb,
    defaults jsonb,
    field_options jsonb
);


--
-- Name: formrecord; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.formrecord (
    id uuid NOT NULL,
    form character varying NOT NULL,
    environment uuid NOT NULL,
    fields jsonb,
    changed timestamp without time zone
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
    send_event boolean
);


--
-- Name: resourceversionid; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resourceversionid (
    environment uuid NOT NULL,
    action_id uuid NOT NULL,
    resource_version_id character varying NOT NULL
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
6c66ca44-da58-4924-ad17-151abc2f3726	localhost	2020-01-14 16:33:21.508732	f	0bcd69e9-d249-46a8-987a-5e5b59d96648
6c66ca44-da58-4924-ad17-151abc2f3726	internal	2020-01-14 16:33:22.830296	f	d9dba702-9f2b-431a-af9f-6aff279867f6
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
d9dba702-9f2b-431a-af9f-6aff279867f6	32210858-36e3-11ea-ad98-50e0859bd318	internal	\N	6c66ca44-da58-4924-ad17-151abc2f3726
0bcd69e9-d249-46a8-987a-5e5b59d96648	32210858-36e3-11ea-ad98-50e0859bd318	localhost	\N	6c66ca44-da58-4924-ad17-151abc2f3726
bdc1c3bd-3b51-4afc-a532-9024bc6b7b91	30731a1e-36e3-11ea-ad98-50e0859bd318	internal	2020-01-14 16:33:22.823099	6c66ca44-da58-4924-ad17-151abc2f3726
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
andras-Latitude-5401	6c66ca44-da58-4924-ad17-151abc2f3726	2020-01-14 16:33:19.688737	2020-01-14 16:33:20.821793	2020-01-14 16:33:22.823099	30731a1e-36e3-11ea-ad98-50e0859bd318
andras-Latitude-5401	6c66ca44-da58-4924-ad17-151abc2f3726	2020-01-14 16:33:21.502489	2020-01-14 16:33:23.546027	\N	32210858-36e3-11ea-ad98-50e0859bd318
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
6c66ca44-da58-4924-ad17-151abc2f3726	std::Service	1	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::File	1	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::Directory	1	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::Package	1	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::Symlink	1	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::AgentConfig	1	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::Service	2	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::File	2	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::Directory	2	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::Package	2	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::Symlink	2	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
6c66ca44-da58-4924-ad17-151abc2f3726	std::AgentConfig	2	{"c4f8831d81b227edbef08fba76b4fa5477b58273": ["/tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2==2.10.3", "email_validator==1.0.5"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled) FROM stdin;
80fc6b23-e753-4e92-a1d3-5ba4c92baeed	6c66ca44-da58-4924-ad17-151abc2f3726	2020-01-14 16:33:14.928901	2020-01-14 16:33:19.757376	2020-01-14 16:33:14.923546	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	e6b05c5d-1880-4fa3-a7f5-c06f77b30755	t
b8b8d763-77e7-41c1-8f12-a4dfed7c4ebc	6c66ca44-da58-4924-ad17-151abc2f3726	2020-01-14 16:33:22.778455	2020-01-14 16:33:23.40357	2020-01-14 16:33:22.769031	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	999a680b-eed8-4631-bd46-950f6f57fc47	t
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	6c66ca44-da58-4924-ad17-151abc2f3726	2020-01-14 16:33:18.153444	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
2	6c66ca44-da58-4924-ad17-151abc2f3726	2020-01-14 16:33:23.344771	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
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
e9e415e4-a426-4893-8e9e-95faf1f14b90	dev-2	e622dc84-7ba6-40e0-b636-d86283d1e2aa			{}	0
6c66ca44-da58-4924-ad17-151abc2f3726	dev-1	e622dc84-7ba6-40e0-b636-d86283d1e2aa			{"auto_deploy": true, "server_compile": true, "purge_on_delete": true, "autostart_on_start": true, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2
\.


--
-- Data for Name: form; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.form (environment, form_type, options, fields, defaults, field_options) FROM stdin;
\.


--
-- Data for Name: formrecord; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.formrecord (id, form, environment, fields, changed) FROM stdin;
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
e622dc84-7ba6-40e0-b636-d86283d1e2aa	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
db7550e9-ce32-4653-aebe-04995ffb223a	2020-01-14 16:33:14.929719	2020-01-14 16:33:14.931557		Init		Using extra environment variables during compile \n	0	80fc6b23-e753-4e92-a1d3-5ba4c92baeed
434c3993-c91d-4027-bdfa-7d0dee5fc82c	2020-01-14 16:33:22.784731	2020-01-14 16:33:23.402577	/home/andras/venv/inmanta/bin/python -m inmanta.app -vvv export -X -e 6c66ca44-da58-4924-ad17-151abc2f3726 --server_address localhost --server_port 49975 --metadata {"type": "api", "message": "Recompile trigger through API call"}	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    verifying project\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001614)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 64, time: 0.001718)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 66, time: 0.000059)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:49975/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:49975/api/v1/file\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:49975/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:49975/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:49975/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	b8b8d763-77e7-41c1-8f12-a4dfed7c4ebc
e19618b7-0087-4941-a58d-ed55fe86a206	2020-01-14 16:33:14.932358	2020-01-14 16:33:19.75653	/home/andras/venv/inmanta/bin/python -m inmanta.app -vvv export -X -e 6c66ca44-da58-4924-ad17-151abc2f3726 --server_address localhost --server_port 49975 --metadata {"type": "api", "message": "Recompile trigger through API call"}	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           WARNING collecting requirements on project that has not been loaded completely\ninmanta.module           INFO    Checking out 1.3.0 on /tmp/tmpg3wja78q/server/environments/6c66ca44-da58-4924-ad17-151abc2f3726/libs/std\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001699)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 64, time: 0.001632)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 66, time: 0.000059)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:49975/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:49975/api/v1/file\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:49975/api/v1/file/c4f8831d81b227edbef08fba76b4fa5477b58273\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:49975/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server POST http://localhost:49975/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:49975/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest    DEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest    DEBUG   Calling server PUT http://localhost:49975/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	80fc6b23-e753-4e92-a1d3-5ba4c92baeed
18edf1bf-3499-490b-96c8-2e5ad7b796d5	2020-01-14 16:33:22.779727	2020-01-14 16:33:22.783247		Init		Using extra environment variables during compile \n	0	b8b8d763-77e7-41c1-8f12-a4dfed7c4ebc
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type) FROM stdin;
6c66ca44-da58-4924-ad17-151abc2f3726	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2020-01-14 16:33:22.601818	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
6c66ca44-da58-4924-ad17-151abc2f3726	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2020-01-14 16:33:23.615815	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
6c66ca44-da58-4924-ad17-151abc2f3726	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2020-01-14 16:33:23.627423	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
6c66ca44-da58-4924-ad17-151abc2f3726	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2020-01-14 16:33:23.669366	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, send_event) FROM stdin;
213a2ff3-0c2c-433e-96db-5e3c3e38eac4	store	2020-01-14 16:33:18.149946	2020-01-14 16:33:18.17121	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2020-01-14T16:33:18.171216\\"}"}	\N	{}	\N	\N
0a69c9a7-c0e2-49b9-9d4b-9363f3d400c4	pull	2020-01-14 16:33:19.710949	2020-01-14 16:33:19.718391	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-01-14T16:33:19.718397\\"}"}	\N	{}	\N	\N
797f4c43-eda8-40ea-96fb-ec85a82a5f5d	pull	2020-01-14 16:33:20.947766	2020-01-14 16:33:20.949603	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-01-14T16:33:20.949610\\"}"}	\N	{}	\N	\N
054d4e65-e12c-45c1-9a9f-d03248452255	deploy	2020-01-14 16:33:20.951209	2020-01-14 16:33:20.972265	{"{\\"msg\\": \\"Failed to load handler code or install handler code dependencies. Check the agent log for details.\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-01-14T16:33:20.972230\\"}"}	unavailable	{}	\N	f
9d8af893-b682-4ca7-8390-81f1d0de54a8	deploy	2020-01-14 16:33:20.943728	2020-01-14 16:33:20.966823	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2020-01-14 16:33:19\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2020-01-14 16:33:19\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"1c5f3f50-3341-40fb-ba46-54bc06844994\\"}, \\"timestamp\\": \\"2020-01-14T16:33:20.943823\\"}","{\\"msg\\": \\"Start deploy 1c5f3f50-3341-40fb-ba46-54bc06844994 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"1c5f3f50-3341-40fb-ba46-54bc06844994\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-01-14T16:33:20.943865\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-01-14T16:33:20.957218\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-01-14T16:33:20.962435\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 1c5f3f50-3341-40fb-ba46-54bc06844994\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"1c5f3f50-3341-40fb-ba46-54bc06844994\\"}, \\"timestamp\\": \\"2020-01-14T16:33:20.966785\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f
989a09fd-9e9d-4e1e-83cb-9825e47c27d8	pull	2020-01-14 16:33:21.518092	2020-01-14 16:33:21.520808	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-01-14T16:33:21.520813\\"}"}	\N	{}	\N	\N
d59c9689-edef-4f3e-8f64-936fbe64a016	deploy	2020-01-14 16:33:23.630475	2020-01-14 16:33:23.64659	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"03d5a21d-6114-476b-a69c-9b8be02bea6e\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.630513\\"}","{\\"msg\\": \\"Start deploy 03d5a21d-6114-476b-a69c-9b8be02bea6e of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"03d5a21d-6114-476b-a69c-9b8be02bea6e\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-01-14T16:33:23.630584\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-01-14T16:33:23.642343\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2020-01-14T16:33:23.645910\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/handler.py\\\\\\", line 860, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpg3wja78q/6c66ca44-da58-4924-ad17-151abc2f3726/agent/code/modules/inmanta_plugins.std.resources.py\\\\\\", line 187, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 589, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-01-14T16:33:23.646182\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 03d5a21d-6114-476b-a69c-9b8be02bea6e\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"03d5a21d-6114-476b-a69c-9b8be02bea6e\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.646565\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"group": {"current": "andras", "desired": "root"}, "owner": {"current": "andras", "desired": "root"}}}	nochange	f
879e7e57-a017-4cc3-b923-d7431ce75082	deploy	2020-01-14 16:33:22.590915	2020-01-14 16:33:22.601818	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2020-01-14 16:33:21\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2020-01-14 16:33:21\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"dbea0598-e44b-41d2-8468-a3ee968d7098\\"}, \\"timestamp\\": \\"2020-01-14T16:33:22.590958\\"}","{\\"msg\\": \\"Start deploy dbea0598-e44b-41d2-8468-a3ee968d7098 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"dbea0598-e44b-41d2-8468-a3ee968d7098\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-01-14T16:33:22.590998\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-01-14T16:33:22.598483\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2020-01-14T16:33:22.601074\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/handler.py\\\\\\", line 860, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpg3wja78q/6c66ca44-da58-4924-ad17-151abc2f3726/agent/code/modules/inmanta_plugins.std.resources.py\\\\\\", line 187, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 589, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-01-14T16:33:22.601562\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy dbea0598-e44b-41d2-8468-a3ee968d7098\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"dbea0598-e44b-41d2-8468-a3ee968d7098\\"}, \\"timestamp\\": \\"2020-01-14T16:33:22.601795\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"group": {"current": "andras", "desired": "root"}, "owner": {"current": "andras", "desired": "root"}}}	nochange	f
053c2ba7-d889-4fb5-83a1-3596eb731c56	pull	2020-01-14 16:33:22.838844	2020-01-14 16:33:22.840304	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-01-14T16:33:22.840309\\"}"}	\N	{}	\N	\N
1ebfbcf3-ea63-48ad-93d0-510afc50ea23	store	2020-01-14 16:33:23.342969	2020-01-14 16:33:23.34723	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2020-01-14T16:33:23.347233\\"}"}	\N	{}	\N	\N
425a8703-4f1b-401b-ba38-d5e00b21bc4e	pull	2020-01-14 16:33:23.361912	2020-01-14 16:33:23.365106	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.366151\\"}"}	\N	{}	\N	\N
5093ba3a-e75b-4ae2-ad36-5251e33763fd	pull	2020-01-14 16:33:23.614834	2020-01-14 16:33:23.615815	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.616936\\"}"}	\N	{}	\N	\N
8b7359c8-456a-4085-8a52-bbe3a7ae40da	deploy	2020-01-14 16:33:23.615815	2020-01-14 16:33:23.615815	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2020-01-14T16:33:23.615815\\"}"}	deployed	{}	nochange	f
9ae892d8-5c8e-4ea9-b536-92addb598f8a	deploy	2020-01-14 16:33:23.611562	2020-01-14 16:33:23.627423	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2020-01-14 16:33:22\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2020-01-14 16:33:22\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"2d1c96a2-a213-4606-ac1b-98e4d68a1498\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.611596\\"}","{\\"msg\\": \\"Start deploy 2d1c96a2-a213-4606-ac1b-98e4d68a1498 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"2d1c96a2-a213-4606-ac1b-98e4d68a1498\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-01-14T16:33:23.611632\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-01-14T16:33:23.621706\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 2d1c96a2-a213-4606-ac1b-98e4d68a1498\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"2d1c96a2-a213-4606-ac1b-98e4d68a1498\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.627391\\"}"}	deployed	{}	nochange	f
37896913-bfa9-4ca9-9447-300f30d3ccf8	pull	2020-01-14 16:33:23.635626	2020-01-14 16:33:23.637399	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.637403\\"}"}	\N	{}	\N	\N
3bf440e8-5598-4d94-a256-c2e1f51f3aad	deploy	2020-01-14 16:33:23.659334	2020-01-14 16:33:23.669366	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"f9df7809-4742-4a90-95c6-7773020b5ef3\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.659360\\"}","{\\"msg\\": \\"Start deploy f9df7809-4742-4a90-95c6-7773020b5ef3 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"f9df7809-4742-4a90-95c6-7773020b5ef3\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-01-14T16:33:23.659389\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-01-14T16:33:23.666465\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2020-01-14T16:33:23.668892\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/handler.py\\\\\\", line 860, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpg3wja78q/6c66ca44-da58-4924-ad17-151abc2f3726/agent/code/modules/inmanta_plugins.std.resources.py\\\\\\", line 187, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 589, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-01-14T16:33:23.669070\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy f9df7809-4742-4a90-95c6-7773020b5ef3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"f9df7809-4742-4a90-95c6-7773020b5ef3\\"}, \\"timestamp\\": \\"2020-01-14T16:33:23.669342\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"group": {"current": "andras", "desired": "root"}, "owner": {"current": "andras", "desired": "root"}}}	nochange	f
\.


--
-- Data for Name: resourceversionid; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceversionid (environment, action_id, resource_version_id) FROM stdin;
6c66ca44-da58-4924-ad17-151abc2f3726	213a2ff3-0c2c-433e-96db-5e3c3e38eac4	std::File[localhost,path=/tmp/test],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	213a2ff3-0c2c-433e-96db-5e3c3e38eac4	std::AgentConfig[internal,agentname=localhost],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	0a69c9a7-c0e2-49b9-9d4b-9363f3d400c4	std::AgentConfig[internal,agentname=localhost],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	797f4c43-eda8-40ea-96fb-ec85a82a5f5d	std::AgentConfig[internal,agentname=localhost],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	9d8af893-b682-4ca7-8390-81f1d0de54a8	std::AgentConfig[internal,agentname=localhost],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	054d4e65-e12c-45c1-9a9f-d03248452255	std::AgentConfig[internal,agentname=localhost],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	989a09fd-9e9d-4e1e-83cb-9825e47c27d8	std::File[localhost,path=/tmp/test],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	879e7e57-a017-4cc3-b923-d7431ce75082	std::File[localhost,path=/tmp/test],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	053c2ba7-d889-4fb5-83a1-3596eb731c56	std::AgentConfig[internal,agentname=localhost],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	1ebfbcf3-ea63-48ad-93d0-510afc50ea23	std::File[localhost,path=/tmp/test],v=2
6c66ca44-da58-4924-ad17-151abc2f3726	1ebfbcf3-ea63-48ad-93d0-510afc50ea23	std::AgentConfig[internal,agentname=localhost],v=2
6c66ca44-da58-4924-ad17-151abc2f3726	425a8703-4f1b-401b-ba38-d5e00b21bc4e	std::File[localhost,path=/tmp/test],v=2
6c66ca44-da58-4924-ad17-151abc2f3726	9ae892d8-5c8e-4ea9-b536-92addb598f8a	std::AgentConfig[internal,agentname=localhost],v=1
6c66ca44-da58-4924-ad17-151abc2f3726	8b7359c8-456a-4085-8a52-bbe3a7ae40da	std::AgentConfig[internal,agentname=localhost],v=2
6c66ca44-da58-4924-ad17-151abc2f3726	37896913-bfa9-4ca9-9447-300f30d3ccf8	std::File[localhost,path=/tmp/test],v=2
6c66ca44-da58-4924-ad17-151abc2f3726	d59c9689-edef-4f3e-8f64-936fbe64a016	std::File[localhost,path=/tmp/test],v=2
6c66ca44-da58-4924-ad17-151abc2f3726	3bf440e8-5598-4d94-a256-c2e1f51f3aad	std::File[localhost,path=/tmp/test],v=2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, current_version) FROM stdin;
core	3
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
-- Name: form form_form_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form
    ADD CONSTRAINT form_form_type_key UNIQUE (form_type);


--
-- Name: form form_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form
    ADD CONSTRAINT form_pkey PRIMARY KEY (environment, form_type);


--
-- Name: formrecord formrecord_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formrecord
    ADD CONSTRAINT formrecord_pkey PRIMARY KEY (id);


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
-- Name: resourceversionid resourceversionid_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceversionid
    ADD CONSTRAINT resourceversionid_pkey PRIMARY KEY (environment, action_id, resource_version_id);


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
-- Name: formrecord_form_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX formrecord_form_index ON public.formrecord USING btree (form);


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
-- Name: resourceaction_action_id_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX resourceaction_action_id_started_index ON public.resourceaction USING btree (action_id, started DESC);


--
-- Name: resourceaction_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_started_index ON public.resourceaction USING btree (started);


--
-- Name: resourceversionid_action_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceversionid_action_id_index ON public.resourceversionid USING btree (action_id);


--
-- Name: resourceversionid_environment_resource_version_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceversionid_environment_resource_version_id_index ON public.resourceversionid USING btree (environment, resource_version_id);


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
-- Name: form form_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.form
    ADD CONSTRAINT form_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: formrecord formrecord_form_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.formrecord
    ADD CONSTRAINT formrecord_form_fkey FOREIGN KEY (form) REFERENCES public.form(form_type) ON DELETE CASCADE;


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
-- Name: resourceversionid resourceversionid_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceversionid
    ADD CONSTRAINT resourceversionid_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.resourceaction(action_id) ON DELETE CASCADE;


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

