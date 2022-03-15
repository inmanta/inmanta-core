--
-- PostgreSQL database dump
--

-- Dumped from database version 10.19 (Ubuntu 10.19-1.pgdg18.04+1)
-- Dumped by pg_dump version 12.9 (Ubuntu 12.9-1.pgdg18.04+1)

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
    halted boolean DEFAULT false NOT NULL,
    description character varying(255) DEFAULT ''::character varying,
    icon character varying(65535) DEFAULT ''::character varying
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
6dec4b53-0150-41bb-8976-eded559f3fbb	internal	2022-03-15 16:35:03.455414+01	f	0952bf44-78af-405a-a734-3a180491141a	\N
6dec4b53-0150-41bb-8976-eded559f3fbb	localhost	2022-03-15 16:35:06.61799+01	f	ee478251-be6b-4923-ad7c-5386c770a462	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
0952bf44-78af-405a-a734-3a180491141a	7ba2d05e-a475-11ec-a554-61d0763a01e1	internal	\N	6dec4b53-0150-41bb-8976-eded559f3fbb
ee478251-be6b-4923-ad7c-5386c770a462	7ba2d05e-a475-11ec-a554-61d0763a01e1	localhost	\N	6dec4b53-0150-41bb-8976-eded559f3fbb
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
andras-Latitude-5401	6dec4b53-0150-41bb-8976-eded559f3fbb	2022-03-15 16:35:03.455414+01	2022-03-15 16:35:18.181708+01	\N	7ba2d05e-a475-11ec-a554-61d0763a01e1
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
6dec4b53-0150-41bb-8976-eded559f3fbb	std::Service	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::File	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::Directory	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::Package	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::Symlink	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::AgentConfig	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::Service	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::File	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::Directory	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::Package	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::Symlink	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
6dec4b53-0150-41bb-8976-eded559f3fbb	std::AgentConfig	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
de3633cb-9c7d-4665-a593-7f8ab30a000d	6dec4b53-0150-41bb-8976-eded559f3fbb	2022-03-15 16:34:55.567873+01	2022-03-15 16:35:03.594583+01	2022-03-15 16:34:55.561895+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	ee4f5af8-1b82-4d26-8a5e-29c46863be89	t	\N	{"errors": []}
f9ef3faf-a217-4ae1-8798-a820d62707ca	6dec4b53-0150-41bb-8976-eded559f3fbb	2022-03-15 16:35:09.403875+01	2022-03-15 16:35:15.043781+01	2022-03-15 16:35:09.398314+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	4fe92307-bc68-4a5a-85b1-ff40419d60a7	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	6dec4b53-0150-41bb-8976-eded559f3fbb	2022-03-15 16:35:02.557823+01	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
2	6dec4b53-0150-41bb-8976-eded559f3fbb	2022-03-15 16:35:14.918956+01	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
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
d738549b-8152-43a3-8100-6209a51f1790	dev-2	7130deb4-7234-4fc1-9000-31f7bc4065f7			{}	0	f		
6dec4b53-0150-41bb-8976-eded559f3fbb	dev-1	7130deb4-7234-4fc1-9000-31f7bc4065f7			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
7130deb4-7234-4fc1-9000-31f7bc4065f7	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
15a85f07-6a7c-48e3-921a-7a7bd52733f2	2022-03-15 16:34:55.568549+01	2022-03-15 16:34:55.570615+01		Init		Using extra environment variables during compile \n	0	de3633cb-9c7d-4665-a593-7f8ab30a000d
57e4c66c-fa31-4fd6-8d65-71663416b314	2022-03-15 16:34:55.571273+01	2022-03-15 16:34:55.597809+01		Creating venv			0	de3633cb-9c7d-4665-a593-7f8ab30a000d
c637ec8d-07ec-423b-9d72-13b9a20f35a9	2022-03-15 16:35:01.652991+01	2022-03-15 16:35:03.593352+01	/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env/bin/python -m inmanta.app -vvv export -X -e 6dec4b53-0150-41bb-8976-eded559f3fbb --server_address localhost --server_port 40551 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpnvetl8et	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.016314 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000109 seconds\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003031)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002083)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000067)\ninmanta.execute.schedulerINFO    Total compilation time 0.005272\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40551/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40551/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40551/api/v1/file/effae82a2fef0c6bdbb8cd55bac37d95534ba286\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40551/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40551/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40551/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40551/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40551/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	de3633cb-9c7d-4665-a593-7f8ab30a000d
799bfca2-503a-462c-ba25-71f45e831f22	2022-03-15 16:34:55.601966+01	2022-03-15 16:35:01.651879+01	/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env/bin/python -m inmanta.app -vvv -X modules update	Updating modules		inmanta.moduletool       WARNING The `inmanta modules update` command has been deprecated in favor of `inmanta project update`.\ninmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           INFO    Checking out 3.0.9 on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           DEBUG   Parsing took 0.000184 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           INFO    Checking out 3.0.9 on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmprjc2rotm', '-r', '/tmp/tmp_lid6_cd']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp_lid6_cd (line 1)) (1.1.3)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp_lid6_cd (line 2)) (1.9.0)\nRequirement already satisfied: Jinja2~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp_lid6_cd (line 3)) (3.0.3)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp_lid6_cd (line 1)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp_lid6_cd (line 1)) (2.2.0)\nCollecting dnspython>=1.15.0\n  Using cached dnspython-2.2.1-py3-none-any.whl (269 kB)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmp_lid6_cd (line 2)) (4.1.1)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmp_lid6_cd (line 3)) (2.1.0)\nCollecting MarkupSafe>=2.0\n  Using cached MarkupSafe-2.1.1-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (25 kB)\nInstalling collected packages: MarkupSafe, dnspython\n  Attempting uninstall: MarkupSafe\n    Found existing installation: MarkupSafe 2.1.0\n    Not uninstalling markupsafe at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env\n    Can't uninstall 'MarkupSafe'. No files were found to uninstall.\n  Attempting uninstall: dnspython\n    Found existing installation: dnspython 2.2.0\n    Not uninstalling dnspython at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env\n    Can't uninstall 'dnspython'. No files were found to uninstall.\nSuccessfully installed MarkupSafe-2.1.1 dnspython-2.2.1\n\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000074 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           INFO    Checking out 3.0.9 on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmpke5pqlc1', '-r', '/tmp/tmpzm_r852z']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpzm_r852z (line 1)) (1.1.3)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpzm_r852z (line 2)) (1.9.0)\nRequirement already satisfied: Jinja2~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpzm_r852z (line 3)) (3.0.3)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpzm_r852z (line 1)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpzm_r852z (line 1)) (3.3)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpzm_r852z (line 2)) (4.1.1)\nRequirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpzm_r852z (line 3)) (2.1.1)\n\n	0	de3633cb-9c7d-4665-a593-7f8ab30a000d
5dda9e0c-b112-4586-8fa4-112213a85dc2	2022-03-15 16:35:14.035889+01	2022-03-15 16:35:15.042985+01	/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env/bin/python -m inmanta.app -vvv export -X -e 6dec4b53-0150-41bb-8976-eded559f3fbb --server_address localhost --server_port 40551 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpx96h9uag	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.015164 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000103 seconds\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002847)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001802)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000065)\ninmanta.execute.schedulerINFO    Total compilation time 0.004794\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40551/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40551/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40551/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:40551/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:40551/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	f9ef3faf-a217-4ae1-8798-a820d62707ca
cffbabc5-ce6b-48f1-8390-08db06372638	2022-03-15 16:35:09.404476+01	2022-03-15 16:35:09.406353+01		Init		Using extra environment variables during compile \n	0	f9ef3faf-a217-4ae1-8798-a820d62707ca
c77d5aae-a074-417d-a401-c7a0cdded400	2022-03-15 16:35:09.41089+01	2022-03-15 16:35:14.034722+01	/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env/bin/python -m inmanta.app -vvv -X modules update	Updating modules		inmanta.moduletool       WARNING The `inmanta modules update` command has been deprecated in favor of `inmanta project update`.\ninmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000117 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           INFO    Checking out 3.0.9 on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmpdzp85xj4', '-r', '/tmp/tmpxbke8zo9']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: Jinja2~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpxbke8zo9 (line 1)) (3.0.3)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpxbke8zo9 (line 3)) (1.9.0)\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpxbke8zo9 (line 4)) (1.1.3)\nRequirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpxbke8zo9 (line 1)) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpxbke8zo9 (line 3)) (4.1.1)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpxbke8zo9 (line 4)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpxbke8zo9 (line 4)) (2.2.1)\n\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000108 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           INFO    Checking out 3.0.9 on /tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpdvw_v_jk/server/environments/6dec4b53-0150-41bb-8976-eded559f3fbb/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmp4r5c822m', '-r', '/tmp/tmp3j1q78zw']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: Jinja2~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp3j1q78zw (line 1)) (3.0.3)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp3j1q78zw (line 3)) (1.9.0)\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp3j1q78zw (line 4)) (1.1.3)\nRequirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmp3j1q78zw (line 1)) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmp3j1q78zw (line 3)) (4.1.1)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp3j1q78zw (line 4)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp3j1q78zw (line 4)) (2.2.1)\n\n	0	f9ef3faf-a217-4ae1-8798-a820d62707ca
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value) FROM stdin;
6dec4b53-0150-41bb-8976-eded559f3fbb	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-03-15 16:35:08.39765+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost
6dec4b53-0150-41bb-8976-eded559f3fbb	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-03-15 16:35:09.322773+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test
6dec4b53-0150-41bb-8976-eded559f3fbb	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-03-15 16:35:18.664352+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost
6dec4b53-0150-41bb-8976-eded559f3fbb	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-03-15 16:35:18.663946+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
80e63371-076d-4ac8-93cd-e8cf5301c575	store	2022-03-15 16:35:02.557191+01	2022-03-15 16:35:02.569547+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-03-15T16:35:02.569564+01:00\\"}"}	\N	\N	\N	6dec4b53-0150-41bb-8976-eded559f3fbb	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
d18db285-6160-4075-a8e8-0a0e14592fd7	pull	2022-03-15 16:35:03.466918+01	2022-03-15 16:35:03.473642+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-15T16:35:03.473658+01:00\\"}"}	\N	\N	\N	6dec4b53-0150-41bb-8976-eded559f3fbb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
5ac40958-f1e6-48e1-b087-18e444e5510c	pull	2022-03-15 16:35:05.591205+01	2022-03-15 16:35:05.598903+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-15T16:35:05.598914+01:00\\"}"}	\N	\N	\N	6dec4b53-0150-41bb-8976-eded559f3fbb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1ad7484b-aaed-4811-a0ba-0bd980a1ee93	deploy	2022-03-15 16:35:05.592065+01	2022-03-15 16:35:05.610806+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-03-15 16:35:03+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-03-15 16:35:03+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"6b7ecccf-85cc-4098-83f3-a3222d67ae21\\"}, \\"timestamp\\": \\"2022-03-15T16:35:05.587706+01:00\\"}","{\\"msg\\": \\"Start deploy 6b7ecccf-85cc-4098-83f3-a3222d67ae21 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"6b7ecccf-85cc-4098-83f3-a3222d67ae21\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-15T16:35:05.594366+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-15T16:35:05.594993+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-15T16:35:05.599032+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 6b7ecccf-85cc-4098-83f3-a3222d67ae21\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"6b7ecccf-85cc-4098-83f3-a3222d67ae21\\"}, \\"timestamp\\": \\"2022-03-15T16:35:05.603132+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	6dec4b53-0150-41bb-8976-eded559f3fbb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1bd6fab5-6ea8-495b-8b03-c972124fe3d0	pull	2022-03-15 16:35:06.625448+01	2022-03-15 16:35:06.631869+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-15T16:35:06.631883+01:00\\"}"}	\N	\N	\N	6dec4b53-0150-41bb-8976-eded559f3fbb	1	{"std::File[localhost,path=/tmp/test],v=1"}
f53d9f2d-73b8-43f1-a892-fa50d4336858	deploy	2022-03-15 16:35:08.387699+01	2022-03-15 16:35:08.39765+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"c17b0f34-41ca-425e-b26e-09b62cfc65ad\\"}, \\"timestamp\\": \\"2022-03-15T16:35:08.382450+01:00\\"}","{\\"msg\\": \\"Start deploy c17b0f34-41ca-425e-b26e-09b62cfc65ad of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"c17b0f34-41ca-425e-b26e-09b62cfc65ad\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-15T16:35:08.390073+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-15T16:35:08.390636+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy c17b0f34-41ca-425e-b26e-09b62cfc65ad\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"c17b0f34-41ca-425e-b26e-09b62cfc65ad\\"}, \\"timestamp\\": \\"2022-03-15T16:35:08.394758+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	6dec4b53-0150-41bb-8976-eded559f3fbb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
2225ce4d-eb94-4adc-9efb-f3550d85f932	deploy	2022-03-15 16:35:09.313108+01	2022-03-15 16:35:09.322773+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-03-15 16:35:06+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-03-15 16:35:06+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"58ed3579-c337-4781-843d-080e670c69b7\\"}, \\"timestamp\\": \\"2022-03-15T16:35:09.309691+01:00\\"}","{\\"msg\\": \\"Start deploy 58ed3579-c337-4781-843d-080e670c69b7 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"58ed3579-c337-4781-843d-080e670c69b7\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-15T16:35:09.314927+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-15T16:35:09.315569+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-03-15T16:35:09.318239+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 924, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpdvw_v_jk/6dec4b53-0150-41bb-8976-eded559f3fbb/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-15T16:35:09.318827+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 58ed3579-c337-4781-843d-080e670c69b7\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"58ed3579-c337-4781-843d-080e670c69b7\\"}, \\"timestamp\\": \\"2022-03-15T16:35:09.319106+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	6dec4b53-0150-41bb-8976-eded559f3fbb	1	{"std::File[localhost,path=/tmp/test],v=1"}
43328530-4572-4a6a-a98e-e312978517e6	store	2022-03-15 16:35:14.918778+01	2022-03-15 16:35:14.924425+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-03-15T16:35:14.924439+01:00\\"}"}	\N	\N	\N	6dec4b53-0150-41bb-8976-eded559f3fbb	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
6fa8024c-f1fb-4c69-b2f4-4ddd8b5b4e82	deploy	2022-03-15 16:35:14.942906+01	2022-03-15 16:35:14.942906+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-03-15T15:35:14.942906+00:00\\"}"}	deployed	\N	nochange	6dec4b53-0150-41bb-8976-eded559f3fbb	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
7ecb44c6-8eb2-4165-99f0-30f335c04b99	pull	2022-03-15 16:35:14.940534+01	2022-03-15 16:35:14.943021+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-15T16:35:14.944544+01:00\\"}"}	\N	\N	\N	6dec4b53-0150-41bb-8976-eded559f3fbb	2	{"std::File[localhost,path=/tmp/test],v=2"}
ad720d13-3650-482e-8466-48f6bbb61b2d	pull	2022-03-15 16:35:15.166585+01	2022-03-15 16:35:15.168019+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-15T16:35:15.168029+01:00\\"}"}	\N	\N	\N	6dec4b53-0150-41bb-8976-eded559f3fbb	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
21d72417-a429-42ef-9ff3-3f57d3a6d5b1	deploy	2022-03-15 16:35:18.647132+01	2022-03-15 16:35:18.664352+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"db48dcb7-b038-435e-8fed-ac8e1e81d7b5\\"}, \\"timestamp\\": \\"2022-03-15T16:35:18.641419+01:00\\"}","{\\"msg\\": \\"Start deploy db48dcb7-b038-435e-8fed-ac8e1e81d7b5 of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"db48dcb7-b038-435e-8fed-ac8e1e81d7b5\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-15T16:35:18.650393+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-15T16:35:18.651204+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy db48dcb7-b038-435e-8fed-ac8e1e81d7b5\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"db48dcb7-b038-435e-8fed-ac8e1e81d7b5\\"}, \\"timestamp\\": \\"2022-03-15T16:35:18.658801+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	6dec4b53-0150-41bb-8976-eded559f3fbb	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
9f0bc652-0e1b-4201-931c-500c2634c586	pull	2022-03-15 16:35:18.645797+01	2022-03-15 16:35:18.648061+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-15T16:35:18.648069+01:00\\"}"}	\N	\N	\N	6dec4b53-0150-41bb-8976-eded559f3fbb	2	{"std::File[localhost,path=/tmp/test],v=2"}
7664087a-2c0b-4452-925f-95da7ab9f42e	deploy	2022-03-15 16:35:18.647344+01	2022-03-15 16:35:18.663946+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"00e34661-85a5-49a2-a645-4f14179e0a98\\"}, \\"timestamp\\": \\"2022-03-15T16:35:18.640998+01:00\\"}","{\\"msg\\": \\"Start deploy 00e34661-85a5-49a2-a645-4f14179e0a98 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"00e34661-85a5-49a2-a645-4f14179e0a98\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-15T16:35:18.651594+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-15T16:35:18.652748+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-03-15T16:35:18.656324+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 924, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpdvw_v_jk/6dec4b53-0150-41bb-8976-eded559f3fbb/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-15T16:35:18.656716+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 00e34661-85a5-49a2-a645-4f14179e0a98\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"00e34661-85a5-49a2-a645-4f14179e0a98\\"}, \\"timestamp\\": \\"2022-03-15T16:35:18.657056+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	6dec4b53-0150-41bb-8976-eded559f3fbb	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140}
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
-- Name: notification_env_created_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notification_env_created_id_index ON public.notification USING btree (environment, created DESC, id);


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

