--
-- PostgreSQL database dump
--

-- Dumped from database version 12.12 (Ubuntu 12.12-0ubuntu0.20.04.1)
-- Dumped by pg_dump version 12.12 (Ubuntu 12.12-0ubuntu0.20.04.1)

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
    'skipped_for_undefined'
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
    'skipped_for_undefined'
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
    compile_data jsonb,
    partial boolean DEFAULT false,
    removed_resource_sets character varying[] DEFAULT ARRAY[]::character varying[],
    notify_failed_compile boolean,
    failed_compile_message character varying,
    exporter_plugin character varying
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
    skipped_for_undeployable character varying[],
    partial_base integer
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
    status public.resourcestate DEFAULT 'available'::public.resourcestate,
    changes jsonb DEFAULT '{}'::jsonb,
    change public.change,
    environment uuid NOT NULL,
    version integer NOT NULL,
    resource_version_ids character varying[] NOT NULL
);


--
-- Name: resourceaction_resource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resourceaction_resource (
    environment uuid NOT NULL,
    resource_action_id uuid NOT NULL,
    resource_id character varying NOT NULL,
    resource_version integer NOT NULL
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
ddf522f8-d667-4055-81dc-dc7939cdf9c3	internal	2022-09-21 13:22:39.232028+02	f	cc0aa152-5f71-4440-be86-f2a1e4a59fa9	\N
ddf522f8-d667-4055-81dc-dc7939cdf9c3	localhost	2022-09-21 13:22:41.812279+02	f	e849eb84-d84b-4fae-80ba-a5f9735add8d	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
cc0aa152-5f71-4440-be86-f2a1e4a59fa9	b379f150-399f-11ed-a996-3be44c2ab5a2	internal	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3
e849eb84-d84b-4fae-80ba-a5f9735add8d	b379f150-399f-11ed-a996-3be44c2ab5a2	localhost	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2022-09-21 13:22:39.232028+02	2022-09-21 13:22:52.396428+02	\N	b379f150-399f-11ed-a996-3be44c2ab5a2
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::Service	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::File	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::Directory	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::Package	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::Symlink	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::AgentConfig	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::Service	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::File	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::Directory	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::Package	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::Symlink	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
ddf522f8-d667-4055-81dc-dc7939cdf9c3	std::AgentConfig	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
64e48d23-20c8-404f-bc7f-1c7632518fb1	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2022-09-21 13:22:17.079994+02	2022-09-21 13:22:39.376088+02	2022-09-21 13:22:16.942104+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	b41d0b4b-3478-4578-a9a4-d1826940848f	t	\N	{"errors": []}	f	{}	\N	\N	\N
8d7dc5ad-44c6-4cbd-9349-4731098a12b9	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2022-09-21 13:22:42.001744+02	2022-09-21 13:22:52.194443+02	2022-09-21 13:22:41.987152+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	4931899e-c8ed-4815-b79a-a8fd2b107456	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2022-09-21 13:22:36.587731+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2022-09-21 13:22:52.104983+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
4536de77-7954-4321-ac8e-57ae31950492	dev-2	a96bbb7e-1ba3-4fae-8b2d-252277b54ce2			{"auto_full_compile": ""}	0	f		
ddf522f8-d667-4055-81dc-dc7939cdf9c3	dev-1	a96bbb7e-1ba3-4fae-8b2d-252277b54ce2			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
a96bbb7e-1ba3-4fae-8b2d-252277b54ce2	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
ffdda48c-2cff-4336-9dc8-56df0253a8e5	2022-09-21 13:22:17.080337+02	2022-09-21 13:22:17.081465+02		Init		Using extra environment variables during compile \n	0	64e48d23-20c8-404f-bc7f-1c7632518fb1
125d2241-4992-4084-a4fb-d552d37f2a09	2022-09-21 13:22:17.081742+02	2022-09-21 13:22:17.087969+02		Creating venv			0	64e48d23-20c8-404f-bc7f-1c7632518fb1
c07cdb5f-1fc2-4821-bc35-049625757cc5	2022-09-21 13:22:17.092431+02	2022-09-21 13:22:17.436645+02	/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	64e48d23-20c8-404f-bc7f-1c7632518fb1
9066ad96-c058-4204-867b-27da99af970d	2022-09-21 13:22:17.4377+02	2022-09-21 13:22:35.715894+02	/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.env              DEBUG   Cloning into '/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std'...\ninmanta.env              DEBUG   remote: Enumerating objects: 2468, done.\ninmanta.env              DEBUG   remote: Counting objects:   0% (1/647)        \rremote: Counting objects:   1% (7/647)        \rremote: Counting objects:   2% (13/647)        \rremote: Counting objects:   3% (20/647)        \rremote: Counting objects:   4% (26/647)        \rremote: Counting objects:   5% (33/647)        \rremote: Counting objects:   6% (39/647)        \rremote: Counting objects:   7% (46/647)        \rremote: Counting objects:   8% (52/647)        \rremote: Counting objects:   9% (59/647)        \rremote: Counting objects:  10% (65/647)        \rremote: Counting objects:  11% (72/647)        \rremote: Counting objects:  12% (78/647)        \rremote: Counting objects:  13% (85/647)        \rremote: Counting objects:  14% (91/647)        \rremote: Counting objects:  15% (98/647)        \rremote: Counting objects:  16% (104/647)        \rremote: Counting objects:  17% (110/647)        \rremote: Counting objects:  18% (117/647)        \rremote: Counting objects:  19% (123/647)        \rremote: Counting objects:  20% (130/647)        \rremote: Counting objects:  21% (136/647)        \rremote: Counting objects:  22% (143/647)        \rremote: Counting objects:  23% (149/647)        \rremote: Counting objects:  24% (156/647)        \rremote: Counting objects:  25% (162/647)        \rremote: Counting objects:  26% (169/647)        \rremote: Counting objects:  27% (175/647)        \rremote: Counting objects:  28% (182/647)        \rremote: Counting objects:  29% (188/647)        \rremote: Counting objects:  30% (195/647)        \rremote: Counting objects:  31% (201/647)        \rremote: Counting objects:  32% (208/647)        \rremote: Counting objects:  33% (214/647)        \rremote: Counting objects:  34% (220/647)        \rremote: Counting objects:  35% (227/647)        \rremote: Counting objects:  36% (233/647)        \rremote: Counting objects:  37% (240/647)        \rremote: Counting objects:  38% (246/647)        \rremote: Counting objects:  39% (253/647)        \rremote: Counting objects:  40% (259/647)        \rremote: Counting objects:  41% (266/647)        \rremote: Counting objects:  42% (272/647)        \rremote: Counting objects:  43% (279/647)        \rremote: Counting objects:  44% (285/647)        \rremote: Counting objects:  45% (292/647)        \rremote: Counting objects:  46% (298/647)        \rremote: Counting objects:  47% (305/647)        \rremote: Counting objects:  48% (311/647)        \rremote: Counting objects:  49% (318/647)        \rremote: Counting objects:  50% (324/647)        \rremote: Counting objects:  51% (330/647)        \rremote: Counting objects:  52% (337/647)        \rremote: Counting objects:  53% (343/647)        \rremote: Counting objects:  54% (350/647)        \rremote: Counting objects:  55% (356/647)        \rremote: Counting objects:  56% (363/647)        \rremote: Counting objects:  57% (369/647)        \rremote: Counting objects:  58% (376/647)        \rremote: Counting objects:  59% (382/647)        \rremote: Counting objects:  60% (389/647)        \rremote: Counting objects:  61% (395/647)        \rremote: Counting objects:  62% (402/647)        \rremote: Counting objects:  63% (408/647)        \rremote: Counting objects:  64% (415/647)        \rremote: Counting objects:  65% (421/647)        \rremote: Counting objects:  66% (428/647)        \rremote: Counting objects:  67% (434/647)        \rremote: Counting objects:  68% (440/647)        \rremote: Counting objects:  69% (447/647)        \rremote: Counting objects:  70% (453/647)        \rremote: Counting objects:  71% (460/647)        \rremote: Counting objects:  72% (466/647)        \rremote: Counting objects:  73% (473/647)        \rremote: Counting objects:  74% (479/647)        \rremote: Counting objects:  75% (486/647)        \rremote: Counting objects:  76% (492/647)        \rremote: Counting objects:  77% (499/647)        \rremote: Counting objects:  78% (505/647)        \rremote: Counting objects:  79% (512/647)        \rremote: Counting objects:  80% (518/647)        \rremote: Counting objects:  81% (525/647)        \rremote: Counting objects:  82% (531/647)        \rremote: Counting objects:  83% (538/647)        \rremote: Counting objects:  84% (544/647)        \rremote: Counting objects:  85% (550/647)        \rremote: Counting objects:  86% (557/647)        \rremote: Counting objects:  87% (563/647)        \rremote: Counting objects:  88% (570/647)        \rremote: Counting objects:  89% (576/647)        \rremote: Counting objects:  90% (583/647)        \rremote: Counting objects:  91% (589/647)        \rremote: Counting objects:  92% (596/647)        \rremote: Counting objects:  93% (602/647)        \rremote: Counting objects:  94% (609/647)        \rremote: Counting objects:  95% (615/647)        \rremote: Counting objects:  96% (622/647)        \rremote: Counting objects:  97% (628/647)        \rremote: Counting objects:  98% (635/647)        \rremote: Counting objects:  99% (641/647)        \rremote: Counting objects: 100% (647/647)        \rremote: Counting objects: 100% (647/647), done.\ninmanta.env              DEBUG   remote: Compressing objects:   0% (1/311)        \rremote: Compressing objects:   1% (4/311)        \rremote: Compressing objects:   2% (7/311)        \rremote: Compressing objects:   3% (10/311)        \rremote: Compressing objects:   4% (13/311)        \rremote: Compressing objects:   5% (16/311)        \rremote: Compressing objects:   6% (19/311)        \rremote: Compressing objects:   7% (22/311)        \rremote: Compressing objects:   8% (25/311)        \rremote: Compressing objects:   9% (28/311)        \rremote: Compressing objects:  10% (32/311)        \rremote: Compressing objects:  11% (35/311)        \rremote: Compressing objects:  12% (38/311)        \rremote: Compressing objects:  13% (41/311)        \rremote: Compressing objects:  14% (44/311)        \rremote: Compressing objects:  15% (47/311)        \rremote: Compressing objects:  16% (50/311)        \rremote: Compressing objects:  17% (53/311)        \rremote: Compressing objects:  18% (56/311)        \rremote: Compressing objects:  19% (60/311)        \rremote: Compressing objects:  20% (63/311)        \rremote: Compressing objects:  21% (66/311)        \rremote: Compressing objects:  22% (69/311)        \rremote: Compressing objects:  23% (72/311)        \rremote: Compressing objects:  24% (75/311)        \rremote: Compressing objects:  25% (78/311)        \rremote: Compressing objects:  26% (81/311)        \rremote: Compressing objects:  27% (84/311)        \rremote: Compressing objects:  28% (88/311)        \rremote: Compressing objects:  29% (91/311)        \rremote: Compressing objects:  30% (94/311)        \rremote: Compressing objects:  31% (97/311)        \rremote: Compressing objects:  32% (100/311)        \rremote: Compressing objects:  33% (103/311)        \rremote: Compressing objects:  34% (106/311)        \rremote: Compressing objects:  35% (109/311)        \rremote: Compressing objects:  36% (112/311)        \rremote: Compressing objects:  37% (116/311)        \rremote: Compressing objects:  38% (119/311)        \rremote: Compressing objects:  39% (122/311)        \rremote: Compressing objects:  40% (125/311)        \rremote: Compressing objects:  41% (128/311)        \rremote: Compressing objects:  42% (131/311)        \rremote: Compressing objects:  43% (134/311)        \rremote: Compressing objects:  44% (137/311)        \rremote: Compressing objects:  45% (140/311)        \rremote: Compressing objects:  46% (144/311)        \rremote: Compressing objects:  47% (147/311)        \rremote: Compressing objects:  48% (150/311)        \rremote: Compressing objects:  49% (153/311)        \rremote: Compressing objects:  50% (156/311)        \rremote: Compressing objects:  51% (159/311)        \rremote: Compressing objects:  52% (162/311)        \rremote: Compressing objects:  53% (165/311)        \rremote: Compressing objects:  54% (168/311)        \rremote: Compressing objects:  55% (172/311)        \rremote: Compressing objects:  56% (175/311)        \rremote: Compressing objects:  57% (178/311)        \rremote: Compressing objects:  58% (181/311)        \rremote: Compressing objects:  59% (184/311)        \rremote: Compressing objects:  60% (187/311)        \rremote: Compressing objects:  61% (190/311)        \rremote: Compressing objects:  62% (193/311)        \rremote: Compressing objects:  63% (196/311)        \rremote: Compressing objects:  64% (200/311)        \rremote: Compressing objects:  65% (203/311)        \rremote: Compressing objects:  66% (206/311)        \rremote: Compressing objects:  67% (209/311)        \rremote: Compressing objects:  68% (212/311)        \rremote: Compressing objects:  69% (215/311)        \rremote: Compressing objects:  70% (218/311)        \rremote: Compressing objects:  71% (221/311)        \rremote: Compressing objects:  72% (224/311)        \rremote: Compressing objects:  73% (228/311)        \rremote: Compressing objects:  74% (231/311)        \rremote: Compressing objects:  75% (234/311)        \rremote: Compressing objects:  76% (237/311)        \rremote: Compressing objects:  77% (240/311)        \rremote: Compressing objects:  78% (243/311)        \rremote: Compressing objects:  79% (246/311)        \rremote: Compressing objects:  80% (249/311)        \rremote: Compressing objects:  81% (252/311)        \rremote: Compressing objects:  82% (256/311)        \rremote: Compressing objects:  83% (259/311)        \rremote: Compressing objects:  84% (262/311)        \rremote: Compressing objects:  85% (265/311)        \rremote: Compressing objects:  86% (268/311)        \rremote: Compressing objects:  87% (271/311)        \rremote: Compressing objects:  88% (274/311)        \rremote: Compressing objects:  89% (277/311)        \rremote: Compressing objects:  90% (280/311)        \rremote: Compressing objects:  91% (284/311)        \rremote: Compressing objects:  92% (287/311)        \rremote: Compressing objects:  93% (290/311)        \rremote: Compressing objects:  94% (293/311)        \rremote: Compressing objects:  95% (296/311)        \rremote: Compressing objects:  96% (299/311)        \rremote: Compressing objects:  97% (302/311)        \rremote: Compressing objects:  98% (305/311)        \rremote: Compressing objects:  99% (308/311)        \rremote: Compressing objects: 100% (311/311)        \rremote: Compressing objects: 100% (311/311), done.\ninmanta.env              DEBUG   Receiving objects:   0% (1/2468)\rReceiving objects:   1% (25/2468)\rReceiving objects:   2% (50/2468)\rReceiving objects:   3% (75/2468)\rReceiving objects:   4% (99/2468)\rReceiving objects:   5% (124/2468)\rReceiving objects:   6% (149/2468)\rReceiving objects:   7% (173/2468)\rReceiving objects:   8% (198/2468)\rReceiving objects:   9% (223/2468)\rReceiving objects:  10% (247/2468)\rReceiving objects:  11% (272/2468)\rReceiving objects:  12% (297/2468)\rReceiving objects:  13% (321/2468)\rReceiving objects:  14% (346/2468)\rReceiving objects:  15% (371/2468)\rReceiving objects:  16% (395/2468)\rReceiving objects:  17% (420/2468)\rReceiving objects:  18% (445/2468)\rReceiving objects:  19% (469/2468)\rReceiving objects:  20% (494/2468)\rReceiving objects:  21% (519/2468)\rReceiving objects:  22% (543/2468)\rReceiving objects:  23% (568/2468)\rReceiving objects:  24% (593/2468)\rReceiving objects:  25% (617/2468)\rReceiving objects:  26% (642/2468)\rReceiving objects:  27% (667/2468)\rReceiving objects:  28% (692/2468)\rReceiving objects:  29% (716/2468)\rReceiving objects:  30% (741/2468)\rReceiving objects:  31% (766/2468)\rReceiving objects:  32% (790/2468)\rReceiving objects:  33% (815/2468)\rReceiving objects:  34% (840/2468)\rReceiving objects:  35% (864/2468)\rReceiving objects:  36% (889/2468)\rReceiving objects:  37% (914/2468)\rReceiving objects:  38% (938/2468)\rReceiving objects:  39% (963/2468)\rReceiving objects:  40% (988/2468)\rReceiving objects:  41% (1012/2468)\rReceiving objects:  42% (1037/2468)\rReceiving objects:  43% (1062/2468)\rReceiving objects:  44% (1086/2468)\rReceiving objects:  45% (1111/2468)\rReceiving objects:  46% (1136/2468)\rReceiving objects:  47% (1160/2468)\rReceiving objects:  48% (1185/2468)\rReceiving objects:  49% (1210/2468)\rReceiving objects:  50% (1234/2468)\rReceiving objects:  51% (1259/2468)\rReceiving objects:  52% (1284/2468)\rReceiving objects:  53% (1309/2468)\rReceiving objects:  54% (1333/2468)\rReceiving objects:  55% (1358/2468)\rReceiving objects:  56% (1383/2468)\rReceiving objects:  57% (1407/2468)\rReceiving objects:  58% (1432/2468)\rReceiving objects:  59% (1457/2468)\rReceiving objects:  60% (1481/2468)\rReceiving objects:  61% (1506/2468)\rReceiving objects:  62% (1531/2468)\rReceiving objects:  63% (1555/2468)\rReceiving objects:  64% (1580/2468)\rReceiving objects:  65% (1605/2468)\rReceiving objects:  66% (1629/2468)\rReceiving objects:  67% (1654/2468)\rReceiving objects:  68% (1679/2468)\rReceiving objects:  69% (1703/2468)\rReceiving objects:  70% (1728/2468)\rReceiving objects:  71% (1753/2468)\rReceiving objects:  72% (1777/2468)\rReceiving objects:  73% (1802/2468)\rReceiving objects:  74% (1827/2468)\rReceiving objects:  75% (1851/2468)\rReceiving objects:  76% (1876/2468)\rReceiving objects:  77% (1901/2468)\rReceiving objects:  78% (1926/2468)\rReceiving objects:  79% (1950/2468)\rReceiving objects:  80% (1975/2468)\rReceiving objects:  81% (2000/2468)\rReceiving objects:  82% (2024/2468)\rReceiving objects:  83% (2049/2468)\rReceiving objects:  84% (2074/2468)\rReceiving objects:  85% (2098/2468)\rReceiving objects:  86% (2123/2468)\rReceiving objects:  87% (2148/2468)\rReceiving objects:  88% (2172/2468)\rReceiving objects:  89% (2197/2468)\rReceiving objects:  90% (2222/2468)\rReceiving objects:  91% (2246/2468)\rReceiving objects:  92% (2271/2468)\rReceiving objects:  93% (2296/2468)\rReceiving objects:  94% (2320/2468)\rReceiving objects:  95% (2345/2468)\rremote: Total 2468 (delta 339), reused 561 (delta 292), pack-reused 1821\ninmanta.env              DEBUG   Receiving objects:  96% (2370/2468)\rReceiving objects:  97% (2394/2468)\rReceiving objects:  98% (2419/2468)\rReceiving objects:  99% (2444/2468)\rReceiving objects: 100% (2468/2468)\rReceiving objects: 100% (2468/2468), 500.83 KiB | 10.89 MiB/s, done.\ninmanta.env              DEBUG   Resolving deltas:   0% (0/1307)\rResolving deltas:   1% (14/1307)\rResolving deltas:   2% (29/1307)\rResolving deltas:   5% (69/1307)\rResolving deltas:   6% (82/1307)\rResolving deltas:   7% (104/1307)\rResolving deltas:   9% (118/1307)\rResolving deltas:  12% (162/1307)\rResolving deltas:  14% (188/1307)\rResolving deltas:  15% (199/1307)\rResolving deltas:  17% (225/1307)\rResolving deltas:  18% (237/1307)\rResolving deltas:  19% (255/1307)\rResolving deltas:  22% (297/1307)\rResolving deltas:  23% (311/1307)\rResolving deltas:  24% (323/1307)\rResolving deltas:  31% (412/1307)\rResolving deltas:  34% (446/1307)\rResolving deltas:  39% (520/1307)\rResolving deltas:  40% (524/1307)\rResolving deltas:  41% (539/1307)\rResolving deltas:  43% (566/1307)\rResolving deltas:  44% (576/1307)\rResolving deltas:  47% (623/1307)\rResolving deltas:  48% (632/1307)\rResolving deltas:  49% (645/1307)\rResolving deltas:  50% (655/1307)\rResolving deltas:  51% (668/1307)\rResolving deltas:  52% (691/1307)\rResolving deltas:  53% (702/1307)\rResolving deltas:  54% (706/1307)\rResolving deltas:  56% (741/1307)\rResolving deltas:  58% (767/1307)\rResolving deltas:  60% (789/1307)\rResolving deltas:  61% (806/1307)\rResolving deltas:  62% (815/1307)\rResolving deltas:  63% (824/1307)\rResolving deltas:  64% (843/1307)\rResolving deltas:  65% (852/1307)\rResolving deltas:  66% (869/1307)\rResolving deltas:  67% (876/1307)\rResolving deltas:  68% (892/1307)\rResolving deltas:  69% (903/1307)\rResolving deltas:  71% (940/1307)\rResolving deltas:  75% (992/1307)\rResolving deltas:  83% (1091/1307)\rResolving deltas:  84% (1099/1307)\rResolving deltas:  86% (1137/1307)\rResolving deltas:  88% (1151/1307)\rResolving deltas:  90% (1183/1307)\rResolving deltas:  92% (1208/1307)\rResolving deltas:  93% (1217/1307)\rResolving deltas:  94% (1231/1307)\rResolving deltas:  95% (1244/1307)\rResolving deltas:  96% (1255/1307)\rResolving deltas: 100% (1307/1307)\rResolving deltas: 100% (1307/1307), done.\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 3.1.4 in /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std from https://github.com/inmanta/std.\ninmanta.module           DEBUG   Parsing took 0.000218 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (38.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.15)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib_metadata~=4.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.1)\ninmanta.env              DEBUG   Collecting pip>=21.3\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b61/a374b5bc40a6e/pip-22.2.2-py3-none-any.whl (2.0 MB)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.5.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Collecting idna>=2.0.0\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/90b/77e79eaa3eba6/idna-3.4-py3-none-any.whl (61 kB)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.12.0)\ninmanta.env              DEBUG   Collecting pep517>=0.9.1\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/4ba/4446d80aed5b5/pep517-0.13.0-py3-none-any.whl (18 kB)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Collecting arrow\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/5a4/9ab92e3b7b71d/arrow-1.2.3-py3-none-any.whl (66 kB)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.env              DEBUG   Collecting certifi>=2017.4.17\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/e23/2343de1ab72c2/certifi-2022.9.14-py3-none-any.whl (162 kB)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.env              DEBUG   Collecting charset-normalizer<3,>=2\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/83e/9a75d1911279a/charset_normalizer-2.1.1-py3-none-any.whl (39 kB)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Collecting urllib3<1.27,>=1.21.1\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b93/0dd878d5a8afb/urllib3-1.26.12-py2.py3-none-any.whl (140 kB)\ninmanta.env              DEBUG   Installing collected packages: urllib3, pip, pep517, idna, charset-normalizer, certifi, arrow\ninmanta.env              DEBUG   Attempting uninstall: urllib3\ninmanta.env              DEBUG   Found existing installation: urllib3 1.26.11\ninmanta.env              DEBUG   Not uninstalling urllib3 at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\ninmanta.env              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: pip\ninmanta.env              DEBUG   Found existing installation: pip 22.2.1\ninmanta.env              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\ninmanta.env              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: pep517\ninmanta.env              DEBUG   Found existing installation: pep517 0.12.0\ninmanta.env              DEBUG   Not uninstalling pep517 at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\ninmanta.env              DEBUG   Can't uninstall 'pep517'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: idna\ninmanta.env              DEBUG   Found existing installation: idna 3.3\ninmanta.env              DEBUG   Not uninstalling idna at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\ninmanta.env              DEBUG   Can't uninstall 'idna'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: charset-normalizer\ninmanta.env              DEBUG   Found existing installation: charset-normalizer 2.1.0\ninmanta.env              DEBUG   Not uninstalling charset-normalizer at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\ninmanta.env              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: certifi\ninmanta.env              DEBUG   Found existing installation: certifi 2022.6.15\ninmanta.env              DEBUG   Not uninstalling certifi at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\ninmanta.env              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: arrow\ninmanta.env              DEBUG   Found existing installation: arrow 1.2.2\ninmanta.env              DEBUG   Not uninstalling arrow at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\ninmanta.env              DEBUG   Can't uninstall 'arrow'. No files were found to uninstall.\ninmanta.env              DEBUG   Successfully installed arrow-1.2.3 certifi-2022.9.14 charset-normalizer-2.1.1 idna-3.4 pep517-0.13.0 pip-22.2.2 urllib3-1.26.12\ninmanta.env              DEBUG   \ninmanta.env              DEBUG   [notice] A new release of pip available: 22.2.1 -> 22.2.2\ninmanta.env              DEBUG   [notice] To update, run: /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env/bin/python -m pip install --upgrade pip\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000041 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (38.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.15)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib_metadata~=4.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.5.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.9.14)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.module           INFO    verifying project\n	0	64e48d23-20c8-404f-bc7f-1c7632518fb1
cd5a31a5-20be-452d-941c-039cdd4649a7	2022-09-21 13:22:35.717053+02	2022-09-21 13:22:39.374958+02	/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env/bin/python -m inmanta.app -vvv export -X -e ddf522f8-d667-4055-81dc-dc7939cdf9c3 --server_address localhost --server_port 46501 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpyetsn5_i	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003268 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000085 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001805)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001196)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000038)\ninmanta.execute.schedulerINFO    Total compilation time 0.003087\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46501/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46501/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46501/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46501/api/v1/file/63ae135b9a2eb874b3aa81fe5bd84283ef3617c9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46501/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46501/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46501/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46501/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	64e48d23-20c8-404f-bc7f-1c7632518fb1
6c0f7605-137a-4cba-8750-f6ecaa1efb0c	2022-09-21 13:22:42.003073+02	2022-09-21 13:22:42.006419+02		Init		Using extra environment variables during compile \n	0	8d7dc5ad-44c6-4cbd-9349-4731098a12b9
a4bddbc1-94bb-468f-94c3-1552ccaaeebe	2022-09-21 13:22:42.016654+02	2022-09-21 13:22:42.378484+02	/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	8d7dc5ad-44c6-4cbd-9349-4731098a12b9
74b53681-15dd-46fd-94b2-c938fb285bb4	2022-09-21 13:22:51.205587+02	2022-09-21 13:22:52.193154+02	/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env/bin/python -m inmanta.app -vvv export -X -e ddf522f8-d667-4055-81dc-dc7939cdf9c3 --server_address localhost --server_port 46501 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpeam3ithh	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003153 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000089 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001934)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001305)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000040)\ninmanta.execute.schedulerINFO    Total compilation time 0.003333\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46501/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46501/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46501/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46501/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46501/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	8d7dc5ad-44c6-4cbd-9349-4731098a12b9
d3293213-5ccc-4481-810a-1dfb545fb0b7	2022-09-21 13:22:42.379332+02	2022-09-21 13:22:51.204429+02	/tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000068 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (38.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.15)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib_metadata~=4.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.5.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.9.14)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000043 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp30w_vknc/server/environments/ddf522f8-d667-4055-81dc-dc7939cdf9c3/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (38.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.15)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib_metadata~=4.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.5.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.9.14)\ninmanta.module           INFO    verifying project\n	0	8d7dc5ad-44c6-4cbd-9349-4731098a12b9
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
ddf522f8-d667-4055-81dc-dc7939cdf9c3	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-09-21 13:22:40.798901+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
ddf522f8-d667-4055-81dc-dc7939cdf9c3	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-09-21 13:22:41.843495+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-09-21 13:22:52.413681+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-09-21 13:22:52.117514+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deploying	{}	std::AgentConfig	localhost	deployed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
266ba4f5-c120-43e0-ac27-5690ec158d49	store	2022-09-21 13:22:36.587119+02	2022-09-21 13:22:37.96218+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-09-21T13:22:37.962200+02:00\\"}"}	\N	\N	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
288f5128-5296-4f08-b27c-10afeaa5bdd3	pull	2022-09-21 13:22:39.23954+02	2022-09-21 13:22:40.062224+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-21T13:22:40.062243+02:00\\"}"}	\N	\N	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c0d3f94d-09d9-4cda-87db-ed6c4b207585	deploy	2022-09-21 13:22:40.787365+02	2022-09-21 13:22:40.798901+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-09-21 13:22:39+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-09-21 13:22:39+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"22ab3d74-f71b-4a19-978e-0f2c033c3821\\"}, \\"timestamp\\": \\"2022-09-21T13:22:40.784876+02:00\\"}","{\\"msg\\": \\"Start deploy 22ab3d74-f71b-4a19-978e-0f2c033c3821 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"22ab3d74-f71b-4a19-978e-0f2c033c3821\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-09-21T13:22:40.788885+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-21T13:22:40.789563+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-21T13:22:40.792290+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 22ab3d74-f71b-4a19-978e-0f2c033c3821\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"22ab3d74-f71b-4a19-978e-0f2c033c3821\\"}, \\"timestamp\\": \\"2022-09-21T13:22:40.794925+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	ddf522f8-d667-4055-81dc-dc7939cdf9c3	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
a1361b46-ea63-4b87-90f3-2fc8b3b55f65	pull	2022-09-21 13:22:41.826465+02	2022-09-21 13:22:41.829347+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-21T13:22:41.829370+02:00\\"}"}	\N	\N	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3	1	{"std::File[localhost,path=/tmp/test],v=1"}
40674fed-0d8a-48d4-b203-ec83b101cd63	deploy	2022-09-21 13:22:41.837834+02	2022-09-21 13:22:41.843495+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-09-21 13:22:41+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-09-21 13:22:41+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"5d6835bd-15e2-4588-ac96-f0af0ceeabb3\\"}, \\"timestamp\\": \\"2022-09-21T13:22:41.836189+02:00\\"}","{\\"msg\\": \\"Start deploy 5d6835bd-15e2-4588-ac96-f0af0ceeabb3 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"5d6835bd-15e2-4588-ac96-f0af0ceeabb3\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-21T13:22:41.839116+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-21T13:22:41.839624+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-21T13:22:41.841183+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp30w_vknc/ddf522f8-d667-4055-81dc-dc7939cdf9c3/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-21T13:22:41.841649+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 5d6835bd-15e2-4588-ac96-f0af0ceeabb3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"5d6835bd-15e2-4588-ac96-f0af0ceeabb3\\"}, \\"timestamp\\": \\"2022-09-21T13:22:41.841876+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	ddf522f8-d667-4055-81dc-dc7939cdf9c3	1	{"std::File[localhost,path=/tmp/test],v=1"}
c89cee21-2e0f-4280-8b45-82d97dbcbd18	store	2022-09-21 13:22:52.104824+02	2022-09-21 13:22:52.106345+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-09-21T13:22:52.106355+02:00\\"}"}	\N	\N	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
ee93e009-82a0-48c8-904d-b2d340afe73d	pull	2022-09-21 13:22:52.115922+02	2022-09-21 13:22:52.117604+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-21T13:22:52.118506+02:00\\"}"}	\N	\N	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	{"std::File[localhost,path=/tmp/test],v=2"}
5dc0f439-b111-4707-8234-96aff1849fdc	deploy	2022-09-21 13:22:52.117514+02	2022-09-21 13:22:52.117514+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-09-21T11:22:52.117514+00:00\\"}"}	deployed	\N	nochange	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
fc3eebba-d73f-485e-9aa0-e2231a66ea9c	pull	2022-09-21 13:22:52.39627+02	2022-09-21 13:22:52.399656+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-21T13:22:52.399670+02:00\\"}"}	\N	\N	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	{"std::File[localhost,path=/tmp/test],v=2"}
a556e058-d0f3-4ed2-83d1-ed5cbe8a652e	deploy	2022-09-21 13:22:52.129178+02	2022-09-21 13:22:52.135239+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"390e1ef1-5367-4dcb-b225-d11e3c88e401\\"}, \\"timestamp\\": \\"2022-09-21T13:22:52.127190+02:00\\"}","{\\"msg\\": \\"Start deploy 390e1ef1-5367-4dcb-b225-d11e3c88e401 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"390e1ef1-5367-4dcb-b225-d11e3c88e401\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-21T13:22:52.130444+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-21T13:22:52.130811+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-21T13:22:52.132568+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp30w_vknc/ddf522f8-d667-4055-81dc-dc7939cdf9c3/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-21T13:22:52.132862+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 390e1ef1-5367-4dcb-b225-d11e3c88e401\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"390e1ef1-5367-4dcb-b225-d11e3c88e401\\"}, \\"timestamp\\": \\"2022-09-21T13:22:52.133135+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	{"std::File[localhost,path=/tmp/test],v=2"}
9381c042-4684-4b99-ad71-bff8b684c12b	deploy	2022-09-21 13:22:52.405408+02	2022-09-21 13:22:52.413681+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"0c480623-a2fc-4040-b482-ed48301be9d1\\"}, \\"timestamp\\": \\"2022-09-21T13:22:52.402575+02:00\\"}","{\\"msg\\": \\"Start deploy 0c480623-a2fc-4040-b482-ed48301be9d1 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"0c480623-a2fc-4040-b482-ed48301be9d1\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-21T13:22:52.407183+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-21T13:22:52.407724+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-21T13:22:52.410034+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp30w_vknc/ddf522f8-d667-4055-81dc-dc7939cdf9c3/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-21T13:22:52.410372+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 0c480623-a2fc-4040-b482-ed48301be9d1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"0c480623-a2fc-4040-b482-ed48301be9d1\\"}, \\"timestamp\\": \\"2022-09-21T13:22:52.410713+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	{"std::File[localhost,path=/tmp/test],v=2"}
236ed14a-bff7-47ca-ac39-5063225b2633	pull	2022-09-21 13:22:52.39612+02	2022-09-21 13:22:52.400107+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-21T13:22:52.400118+02:00\\"}"}	\N	\N	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
03fa676a-5e87-4156-877a-691725092e6e	deploy	2022-09-21 13:22:53.164932+02	\N	{"{\\"msg\\": \\"Resource deploy started on agent internal, setting status to deploying\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-21T13:22:53.164942+02:00\\"}"}	deploying	\N	\N	ddf522f8-d667-4055-81dc-dc7939cdf9c3	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
ddf522f8-d667-4055-81dc-dc7939cdf9c3	266ba4f5-c120-43e0-ac27-5690ec158d49	std::File[localhost,path=/tmp/test]	1
ddf522f8-d667-4055-81dc-dc7939cdf9c3	266ba4f5-c120-43e0-ac27-5690ec158d49	std::AgentConfig[internal,agentname=localhost]	1
ddf522f8-d667-4055-81dc-dc7939cdf9c3	288f5128-5296-4f08-b27c-10afeaa5bdd3	std::AgentConfig[internal,agentname=localhost]	1
ddf522f8-d667-4055-81dc-dc7939cdf9c3	c0d3f94d-09d9-4cda-87db-ed6c4b207585	std::AgentConfig[internal,agentname=localhost]	1
ddf522f8-d667-4055-81dc-dc7939cdf9c3	a1361b46-ea63-4b87-90f3-2fc8b3b55f65	std::File[localhost,path=/tmp/test]	1
ddf522f8-d667-4055-81dc-dc7939cdf9c3	40674fed-0d8a-48d4-b203-ec83b101cd63	std::File[localhost,path=/tmp/test]	1
ddf522f8-d667-4055-81dc-dc7939cdf9c3	c89cee21-2e0f-4280-8b45-82d97dbcbd18	std::File[localhost,path=/tmp/test]	2
ddf522f8-d667-4055-81dc-dc7939cdf9c3	c89cee21-2e0f-4280-8b45-82d97dbcbd18	std::AgentConfig[internal,agentname=localhost]	2
ddf522f8-d667-4055-81dc-dc7939cdf9c3	5dc0f439-b111-4707-8234-96aff1849fdc	std::AgentConfig[internal,agentname=localhost]	2
ddf522f8-d667-4055-81dc-dc7939cdf9c3	ee93e009-82a0-48c8-904d-b2d340afe73d	std::File[localhost,path=/tmp/test]	2
ddf522f8-d667-4055-81dc-dc7939cdf9c3	a556e058-d0f3-4ed2-83d1-ed5cbe8a652e	std::File[localhost,path=/tmp/test]	2
ddf522f8-d667-4055-81dc-dc7939cdf9c3	fc3eebba-d73f-485e-9aa0-e2231a66ea9c	std::File[localhost,path=/tmp/test]	2
ddf522f8-d667-4055-81dc-dc7939cdf9c3	9381c042-4684-4b99-ad71-bff8b684c12b	std::File[localhost,path=/tmp/test]	2
ddf522f8-d667-4055-81dc-dc7939cdf9c3	236ed14a-bff7-47ca-ac39-5063225b2633	std::AgentConfig[internal,agentname=localhost]	2
ddf522f8-d667-4055-81dc-dc7939cdf9c3	03fa676a-5e87-4156-877a-691725092e6e	std::AgentConfig[internal,agentname=localhost]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160}
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
-- Name: resourceaction_resource resourceaction_resource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction_resource
    ADD CONSTRAINT resourceaction_resource_pkey PRIMARY KEY (environment, resource_id, resource_version, resource_action_id);


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

CREATE UNIQUE INDEX resource_env_resourceid_index ON public.resource USING btree (environment, resource_id, model DESC);


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
-- Name: resourceaction_resource resourceaction_resource_environment_resource_id_resource_v_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction_resource
    ADD CONSTRAINT resourceaction_resource_environment_resource_id_resource_v_fkey FOREIGN KEY (environment, resource_id, resource_version) REFERENCES public.resource(environment, resource_id, model) ON DELETE CASCADE;


--
-- Name: resourceaction_resource resourceaction_resource_resource_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction_resource
    ADD CONSTRAINT resourceaction_resource_resource_action_id_fkey FOREIGN KEY (resource_action_id) REFERENCES public.resourceaction(action_id) ON DELETE CASCADE;


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

