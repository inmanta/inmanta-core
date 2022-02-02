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
    resource_id_value character varying NOT NULL
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
18c3a11d-132f-4293-987c-de797eb36244	internal	2021-06-24 15:18:25.994112+02	f	bfd1465f-c13b-4928-a364-5da61bb1e4a9	\N
18c3a11d-132f-4293-987c-de797eb36244	localhost	2021-06-24 15:18:27.960457+02	f	c68b9fd7-c7a7-42a5-9a16-097595f45855	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
bfd1465f-c13b-4928-a364-5da61bb1e4a9	a88641c0-d4ee-11eb-a3b3-50e0859bd318	internal	\N	18c3a11d-132f-4293-987c-de797eb36244
c68b9fd7-c7a7-42a5-9a16-097595f45855	a88641c0-d4ee-11eb-a3b3-50e0859bd318	localhost	\N	18c3a11d-132f-4293-987c-de797eb36244
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
andras-Latitude-5401	18c3a11d-132f-4293-987c-de797eb36244	2021-06-24 15:18:25.994112+02	2021-06-24 15:18:28.99619+02	\N	a88641c0-d4ee-11eb-a3b3-50e0859bd318
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
18c3a11d-132f-4293-987c-de797eb36244	std::Service	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::File	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::Directory	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::Package	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::Symlink	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::AgentConfig	1	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::Service	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::File	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::Directory	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::Package	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::Symlink	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
18c3a11d-132f-4293-987c-de797eb36244	std::AgentConfig	2	{"7f65552db2702d19fcc07c97d5cafac4431b094d": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.8", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
c6110ef1-accc-4ff7-9425-2b739be505dd	18c3a11d-132f-4293-987c-de797eb36244	2021-06-24 15:18:23.788209+02	2021-06-24 15:18:26.133853+02	2021-06-24 15:18:23.782083+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	8ec8e1a5-4725-4bba-ad6c-34109469dd92	t	\N	{"errors": []}
e57929f4-1a83-4480-87db-ee23eded51db	18c3a11d-132f-4293-987c-de797eb36244	2021-06-24 15:18:28.135821+02	2021-06-24 15:18:28.932565+02	2021-06-24 15:18:28.125118+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	b2820264-b663-46f6-8238-3712f6d6c535	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	18c3a11d-132f-4293-987c-de797eb36244	2021-06-24 15:18:25.314105+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
2	18c3a11d-132f-4293-987c-de797eb36244	2021-06-24 15:18:28.843886+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
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
483a69e6-8e55-4eba-a77e-9865628a1155	dev-2	760ceb74-01e1-49ed-bbed-8a313ba07419			{}	0	f
18c3a11d-132f-4293-987c-de797eb36244	dev-1	760ceb74-01e1-49ed-bbed-8a313ba07419			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
760ceb74-01e1-49ed-bbed-8a313ba07419	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
572a1a3b-9828-40ed-b430-3b85aabe66a5	2021-06-24 15:18:23.788749+02	2021-06-24 15:18:23.790278+02		Init		Using extra environment variables during compile \n	0	c6110ef1-accc-4ff7-9425-2b739be505dd
b715a740-631b-4c52-81b2-1b81d4e09abf	2021-06-24 15:18:23.790804+02	2021-06-24 15:18:26.132629+02	/home/andras/git-repos/inmanta-core/.env6/bin/python -m inmanta.app -vvv export -X -e 18c3a11d-132f-4293-987c-de797eb36244 --server_address localhost --server_port 58019 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpj9fsq1ju	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    Checking out 3.0.2 on /tmp/tmppq3mal4n/server/environments/18c3a11d-132f-4293-987c-de797eb36244/libs/std\ninmanta.module           DEBUG   Parsing took 0.814542 seconds\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003142)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001910)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000065)\ninmanta.execute.schedulerINFO    Total compilation time 0.005189\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58019/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58019/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58019/api/v1/file/7f65552db2702d19fcc07c97d5cafac4431b094d\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58019/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58019/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58019/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58019/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58019/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	c6110ef1-accc-4ff7-9425-2b739be505dd
c383b4dc-069e-4a8c-a3aa-5cb00d4edc2f	2021-06-24 15:18:28.136753+02	2021-06-24 15:18:28.138914+02		Init		Using extra environment variables during compile \n	0	e57929f4-1a83-4480-87db-ee23eded51db
b241a77b-4b7f-4402-82b6-ee73516e8d45	2021-06-24 15:18:28.139729+02	2021-06-24 15:18:28.931606+02	/home/andras/git-repos/inmanta-core/.env6/bin/python -m inmanta.app -vvv export -X -e 18c3a11d-132f-4293-987c-de797eb36244 --server_address localhost --server_port 58019 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpd4ef5evf	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.015403 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003045)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001895)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000065)\ninmanta.execute.schedulerINFO    Total compilation time 0.005076\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58019/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58019/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58019/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58019/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58019/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	e57929f4-1a83-4480-87db-ee23eded51db
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value) FROM stdin;
18c3a11d-132f-4293-987c-de797eb36244	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2021-06-24 15:18:26.982596+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost
18c3a11d-132f-4293-987c-de797eb36244	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2021-06-24 15:18:28.023785+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test
18c3a11d-132f-4293-987c-de797eb36244	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2021-06-24 15:18:28.864023+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost
18c3a11d-132f-4293-987c-de797eb36244	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2021-06-24 15:18:29.024627+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
5562f5b8-d6e2-4fd6-a4f3-666e71b97803	store	2021-06-24 15:18:25.313583+02	2021-06-24 15:18:25.325755+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"NOTSET\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2021-06-24T15:18:25.325772+02:00\\"}"}	\N	\N	\N	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
b57dfef7-0a24-419e-8588-e49f7f4c9dce	pull	2021-06-24 15:18:26.00681+02	2021-06-24 15:18:26.01468+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.014697+02:00\\"}"}	\N	\N	\N	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
9608bfac-40f7-4954-a904-8ccb66d1230f	pull	2021-06-24 15:18:26.909323+02	2021-06-24 15:18:26.910409+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.910416+02:00\\"}"}	\N	\N	\N	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
0381308b-b89f-404d-8944-170c16e4e98b	deploy	2021-06-24 15:18:26.914489+02	2021-06-24 15:18:26.938248+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2021-06-24 15:18:25+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2021-06-24 15:18:25+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"9092628b-b88c-4ee9-bec9-009b0c466b94\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.905985+02:00\\"}","{\\"msg\\": \\"Start deploy 9092628b-b88c-4ee9-bec9-009b0c466b94 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"9092628b-b88c-4ee9-bec9-009b0c466b94\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:26.920667+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-24T15:18:26.921335+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-24T15:18:26.925740+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 9092628b-b88c-4ee9-bec9-009b0c466b94\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"9092628b-b88c-4ee9-bec9-009b0c466b94\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.930273+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
d28cbddf-fabd-400a-bd48-815461ad8e8c	deploy	2021-06-24 15:18:26.94941+02	2021-06-24 15:18:26.957754+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"51d103e6-9fa5-42df-9d88-b8957d4a9d14\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.946064+02:00\\"}","{\\"msg\\": \\"Start deploy 51d103e6-9fa5-42df-9d88-b8957d4a9d14 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"51d103e6-9fa5-42df-9d88-b8957d4a9d14\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:26.951251+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-24T15:18:26.951689+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 51d103e6-9fa5-42df-9d88-b8957d4a9d14\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"51d103e6-9fa5-42df-9d88-b8957d4a9d14\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.955061+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
fd7ab42d-cea9-464c-aa21-bc59b2f6990a	pull	2021-06-24 15:18:26.962805+02	2021-06-24 15:18:26.964013+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.964020+02:00\\"}"}	\N	\N	\N	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c95800a9-4106-4605-9826-d1519c67013d	deploy	2021-06-24 15:18:26.972827+02	2021-06-24 15:18:26.982596+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2021-06-24 15:18:25+0200', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2021-06-24 15:18:25+0200', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"812a394e-30ff-4425-80b1-ee0528e35dc6\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.970472+02:00\\"}","{\\"msg\\": \\"Start deploy 812a394e-30ff-4425-80b1-ee0528e35dc6 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"812a394e-30ff-4425-80b1-ee0528e35dc6\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:26.975712+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-24T15:18:26.976090+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 812a394e-30ff-4425-80b1-ee0528e35dc6\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"812a394e-30ff-4425-80b1-ee0528e35dc6\\"}, \\"timestamp\\": \\"2021-06-24T15:18:26.979765+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
f2552f19-7cb4-4041-9882-0b30f3f43ebd	pull	2021-06-24 15:18:27.980194+02	2021-06-24 15:18:27.982388+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-24T15:18:27.982403+02:00\\"}"}	\N	\N	\N	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::File[localhost,path=/tmp/test],v=1"}
fba64490-dcda-4be1-9032-5986739594a6	deploy	2021-06-24 15:18:28.864023+02	2021-06-24 15:18:28.864023+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2021-06-24T13:18:28.864023+00:00\\"}"}	deployed	\N	nochange	18c3a11d-132f-4293-987c-de797eb36244	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
30596b2c-2ea2-4ca2-b631-4c3efc620172	deploy	2021-06-24 15:18:28.003723+02	2021-06-24 15:18:28.023785+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2021-06-24 15:18:27+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2021-06-24 15:18:27+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"3eb798db-d41f-42c0-99d8-a978ea4b65d9\\"}, \\"timestamp\\": \\"2021-06-24T15:18:27.999656+02:00\\"}","{\\"msg\\": \\"Start deploy 3eb798db-d41f-42c0-99d8-a978ea4b65d9 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"3eb798db-d41f-42c0-99d8-a978ea4b65d9\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:28.006232+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-24T15:18:28.006835+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:28.018418+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 918, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmppq3mal4n/18c3a11d-132f-4293-987c-de797eb36244/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:28.019043+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 3eb798db-d41f-42c0-99d8-a978ea4b65d9\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"3eb798db-d41f-42c0-99d8-a978ea4b65d9\\"}, \\"timestamp\\": \\"2021-06-24T15:18:28.019366+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	18c3a11d-132f-4293-987c-de797eb36244	1	{"std::File[localhost,path=/tmp/test],v=1"}
61c9baf9-1c7b-4cf9-bee1-3653d2971991	store	2021-06-24 15:18:28.843683+02	2021-06-24 15:18:28.846571+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"NOTSET\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2021-06-24T15:18:28.846585+02:00\\"}"}	\N	\N	\N	18c3a11d-132f-4293-987c-de797eb36244	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
c3afbb27-7144-4658-bb38-c4dee924edaf	pull	2021-06-24 15:18:28.861971+02	2021-06-24 15:18:28.86413+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-24T15:18:28.865866+02:00\\"}"}	\N	\N	\N	18c3a11d-132f-4293-987c-de797eb36244	2	{"std::File[localhost,path=/tmp/test],v=2"}
0aa59e56-e32b-486c-9f73-5ff92fe84193	pull	2021-06-24 15:18:28.997113+02	2021-06-24 15:18:28.999218+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2021-06-24T15:18:28.999226+02:00\\"}"}	\N	\N	\N	18c3a11d-132f-4293-987c-de797eb36244	2	{"std::File[localhost,path=/tmp/test],v=2"}
10fefa89-9afd-4240-ab54-624a5369093d	deploy	2021-06-24 15:18:28.880521+02	2021-06-24 15:18:28.890386+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"16c62526-9aee-41d6-a00b-f61e3529f2be\\"}, \\"timestamp\\": \\"2021-06-24T15:18:28.877007+02:00\\"}","{\\"msg\\": \\"Start deploy 16c62526-9aee-41d6-a00b-f61e3529f2be of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"16c62526-9aee-41d6-a00b-f61e3529f2be\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:28.882733+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-24T15:18:28.883219+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:28.885802+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 918, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmppq3mal4n/18c3a11d-132f-4293-987c-de797eb36244/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:28.886031+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 16c62526-9aee-41d6-a00b-f61e3529f2be\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"16c62526-9aee-41d6-a00b-f61e3529f2be\\"}, \\"timestamp\\": \\"2021-06-24T15:18:28.886275+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	18c3a11d-132f-4293-987c-de797eb36244	2	{"std::File[localhost,path=/tmp/test],v=2"}
4d2bcfa1-641a-444f-8ad1-049a08bada9b	deploy	2021-06-24 15:18:29.015897+02	2021-06-24 15:18:29.024627+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"529cda84-8e3e-4f0c-a3c2-05d1a34977cc\\"}, \\"timestamp\\": \\"2021-06-24T15:18:29.012664+02:00\\"}","{\\"msg\\": \\"Start deploy 529cda84-8e3e-4f0c-a3c2-05d1a34977cc of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"529cda84-8e3e-4f0c-a3c2-05d1a34977cc\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:29.017615+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2021-06-24T15:18:29.018028+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:29.020474+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 918, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmppq3mal4n/18c3a11d-132f-4293-987c-de797eb36244/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {}}, \\"timestamp\\": \\"2021-06-24T15:18:29.020669+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 529cda84-8e3e-4f0c-a3c2-05d1a34977cc\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"529cda84-8e3e-4f0c-a3c2-05d1a34977cc\\"}, \\"timestamp\\": \\"2021-06-24T15:18:29.020889+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	18c3a11d-132f-4293-987c-de797eb36244	2	{"std::File[localhost,path=/tmp/test],v=2"}
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
-- Name: resource_environment_resource_id_value_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_id_value_index ON public.resource USING btree (environment, resource_id_value);


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

