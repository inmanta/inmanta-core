--
-- PostgreSQL database dump
--

-- Dumped from database version 13.4
-- Dumped by pg_dump version 13.4

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
-- Name: change; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.change AS ENUM (
    'nochange',
    'created',
    'purged',
    'updated'
);


--
-- Name: non_deploying_resource_state; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.non_deploying_resource_state AS ENUM (
    'unavailable',
    'skipped',
    'dry',
    'deployed',
    'failed',
    'available',
    'cancelled',
    'undefined',
    'skipped_for_undefined',
    'processing_events'
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

SET default_table_access_method = heap;

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
    resource_id_value character varying NOT NULL,
    last_non_deploying_status public.non_deploying_resource_state DEFAULT 'available'::public.non_deploying_resource_state NOT NULL
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
2353f882-e6e8-41b9-8772-80c5eea772f2	internal	2022-03-17 14:52:49.444004+01	f	f33403da-37b9-4b02-a54e-0516a003ec2c	\N
2353f882-e6e8-41b9-8772-80c5eea772f2	localhost	2022-03-17 14:52:51.762502+01	f	a33e0e3b-2a63-4b37-a367-f138e1a70962	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
f33403da-37b9-4b02-a54e-0516a003ec2c	8853a38e-a5f9-11ec-aea2-84144dfe5579	internal	\N	2353f882-e6e8-41b9-8772-80c5eea772f2
a33e0e3b-2a63-4b37-a367-f138e1a70962	8853a38e-a5f9-11ec-aea2-84144dfe5579	localhost	\N	2353f882-e6e8-41b9-8772-80c5eea772f2
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-inmanta-laptop	2353f882-e6e8-41b9-8772-80c5eea772f2	2022-03-17 14:52:49.444004+01	2022-03-17 14:53:00.070663+01	\N	8853a38e-a5f9-11ec-aea2-84144dfe5579
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
2353f882-e6e8-41b9-8772-80c5eea772f2	std::Service	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::File	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::Directory	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::Package	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::Symlink	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::AgentConfig	1	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::Service	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::File	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::Directory	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::Package	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::Symlink	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
2353f882-e6e8-41b9-8772-80c5eea772f2	std::AgentConfig	2	{"9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "effae82a2fef0c6bdbb8cd55bac37d95534ba286": ["/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.0", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
7d09c85a-ac04-45ad-ae4b-06cb93357ba1	2353f882-e6e8-41b9-8772-80c5eea772f2	2022-03-17 14:52:43.940021+01	2022-03-17 14:52:49.569511+01	2022-03-17 14:52:43.936296+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	1f010e0e-5718-4469-bc81-6ab5170ff9f0	t	\N	{"errors": []}
8c4b9c08-975d-4fdf-b72a-b22d84258715	2353f882-e6e8-41b9-8772-80c5eea772f2	2022-03-17 14:52:53.813204+01	2022-03-17 14:52:58.025444+01	2022-03-17 14:52:53.810359+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	a27f3faa-f9e3-41f6-ab26-60884a72e38a	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	2353f882-e6e8-41b9-8772-80c5eea772f2	2022-03-17 14:52:48.764147+01	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
2	2353f882-e6e8-41b9-8772-80c5eea772f2	2022-03-17 14:52:57.941179+01	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
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
75f62328-9ea8-4abf-a4ee-bb3ef00d9bad	dev-2	ca71ae08-9cb5-4f7b-b5dc-58f1edaf50d4			{}	0	f		
2353f882-e6e8-41b9-8772-80c5eea772f2	dev-1	ca71ae08-9cb5-4f7b-b5dc-58f1edaf50d4			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
ca71ae08-9cb5-4f7b-b5dc-58f1edaf50d4	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
228b6503-e6a1-46b3-b5a9-e03db19f9d5d	2022-03-17 14:52:43.940382+01	2022-03-17 14:52:43.941492+01		Init		Using extra environment variables during compile \n	0	7d09c85a-ac04-45ad-ae4b-06cb93357ba1
97dfa2db-c5b3-4953-a0bd-a7d06062eb6a	2022-03-17 14:52:43.941812+01	2022-03-17 14:52:43.94257+01		Creating venv			0	7d09c85a-ac04-45ad-ae4b-06cb93357ba1
2cba326f-616c-4ae2-a07e-dec797aeb305	2022-03-17 14:52:43.946765+01	2022-03-17 14:52:48.079055+01	/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/.env/bin/python -m inmanta.app -vvv -X modules update	Updating modules		inmanta.moduletool       WARNING The `inmanta modules update` command has been deprecated in favor of `inmanta project update`.\ninmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           INFO    Checking out 3.0.10 on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           DEBUG   Parsing took 0.000077 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           INFO    Checking out 3.0.10 on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmpbrl58ya1', '-r', '/tmp/tmpw9nvjs3z']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: Jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from -r /tmp/tmpw9nvjs3z (line 2)) (3.0.3)\nRequirement already satisfied: pydantic~=1.9 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from -r /tmp/tmpw9nvjs3z (line 3)) (1.9.0)\nRequirement already satisfied: email_validator~=1.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from -r /tmp/tmpw9nvjs3z (line 4)) (1.1.3)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpw9nvjs3z (line 2)) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpw9nvjs3z (line 3)) (4.1.1)\nRequirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpw9nvjs3z (line 4)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpw9nvjs3z (line 4)) (2.2.1)\n\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000042 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           INFO    Checking out 3.0.10 on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmp90vytelt', '-r', '/tmp/tmp6cc6ew_i']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: Jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from -r /tmp/tmp6cc6ew_i (line 2)) (3.0.3)\nRequirement already satisfied: pydantic~=1.9 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from -r /tmp/tmp6cc6ew_i (line 3)) (1.9.0)\nRequirement already satisfied: email_validator~=1.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from -r /tmp/tmp6cc6ew_i (line 4)) (1.1.3)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmp6cc6ew_i (line 2)) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmp6cc6ew_i (line 3)) (4.1.1)\nRequirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp6cc6ew_i (line 4)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp6cc6ew_i (line 4)) (3.3)\n\n	0	7d09c85a-ac04-45ad-ae4b-06cb93357ba1
c08a1f95-3f4b-4e6d-8f81-1949bdd2378a	2022-03-17 14:52:48.079824+01	2022-03-17 14:52:49.56848+01	/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/.env/bin/python -m inmanta.app -vvv export -X -e 2353f882-e6e8-41b9-8772-80c5eea772f2 --server_address localhost --server_port 58235 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmptmgs9b12	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.010104 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000065 seconds\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001926)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001215)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000041)\ninmanta.execute.schedulerINFO    Total compilation time 0.003235\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58235/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58235/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58235/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58235/api/v1/file/effae82a2fef0c6bdbb8cd55bac37d95534ba286\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58235/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58235/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58235/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58235/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	7d09c85a-ac04-45ad-ae4b-06cb93357ba1
91c5388e-4b71-4158-bde8-5fa988e3fe79	2022-03-17 14:52:53.813562+01	2022-03-17 14:52:53.814444+01		Init		Using extra environment variables during compile \n	0	8c4b9c08-975d-4fdf-b72a-b22d84258715
06424f0b-d2c7-49a5-bf47-35c14c89ca6a	2022-03-17 14:52:57.23095+01	2022-03-17 14:52:58.024336+01	/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/.env/bin/python -m inmanta.app -vvv export -X -e 2353f882-e6e8-41b9-8772-80c5eea772f2 --server_address localhost --server_port 58235 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpdu18fw17	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.010585 seconds\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000068 seconds\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002119)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001320)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000045)\ninmanta.execute.schedulerINFO    Total compilation time 0.003544\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58235/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58235/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58235/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:58235/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:58235/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	8c4b9c08-975d-4fdf-b72a-b22d84258715
9aea0746-6923-4397-aa3c-3366a50a2cde	2022-03-17 14:52:53.818712+01	2022-03-17 14:52:57.230083+01	/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/.env/bin/python -m inmanta.app -vvv -X modules update	Updating modules		inmanta.moduletool       WARNING The `inmanta modules update` command has been deprecated in favor of `inmanta project update`.\ninmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000065 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           INFO    Checking out 3.0.10 on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmpsh3hme_w', '-r', '/tmp/tmpyq2q915r']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: email_validator~=1.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from -r /tmp/tmpyq2q915r (line 1)) (1.1.3)\nRequirement already satisfied: Jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from -r /tmp/tmpyq2q915r (line 2)) (3.0.3)\nRequirement already satisfied: pydantic~=1.9 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from -r /tmp/tmpyq2q915r (line 3)) (1.9.0)\nRequirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpyq2q915r (line 1)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpyq2q915r (line 1)) (2.2.1)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpyq2q915r (line 2)) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpyq2q915r (line 3)) (4.1.1)\n\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000046 seconds\ninmanta.module           INFO    Performing fetch on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           INFO    Checking out 3.0.10 on /tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpdm6tpxpc/server/environments/2353f882-e6e8-41b9-8772-80c5eea772f2/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-c', '/tmp/tmprhsfx13w', '-r', '/tmp/tmpr0qs541a']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: email_validator~=1.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from -r /tmp/tmpr0qs541a (line 1)) (1.1.3)\nRequirement already satisfied: Jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from -r /tmp/tmpr0qs541a (line 2)) (3.0.3)\nRequirement already satisfied: pydantic~=1.9 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from -r /tmp/tmpr0qs541a (line 3)) (1.9.0)\nRequirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpr0qs541a (line 1)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpr0qs541a (line 1)) (3.3)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.0->-r /tmp/tmpr0qs541a (line 2)) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpr0qs541a (line 3)) (4.1.1)\n\n	0	8c4b9c08-975d-4fdf-b72a-b22d84258715
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status) FROM stdin;
2353f882-e6e8-41b9-8772-80c5eea772f2	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-03-17 14:52:53.759979+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed
2353f882-e6e8-41b9-8772-80c5eea772f2	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-03-17 14:52:54.373888+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed
2353f882-e6e8-41b9-8772-80c5eea772f2	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-03-17 14:53:00.398281+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed
2353f882-e6e8-41b9-8772-80c5eea772f2	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-03-17 14:53:00.403511+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
45d57d21-5c50-4c38-bf00-417603f939fc	store	2022-03-17 14:52:48.763755+01	2022-03-17 14:52:48.77127+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-03-17T14:52:48.771280+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
09b91934-079e-49e0-ac31-d2192c6185dd	pull	2022-03-17 14:52:49.449644+01	2022-03-17 14:52:49.451931+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-17T14:52:49.451942+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
a3737719-a707-42a7-bef4-a69d44a4aeaa	pull	2022-03-17 14:52:50.737764+01	2022-03-17 14:52:50.739285+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-17T14:52:50.740194+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
e8f6f1b3-356a-48d3-baf4-2e52e40070d0	deploy	2022-03-17 14:52:50.738432+01	2022-03-17 14:52:50.758519+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-03-17 14:52:49+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-03-17 14:52:49+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"77f3fb3e-f4c2-40f7-b637-fab1b0f78999\\"}, \\"timestamp\\": \\"2022-03-17T14:52:50.734966+01:00\\"}","{\\"msg\\": \\"Start deploy 77f3fb3e-f4c2-40f7-b637-fab1b0f78999 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"77f3fb3e-f4c2-40f7-b637-fab1b0f78999\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-17T14:52:50.739961+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-17T14:52:50.740545+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-17T14:52:50.743572+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 77f3fb3e-f4c2-40f7-b637-fab1b0f78999\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"77f3fb3e-f4c2-40f7-b637-fab1b0f78999\\"}, \\"timestamp\\": \\"2022-03-17T14:52:50.751744+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
e0707702-f969-4584-96dd-6a45872fcd60	pull	2022-03-17 14:52:51.767015+01	2022-03-17 14:52:51.767785+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-17T14:52:51.767790+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::File[localhost,path=/tmp/test],v=1"}
a0022d3a-a1d4-4021-8609-07141db4b180	pull	2022-03-17 14:52:52.52818+01	2022-03-17 14:52:52.52901+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-17T14:52:52.529015+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
134adf10-ea15-4c80-ad5a-b5684056ae3d	deploy	2022-03-17 14:52:52.528778+01	2022-03-17 14:52:52.536431+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"759c9f7e-89b0-4aa3-86a1-2711eb029964\\"}, \\"timestamp\\": \\"2022-03-17T14:52:52.523407+01:00\\"}","{\\"msg\\": \\"Start deploy 759c9f7e-89b0-4aa3-86a1-2711eb029964 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"759c9f7e-89b0-4aa3-86a1-2711eb029964\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-17T14:52:52.530693+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-17T14:52:52.531278+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 759c9f7e-89b0-4aa3-86a1-2711eb029964\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"759c9f7e-89b0-4aa3-86a1-2711eb029964\\"}, \\"timestamp\\": \\"2022-03-17T14:52:52.534067+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
707363bd-deff-4945-9763-e77a17b6fd53	deploy	2022-03-17 14:52:53.753731+01	2022-03-17 14:52:53.759979+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-03-17 14:52:51+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-03-17 14:52:51+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"4145d88f-1d44-4332-b433-cfd88d7eca5b\\"}, \\"timestamp\\": \\"2022-03-17T14:52:53.750353+01:00\\"}","{\\"msg\\": \\"Start deploy 4145d88f-1d44-4332-b433-cfd88d7eca5b of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"4145d88f-1d44-4332-b433-cfd88d7eca5b\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-17T14:52:53.754866+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-17T14:52:53.755486+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-17T14:52:53.755597+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 918, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpdm6tpxpc/2353f882-e6e8-41b9-8772-80c5eea772f2/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-17T14:52:53.757756+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 4145d88f-1d44-4332-b433-cfd88d7eca5b\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"4145d88f-1d44-4332-b433-cfd88d7eca5b\\"}, \\"timestamp\\": \\"2022-03-17T14:52:53.757963+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::File[localhost,path=/tmp/test],v=1"}
4ddab07d-8c34-4fe4-9aa6-90939dcf56cb	deploy	2022-03-17 14:52:57.952624+01	2022-03-17 14:52:57.952624+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-03-17T13:52:57.952624+00:00\\"}"}	deployed	\N	nochange	2353f882-e6e8-41b9-8772-80c5eea772f2	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
e70eee3c-6120-407d-bb18-c9ebc2f188d0	pull	2022-03-17 14:52:58.062739+01	2022-03-17 14:52:58.063424+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-03-17T14:52:58.063431+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
8a73c51e-2ac8-4064-9c1b-c1e304c0c3d6	deploy	2022-03-17 14:52:54.36779+01	2022-03-17 14:52:54.373888+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"7a9041e2-558e-43cd-8593-8de1ad8cb47a\\"}, \\"timestamp\\": \\"2022-03-17T14:52:54.364729+01:00\\"}","{\\"msg\\": \\"Start deploy 7a9041e2-558e-43cd-8593-8de1ad8cb47a of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"7a9041e2-558e-43cd-8593-8de1ad8cb47a\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-17T14:52:54.368985+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-17T14:52:54.369362+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 7a9041e2-558e-43cd-8593-8de1ad8cb47a\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"7a9041e2-558e-43cd-8593-8de1ad8cb47a\\"}, \\"timestamp\\": \\"2022-03-17T14:52:54.372047+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	2353f882-e6e8-41b9-8772-80c5eea772f2	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
03dbe965-e46b-4006-a68b-de9472651edb	store	2022-03-17 14:52:57.941012+01	2022-03-17 14:52:57.942709+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-03-17T14:52:57.942720+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
388cdd17-60dc-4fc4-ad0a-fb10e42f471e	pull	2022-03-17 14:52:57.951503+01	2022-03-17 14:52:57.952702+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-17T14:52:57.958483+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	2	{"std::File[localhost,path=/tmp/test],v=2"}
65cf7ab3-775b-4422-b4c5-cf1781bd8999	deploy	2022-03-17 14:53:00.388872+01	2022-03-17 14:53:00.398281+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"440c629e-9f6b-41c0-ba29-4ca9336368de\\"}, \\"timestamp\\": \\"2022-03-17T14:53:00.385050+01:00\\"}","{\\"msg\\": \\"Start deploy 440c629e-9f6b-41c0-ba29-4ca9336368de of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"440c629e-9f6b-41c0-ba29-4ca9336368de\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-03-17T14:53:00.390789+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-17T14:53:00.391510+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy 440c629e-9f6b-41c0-ba29-4ca9336368de\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"440c629e-9f6b-41c0-ba29-4ca9336368de\\"}, \\"timestamp\\": \\"2022-03-17T14:53:00.394582+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	2353f882-e6e8-41b9-8772-80c5eea772f2	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
45f555bb-f674-444e-8227-923ef084009b	deploy	2022-03-17 14:53:00.388962+01	2022-03-17 14:53:00.403511+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"a8364c78-11c5-429b-a515-782f403f63d7\\"}, \\"timestamp\\": \\"2022-03-17T14:53:00.384764+01:00\\"}","{\\"msg\\": \\"Start deploy a8364c78-11c5-429b-a515-782f403f63d7 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"a8364c78-11c5-429b-a515-782f403f63d7\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-17T14:53:00.391189+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-03-17T14:53:00.392533+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-03-17T14:53:00.395440+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 925, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpdm6tpxpc/2353f882-e6e8-41b9-8772-80c5eea772f2/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-03-17T14:53:00.395849+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy a8364c78-11c5-429b-a515-782f403f63d7\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"a8364c78-11c5-429b-a515-782f403f63d7\\"}, \\"timestamp\\": \\"2022-03-17T14:53:00.396055+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	2353f882-e6e8-41b9-8772-80c5eea772f2	2	{"std::File[localhost,path=/tmp/test],v=2"}
3733ad93-ad22-47fd-a90d-b2182d338c45	pull	2022-03-17 14:53:00.388163+01	2022-03-17 14:53:00.389421+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-03-17T14:53:00.389428+01:00\\"}"}	\N	\N	\N	2353f882-e6e8-41b9-8772-80c5eea772f2	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203160}
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
-- Name: dryrun dryrun_environment_model_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun
    ADD CONSTRAINT dryrun_environment_model_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


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
-- Name: resource resource_environment_model_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_environment_model_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: resourceaction resourceaction_environment_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction
    ADD CONSTRAINT resourceaction_environment_version_fkey FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_version_fkey FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

