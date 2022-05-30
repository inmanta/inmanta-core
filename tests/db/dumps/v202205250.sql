--
-- PostgreSQL database dump
--

-- Dumped from database version 12.11 (Ubuntu 12.11-1.pgdg18.04+1)
-- Dumped by pg_dump version 12.11 (Ubuntu 12.11-1.pgdg18.04+1)

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
    resource_id_value character varying NOT NULL,
    last_non_deploying_status public.non_deploying_resource_state DEFAULT 'available'::public.non_deploying_resource_state NOT NULL,
    resource_set character varying
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
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	internal	2022-05-30 11:04:44.027247+02	f	9344f8e6-77ef-406b-b519-de688b74c03e	\N
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	localhost	2022-05-30 11:04:46.743137+02	f	1e0d357d-11b2-4c6a-ac05-983f7a043a5b	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
9344f8e6-77ef-406b-b519-de688b74c03e	8bf69220-dff7-11ec-89c9-d3032acba9d0	internal	\N	527be28f-0f16-40b6-bb6d-8cc03b1bbca9
1e0d357d-11b2-4c6a-ac05-983f7a043a5b	8bf69220-dff7-11ec-89c9-d3032acba9d0	localhost	\N	527be28f-0f16-40b6-bb6d-8cc03b1bbca9
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
andras-Latitude-5401	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2022-05-30 11:04:44.027247+02	2022-05-30 11:05:05.415182+02	\N	8bf69220-dff7-11ec-89c9-d3032acba9d0
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::Service	1	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::File	1	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::Directory	1	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::Package	1	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::Symlink	1	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::AgentConfig	1	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::Service	2	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::File	2	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::Directory	2	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::Package	2	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::Symlink	2	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	std::AgentConfig	2	{"7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "a57d1721252af61207a107375d7ccdd9c54ef7d7": ["/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
0216c124-76f2-46f4-962e-ff1fe7a9dbd0	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2022-05-30 11:04:19.244449+02	2022-05-30 11:04:44.218527+02	2022-05-30 11:04:19.239584+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	d9b370cc-0872-491a-a79a-e8e41356b07a	t	\N	{"errors": []}
880884bd-f25b-4578-a530-5b553e7de1dc	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2022-05-30 11:04:47.753782+02	2022-05-30 11:05:05.290489+02	2022-05-30 11:04:47.749373+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	98d168b9-447b-4e21-bd62-1874d39e9b99	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2022-05-30 11:04:40.547079+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
2	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2022-05-30 11:05:04.378605+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "andras", "hostname": "andras-Latitude-5401", "inmanta:compile:state": "success"}}	2	{}	{}
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
eeaabbf0-029d-40df-ace8-885562378ae5	dev-2	c80e1f37-771d-4a78-8e61-4eca4807f709			{}	0	f
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	dev-1	c80e1f37-771d-4a78-8e61-4eca4807f709			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
c80e1f37-771d-4a78-8e61-4eca4807f709	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
732800f0-b481-4bae-8daf-fb96b7574337	2022-05-30 11:04:19.245204+02	2022-05-30 11:04:19.247008+02		Init		Using extra environment variables during compile \n	0	0216c124-76f2-46f4-962e-ff1fe7a9dbd0
ccacbab1-072a-44e3-b964-ccb37630a483	2022-05-30 11:04:19.247544+02	2022-05-30 11:04:19.2738+02		Creating venv			0	0216c124-76f2-46f4-962e-ff1fe7a9dbd0
97c1d12d-7f84-451e-a75f-6a396a5f4912	2022-05-30 11:04:19.277872+02	2022-05-30 11:04:39.538572+02	/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env/bin/python -m inmanta.app -vvv -X modules update	Updating modules		inmanta.moduletool       WARNING The `inmanta modules update` command has been deprecated in favor of `inmanta project update`.\ninmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           INFO    Checking out 3.1.0 on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           DEBUG   Parsing took 0.000109 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           INFO    Checking out 3.1.0 on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-r', '/tmp/tmpgttjeh3i', 'inmanta-core==7.0.0.dev0', 'inmanta==2020.6.dev0', 'inmanta-dev-dependencies==2.16.0', 'inmanta-sphinx==1.5.0']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/andras/git-repos/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: inmanta==2020.6.dev0 in /home/andras/git-repos/inmanta-core/src (2020.6.dev0)\nRequirement already satisfied: inmanta-dev-dependencies==2.16.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (2.16.0)\nRequirement already satisfied: inmanta-sphinx==1.5.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (1.5.0)\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpgttjeh3i (line 2)) (1.2.1)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpgttjeh3i (line 3)) (1.9.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpgttjeh3i (line 4)) (3.1.2)\nRequirement already satisfied: asyncpg~=0.25 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.7.3)\nRequirement already satisfied: cryptography<38,>=36 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.11.4)\nRequirement already satisfied: more-itertools~=8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.1)\nRequirement already satisfied: ply~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nRequirement already satisfied: typing_inspect~=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: flake8-isort==4.1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (4.1.1)\nRequirement already satisfied: flake8-copyright==0.2.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.2.2)\nRequirement already satisfied: flake8==3.9.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (3.9.2)\nRequirement already satisfied: black==22.3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (22.3.0)\nRequirement already satisfied: lxml==4.8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (4.8.0)\nRequirement already satisfied: psycopg==3.0.11 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (3.0.11)\nRequirement already satisfied: mypy==0.950 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.950)\nRequirement already satisfied: pytest==7.1.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (7.1.2)\nRequirement already satisfied: pep8-naming==0.12.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.12.1)\nRequirement already satisfied: flake8-black==0.3.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.3.2)\nRequirement already satisfied: isort==5.10.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (5.10.1)\nRequirement already satisfied: Sphinx>=1.5 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-sphinx==1.5.0) (4.5.0)\nCollecting Sphinx>=1.5\n  Using cached Sphinx-5.0.0-py3-none-any.whl (3.1 MB)\nRequirement already satisfied: platformdirs>=2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (2.5.1)\nCollecting platformdirs>=2\n  Using cached platformdirs-2.5.2-py3-none-any.whl (14 kB)\nRequirement already satisfied: pathspec>=0.9.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (0.9.0)\nRequirement already satisfied: mypy-extensions>=0.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (0.4.3)\nRequirement already satisfied: tomli>=1.1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (2.0.1)\nRequirement already satisfied: typing-extensions>=3.10.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (4.1.1)\nCollecting typing-extensions>=3.10.0.0\n  Using cached typing_extensions-4.2.0-py3-none-any.whl (24 kB)\nRequirement already satisfied: pyflakes<2.4.0,>=2.3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (2.3.1)\nRequirement already satisfied: pycodestyle<2.8.0,>=2.7.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (2.7.0)\nRequirement already satisfied: mccabe<0.7.0,>=0.6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (0.6.1)\nRequirement already satisfied: setuptools in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8-copyright==0.2.2->inmanta-dev-dependencies==2.16.0) (62.3.2)\nRequirement already satisfied: testfixtures<7,>=6.8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8-isort==4.1.1->inmanta-dev-dependencies==2.16.0) (6.18.4)\nCollecting testfixtures<7,>=6.8.0\n  Using cached testfixtures-6.18.5-py2.py3-none-any.whl (95 kB)\nRequirement already satisfied: flake8-polyfill<2,>=1.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pep8-naming==0.12.1->inmanta-dev-dependencies==2.16.0) (1.0.2)\nRequirement already satisfied: pluggy<2.0,>=0.12 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.0.0)\nRequirement already satisfied: iniconfig in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.1.1)\nRequirement already satisfied: py>=1.8.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.11.0)\nRequirement already satisfied: attrs>=19.2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (21.4.0)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpgttjeh3i (line 2)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpgttjeh3i (line 2)) (2.2.0)\nCollecting dnspython>=1.15.0\n  Using cached dnspython-2.2.1-py3-none-any.whl (269 kB)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Jinja2~=3.1->-r /tmp/tmpgttjeh3i (line 4)) (2.1.0)\nCollecting MarkupSafe>=2.0\n  Using cached MarkupSafe-2.1.1-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (25 kB)\nRequirement already satisfied: pep517>=0.9.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nRequirement already satisfied: poyo>=0.5.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.5.0)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (6.1.1)\nCollecting python-slugify>=4.0.0\n  Using cached python_slugify-6.1.2-py2.py3-none-any.whl (9.4 kB)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: six>=1.10 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: requests>=2.23.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2.27.1)\nRequirement already satisfied: cffi>=1.12 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.0)\nRequirement already satisfied: zipp>=0.5 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.7.0)\nCollecting zipp>=0.5\n  Using cached zipp-3.8.0-py3-none-any.whl (5.4 kB)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.7)\nCollecting pyparsing!=3.0.5,>=2.0.2\n  Using cached pyparsing-3.0.9-py3-none-any.whl (98 kB)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: snowballstemmer>=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.2.0)\nRequirement already satisfied: sphinxcontrib-jsmath in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.1)\nRequirement already satisfied: alabaster<0.8,>=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (0.7.12)\nRequirement already satisfied: Pygments>=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.11.2)\nCollecting Pygments>=2.0\n  Using cached Pygments-2.12.0-py3-none-any.whl (1.1 MB)\nRequirement already satisfied: sphinxcontrib-qthelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.3)\nRequirement already satisfied: sphinxcontrib-applehelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.2)\nRequirement already satisfied: sphinxcontrib-serializinghtml>=1.1.5 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.1.5)\nRequirement already satisfied: babel>=1.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.9.1)\nCollecting babel>=1.3\n  Using cached Babel-2.10.1-py3-none-any.whl (9.5 MB)\nRequirement already satisfied: sphinxcontrib-htmlhelp>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.0.0)\nRequirement already satisfied: sphinxcontrib-devhelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.2)\nRequirement already satisfied: imagesize in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.3.0)\nRequirement already satisfied: docutils<0.19,>=0.14 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (0.17.1)\nCollecting docutils<0.19,>=0.14\n  Using cached docutils-0.18.1-py2.py3-none-any.whl (570 kB)\nRequirement already satisfied: pytz>=2015.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from babel>=1.3->Sphinx>=1.5->inmanta-sphinx==1.5.0) (2021.3)\nCollecting pytz>=2015.7\n  Using cached pytz-2022.1-py2.py3-none-any.whl (503 kB)\nRequirement already satisfied: chardet>=3.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (4.0.0)\nRequirement already satisfied: pycparser in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.26.8)\nCollecting urllib3<1.27,>=1.21.1\n  Using cached urllib3-1.26.9-py2.py3-none-any.whl (138 kB)\nRequirement already satisfied: charset-normalizer~=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2.0.12)\nRequirement already satisfied: certifi>=2017.4.17 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2021.10.8)\nCollecting certifi>=2017.4.17\n  Using cached certifi-2022.5.18.1-py3-none-any.whl (155 kB)\nInstalling collected packages: testfixtures, pytz, zipp, urllib3, typing-extensions, python-slugify, pyparsing, Pygments, platformdirs, MarkupSafe, docutils, dnspython, certifi, babel, Sphinx\n  Attempting uninstall: testfixtures\n    Found existing installation: testfixtures 6.18.4\n    Not uninstalling testfixtures at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'testfixtures'. No files were found to uninstall.\n  Attempting uninstall: pytz\n    Found existing installation: pytz 2021.3\n    Not uninstalling pytz at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'pytz'. No files were found to uninstall.\n  Attempting uninstall: zipp\n    Found existing installation: zipp 3.7.0\n    Not uninstalling zipp at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'zipp'. No files were found to uninstall.\n  Attempting uninstall: urllib3\n    Found existing installation: urllib3 1.26.8\n    Not uninstalling urllib3 at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'urllib3'. No files were found to uninstall.\n  Attempting uninstall: typing-extensions\n    Found existing installation: typing_extensions 4.1.1\n    Not uninstalling typing-extensions at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'typing_extensions'. No files were found to uninstall.\n  Attempting uninstall: python-slugify\n    Found existing installation: python-slugify 6.1.1\n    Not uninstalling python-slugify at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'python-slugify'. No files were found to uninstall.\n  Attempting uninstall: pyparsing\n    Found existing installation: pyparsing 3.0.7\n    Not uninstalling pyparsing at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'pyparsing'. No files were found to uninstall.\n  Attempting uninstall: Pygments\n    Found existing installation: Pygments 2.11.2\n    Not uninstalling pygments at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'Pygments'. No files were found to uninstall.\n  Attempting uninstall: platformdirs\n    Found existing installation: platformdirs 2.5.1\n    Not uninstalling platformdirs at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'platformdirs'. No files were found to uninstall.\n  Attempting uninstall: MarkupSafe\n    Found existing installation: MarkupSafe 2.1.0\n    Not uninstalling markupsafe at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'MarkupSafe'. No files were found to uninstall.\n  Attempting uninstall: docutils\n    Found existing installation: docutils 0.17.1\n    Not uninstalling docutils at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'docutils'. No files were found to uninstall.\n  Attempting uninstall: dnspython\n    Found existing installation: dnspython 2.2.0\n    Not uninstalling dnspython at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'dnspython'. No files were found to uninstall.\n  Attempting uninstall: certifi\n    Found existing installation: certifi 2021.10.8\n    Not uninstalling certifi at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'certifi'. No files were found to uninstall.\n  Attempting uninstall: babel\n    Found existing installation: Babel 2.9.1\n    Not uninstalling babel at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'Babel'. No files were found to uninstall.\n  Attempting uninstall: Sphinx\n    Found existing installation: Sphinx 4.5.0\n    Not uninstalling sphinx at /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages, outside environment /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env\n    Can't uninstall 'Sphinx'. No files were found to uninstall.\nSuccessfully installed MarkupSafe-2.1.1 Pygments-2.12.0 Sphinx-5.0.0 babel-2.10.1 certifi-2022.5.18.1 dnspython-2.2.1 docutils-0.18.1 platformdirs-2.5.2 pyparsing-3.0.9 python-slugify-6.1.2 pytz-2022.1 testfixtures-6.18.5 typing-extensions-4.2.0 urllib3-1.26.9 zipp-3.8.0\n\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000091 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           INFO    Checking out 3.1.0 on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-r', '/tmp/tmp8k47fgnf', 'inmanta-core==7.0.0.dev0', 'inmanta==2020.6.dev0', 'inmanta-dev-dependencies==2.16.0', 'inmanta-sphinx==1.5.0']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/andras/git-repos/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: inmanta==2020.6.dev0 in /home/andras/git-repos/inmanta-core/src (2020.6.dev0)\nRequirement already satisfied: inmanta-dev-dependencies==2.16.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (2.16.0)\nRequirement already satisfied: inmanta-sphinx==1.5.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (1.5.0)\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp8k47fgnf (line 2)) (1.2.1)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp8k47fgnf (line 3)) (1.9.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp8k47fgnf (line 4)) (3.1.2)\nRequirement already satisfied: asyncpg~=0.25 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.7.3)\nRequirement already satisfied: cryptography<38,>=36 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.11.4)\nRequirement already satisfied: more-itertools~=8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.1)\nRequirement already satisfied: ply~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nRequirement already satisfied: typing_inspect~=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: lxml==4.8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (4.8.0)\nRequirement already satisfied: psycopg==3.0.11 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (3.0.11)\nRequirement already satisfied: flake8-isort==4.1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (4.1.1)\nRequirement already satisfied: flake8-black==0.3.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.3.2)\nRequirement already satisfied: isort==5.10.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (5.10.1)\nRequirement already satisfied: pytest==7.1.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (7.1.2)\nRequirement already satisfied: mypy==0.950 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.950)\nRequirement already satisfied: flake8==3.9.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (3.9.2)\nRequirement already satisfied: black==22.3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (22.3.0)\nRequirement already satisfied: flake8-copyright==0.2.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.2.2)\nRequirement already satisfied: pep8-naming==0.12.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.12.1)\nRequirement already satisfied: Sphinx>=1.5 in ./.env/lib/python3.9/site-packages (from inmanta-sphinx==1.5.0) (5.0.0)\nRequirement already satisfied: mypy-extensions>=0.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (0.4.3)\nRequirement already satisfied: platformdirs>=2 in ./.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (2.5.2)\nRequirement already satisfied: tomli>=1.1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (2.0.1)\nRequirement already satisfied: typing-extensions>=3.10.0.0 in ./.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (4.2.0)\nRequirement already satisfied: pathspec>=0.9.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (0.9.0)\nRequirement already satisfied: mccabe<0.7.0,>=0.6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (0.6.1)\nRequirement already satisfied: pycodestyle<2.8.0,>=2.7.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (2.7.0)\nRequirement already satisfied: pyflakes<2.4.0,>=2.3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (2.3.1)\nRequirement already satisfied: setuptools in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8-copyright==0.2.2->inmanta-dev-dependencies==2.16.0) (62.3.2)\nRequirement already satisfied: testfixtures<7,>=6.8.0 in ./.env/lib/python3.9/site-packages (from flake8-isort==4.1.1->inmanta-dev-dependencies==2.16.0) (6.18.5)\nRequirement already satisfied: flake8-polyfill<2,>=1.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pep8-naming==0.12.1->inmanta-dev-dependencies==2.16.0) (1.0.2)\nRequirement already satisfied: pluggy<2.0,>=0.12 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.0.0)\nRequirement already satisfied: py>=1.8.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.11.0)\nRequirement already satisfied: iniconfig in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.1.1)\nRequirement already satisfied: attrs>=19.2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (21.4.0)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp8k47fgnf (line 2)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp8k47fgnf (line 2)) (3.3)\nRequirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.9/site-packages (from Jinja2~=3.1->-r /tmp/tmp8k47fgnf (line 4)) (2.1.1)\nRequirement already satisfied: pep517>=0.9.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nRequirement already satisfied: six>=1.10 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: poyo>=0.5.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.5.0)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: requests>=2.23.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2.27.1)\nRequirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: cffi>=1.12 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.0)\nRequirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.0)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in ./.env/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: alabaster<0.8,>=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (0.7.12)\nRequirement already satisfied: sphinxcontrib-jsmath in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.1)\nRequirement already satisfied: Pygments>=2.0 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.12.0)\nRequirement already satisfied: sphinxcontrib-devhelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.2)\nRequirement already satisfied: sphinxcontrib-serializinghtml>=1.1.5 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.1.5)\nRequirement already satisfied: imagesize in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.3.0)\nRequirement already satisfied: sphinxcontrib-applehelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.2)\nRequirement already satisfied: snowballstemmer>=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.2.0)\nRequirement already satisfied: babel>=1.3 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.10.1)\nRequirement already satisfied: docutils<0.19,>=0.14 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (0.18.1)\nRequirement already satisfied: sphinxcontrib-qthelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.3)\nRequirement already satisfied: sphinxcontrib-htmlhelp>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.0.0)\nRequirement already satisfied: pytz>=2015.7 in ./.env/lib/python3.9/site-packages (from babel>=1.3->Sphinx>=1.5->inmanta-sphinx==1.5.0) (2022.1)\nRequirement already satisfied: chardet>=3.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (4.0.0)\nRequirement already satisfied: pycparser in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2022.5.18.1)\nRequirement already satisfied: charset-normalizer~=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2.0.12)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.26.9)\n\n	0	0216c124-76f2-46f4-962e-ff1fe7a9dbd0
181bb58a-9a08-4593-8fcd-0c9d7bb1b94f	2022-05-30 11:04:39.539511+02	2022-05-30 11:04:44.217215+02	/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env/bin/python -m inmanta.app -vvv export -X -e 527be28f-0f16-40b6-bb6d-8cc03b1bbca9 --server_address localhost --server_port 35269 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp6nqquzl7	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.007008 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000186 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003059)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002051)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000069)\ninmanta.execute.schedulerINFO    Total compilation time 0.005260\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:35269/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:35269/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:35269/api/v1/file/a57d1721252af61207a107375d7ccdd9c54ef7d7\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:35269/api/v1/file/7e7cfcd78427dd36f0c0405e6b0ddd5f01a16f5c\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:35269/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:35269/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:35269/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:35269/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	0216c124-76f2-46f4-962e-ff1fe7a9dbd0
90ad6611-7bc2-4446-95e4-53715c508e4f	2022-05-30 11:04:47.754636+02	2022-05-30 11:04:47.75695+02		Init		Using extra environment variables during compile \n	0	880884bd-f25b-4578-a530-5b553e7de1dc
b68f37db-0dea-4ef8-bc5e-b84052589465	2022-05-30 11:04:47.761336+02	2022-05-30 11:05:03.377625+02	/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env/bin/python -m inmanta.app -vvv -X modules update	Updating modules		inmanta.moduletool       WARNING The `inmanta modules update` command has been deprecated in favor of `inmanta project update`.\ninmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000093 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           INFO    Checking out 3.1.0 on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-r', '/tmp/tmp6og19atp', 'inmanta-core==7.0.0.dev0', 'inmanta==2020.6.dev0', 'inmanta-dev-dependencies==2.16.0', 'inmanta-sphinx==1.5.0']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/andras/git-repos/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: inmanta==2020.6.dev0 in /home/andras/git-repos/inmanta-core/src (2020.6.dev0)\nRequirement already satisfied: inmanta-dev-dependencies==2.16.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (2.16.0)\nRequirement already satisfied: inmanta-sphinx==1.5.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (1.5.0)\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp6og19atp (line 2)) (1.2.1)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp6og19atp (line 3)) (1.9.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmp6og19atp (line 4)) (3.1.2)\nRequirement already satisfied: asyncpg~=0.25 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.7.3)\nRequirement already satisfied: cryptography<38,>=36 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.11.4)\nRequirement already satisfied: more-itertools~=8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.1)\nRequirement already satisfied: ply~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nRequirement already satisfied: typing_inspect~=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: psycopg==3.0.11 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (3.0.11)\nRequirement already satisfied: isort==5.10.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (5.10.1)\nRequirement already satisfied: flake8-copyright==0.2.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.2.2)\nRequirement already satisfied: mypy==0.950 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.950)\nRequirement already satisfied: pytest==7.1.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (7.1.2)\nRequirement already satisfied: lxml==4.8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (4.8.0)\nRequirement already satisfied: flake8-isort==4.1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (4.1.1)\nRequirement already satisfied: pep8-naming==0.12.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.12.1)\nRequirement already satisfied: black==22.3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (22.3.0)\nRequirement already satisfied: flake8==3.9.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (3.9.2)\nRequirement already satisfied: flake8-black==0.3.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.3.2)\nRequirement already satisfied: Sphinx>=1.5 in ./.env/lib/python3.9/site-packages (from inmanta-sphinx==1.5.0) (5.0.0)\nRequirement already satisfied: typing-extensions>=3.10.0.0 in ./.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (4.2.0)\nRequirement already satisfied: pathspec>=0.9.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (0.9.0)\nRequirement already satisfied: mypy-extensions>=0.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (0.4.3)\nRequirement already satisfied: platformdirs>=2 in ./.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (2.5.2)\nRequirement already satisfied: tomli>=1.1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (2.0.1)\nRequirement already satisfied: pycodestyle<2.8.0,>=2.7.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (2.7.0)\nRequirement already satisfied: mccabe<0.7.0,>=0.6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (0.6.1)\nRequirement already satisfied: pyflakes<2.4.0,>=2.3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (2.3.1)\nRequirement already satisfied: setuptools in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8-copyright==0.2.2->inmanta-dev-dependencies==2.16.0) (62.3.2)\nRequirement already satisfied: testfixtures<7,>=6.8.0 in ./.env/lib/python3.9/site-packages (from flake8-isort==4.1.1->inmanta-dev-dependencies==2.16.0) (6.18.5)\nRequirement already satisfied: flake8-polyfill<2,>=1.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pep8-naming==0.12.1->inmanta-dev-dependencies==2.16.0) (1.0.2)\nRequirement already satisfied: pluggy<2.0,>=0.12 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.0.0)\nRequirement already satisfied: iniconfig in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.1.1)\nRequirement already satisfied: py>=1.8.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.11.0)\nRequirement already satisfied: attrs>=19.2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (21.4.0)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp6og19atp (line 2)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp6og19atp (line 2)) (2.2.1)\nRequirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.9/site-packages (from Jinja2~=3.1->-r /tmp/tmp6og19atp (line 4)) (2.1.1)\nRequirement already satisfied: pep517>=0.9.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: requests>=2.23.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2.27.1)\nRequirement already satisfied: six>=1.10 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: poyo>=0.5.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.5.0)\nRequirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: cffi>=1.12 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.0)\nRequirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.0)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in ./.env/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: sphinxcontrib-jsmath in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.1)\nRequirement already satisfied: sphinxcontrib-htmlhelp>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.0.0)\nRequirement already satisfied: sphinxcontrib-devhelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.2)\nRequirement already satisfied: alabaster<0.8,>=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (0.7.12)\nRequirement already satisfied: sphinxcontrib-qthelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.3)\nRequirement already satisfied: imagesize in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.3.0)\nRequirement already satisfied: sphinxcontrib-serializinghtml>=1.1.5 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.1.5)\nRequirement already satisfied: babel>=1.3 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.10.1)\nRequirement already satisfied: snowballstemmer>=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.2.0)\nRequirement already satisfied: docutils<0.19,>=0.14 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (0.18.1)\nRequirement already satisfied: sphinxcontrib-applehelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.2)\nRequirement already satisfied: Pygments>=2.0 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.12.0)\nRequirement already satisfied: pytz>=2015.7 in ./.env/lib/python3.9/site-packages (from babel>=1.3->Sphinx>=1.5->inmanta-sphinx==1.5.0) (2022.1)\nRequirement already satisfied: chardet>=3.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (4.0.0)\nRequirement already satisfied: pycparser in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.26.9)\nRequirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2022.5.18.1)\nRequirement already satisfied: charset-normalizer~=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2.0.12)\n\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000088 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           INFO    Checking out 3.1.0 on /tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-r', '/tmp/tmpf3l8v238', 'inmanta-core==7.0.0.dev0', 'inmanta==2020.6.dev0', 'inmanta-dev-dependencies==2.16.0', 'inmanta-sphinx==1.5.0']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/andras/git-repos/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: inmanta==2020.6.dev0 in /home/andras/git-repos/inmanta-core/src (2020.6.dev0)\nRequirement already satisfied: inmanta-dev-dependencies==2.16.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (2.16.0)\nRequirement already satisfied: inmanta-sphinx==1.5.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (1.5.0)\nRequirement already satisfied: email_validator~=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpf3l8v238 (line 2)) (1.2.1)\nRequirement already satisfied: pydantic~=1.9 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpf3l8v238 (line 3)) (1.9.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from -r /tmp/tmpf3l8v238 (line 4)) (3.1.2)\nRequirement already satisfied: asyncpg~=0.25 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.7.3)\nRequirement already satisfied: cryptography<38,>=36 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.11.4)\nRequirement already satisfied: more-itertools~=8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.1)\nRequirement already satisfied: ply~=3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nRequirement already satisfied: typing_inspect~=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: flake8-copyright==0.2.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.2.2)\nRequirement already satisfied: pep8-naming==0.12.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.12.1)\nRequirement already satisfied: psycopg==3.0.11 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (3.0.11)\nRequirement already satisfied: isort==5.10.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (5.10.1)\nRequirement already satisfied: mypy==0.950 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.950)\nRequirement already satisfied: pytest==7.1.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (7.1.2)\nRequirement already satisfied: lxml==4.8.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (4.8.0)\nRequirement already satisfied: flake8-black==0.3.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (0.3.2)\nRequirement already satisfied: flake8==3.9.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (3.9.2)\nRequirement already satisfied: black==22.3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (22.3.0)\nRequirement already satisfied: flake8-isort==4.1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from inmanta-dev-dependencies==2.16.0) (4.1.1)\nRequirement already satisfied: Sphinx>=1.5 in ./.env/lib/python3.9/site-packages (from inmanta-sphinx==1.5.0) (5.0.0)\nRequirement already satisfied: mypy-extensions>=0.4.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (0.4.3)\nRequirement already satisfied: pathspec>=0.9.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (0.9.0)\nRequirement already satisfied: platformdirs>=2 in ./.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (2.5.2)\nRequirement already satisfied: tomli>=1.1.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (2.0.1)\nRequirement already satisfied: typing-extensions>=3.10.0.0 in ./.env/lib/python3.9/site-packages (from black==22.3.0->inmanta-dev-dependencies==2.16.0) (4.2.0)\nRequirement already satisfied: pycodestyle<2.8.0,>=2.7.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (2.7.0)\nRequirement already satisfied: mccabe<0.7.0,>=0.6.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (0.6.1)\nRequirement already satisfied: pyflakes<2.4.0,>=2.3.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8==3.9.2->inmanta-dev-dependencies==2.16.0) (2.3.1)\nRequirement already satisfied: setuptools in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from flake8-copyright==0.2.2->inmanta-dev-dependencies==2.16.0) (62.3.2)\nRequirement already satisfied: testfixtures<7,>=6.8.0 in ./.env/lib/python3.9/site-packages (from flake8-isort==4.1.1->inmanta-dev-dependencies==2.16.0) (6.18.5)\nRequirement already satisfied: flake8-polyfill<2,>=1.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pep8-naming==0.12.1->inmanta-dev-dependencies==2.16.0) (1.0.2)\nRequirement already satisfied: attrs>=19.2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (21.4.0)\nRequirement already satisfied: pluggy<2.0,>=0.12 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.0.0)\nRequirement already satisfied: py>=1.8.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.11.0)\nRequirement already satisfied: iniconfig in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from pytest==7.1.2->inmanta-dev-dependencies==2.16.0) (1.1.1)\nRequirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpf3l8v238 (line 2)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpf3l8v238 (line 2)) (3.3)\nRequirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.9/site-packages (from Jinja2~=3.1->-r /tmp/tmpf3l8v238 (line 4)) (2.1.1)\nRequirement already satisfied: pep517>=0.9.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nRequirement already satisfied: six>=1.10 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: poyo>=0.5.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.5.0)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: requests>=2.23.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2.27.1)\nRequirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: cffi>=1.12 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.0)\nRequirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.0)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in ./.env/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: sphinxcontrib-jsmath in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.1)\nRequirement already satisfied: sphinxcontrib-qthelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.3)\nRequirement already satisfied: sphinxcontrib-htmlhelp>=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.0.0)\nRequirement already satisfied: docutils<0.19,>=0.14 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (0.18.1)\nRequirement already satisfied: sphinxcontrib-applehelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.2)\nRequirement already satisfied: sphinxcontrib-serializinghtml>=1.1.5 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.1.5)\nRequirement already satisfied: imagesize in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.3.0)\nRequirement already satisfied: snowballstemmer>=1.1 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.2.0)\nRequirement already satisfied: babel>=1.3 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.10.1)\nRequirement already satisfied: sphinxcontrib-devhelp in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (1.0.2)\nRequirement already satisfied: Pygments>=2.0 in ./.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (2.12.0)\nRequirement already satisfied: alabaster<0.8,>=0.7 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from Sphinx>=1.5->inmanta-sphinx==1.5.0) (0.7.12)\nRequirement already satisfied: pytz>=2015.7 in ./.env/lib/python3.9/site-packages (from babel>=1.3->Sphinx>=1.5->inmanta-sphinx==1.5.0) (2022.1)\nRequirement already satisfied: chardet>=3.0.2 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (4.0.0)\nRequirement already satisfied: pycparser in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (1.26.9)\nRequirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2022.5.18.1)\nRequirement already satisfied: charset-normalizer~=2.0.0 in /home/andras/git-repos/inmanta-core/.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter~=1.0->inmanta-core==7.0.0.dev0) (2.0.12)\n\n	0	880884bd-f25b-4578-a530-5b553e7de1dc
c55760db-414f-4bdc-b534-445db48517b7	2022-05-30 11:05:03.378715+02	2022-05-30 11:05:05.289525+02	/tmp/tmpv_i_r8jp/server/environments/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/.env/bin/python -m inmanta.app -vvv export -X -e 527be28f-0f16-40b6-bb6d-8cc03b1bbca9 --server_address localhost --server_port 35269 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpez4ts15_	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.005615 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000126 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003146)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002077)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000074)\ninmanta.execute.schedulerINFO    Total compilation time 0.005382\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:35269/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:35269/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:35269/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:35269/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:35269/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	880884bd-f25b-4578-a530-5b553e7de1dc
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-05-30 11:04:45.729705+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-05-30 11:04:46.778703+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-05-30 11:05:05.195478+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-05-30 11:05:05.474639+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
b5e72707-ebd1-4378-89f4-848bdd60fe43	store	2022-05-30 11:04:40.546305+02	2022-05-30 11:04:42.268286+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-05-30T11:04:42.268307+02:00\\"}"}	\N	\N	\N	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
f3811f24-0eb5-44dd-9af5-0a586ff5e13f	pull	2022-05-30 11:04:44.037533+02	2022-05-30 11:04:44.902594+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-05-30T11:04:44.902614+02:00\\"}"}	\N	\N	\N	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
68a45beb-289b-4b23-9826-07a7415f4301	deploy	2022-05-30 11:04:45.713808+02	2022-05-30 11:04:45.729705+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-05-30 11:04:44+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-05-30 11:04:44+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"d3c80473-09eb-46e3-92b7-246a4d040fcb\\"}, \\"timestamp\\": \\"2022-05-30T11:04:45.710400+02:00\\"}","{\\"msg\\": \\"Start deploy d3c80473-09eb-46e3-92b7-246a4d040fcb of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"d3c80473-09eb-46e3-92b7-246a4d040fcb\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-05-30T11:04:45.715992+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-05-30T11:04:45.716597+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-05-30T11:04:45.720213+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy d3c80473-09eb-46e3-92b7-246a4d040fcb\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"d3c80473-09eb-46e3-92b7-246a4d040fcb\\"}, \\"timestamp\\": \\"2022-05-30T11:04:45.723739+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
f6ea8148-e3cb-4b98-b1f3-570470c119ae	pull	2022-05-30 11:04:46.754188+02	2022-05-30 11:04:46.755484+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-05-30T11:04:46.755493+02:00\\"}"}	\N	\N	\N	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	1	{"std::File[localhost,path=/tmp/test],v=1"}
47701185-b191-46fa-aac2-b75dd828e12e	deploy	2022-05-30 11:04:46.770081+02	2022-05-30 11:04:46.778703+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-05-30 11:04:46+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-05-30 11:04:46+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"8f5d06a2-4d4b-4d40-b51d-ca69c72311cb\\"}, \\"timestamp\\": \\"2022-05-30T11:04:46.767182+02:00\\"}","{\\"msg\\": \\"Start deploy 8f5d06a2-4d4b-4d40-b51d-ca69c72311cb of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"8f5d06a2-4d4b-4d40-b51d-ca69c72311cb\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-05-30T11:04:46.771609+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-05-30T11:04:46.772139+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-05-30T11:04:46.772294+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 918, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpv_i_r8jp/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-05-30T11:04:46.775191+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 8f5d06a2-4d4b-4d40-b51d-ca69c72311cb\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"8f5d06a2-4d4b-4d40-b51d-ca69c72311cb\\"}, \\"timestamp\\": \\"2022-05-30T11:04:46.775506+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	1	{"std::File[localhost,path=/tmp/test],v=1"}
14ccb162-79d7-449f-bce3-0bafffffb901	store	2022-05-30 11:05:04.378357+02	2022-05-30 11:05:04.381549+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-05-30T11:05:04.381564+02:00\\"}"}	\N	\N	\N	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
fbf85a06-8db1-4f8f-8f9c-8bd060140532	pull	2022-05-30 11:05:05.193135+02	2022-05-30 11:05:05.195336+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-05-30T11:05:05.196982+02:00\\"}"}	\N	\N	\N	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2	{"std::File[localhost,path=/tmp/test],v=2"}
04243b30-2ac8-4985-9f08-0ff3a7e8b7ab	deploy	2022-05-30 11:05:05.195478+02	2022-05-30 11:05:05.195478+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-05-30T09:05:05.195478+00:00\\"}"}	deployed	\N	nochange	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
d777848d-89b7-484c-bcfb-da247aaa441b	deploy	2022-05-30 11:05:05.216382+02	2022-05-30 11:05:05.226249+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"e5b8bd47-e655-4231-bb34-428c72bfeaba\\"}, \\"timestamp\\": \\"2022-05-30T11:05:05.213285+02:00\\"}","{\\"msg\\": \\"Start deploy e5b8bd47-e655-4231-bb34-428c72bfeaba of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e5b8bd47-e655-4231-bb34-428c72bfeaba\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-05-30T11:05:05.218648+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-05-30T11:05:05.219124+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-05-30T11:05:05.222325+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 925, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpv_i_r8jp/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-05-30T11:05:05.222575+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy e5b8bd47-e655-4231-bb34-428c72bfeaba\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"e5b8bd47-e655-4231-bb34-428c72bfeaba\\"}, \\"timestamp\\": \\"2022-05-30T11:05:05.222885+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2	{"std::File[localhost,path=/tmp/test],v=2"}
fbead8ae-736d-409a-aa61-38b15162ac00	pull	2022-05-30 11:05:05.415019+02	2022-05-30 11:05:05.416833+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-05-30T11:05:05.416842+02:00\\"}"}	\N	\N	\N	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2	{"std::File[localhost,path=/tmp/test],v=2"}
b3f3132d-5efe-4f78-9cb4-ef3ffea946d9	deploy	2022-05-30 11:05:05.465401+02	2022-05-30 11:05:05.474639+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"df7fecf6-4c3b-41ac-bb3c-0b2d6efe28fa\\"}, \\"timestamp\\": \\"2022-05-30T11:05:05.460653+02:00\\"}","{\\"msg\\": \\"Start deploy df7fecf6-4c3b-41ac-bb3c-0b2d6efe28fa of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"df7fecf6-4c3b-41ac-bb3c-0b2d6efe28fa\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-05-30T11:05:05.467683+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-05-30T11:05:05.468298+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"andras\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-05-30T11:05:05.470696+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 925, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpv_i_r8jp/527be28f-0f16-40b6-bb6d-8cc03b1bbca9/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/andras/git-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-05-30T11:05:05.470974+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy df7fecf6-4c3b-41ac-bb3c-0b2d6efe28fa\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"df7fecf6-4c3b-41ac-bb3c-0b2d6efe28fa\\"}, \\"timestamp\\": \\"2022-05-30T11:05:05.471293+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	527be28f-0f16-40b6-bb6d-8cc03b1bbca9	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250}
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

