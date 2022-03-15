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
    severity character varying DEFAULT 'message'::character varying,
    uri character varying DEFAULT ''::character varying,
    read boolean DEFAULT false,
    cleared boolean DEFAULT false
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
cfaba70c-42ad-41bd-98e3-c0470ebd2170	internal	2022-03-14 15:27:05.914509+01	f	ddfe3876-95f4-405f-bd74-488dd8b6985a	\N
cfaba70c-42ad-41bd-98e3-c0470ebd2170	localhost	2022-03-14 15:27:09.022685+01	f	2441b4a1-0e41-402a-883f-6042c7455a24	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
ddfe3876-95f4-405f-bd74-488dd8b6985a	d2d173a4-a3a2-11ec-a554-61d0763a01e1	internal	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170
2441b4a1-0e41-402a-883f-6042c7455a24	d2d173a4-a3a2-11ec-a554-61d0763a01e1	localhost	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
andras-Latitude-5401	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2022-03-14 15:27:05.914509+01	2022-03-14 15:27:20.378833+01	\N	d2d173a4-a3a2-11ec-a554-61d0763a01e1
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::Service	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::File	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::Directory	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::Package	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::Symlink	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::AgentConfig	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::Service	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::File	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::Directory	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::Package	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::Symlink	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cfaba70c-42ad-41bd-98e3-c0470ebd2170	std::AgentConfig	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
3602f1b7-70c6-4fef-aea2-3dc1a64b86b6	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2022-03-14 15:26:58.85147+01	2022-03-14 15:27:06.089669+01	2022-03-14 15:26:58.845234+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	ed2ffca2-58da-417e-9f89-699393862039	t	\N	{"errors": []}
518e9c06-1966-43c9-a7f5-989685b0ebf5	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2022-03-14 15:27:11.924392+01	2022-03-14 15:27:17.26342+01	2022-03-14 15:27:11.91293+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	c4ff5dd5-d7a7-464f-8e0d-f2d8a7983d63	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2022-03-14 15:27:04.935573+01	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
2	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2022-03-14 15:27:17.150942+01	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
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
529040fc-d874-4dc9-83d4-284e78f5ff8c	dev-2	328d8c1a-a595-4e1c-8f79-624c65f45f96			{}	0	f		
cfaba70c-42ad-41bd-98e3-c0470ebd2170	dev-1	328d8c1a-a595-4e1c-8f79-624c65f45f96			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
328d8c1a-a595-4e1c-8f79-624c65f45f96	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
82771335-8181-463e-b0b2-ceba76b09462	2022-03-14 15:26:58.852201+01	2022-03-14 15:26:58.854985+01		Init		Using extra environment variables during compile \n	0	3602f1b7-70c6-4fef-aea2-3dc1a64b86b6
ace2673b-dbfd-403d-8674-d616a5720bbe	2022-03-14 15:26:58.855777+01	2022-03-14 15:26:58.899197+01		Creating venv			0	3602f1b7-70c6-4fef-aea2-3dc1a64b86b6
acb00699-cc07-45fb-a487-59f601075dde	2022-03-14 15:26:58.904494+01	2022-03-14 15:27:04.020083+01	/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env/bin/python -m inmanta.app -vvv -X modules update	Updating modules		inmanta.moduletool       WARNING The `inmanta modules update` command has been deprecated in favor of `inmanta project update`.\ninmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           INFO    Checking out 3.0.8 on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           DEBUG   Parsing took 0.000188 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           INFO    Checking out 3.0.8 on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmpuk8mg3v6', '-r', '/tmp/tmpx8ot43qf']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpx8ot43qf (line 1)) (1.9.0)\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpx8ot43qf (line 3)) (1.1.3)\nRequirement already satisfied: Jinja2~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpx8ot43qf (line 4)) (3.0.3)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpx8ot43qf (line 1)) (4.1.1)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpx8ot43qf (line 3)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpx8ot43qf (line 3)) (2.2.0)\nCollecting dnspython>=1.15.0\n  Using cached dnspython-2.2.1-py3-none-any.whl (269 kB)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpx8ot43qf (line 4)) (2.1.0)\nInstalling collected packages: dnspython\n  Attempting uninstall: dnspython\n    Found existing installation: dnspython 2.2.0\n    Not uninstalling dnspython at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env\n    Can't uninstall 'dnspython'. No files were found to uninstall.\nSuccessfully installed dnspython-2.2.1\n\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000073 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           INFO    Checking out 3.0.8 on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmplszkm9s1', '-r', '/tmp/tmpcgvwn92q']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpcgvwn92q (line 1)) (1.9.0)\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpcgvwn92q (line 3)) (1.1.3)\nRequirement already satisfied: Jinja2~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpcgvwn92q (line 4)) (3.0.3)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpcgvwn92q (line 1)) (4.1.1)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpcgvwn92q (line 3)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpcgvwn92q (line 3)) (2.2.1)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpcgvwn92q (line 4)) (2.1.0)\n\n	0	3602f1b7-70c6-4fef-aea2-3dc1a64b86b6
e5458d44-c7c3-43a0-a038-0e722d79426a	2022-03-14 15:27:04.021309+01	2022-03-14 15:27:06.088371+01	/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env/bin/python -m inmanta.app -vvv export -X -e cfaba70c-42ad-41bd-98e3-c0470ebd2170 --server_address localhost --server_port 58745 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpz7vy_r93	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.015799 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000176 seconds\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002984)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001770)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000065)\ninmanta.execute.schedulerINFO    Total compilation time 0.004894\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58745/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58745/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58745/api/v1/file/effae82a2fef0c6bdbb8cd55bac37d95534ba286\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58745/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58745/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58745/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58745/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58745/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	3602f1b7-70c6-4fef-aea2-3dc1a64b86b6
5709aeff-84a7-4e9b-aa7e-1af0621322dd	2022-03-14 15:27:11.925496+01	2022-03-14 15:27:11.928887+01		Init		Using extra environment variables during compile \n	0	518e9c06-1966-43c9-a7f5-989685b0ebf5
6ebeb4b6-90a6-4efb-be52-e21c8f0618a7	2022-03-14 15:27:11.937691+01	2022-03-14 15:27:16.209667+01	/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env/bin/python -m inmanta.app -vvv -X modules update	Updating modules		inmanta.moduletool       WARNING The `inmanta modules update` command has been deprecated in favor of `inmanta project update`.\ninmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000115 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           INFO    Checking out 3.0.8 on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmp0ih27p5y', '-r', '/tmp/tmpr_9ofc99']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpr_9ofc99 (line 1)) (1.1.3)\nRequirement already satisfied: Jinja2~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpr_9ofc99 (line 2)) (3.0.3)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpr_9ofc99 (line 4)) (1.9.0)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpr_9ofc99 (line 1)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpr_9ofc99 (line 1)) (3.3)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpr_9ofc99 (line 2)) (2.1.0)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpr_9ofc99 (line 4)) (4.1.1)\n\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000073 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           INFO    Checking out 3.0.8 on /tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmp2h1qtmqm', '-r', '/tmp/tmpzvouool9']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpzvouool9 (line 1)) (1.1.3)\nRequirement already satisfied: Jinja2~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpzvouool9 (line 2)) (3.0.3)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpzvouool9 (line 4)) (1.9.0)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpzvouool9 (line 1)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpzvouool9 (line 1)) (2.2.1)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpzvouool9 (line 2)) (2.1.0)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpzvouool9 (line 4)) (4.1.1)\n\n	0	518e9c06-1966-43c9-a7f5-989685b0ebf5
f8688df8-60cc-4eb4-bf44-eb9de97150fe	2022-03-14 15:27:16.210797+01	2022-03-14 15:27:17.262347+01	/tmp/tmpjkgmoxjd/server/environments/cfaba70c-42ad-41bd-98e3-c0470ebd2170/.env/bin/python -m inmanta.app -vvv export -X -e cfaba70c-42ad-41bd-98e3-c0470ebd2170 --server_address localhost --server_port 58745 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpt0cmqzw7	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.016638 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000120 seconds\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003081)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002028)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000070)\ninmanta.execute.schedulerINFO    Total compilation time 0.005263\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58745/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58745/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58745/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58745/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58745/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	518e9c06-1966-43c9-a7f5-989685b0ebf5
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value) FROM stdin;
cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-03-14 15:27:10.861058+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost
cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-03-14 15:27:11.785036+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test
cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-03-14 15:27:21.112587+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test
cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-03-14 15:27:21.113612+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
c4838d6a-1b42-4bfc-a18f-8bf66f94202d	store	2022-03-14 15:27:04.934751+01	2022-03-14 15:27:04.949014+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-03-14T15:27:04.949036+01:00\\"}"}	\N	\N	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
2d5848b3-2bf7-42df-a31c-6f7b0c64186e	pull	2022-03-14 15:27:05.925269+01	2022-03-14 15:27:05.929316+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-14T15:27:05.929329+01:00\\"}"}	\N	\N	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
236b8a41-1975-4e21-90d7-df7c40064942	pull	2022-03-14 15:27:07.983422+01	2022-03-14 15:27:07.985193+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-14T15:27:07.985203+01:00\\"}"}	\N	\N	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
dd5bb9b1-c3cf-431f-a50a-29b695b47cf6	deploy	2022-03-14 15:27:07.991279+01	2022-03-14 15:27:08.01489+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-03-14 15:27:05+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-03-14 15:27:05+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"9ba4a976-0f67-4337-980c-232107ef7f9d\\"}, \\"timestamp\\": \\"2022-03-14T15:27:07.980108+01:00\\"}","{\\"msg\\": \\"Start deploy 9ba4a976-0f67-4337-980c-232107ef7f9d of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"9ba4a976-0f67-4337-980c-232107ef7f9d\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-14T15:27:07.996494+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-14T15:27:07.997388+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-14T15:27:08.002877+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 9ba4a976-0f67-4337-980c-232107ef7f9d\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"9ba4a976-0f67-4337-980c-232107ef7f9d\\"}, \\"timestamp\\": \\"2022-03-14T15:27:08.007482+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
b93f6507-8627-419c-9b63-64c0ab63c4fd	pull	2022-03-14 15:27:09.030716+01	2022-03-14 15:27:09.032421+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-14T15:27:09.032430+01:00\\"}"}	\N	\N	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	{"std::File[localhost,path=/tmp/test],v=1"}
14897a18-b2ea-4e0c-b8d1-fb97e8149c17	deploy	2022-03-14 15:27:10.848225+01	2022-03-14 15:27:10.861058+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"7f057d1a-22fc-477d-aea9-b43a54179a4c\\"}, \\"timestamp\\": \\"2022-03-14T15:27:10.838011+01:00\\"}","{\\"msg\\": \\"Start deploy 7f057d1a-22fc-477d-aea9-b43a54179a4c of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"7f057d1a-22fc-477d-aea9-b43a54179a4c\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-14T15:27:10.851075+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-14T15:27:10.851787+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 7f057d1a-22fc-477d-aea9-b43a54179a4c\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"7f057d1a-22fc-477d-aea9-b43a54179a4c\\"}, \\"timestamp\\": \\"2022-03-14T15:27:10.857079+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
440b845c-c079-48b3-a815-16b002f3d43d	deploy	2022-03-14 15:27:11.776885+01	2022-03-14 15:27:11.785036+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-03-14 15:27:09+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-03-14 15:27:09+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"25262924-5e90-4de6-a909-1a3f49c82cda\\"}, \\"timestamp\\": \\"2022-03-14T15:27:11.773687+01:00\\"}","{\\"msg\\": \\"Start deploy 25262924-5e90-4de6-a909-1a3f49c82cda of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"25262924-5e90-4de6-a909-1a3f49c82cda\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-14T15:27:11.778452+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-14T15:27:11.778995+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-14T15:27:11.779145+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 917, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpjkgmoxjd/cfaba70c-42ad-41bd-98e3-c0470ebd2170/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-14T15:27:11.781952+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 25262924-5e90-4de6-a909-1a3f49c82cda\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"25262924-5e90-4de6-a909-1a3f49c82cda\\"}, \\"timestamp\\": \\"2022-03-14T15:27:11.782205+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	cfaba70c-42ad-41bd-98e3-c0470ebd2170	1	{"std::File[localhost,path=/tmp/test],v=1"}
e516607b-7d33-4012-a7c6-aee5606f07ba	store	2022-03-14 15:27:17.150768+01	2022-03-14 15:27:17.154114+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-03-14T15:27:17.154129+01:00\\"}"}	\N	\N	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
5ed7a46d-b975-4a2f-927e-56791f743c0e	deploy	2022-03-14 15:27:17.172599+01	2022-03-14 15:27:17.172599+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-03-14T14:27:17.172599+00:00\\"}"}	deployed	\N	nochange	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
5a43f37e-78c3-450e-9eee-7f9aaefef547	pull	2022-03-14 15:27:17.360946+01	2022-03-14 15:27:17.36269+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-14T15:27:17.362702+01:00\\"}"}	\N	\N	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
734df1a4-0db4-44f5-9f66-7b4bc1580d0e	pull	2022-03-14 15:27:17.169857+01	2022-03-14 15:27:17.172706+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-14T15:27:17.174421+01:00\\"}"}	\N	\N	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	{"std::File[localhost,path=/tmp/test],v=2"}
616748a9-ab90-41d9-b2f5-c8d223a0e5fd	deploy	2022-03-14 15:27:21.059474+01	2022-03-14 15:27:21.113612+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"e5bbfcb2-4234-418f-ae7a-e49dcded7e56\\"}, \\"timestamp\\": \\"2022-03-14T15:27:21.053440+01:00\\"}","{\\"msg\\": \\"Start deploy e5bbfcb2-4234-418f-ae7a-e49dcded7e56 of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e5bbfcb2-4234-418f-ae7a-e49dcded7e56\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-14T15:27:21.062327+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-14T15:27:21.063360+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy e5bbfcb2-4234-418f-ae7a-e49dcded7e56\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"e5bbfcb2-4234-418f-ae7a-e49dcded7e56\\"}, \\"timestamp\\": \\"2022-03-14T15:27:21.070511+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
238d0e15-8a74-48f4-bab3-911a7305b1c4	deploy	2022-03-14 15:27:21.059329+01	2022-03-14 15:27:21.112587+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"d608287a-9461-4daa-acd4-b053bacc2b0f\\"}, \\"timestamp\\": \\"2022-03-14T15:27:21.052998+01:00\\"}","{\\"msg\\": \\"Start deploy d608287a-9461-4daa-acd4-b053bacc2b0f of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"d608287a-9461-4daa-acd4-b053bacc2b0f\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-14T15:27:21.061726+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-14T15:27:21.063540+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-03-14T15:27:21.067272+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 924, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpjkgmoxjd/cfaba70c-42ad-41bd-98e3-c0470ebd2170/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-14T15:27:21.067510+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy d608287a-9461-4daa-acd4-b053bacc2b0f\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"d608287a-9461-4daa-acd4-b053bacc2b0f\\"}, \\"timestamp\\": \\"2022-03-14T15:27:21.067742+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	{"std::File[localhost,path=/tmp/test],v=2"}
d45cda04-c55a-4cb2-9ef6-1fcd44b2b3e5	pull	2022-03-14 15:27:21.058778+01	2022-03-14 15:27:21.060839+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-14T15:27:21.060848+01:00\\"}"}	\N	\N	\N	cfaba70c-42ad-41bd-98e3-c0470ebd2170	2	{"std::File[localhost,path=/tmp/test],v=2"}
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

