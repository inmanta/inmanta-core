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

--SET default_table_access_method = heap;

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
    removed_resource_sets character varying[] DEFAULT ARRAY[]::character varying[]
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
57667d1c-1bce-4c18-809a-3b1ca515bbac	internal	2022-08-05 11:49:29.211279+02	f	6f07bb29-afc9-4efc-82d8-d39d892a0035	\N
57667d1c-1bce-4c18-809a-3b1ca515bbac	localhost	2022-08-05 11:49:31.806798+02	f	3df20cd2-1262-4f67-85d0-dd8281f7fbcd	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
6f07bb29-afc9-4efc-82d8-d39d892a0035	e6263c7e-14a3-11ed-9393-50e0859859ea	internal	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac
3df20cd2-1262-4f67-85d0-dd8281f7fbcd	e6263c7e-14a3-11ed-9393-50e0859859ea	localhost	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
bedevere	57667d1c-1bce-4c18-809a-3b1ca515bbac	2022-08-05 11:49:29.211279+02	2022-08-05 11:49:43.817596+02	\N	e6263c7e-14a3-11ed-9393-50e0859859ea
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::Service	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::File	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::Directory	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::Package	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::Symlink	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::AgentConfig	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::Service	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::File	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::Directory	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::Package	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::Symlink	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
57667d1c-1bce-4c18-809a-3b1ca515bbac	std::AgentConfig	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets) FROM stdin;
c2d40749-dfd2-497f-be42-b7171694efcb	57667d1c-1bce-4c18-809a-3b1ca515bbac	2022-08-05 11:49:11.233085+02	2022-08-05 11:49:29.379354+02	2022-08-05 11:49:11.148134+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	d77a5c61-d7ed-4e8a-9fe2-9b9e90875e45	t	\N	{"errors": []}	f	{}
ce0bfdc3-164f-4595-a49a-45478d910655	57667d1c-1bce-4c18-809a-3b1ca515bbac	2022-08-05 11:49:31.997358+02	2022-08-05 11:49:43.611757+02	2022-08-05 11:49:31.980797+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	6f5cb857-65d2-4c99-be90-9e7612330ab6	t	\N	{"errors": []}	f	{}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	57667d1c-1bce-4c18-809a-3b1ca515bbac	2022-08-05 11:49:26.026093+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "bedevere", "inmanta:compile:state": "success"}}	2	{}	{}
2	57667d1c-1bce-4c18-809a-3b1ca515bbac	2022-08-05 11:49:43.49084+02	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "bedevere", "inmanta:compile:state": "success"}}	2	{}	{}
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
ad1cbd9d-f0f8-4fd1-8930-8590dc5bedc9	dev-2	ddd3675a-93d3-491b-acf3-1a4a8b6ba986			{"auto_full_compile": ""}	0	f		
57667d1c-1bce-4c18-809a-3b1ca515bbac	dev-1	ddd3675a-93d3-491b-acf3-1a4a8b6ba986			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
ddd3675a-93d3-491b-acf3-1a4a8b6ba986	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
6bc2f645-d313-4fe0-98be-bb4c8610960d	2022-08-05 11:49:11.233639+02	2022-08-05 11:49:11.235672+02		Init		Using extra environment variables during compile \n	0	c2d40749-dfd2-497f-be42-b7171694efcb
6c69bca5-b73e-480c-8ffc-1464f5af7bf5	2022-08-05 11:49:11.236091+02	2022-08-05 11:49:11.237163+02		Creating venv			0	c2d40749-dfd2-497f-be42-b7171694efcb
a751f945-f1b0-47b8-836e-7aa80e2c5f45	2022-08-05 11:49:11.24177+02	2022-08-05 11:49:24.496983+02	/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           DEBUG   Parsing took 0.000104 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', 'email_validator~=1.1', 'dataclasses~=0.7; python_version < "3.7"', 'Jinja2~=3.1', 'pydantic~=1.9', 'inmanta-core==7.0.0.dev0']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\nRequirement already satisfied: pydantic~=1.9 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.9.1)\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/sander/documents/projects/inmanta/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nCollecting asyncpg~=0.25\n  Using cached asyncpg-0.26.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.7 MB)\nRequirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.1.1)\nRequirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.23.0)\nRequirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nCollecting cryptography<38,>=36\n  Using cached cryptography-37.0.4-cp36-abi3-manylinux_2_24_x86_64.whl (4.1 MB)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.12.0)\nRequirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.2)\nCollecting pip>=21.3\n  Using cached pip-22.2.2-py3-none-any.whl (2.0 MB)\nRequirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nCollecting tornado~=6.0\n  Using cached tornado-6.2-cp37-abi3-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl (423 kB)\nRequirement already satisfied: typing_inspect~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.10.2)\nRequirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.2.0)\nCollecting typing-extensions>=3.7.4.3\n  Using cached typing_extensions-4.3.0-py3-none-any.whl (25 kB)\nRequirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (2.0.1)\nRequirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nCollecting pep517>=0.9.1\n  Using cached pep517-0.13.0-py3-none-any.whl (18 kB)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.28.0)\nCollecting requests>=2.23.0\n  Using cached requests-2.28.1-py3-none-any.whl (62 kB)\nRequirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.0)\nCollecting cffi>=1.12\n  Using cached cffi-1.15.1-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (441 kB)\nRequirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.0)\nCollecting zipp>=0.5\n  Using cached zipp-3.8.1-py3-none-any.whl (5.6 kB)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.0.dev0) (0.4.3)\nRequirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (4.0.0)\nCollecting chardet>=3.0.2\n  Using cached chardet-5.0.0-py3-none-any.whl (193 kB)\nRequirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: charset-normalizer<3,>=2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.0.12)\nCollecting charset-normalizer<3,>=2\n  Using cached charset_normalizer-2.1.0-py3-none-any.whl (39 kB)\nRequirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2022.6.15)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.26.9)\nCollecting urllib3<1.27,>=1.21.1\n  Using cached urllib3-1.26.11-py2.py3-none-any.whl (139 kB)\nInstalling collected packages: zipp, urllib3, typing-extensions, tornado, pip, pep517, charset-normalizer, chardet, cffi, asyncpg, requests, cryptography\n  Attempting uninstall: zipp\n    Found existing installation: zipp 3.8.0\n    Not uninstalling zipp at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'zipp'. No files were found to uninstall.\n  Attempting uninstall: urllib3\n    Found existing installation: urllib3 1.26.9\n    Not uninstalling urllib3 at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'urllib3'. No files were found to uninstall.\n  Attempting uninstall: typing-extensions\n    Found existing installation: typing_extensions 4.2.0\n    Not uninstalling typing-extensions at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'typing_extensions'. No files were found to uninstall.\n  Attempting uninstall: tornado\n    Found existing installation: tornado 6.1\n    Not uninstalling tornado at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'tornado'. No files were found to uninstall.\n  Attempting uninstall: pip\n    Found existing installation: pip 22.1.2\n    Not uninstalling pip at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'pip'. No files were found to uninstall.\n  Attempting uninstall: pep517\n    Found existing installation: pep517 0.12.0\n    Not uninstalling pep517 at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'pep517'. No files were found to uninstall.\n  Attempting uninstall: charset-normalizer\n    Found existing installation: charset-normalizer 2.0.12\n    Not uninstalling charset-normalizer at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'charset-normalizer'. No files were found to uninstall.\n  Attempting uninstall: chardet\n    Found existing installation: chardet 4.0.0\n    Not uninstalling chardet at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'chardet'. No files were found to uninstall.\n  Attempting uninstall: cffi\n    Found existing installation: cffi 1.15.0\n    Not uninstalling cffi at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'cffi'. No files were found to uninstall.\n  Attempting uninstall: asyncpg\n    Found existing installation: asyncpg 0.25.0\n    Not uninstalling asyncpg at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'asyncpg'. No files were found to uninstall.\n  Attempting uninstall: requests\n    Found existing installation: requests 2.28.0\n    Not uninstalling requests at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'requests'. No files were found to uninstall.\n  Attempting uninstall: cryptography\n    Found existing installation: cryptography 37.0.2\n    Not uninstalling cryptography at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env\n    Can't uninstall 'cryptography'. No files were found to uninstall.\nSuccessfully installed asyncpg-0.26.0 cffi-1.15.1 chardet-5.0.0 charset-normalizer-2.1.0 cryptography-37.0.4 pep517-0.13.0 pip-22.2.2 requests-2.28.1 tornado-6.2 typing-extensions-4.3.0 urllib3-1.26.11 zipp-3.8.1\n\n[notice] A new release of pip available: 22.1.2 -> 22.2.2\n[notice] To update, run: /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python -m pip install --upgrade pip\n\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000129 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', 'email_validator~=1.1', 'dataclasses~=0.7; python_version < "3.7"', 'Jinja2~=3.1', 'pydantic~=1.9', 'inmanta-core==7.0.0.dev0']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\nRequirement already satisfied: pydantic~=1.9 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.9.1)\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/sander/documents/projects/inmanta/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.26.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.1.1)\nRequirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.23.0)\nRequirement already satisfied: cryptography<38,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.4)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.12.0)\nRequirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.2.2)\nRequirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.2)\nRequirement already satisfied: typing_inspect~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.10.2)\nRequirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in ./.env/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\nRequirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.13.0)\nRequirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (2.0.1)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.28.1)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: cffi>=1.12 in ./.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.1)\nRequirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.1)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.0.dev0) (0.4.3)\nRequirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (5.0.0)\nRequirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2022.6.15)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.26.11)\nRequirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.1.0)\n\ninmanta.module           INFO    verifying project\n	0	c2d40749-dfd2-497f-be42-b7171694efcb
34a8a00c-6dd2-4d88-a036-963336435e9b	2022-08-05 11:49:32.010094+02	2022-08-05 11:49:41.990812+02	/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000083 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', 'dataclasses~=0.7; python_version < "3.7"', 'pydantic~=1.9', 'email_validator~=1.1', 'Jinja2~=3.1', 'inmanta-core==7.0.0.dev0']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: pydantic~=1.9 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.9.1)\nRequirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/sander/documents/projects/inmanta/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.26.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.1.1)\nRequirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.23.0)\nRequirement already satisfied: cryptography<38,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.4)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.12.0)\nRequirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.2.2)\nRequirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.2)\nRequirement already satisfied: typing_inspect~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.10.2)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in ./.env/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\nRequirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\nRequirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.13.0)\nRequirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (2.0.1)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.28.1)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: cffi>=1.12 in ./.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.1)\nRequirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.1)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.0.dev0) (0.4.3)\nRequirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (5.0.0)\nRequirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2022.6.15)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.26.11)\nRequirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.1.0)\n\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000079 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', 'dataclasses~=0.7; python_version < "3.7"', 'pydantic~=1.9', 'email_validator~=1.1', 'Jinja2~=3.1', 'inmanta-core==7.0.0.dev0']: Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: pydantic~=1.9 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.9.1)\nRequirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/sander/documents/projects/inmanta/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.26.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.1.1)\nRequirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.23.0)\nRequirement already satisfied: cryptography<38,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.4)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.12.0)\nRequirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.2.2)\nRequirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.2)\nRequirement already satisfied: typing_inspect~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.10.2)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in ./.env/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\nRequirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\nRequirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (2.0.1)\nRequirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.13.0)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.28.1)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: cffi>=1.12 in ./.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.1)\nRequirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.1)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.0.dev0) (0.4.3)\nRequirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (5.0.0)\nRequirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.26.11)\nRequirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.1.0)\nRequirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2022.6.15)\n\ninmanta.module           INFO    verifying project\n	0	ce0bfdc3-164f-4595-a49a-45478d910655
bda4547f-bd5a-43c2-b150-cbf5d817c7db	2022-08-05 11:49:31.998891+02	2022-08-05 11:49:32.00266+02		Init		Using extra environment variables during compile \n	0	ce0bfdc3-164f-4595-a49a-45478d910655
35be12ff-1810-4471-af83-66f0a0139cbf	2022-08-05 11:49:24.497988+02	2022-08-05 11:49:29.378158+02	/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python -m inmanta.app -vvv export -X -e 57667d1c-1bce-4c18-809a-3b1ca515bbac --server_address localhost --server_port 55431 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmplpugttja	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.004927 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000105 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002876)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001998)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000068)\ninmanta.execute.schedulerINFO    Total compilation time 0.005021\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55431/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55431/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55431/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55431/api/v1/file/63ae135b9a2eb874b3aa81fe5bd84283ef3617c9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55431/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55431/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55431/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55431/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	c2d40749-dfd2-497f-be42-b7171694efcb
d1c2935a-028e-40e7-85ac-ff34583c9ed3	2022-08-05 11:49:41.99176+02	2022-08-05 11:49:43.61056+02	/tmp/tmp2dgdshoy/server/environments/57667d1c-1bce-4c18-809a-3b1ca515bbac/.env/bin/python -m inmanta.app -vvv export -X -e 57667d1c-1bce-4c18-809a-3b1ca515bbac --server_address localhost --server_port 55431 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpdldlckax	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.005072 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000176 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003389)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002248)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000071)\ninmanta.execute.schedulerINFO    Total compilation time 0.005792\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55431/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55431/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55431/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55431/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55431/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	ce0bfdc3-164f-4595-a49a-45478d910655
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
57667d1c-1bce-4c18-809a-3b1ca515bbac	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-08-05 11:49:30.899902+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
57667d1c-1bce-4c18-809a-3b1ca515bbac	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-08-05 11:49:31.844208+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
57667d1c-1bce-4c18-809a-3b1ca515bbac	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-08-05 11:49:43.510122+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
57667d1c-1bce-4c18-809a-3b1ca515bbac	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-08-05 11:49:43.542537+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	deploying	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
890c4f8b-c39e-44a6-bea7-ae44e50c2806	store	2022-08-05 11:49:26.025407+02	2022-08-05 11:49:27.554672+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-08-05T11:49:27.554689+02:00\\"}"}	\N	\N	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
87ef8345-3b66-4921-9716-873b3d7c68bf	pull	2022-08-05 11:49:29.220661+02	2022-08-05 11:49:29.224075+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-08-05T11:49:29.224101+02:00\\"}"}	\N	\N	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
a1c0ddb9-59b6-4d20-88b3-c4c68275567c	deploy	2022-08-05 11:49:30.0526+02	2022-08-05 11:49:30.792183+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-08-05 11:49:29+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-08-05 11:49:29+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"34cd66dc-c6ce-40cc-9699-1b9feb67d7eb\\"}, \\"timestamp\\": \\"2022-08-05T11:49:29.247922+02:00\\"}","{\\"msg\\": \\"Start deploy 34cd66dc-c6ce-40cc-9699-1b9feb67d7eb of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"34cd66dc-c6ce-40cc-9699-1b9feb67d7eb\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-08-05T11:49:30.775716+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-05T11:49:30.776529+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-05T11:49:30.780953+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 34cd66dc-c6ce-40cc-9699-1b9feb67d7eb\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"34cd66dc-c6ce-40cc-9699-1b9feb67d7eb\\"}, \\"timestamp\\": \\"2022-08-05T11:49:30.785392+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	57667d1c-1bce-4c18-809a-3b1ca515bbac	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
21932547-cbf1-4f46-bf82-8174ce9182d3	pull	2022-08-05 11:49:29.42402+02	2022-08-05 11:49:30.180171+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-08-05T11:49:30.180185+02:00\\"}"}	\N	\N	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
194483c2-4761-484a-9090-531e203bb4cb	deploy	2022-08-05 11:49:30.890978+02	2022-08-05 11:49:30.899902+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"73616ea0-d0e1-4de4-8351-2f83b561d1f8\\"}, \\"timestamp\\": \\"2022-08-05T11:49:30.887684+02:00\\"}","{\\"msg\\": \\"Start deploy 73616ea0-d0e1-4de4-8351-2f83b561d1f8 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"73616ea0-d0e1-4de4-8351-2f83b561d1f8\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-08-05T11:49:30.892892+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-05T11:49:30.893287+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 73616ea0-d0e1-4de4-8351-2f83b561d1f8\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"73616ea0-d0e1-4de4-8351-2f83b561d1f8\\"}, \\"timestamp\\": \\"2022-08-05T11:49:30.897164+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	57667d1c-1bce-4c18-809a-3b1ca515bbac	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
bf623a9a-d672-4901-b15d-6a4f3a4a47e5	pull	2022-08-05 11:49:31.817825+02	2022-08-05 11:49:31.81908+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-08-05T11:49:31.819088+02:00\\"}"}	\N	\N	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac	1	{"std::File[localhost,path=/tmp/test],v=1"}
9755ba0b-b0b3-410a-a931-687e726ec141	deploy	2022-08-05 11:49:31.83551+02	2022-08-05 11:49:31.844208+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-08-05 11:49:31+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-08-05 11:49:31+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"35117064-6649-4a92-bfe2-a9c0f0ed4acc\\"}, \\"timestamp\\": \\"2022-08-05T11:49:31.831574+02:00\\"}","{\\"msg\\": \\"Start deploy 35117064-6649-4a92-bfe2-a9c0f0ed4acc of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"35117064-6649-4a92-bfe2-a9c0f0ed4acc\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-05T11:49:31.837792+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-05T11:49:31.838331+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-05T11:49:31.838618+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 929, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmp2dgdshoy/57667d1c-1bce-4c18-809a-3b1ca515bbac/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-05T11:49:31.841240+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 35117064-6649-4a92-bfe2-a9c0f0ed4acc\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"35117064-6649-4a92-bfe2-a9c0f0ed4acc\\"}, \\"timestamp\\": \\"2022-08-05T11:49:31.841509+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	57667d1c-1bce-4c18-809a-3b1ca515bbac	1	{"std::File[localhost,path=/tmp/test],v=1"}
364ade3a-cdea-479b-832e-55809063f4f0	store	2022-08-05 11:49:43.490566+02	2022-08-05 11:49:43.493207+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-08-05T11:49:43.493219+02:00\\"}"}	\N	\N	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
f086f43b-a7c4-4748-a5ca-f363a0869579	pull	2022-08-05 11:49:43.818168+02	2022-08-05 11:49:43.822534+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-08-05T11:49:43.822550+02:00\\"}"}	\N	\N	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac	2	{"std::File[localhost,path=/tmp/test],v=2"}
e0c1793e-77b2-4761-b5d8-da29b2fe53ac	pull	2022-08-05 11:49:43.506375+02	2022-08-05 11:49:43.510231+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-08-05T11:49:43.511536+02:00\\"}"}	\N	\N	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac	2	{"std::File[localhost,path=/tmp/test],v=2"}
9d6c00aa-91b0-429c-954c-4ac29789a936	deploy	2022-08-05 11:49:43.532934+02	2022-08-05 11:49:43.542537+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"17c56ca3-1d35-4836-ad16-e8ea7f78cefe\\"}, \\"timestamp\\": \\"2022-08-05T11:49:43.529367+02:00\\"}","{\\"msg\\": \\"Start deploy 17c56ca3-1d35-4836-ad16-e8ea7f78cefe of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"17c56ca3-1d35-4836-ad16-e8ea7f78cefe\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-05T11:49:43.534958+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-05T11:49:43.535433+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-08-05T11:49:43.538350+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp2dgdshoy/57667d1c-1bce-4c18-809a-3b1ca515bbac/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-05T11:49:43.538613+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 17c56ca3-1d35-4836-ad16-e8ea7f78cefe\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"17c56ca3-1d35-4836-ad16-e8ea7f78cefe\\"}, \\"timestamp\\": \\"2022-08-05T11:49:43.538903+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	57667d1c-1bce-4c18-809a-3b1ca515bbac	2	{"std::File[localhost,path=/tmp/test],v=2"}
6afada26-4bd3-4549-91d2-487cf74ff144	deploy	2022-08-05 11:49:43.510122+02	2022-08-05 11:49:43.510122+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-08-05T09:49:43.510122+00:00\\"}"}	deployed	\N	nochange	57667d1c-1bce-4c18-809a-3b1ca515bbac	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
5f223d0d-cd7c-4952-a362-f8dfac3ee0cd	deploy	2022-08-05 11:49:43.846808+02	\N	{"{\\"msg\\": \\"Resource deploy started on agent localhost, setting status to deploying\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-08-05T11:49:43.846839+02:00\\"}"}	deploying	\N	\N	57667d1c-1bce-4c18-809a-3b1ca515bbac	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290}
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

