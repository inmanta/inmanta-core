--
-- PostgreSQL database dump
--

-- Dumped from database version 14.3
-- Dumped by pg_dump version 14.3

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
194995f6-c5cb-433a-b497-73792730e283	localhost	2022-11-23 16:02:59.390588+01	f	07f242b9-457b-4bcd-b45c-c8915c460487	\N
194995f6-c5cb-433a-b497-73792730e283	internal	2022-11-23 16:03:00.845+01	f	f7a76d45-6cb5-4bf3-a25a-1483378df07f	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
f7a76d45-6cb5-4bf3-a25a-1483378df07f	eb55f688-6b3f-11ed-9960-58ce2a79a3a6	internal	\N	194995f6-c5cb-433a-b497-73792730e283
07f242b9-457b-4bcd-b45c-c8915c460487	eb55f688-6b3f-11ed-9960-58ce2a79a3a6	localhost	\N	194995f6-c5cb-433a-b497-73792730e283
72546df7-4b52-421a-bb2a-955fdc01293e	eaf90e0a-6b3f-11ed-951f-58ce2a79a3a6	internal	2022-11-23 16:03:00.845+01	194995f6-c5cb-433a-b497-73792730e283
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
sentinella	194995f6-c5cb-433a-b497-73792730e283	2022-11-23 16:02:58.78338+01	2022-11-23 16:02:58.844169+01	2022-11-23 16:03:00.845+01	eaf90e0a-6b3f-11ed-951f-58ce2a79a3a6
sentinella	194995f6-c5cb-433a-b497-73792730e283	2022-11-23 16:02:59.390588+01	2022-11-23 16:03:12.473309+01	\N	eb55f688-6b3f-11ed-9960-58ce2a79a3a6
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
194995f6-c5cb-433a-b497-73792730e283	std::Service	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::File	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::Directory	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::Package	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::Symlink	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::AgentConfig	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::Service	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::File	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::Directory	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::Package	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::Symlink	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
194995f6-c5cb-433a-b497-73792730e283	std::AgentConfig	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
3e0da969-ae2c-4231-bb57-c3af69ae6141	194995f6-c5cb-433a-b497-73792730e283	2022-11-23 16:02:37.049272+01	2022-11-23 16:02:58.91382+01	2022-11-23 16:02:37.029384+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	660efa4e-7b6d-4b2b-935d-ceef17ebb5d8	t	\N	{"errors": []}	f	{}	\N	\N	\N
65f0e4f2-ba68-46ab-99e6-347446ecf7df	194995f6-c5cb-433a-b497-73792730e283	2022-11-23 16:02:59.532516+01	2022-11-23 16:03:12.335776+01	2022-11-23 16:02:59.527666+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	a4f523bf-6366-4cc0-b044-e2caf2cebbd7	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	194995f6-c5cb-433a-b497-73792730e283	2022-11-23 16:02:58.383226+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "wouter", "hostname": "sentinella", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	194995f6-c5cb-433a-b497-73792730e283	2022-11-23 16:03:12.220554+01	t	t	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "wouter", "hostname": "sentinella", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
8425a9b3-b7cd-4dc9-8505-a370b88bbde6	dev-2	01fbcc95-7f32-4753-b5ba-9d49aeacc5d0			{"auto_full_compile": ""}	0	f		
194995f6-c5cb-433a-b497-73792730e283	dev-1	01fbcc95-7f32-4753-b5ba-9d49aeacc5d0			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
01fbcc95-7f32-4753-b5ba-9d49aeacc5d0	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
b9c0e4ba-06a7-43d7-8297-bfc68179fbb8	2022-11-23 16:02:37.050584+01	2022-11-23 16:02:37.053363+01		Init		Using extra environment variables during compile \n	0	3e0da969-ae2c-4231-bb57-c3af69ae6141
8385a408-e4bd-4c6f-82a1-769ae8ed4dff	2022-11-23 16:02:37.054088+01	2022-11-23 16:02:37.055932+01		Creating venv			0	3e0da969-ae2c-4231-bb57-c3af69ae6141
f1d79209-24d8-4340-8216-7d54cc632847	2022-11-23 16:02:37.058088+01	2022-11-23 16:02:37.439711+01	/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core inmanta-ui	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.2.0.dev0\nNot uninstalling inmanta-core at /home/wouter/projects/inmanta/src, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\nFound existing installation: inmanta-ui 3.0.2\nNot uninstalling inmanta-ui at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\nCan't uninstall 'inmanta-ui'. No files were found to uninstall.\n	0	3e0da969-ae2c-4231-bb57-c3af69ae6141
9b4365a4-445c-4df6-8b4f-8ea17a816e14	2022-11-23 16:02:37.441185+01	2022-11-23 16:02:57.648969+01	/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.0.1 on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.0.1 in /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std from https://github.com/inmanta/std.\npy.warnings              WARNING /home/wouter/projects/inmanta/src/inmanta/module.py:2194: DeprecationWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\n                                   warnings.warn(\n\ninmanta.module           DEBUG   Parsing took 0.000107 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\ninmanta.module           INFO    Checking out 4.0.1 on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\npy.warnings              WARNING /home/wouter/projects/inmanta/src/inmanta/module.py:2194: DeprecationWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\n                                   warnings.warn(\n\ninmanta.pip              DEBUG   Pip command: /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 inmanta-core==7.2.0.dev0 inmanta-ui==3.0.2\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/wouter/projects/inmanta/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-ui==3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (38.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.6.4)\ninmanta.pip              DEBUG   Collecting texttable~=1.0\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b7b/68139aa8a6339/texttable-1.6.7-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pydantic~=1.10) (4.3.0)\ninmanta.pip              DEBUG   Collecting typing-extensions>=4.1.0\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/16f/a4864408f655d/typing_extensions-4.4.0-py3-none-any.whl (26 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/003/aee64f9fd955d/python_slugify-7.0.0-py2.py3-none-any.whl (9.4 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.8.1)\ninmanta.pip              DEBUG   Collecting zipp>=0.5\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/4fc/b6f278987a660/zipp-3.10.0-py3-none-any.whl (6.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.6)\ninmanta.pip              DEBUG   Collecting ruamel.yaml.clib>=0.2.6\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/efa/08d63ef03d079/ruamel.yaml.clib-0.2.7-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_24_x86_64.whl (485 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.12)\ninmanta.pip              DEBUG   Installing collected packages: texttable, zipp, typing-extensions, ruamel.yaml.clib, python-slugify\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.6.4\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: zipp\ninmanta.pip              DEBUG   Found existing installation: zipp 3.8.1\ninmanta.pip              DEBUG   Not uninstalling zipp at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\ninmanta.pip              DEBUG   Can't uninstall 'zipp'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: typing-extensions\ninmanta.pip              DEBUG   Found existing installation: typing_extensions 4.3.0\ninmanta.pip              DEBUG   Not uninstalling typing-extensions at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\ninmanta.pip              DEBUG   Can't uninstall 'typing_extensions'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: ruamel.yaml.clib\ninmanta.pip              DEBUG   Found existing installation: ruamel.yaml.clib 0.2.6\ninmanta.pip              DEBUG   Not uninstalling ruamel-yaml-clib at /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\ninmanta.pip              DEBUG   Can't uninstall 'ruamel.yaml.clib'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   pyadr 0.19.0 requires python-slugify<7,>=6, but you have python-slugify 7.0.0 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed python-slugify-7.0.0 ruamel.yaml.clib-0.2.7 texttable-1.6.7 typing-extensions-4.4.0 zipp-3.10.0\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000045 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\ninmanta.module           INFO    Checking out 4.0.1 on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\npy.warnings              WARNING /home/wouter/projects/inmanta/src/inmanta/module.py:2194: DeprecationWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\n                                   warnings.warn(\n\ninmanta.pip              DEBUG   Pip command: /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 inmanta-core==7.2.0.dev0 inmanta-ui==3.0.2\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/wouter/projects/inmanta/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-ui==3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (38.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in ./.env/lib/python3.10/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.12)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\n	0	3e0da969-ae2c-4231-bb57-c3af69ae6141
ff28c639-f0ec-4aaf-aefd-7ee4f48a6e71	2022-11-23 16:02:57.649952+01	2022-11-23 16:02:58.912899+01	/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m inmanta.app -vvv export -X -e 194995f6-c5cb-433a-b497-73792730e283 --server_address localhost --server_port 46919 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpnvnx18oy	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\npy.warnings              WARNING /home/wouter/projects/inmanta/src/inmanta/module.py:2194: DeprecationWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\n                                   warnings.warn(\n\ninmanta.module           DEBUG   Parsing took 0.005036 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000078 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.0.1\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001698)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001392)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000186)\ninmanta.execute.schedulerINFO    Total compilation time 0.003418\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46919/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46919/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46919/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46919/api/v1/file/5309d4b5db445e9c423dc60125f5b50b2926239e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46919/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46919/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46919/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46919/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	3e0da969-ae2c-4231-bb57-c3af69ae6141
56ff05e6-fd6c-45dc-b6ee-d70c83af7251	2022-11-23 16:02:59.532945+01	2022-11-23 16:02:59.533962+01		Init		Using extra environment variables during compile \n	0	65f0e4f2-ba68-46ab-99e6-347446ecf7df
948f831d-8690-4a66-b2bb-55c70bb60d4f	2022-11-23 16:02:59.535496+01	2022-11-23 16:02:59.772359+01	/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core inmanta-ui	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.2.0.dev0\nNot uninstalling inmanta-core at /home/wouter/projects/inmanta/src, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\nFound existing installation: inmanta-ui 3.0.2\nNot uninstalling inmanta-ui at /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages, outside environment /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env\nCan't uninstall 'inmanta-ui'. No files were found to uninstall.\n	0	65f0e4f2-ba68-46ab-99e6-347446ecf7df
7fa639db-d278-4b14-b889-2215b771f352	2022-11-23 16:03:11.45209+01	2022-11-23 16:03:12.334784+01	/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m inmanta.app -vvv export -X -e 194995f6-c5cb-433a-b497-73792730e283 --server_address localhost --server_port 46919 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpi6i01c9e	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\npy.warnings              WARNING /home/wouter/projects/inmanta/src/inmanta/module.py:2194: DeprecationWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\n                                   warnings.warn(\n\ninmanta.module           DEBUG   Parsing took 0.004362 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000106 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.0.1\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001946)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001478)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000209)\ninmanta.execute.schedulerINFO    Total compilation time 0.003743\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46919/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46919/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46919/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:46919/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:46919/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	65f0e4f2-ba68-46ab-99e6-347446ecf7df
9ebb53d4-ebac-4dc7-a2c4-befc243e1229	2022-11-23 16:02:59.7732+01	2022-11-23 16:03:11.450889+01	/tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\npy.warnings              WARNING /home/wouter/projects/inmanta/src/inmanta/module.py:2194: DeprecationWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\n                                   warnings.warn(\n\ninmanta.module           DEBUG   Parsing took 0.000063 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\ninmanta.module           INFO    Checking out 4.0.1 on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\npy.warnings              WARNING /home/wouter/projects/inmanta/src/inmanta/module.py:2194: DeprecationWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\n                                   warnings.warn(\n\ninmanta.pip              DEBUG   Pip command: /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 inmanta-core==7.2.0.dev0 inmanta-ui==3.0.2\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/wouter/projects/inmanta/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-ui==3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (38.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in ./.env/lib/python3.10/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.12)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000036 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\ninmanta.module           INFO    Checking out 4.0.1 on /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/libs/std\npy.warnings              WARNING /home/wouter/projects/inmanta/src/inmanta/module.py:2194: DeprecationWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\n                                   warnings.warn(\n\ninmanta.pip              DEBUG   Pip command: /tmp/tmp200jud7m/server/environments/194995f6-c5cb-433a-b497-73792730e283/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 inmanta-core==7.2.0.dev0 inmanta-ui==3.0.2\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/wouter/projects/inmanta/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-ui==3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (3.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (38.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in ./.env/lib/python3.10/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/wouter/.virtualenvs/inmanta/lib64/python3.10/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.10/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.10/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.12)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/wouter/.virtualenvs/inmanta/lib/python3.10/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\n	0	65f0e4f2-ba68-46ab-99e6-347446ecf7df
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
194995f6-c5cb-433a-b497-73792730e283	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-11-23 16:02:59.440721+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": ["std::AgentConfig[internal,agentname=localhost],v=1"], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
194995f6-c5cb-433a-b497-73792730e283	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-11-23 16:03:00.888924+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{"std::File[localhost,path=/tmp/test],v=1"}	std::AgentConfig	localhost	deployed	\N
194995f6-c5cb-433a-b497-73792730e283	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-11-23 16:03:12.245099+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{"std::File[localhost,path=/tmp/test],v=2"}	std::AgentConfig	localhost	deployed	\N
194995f6-c5cb-433a-b497-73792730e283	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-11-23 16:03:12.271431+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": ["std::AgentConfig[internal,agentname=localhost],v=2"], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
d935f6a5-5d77-4948-8124-04143db042bd	store	2022-11-23 16:02:58.382393+01	2022-11-23 16:02:58.3922+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-11-23T16:02:58.392219+01:00\\"}"}	\N	\N	\N	194995f6-c5cb-433a-b497-73792730e283	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
2f381fbd-be78-4ac5-9a6a-5b45f1e180bc	pull	2022-11-23 16:02:58.792945+01	2022-11-23 16:02:58.796876+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-11-23T16:02:58.796885+01:00\\"}"}	\N	\N	\N	194995f6-c5cb-433a-b497-73792730e283	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1192a5f3-8cac-4a1d-9c64-ae47d291e5e7	deploy	2022-11-23 16:02:58.826956+01	2022-11-23 16:02:58.843488+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-11-23 16:02:58+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-11-23 16:02:58+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"6e7b5427-d5dc-489e-a82e-8baabec5b479\\"}, \\"timestamp\\": \\"2022-11-23T16:02:58.823269+01:00\\"}","{\\"msg\\": \\"Start deploy 6e7b5427-d5dc-489e-a82e-8baabec5b479 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"6e7b5427-d5dc-489e-a82e-8baabec5b479\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-11-23T16:02:58.829203+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-11-23T16:02:58.829847+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-11-23T16:02:58.833809+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 6e7b5427-d5dc-489e-a82e-8baabec5b479\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"6e7b5427-d5dc-489e-a82e-8baabec5b479\\"}, \\"timestamp\\": \\"2022-11-23T16:02:58.837255+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	194995f6-c5cb-433a-b497-73792730e283	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
20fbb8f2-d65d-4ece-b8c5-1ded04eca2a6	pull	2022-11-23 16:02:59.397818+01	2022-11-23 16:02:59.40133+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-11-23T16:02:59.401339+01:00\\"}"}	\N	\N	\N	194995f6-c5cb-433a-b497-73792730e283	1	{"std::File[localhost,path=/tmp/test],v=1"}
367c7ee2-c229-45b4-99a4-c634831ac643	deploy	2022-11-23 16:02:59.431178+01	2022-11-23 16:02:59.440721+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-11-23 16:02:59+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-11-23 16:02:59+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"497ae717-ca7f-4db8-9a87-d6de2fbf5474\\"}, \\"timestamp\\": \\"2022-11-23T16:02:59.428842+01:00\\"}","{\\"msg\\": \\"Start deploy 497ae717-ca7f-4db8-9a87-d6de2fbf5474 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"497ae717-ca7f-4db8-9a87-d6de2fbf5474\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-11-23T16:02:59.434927+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-11-23T16:02:59.435548+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"wouter\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"wouter\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-11-23T16:02:59.437663+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp200jud7m/194995f6-c5cb-433a-b497-73792730e283/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-11-23T16:02:59.438080+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 497ae717-ca7f-4db8-9a87-d6de2fbf5474\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"497ae717-ca7f-4db8-9a87-d6de2fbf5474\\"}, \\"timestamp\\": \\"2022-11-23T16:02:59.438306+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	194995f6-c5cb-433a-b497-73792730e283	1	{"std::File[localhost,path=/tmp/test],v=1"}
dd9bdca2-ca3a-4835-a017-18f44c1d04d9	pull	2022-11-23 16:03:00.85161+01	2022-11-23 16:03:00.85283+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-11-23T16:03:00.852835+01:00\\"}"}	\N	\N	\N	194995f6-c5cb-433a-b497-73792730e283	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
8691c0a5-2b41-49ef-891c-2903d020f25f	deploy	2022-11-23 16:03:00.880491+01	2022-11-23 16:03:00.888924+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-11-23 16:03:00+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-11-23 16:03:00+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"57adeb43-f0fa-4d10-8e66-42a9cd1ec334\\"}, \\"timestamp\\": \\"2022-11-23T16:03:00.875564+01:00\\"}","{\\"msg\\": \\"Start deploy 57adeb43-f0fa-4d10-8e66-42a9cd1ec334 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"57adeb43-f0fa-4d10-8e66-42a9cd1ec334\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-11-23T16:03:00.882288+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-11-23T16:03:00.883040+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 57adeb43-f0fa-4d10-8e66-42a9cd1ec334\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"57adeb43-f0fa-4d10-8e66-42a9cd1ec334\\"}, \\"timestamp\\": \\"2022-11-23T16:03:00.886569+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	194995f6-c5cb-433a-b497-73792730e283	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
3aa360da-da12-4903-87fe-937347aeaf7c	store	2022-11-23 16:03:12.220425+01	2022-11-23 16:03:12.227279+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-11-23T16:03:12.227291+01:00\\"}"}	\N	\N	\N	194995f6-c5cb-433a-b497-73792730e283	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
cd79ff30-2586-4e6a-8b57-ef127d5a1721	deploy	2022-11-23 16:03:12.245099+01	2022-11-23 16:03:12.245099+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-11-23T15:03:12.245099+00:00\\"}"}	deployed	\N	nochange	194995f6-c5cb-433a-b497-73792730e283	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
59b25ea3-4a33-4b03-a0d4-5ae7c5a9d582	deploy	2022-11-23 16:03:12.264408+01	2022-11-23 16:03:12.271431+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"53ebf464-67cb-450b-8bb4-c1dc862c2a45\\"}, \\"timestamp\\": \\"2022-11-23T16:03:12.262094+01:00\\"}","{\\"msg\\": \\"Start deploy 53ebf464-67cb-450b-8bb4-c1dc862c2a45 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"53ebf464-67cb-450b-8bb4-c1dc862c2a45\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-11-23T16:03:12.266057+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-11-23T16:03:12.266379+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"wouter\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"wouter\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-11-23T16:03:12.268399+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp200jud7m/194995f6-c5cb-433a-b497-73792730e283/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/wouter/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-11-23T16:03:12.268585+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 53ebf464-67cb-450b-8bb4-c1dc862c2a45\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"53ebf464-67cb-450b-8bb4-c1dc862c2a45\\"}, \\"timestamp\\": \\"2022-11-23T16:03:12.268848+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	194995f6-c5cb-433a-b497-73792730e283	2	{"std::File[localhost,path=/tmp/test],v=2"}
da1cb294-9454-45a3-84be-d653f851dbd0	pull	2022-11-23 16:03:12.24361+01	2022-11-23 16:03:12.245019+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-11-23T16:03:12.245953+01:00\\"}"}	\N	\N	\N	194995f6-c5cb-433a-b497-73792730e283	2	{"std::File[localhost,path=/tmp/test],v=2"}
ec880549-a116-4407-954e-244827f42f6b	pull	2022-11-23 16:03:12.473632+01	2022-11-23 16:03:12.476196+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-11-23T16:03:12.476200+01:00\\"}"}	\N	\N	\N	194995f6-c5cb-433a-b497-73792730e283	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
f0f45f7a-1ee7-42dc-8a67-1d764694add0	pull	2022-11-23 16:03:12.474017+01	2022-11-23 16:03:12.475953+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-11-23T16:03:12.475960+01:00\\"}"}	\N	\N	\N	194995f6-c5cb-433a-b497-73792730e283	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
194995f6-c5cb-433a-b497-73792730e283	d935f6a5-5d77-4948-8124-04143db042bd	std::File[localhost,path=/tmp/test]	1
194995f6-c5cb-433a-b497-73792730e283	d935f6a5-5d77-4948-8124-04143db042bd	std::AgentConfig[internal,agentname=localhost]	1
194995f6-c5cb-433a-b497-73792730e283	2f381fbd-be78-4ac5-9a6a-5b45f1e180bc	std::AgentConfig[internal,agentname=localhost]	1
194995f6-c5cb-433a-b497-73792730e283	1192a5f3-8cac-4a1d-9c64-ae47d291e5e7	std::AgentConfig[internal,agentname=localhost]	1
194995f6-c5cb-433a-b497-73792730e283	20fbb8f2-d65d-4ece-b8c5-1ded04eca2a6	std::File[localhost,path=/tmp/test]	1
194995f6-c5cb-433a-b497-73792730e283	367c7ee2-c229-45b4-99a4-c634831ac643	std::File[localhost,path=/tmp/test]	1
194995f6-c5cb-433a-b497-73792730e283	dd9bdca2-ca3a-4835-a017-18f44c1d04d9	std::AgentConfig[internal,agentname=localhost]	1
194995f6-c5cb-433a-b497-73792730e283	8691c0a5-2b41-49ef-891c-2903d020f25f	std::AgentConfig[internal,agentname=localhost]	1
194995f6-c5cb-433a-b497-73792730e283	3aa360da-da12-4903-87fe-937347aeaf7c	std::File[localhost,path=/tmp/test]	2
194995f6-c5cb-433a-b497-73792730e283	3aa360da-da12-4903-87fe-937347aeaf7c	std::AgentConfig[internal,agentname=localhost]	2
194995f6-c5cb-433a-b497-73792730e283	da1cb294-9454-45a3-84be-d653f851dbd0	std::File[localhost,path=/tmp/test]	2
194995f6-c5cb-433a-b497-73792730e283	cd79ff30-2586-4e6a-8b57-ef127d5a1721	std::AgentConfig[internal,agentname=localhost]	2
194995f6-c5cb-433a-b497-73792730e283	59b25ea3-4a33-4b03-a0d4-5ae7c5a9d582	std::File[localhost,path=/tmp/test]	2
194995f6-c5cb-433a-b497-73792730e283	ec880549-a116-4407-954e-244827f42f6b	std::AgentConfig[internal,agentname=localhost]	2
194995f6-c5cb-433a-b497-73792730e283	f0f45f7a-1ee7-42dc-8a67-1d764694add0	std::File[localhost,path=/tmp/test]	2
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

