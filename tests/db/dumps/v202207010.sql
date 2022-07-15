--
-- PostgreSQL database dump
--

-- Dumped from database version 13.6 (Ubuntu 13.6-0ubuntu0.21.10.1)
-- Dumped by pg_dump version 14.3 (Ubuntu 14.3-0ubuntu0.22.04.1)

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
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	internal	2022-07-01 17:14:05.125897+02	f	b614c668-9e80-4476-b765-e32322da594c	\N
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	localhost	2022-07-01 17:14:07.353187+02	f	a1275d75-d6af-4713-b946-87cb9dbe3563	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
b614c668-9e80-4476-b765-e32322da594c	723dfaea-f950-11ec-8101-5512854ecdf6	internal	\N	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22
a1275d75-d6af-4713-b946-87cb9dbe3563	723dfaea-f950-11ec-8101-5512854ecdf6	localhost	\N	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
florent-Latitude-5421	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2022-07-01 17:14:05.125897+02	2022-07-01 17:14:18.510571+02	\N	723dfaea-f950-11ec-8101-5512854ecdf6
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::Service	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::File	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::Directory	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::Package	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::Symlink	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::AgentConfig	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::Service	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::File	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::Directory	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::Package	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::Symlink	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	std::AgentConfig	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
99982183-dc94-4f08-9f60-c858fdaf3f6b	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2022-07-01 17:13:50.444331+02	2022-07-01 17:14:05.231503+02	2022-07-01 17:13:50.440801+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	ebc42c0c-f519-4e83-8218-140d15d93aef	t	\N	{"errors": []}
af71f483-61ed-42ee-93ff-eed3786feab9	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2022-07-01 17:14:07.985078+02	2022-07-01 17:14:18.420052+02	2022-07-01 17:14:07.981602+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	59b5faee-60de-4f46-a5b6-741932b62ce7	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2022-07-01 17:14:02.940933+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}
2	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2022-07-01 17:14:18.334816+02	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}
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
0ae5515e-3953-4a7f-9591-c0615fb35c25	dev-2	4fe68c78-f8e0-464a-b51f-781ead502bff			{"auto_full_compile": ""}	0	f		
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	dev-1	4fe68c78-f8e0-464a-b51f-781ead502bff			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
4fe68c78-f8e0-464a-b51f-781ead502bff	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
58ef3814-0d6b-4779-bd1b-d05539ac0715	2022-07-01 17:13:50.444669+02	2022-07-01 17:13:50.445663+02		Init		Using extra environment variables during compile \n	0	99982183-dc94-4f08-9f60-c858fdaf3f6b
a9bfd75f-c8f5-41ef-a9c7-e65e66796439	2022-07-01 17:13:50.445932+02	2022-07-01 17:13:50.452117+02		Creating venv			0	99982183-dc94-4f08-9f60-c858fdaf3f6b
c7f882d8-7360-4f70-9782-16f71abc5679	2022-07-01 17:14:02.003705+02	2022-07-01 17:14:05.229967+02	/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env/bin/python -m inmanta.app -vvv export -X -e 8e64f8fb-68bb-46b2-b0ae-6dee0a300b22 --server_address localhost --server_port 60931 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpk5ia5s_h	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003310 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000088 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.024150)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001256)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000056)\ninmanta.execute.schedulerINFO    Total compilation time 0.025515\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:60931/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:60931/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:60931/api/v1/file/63ae135b9a2eb874b3aa81fe5bd84283ef3617c9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:60931/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:60931/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:60931/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:60931/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:60931/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	99982183-dc94-4f08-9f60-c858fdaf3f6b
a2c9dba6-eacc-4e4e-b2ab-c80f9c2d2b02	2022-07-01 17:14:07.985416+02	2022-07-01 17:14:07.986079+02		Init		Using extra environment variables during compile \n	0	af71f483-61ed-42ee-93ff-eed3786feab9
9ba39a31-a4d8-4e05-8c35-6131dc93f42a	2022-07-01 17:14:07.990697+02	2022-07-01 17:14:17.428706+02	/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000078 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           INFO    Checking out 3.1.3 on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-r', '/tmp/tmp98z7cw4q', 'inmanta-core==7.0.0.dev0']: Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\nIgnoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmp98z7cw4q (line 1)) (3.1.2)\nRequirement already satisfied: pydantic~=1.9 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmp98z7cw4q (line 2)) (1.9.1)\nRequirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmp98z7cw4q (line 3)) (1.2.1)\nRequirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.1.1)\nRequirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.23.0)\nRequirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.12.0)\nRequirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.2)\nRequirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nRequirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.10.2)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from Jinja2~=3.1->-r /tmp/tmp98z7cw4q (line 1)) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmp98z7cw4q (line 2)) (4.2.0)\nRequirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp98z7cw4q (line 3)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp98z7cw4q (line 3)) (3.3)\nRequirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (2.0.1)\nRequirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.28.1)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: cffi>=1.12 in ./.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.1)\nRequirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.0)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in ./.env/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: six in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.0.dev0) (0.4.3)\nRequirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (5.0.0)\nRequirement already satisfied: pycparser in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2022.6.15)\nRequirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.1.0)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.26.9)\n\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000041 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           INFO    Checking out 3.1.3 on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-r', '/tmp/tmpp23wjf6j', 'inmanta-core==7.0.0.dev0']: Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\nIgnoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmpp23wjf6j (line 1)) (3.1.2)\nRequirement already satisfied: pydantic~=1.9 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmpp23wjf6j (line 2)) (1.9.1)\nRequirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmpp23wjf6j (line 3)) (1.2.1)\nRequirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.1.1)\nRequirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.23.0)\nRequirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.12.0)\nRequirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.2)\nRequirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nRequirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.10.2)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from Jinja2~=3.1->-r /tmp/tmpp23wjf6j (line 1)) (2.1.1)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpp23wjf6j (line 2)) (4.2.0)\nRequirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpp23wjf6j (line 3)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpp23wjf6j (line 3)) (3.3)\nRequirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nRequirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (2.0.1)\nRequirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.28.1)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: cffi>=1.12 in ./.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.1)\nRequirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.0)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in ./.env/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: six in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.0.dev0) (0.4.3)\nRequirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (5.0.0)\nRequirement already satisfied: pycparser in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.1.0)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.26.9)\nRequirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2022.6.15)\n\ninmanta.module           INFO    verifying project\n	0	af71f483-61ed-42ee-93ff-eed3786feab9
e6bb857c-b3b5-45ff-ba79-39275869d0d9	2022-07-01 17:13:50.456251+02	2022-07-01 17:14:02.00283+02	/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           INFO    Checking out 3.1.3 on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           DEBUG   Parsing took 0.000079 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           INFO    Checking out 3.1.3 on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-r', '/tmp/tmpq2bx_g89', 'inmanta-core==7.0.0.dev0']: Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\nIgnoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: pydantic~=1.9 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmpq2bx_g89 (line 1)) (1.9.1)\nRequirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmpq2bx_g89 (line 3)) (1.2.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmpq2bx_g89 (line 4)) (3.1.2)\nRequirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.1.1)\nRequirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.23.0)\nRequirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.12.0)\nRequirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.2)\nRequirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nRequirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.10.2)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmpq2bx_g89 (line 1)) (4.2.0)\nRequirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpq2bx_g89 (line 3)) (3.3)\nRequirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmpq2bx_g89 (line 3)) (2.2.1)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from Jinja2~=3.1->-r /tmp/tmpq2bx_g89 (line 4)) (2.1.1)\nRequirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nRequirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (2.0.1)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.27.1)\nCollecting requests>=2.23.0\n  Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/8fe/fa2a1a1365bf5/requests-2.28.1-py3-none-any.whl (62 kB)\nRequirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.0)\nCollecting cffi>=1.12\n  Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/5d5/98b938678ebf3/cffi-1.15.1-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (441 kB)\nRequirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.0)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.8)\nCollecting pyparsing!=3.0.5,>=2.0.2\n  Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/502/6bae9a10eeaef/pyparsing-3.0.9-py3-none-any.whl (98 kB)\nRequirement already satisfied: six in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.0.dev0) (0.4.3)\nRequirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (4.0.0)\nCollecting chardet>=3.0.2\n  Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/d3e/64f022d254183/chardet-5.0.0-py3-none-any.whl (193 kB)\nRequirement already satisfied: pycparser in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.0.12)\nCollecting charset-normalizer<3,>=2\n  Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/518/9b6f22b019574/charset_normalizer-2.1.0-py3-none-any.whl (39 kB)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.26.9)\nRequirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2021.10.8)\nCollecting certifi>=2017.4.17\n  Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/fe8/6415d55e84719/certifi-2022.6.15-py3-none-any.whl (160 kB)\nInstalling collected packages: pyparsing, charset-normalizer, chardet, cffi, certifi, requests\n  Attempting uninstall: pyparsing\n    Found existing installation: pyparsing 3.0.8\n    Not uninstalling pyparsing at /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages, outside environment /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env\n    Can't uninstall 'pyparsing'. No files were found to uninstall.\n  Attempting uninstall: charset-normalizer\n    Found existing installation: charset-normalizer 2.0.12\n    Not uninstalling charset-normalizer at /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages, outside environment /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env\n    Can't uninstall 'charset-normalizer'. No files were found to uninstall.\n  Attempting uninstall: chardet\n    Found existing installation: chardet 4.0.0\n    Not uninstalling chardet at /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages, outside environment /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env\n    Can't uninstall 'chardet'. No files were found to uninstall.\n  Attempting uninstall: cffi\n    Found existing installation: cffi 1.15.0\n    Not uninstalling cffi at /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages, outside environment /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env\n    Can't uninstall 'cffi'. No files were found to uninstall.\n  Attempting uninstall: certifi\n    Found existing installation: certifi 2021.10.8\n    Not uninstalling certifi at /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages, outside environment /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env\n    Can't uninstall 'certifi'. No files were found to uninstall.\n  Attempting uninstall: requests\n    Found existing installation: requests 2.27.1\n    Not uninstalling requests at /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages, outside environment /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env\n    Can't uninstall 'requests'. No files were found to uninstall.\nSuccessfully installed certifi-2022.6.15 cffi-1.15.1 chardet-5.0.0 charset-normalizer-2.1.0 pyparsing-3.0.9 requests-2.28.1\n\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000046 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           INFO    Checking out 3.1.3 on /tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   ['/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env/bin/python', '-m', 'pip', 'install', '--upgrade', '--upgrade-strategy', 'eager', '-r', '/tmp/tmp4rnnl3ms', 'inmanta-core==7.0.0.dev0']: Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\nIgnoring dataclasses: markers 'python_version < "3.7"' don't match your environment\nRequirement already satisfied: inmanta-core==7.0.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.0.0.dev0)\nRequirement already satisfied: pydantic~=1.9 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmp4rnnl3ms (line 1)) (1.9.1)\nRequirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmp4rnnl3ms (line 3)) (1.2.1)\nRequirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from -r /tmp/tmp4rnnl3ms (line 4)) (3.1.2)\nRequirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.25.0)\nRequirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.1.1)\nRequirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.1.3)\nRequirement already satisfied: colorlog~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.6.0)\nRequirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.1.1)\nRequirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.23.0)\nRequirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (37.0.2)\nRequirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.14.1)\nRequirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.9.0)\nRequirement already satisfied: importlib_metadata~=4.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (4.12.0)\nRequirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (8.13.0)\nRequirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.11.0)\nRequirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (21.3)\nRequirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (22.1.2)\nRequirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (3.11)\nRequirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.4)\nRequirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.4.0)\nRequirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (2.8.2)\nRequirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.0)\nRequirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (1.6.4)\nRequirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (6.1)\nRequirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.7.1)\nRequirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.8.0)\nRequirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.17.21)\nRequirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from inmanta-core==7.0.0.dev0) (0.10.2)\nRequirement already satisfied: typing-extensions>=3.7.4.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from pydantic~=1.9->-r /tmp/tmp4rnnl3ms (line 1)) (4.2.0)\nRequirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp4rnnl3ms (line 3)) (2.2.1)\nRequirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from email_validator~=1.1->-r /tmp/tmp4rnnl3ms (line 3)) (3.3)\nRequirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from Jinja2~=3.1->-r /tmp/tmp4rnnl3ms (line 4)) (2.1.1)\nRequirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (2.0.1)\nRequirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.0.dev0) (0.12.0)\nRequirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (6.1.2)\nRequirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.4.4)\nRequirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (0.2.0)\nRequirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.28.1)\nRequirement already satisfied: cffi>=1.12 in ./.env/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.0.dev0) (1.15.1)\nRequirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.0.dev0) (3.8.0)\nRequirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in ./.env/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.0.dev0) (3.0.9)\nRequirement already satisfied: six in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.0.dev0) (1.16.0)\nRequirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.0.dev0) (0.2.6)\nRequirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.0.dev0) (0.4.3)\nRequirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (5.0.0)\nRequirement already satisfied: pycparser in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.0.dev0) (2.21)\nRequirement already satisfied: arrow in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.2.2)\nRequirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.3)\nRequirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/core3.9/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (1.26.9)\nRequirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2022.6.15)\nRequirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0.dev0) (2.1.0)\n\ninmanta.module           INFO    verifying project\n	0	99982183-dc94-4f08-9f60-c858fdaf3f6b
595d3a95-d30b-49fd-ab54-b828bce760dd	2022-07-01 17:14:17.429603+02	2022-07-01 17:14:18.418631+02	/tmp/tmpyj87xep8/server/environments/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/.env/bin/python -m inmanta.app -vvv export -X -e 8e64f8fb-68bb-46b2-b0ae-6dee0a300b22 --server_address localhost --server_port 60931 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpdkk1oa8n	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003239 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000072 seconds\ninmanta.parser.cache     INFO    Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.023087)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001185)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000040)\ninmanta.execute.schedulerINFO    Total compilation time 0.024363\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:60931/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:60931/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:60931/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:60931/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:60931/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	af71f483-61ed-42ee-93ff-eed3786feab9
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-07-01 17:14:06.35026+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-07-01 17:14:07.372758+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-07-01 17:14:18.346509+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-07-01 17:14:18.372302+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
547d38cd-78d1-4de0-a860-6cae1306a28e	store	2022-07-01 17:14:02.940386+02	2022-07-01 17:14:04.018965+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-07-01T17:14:04.018985+02:00\\"}"}	\N	\N	\N	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
a4a0e26d-e6dc-4d08-84c8-b2638c2bcd18	pull	2022-07-01 17:14:05.134249+02	2022-07-01 17:14:05.763746+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-07-01T17:14:05.763769+02:00\\"}"}	\N	\N	\N	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
71d75563-bc30-49e1-a791-07fbae0f62e3	deploy	2022-07-01 17:14:06.337504+02	2022-07-01 17:14:06.35026+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-07-01 17:14:05+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-07-01 17:14:05+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"dda80abe-1c3f-4267-b2cd-dc8bdf9a1640\\"}, \\"timestamp\\": \\"2022-07-01T17:14:06.334785+02:00\\"}","{\\"msg\\": \\"Start deploy dda80abe-1c3f-4267-b2cd-dc8bdf9a1640 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"dda80abe-1c3f-4267-b2cd-dc8bdf9a1640\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-07-01T17:14:06.338715+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-07-01T17:14:06.339648+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-07-01T17:14:06.342729+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy dda80abe-1c3f-4267-b2cd-dc8bdf9a1640\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"dda80abe-1c3f-4267-b2cd-dc8bdf9a1640\\"}, \\"timestamp\\": \\"2022-07-01T17:14:06.346641+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c2dfd0ec-47a2-492e-a8ae-1e02c84b8fd5	pull	2022-07-01 17:14:07.357019+02	2022-07-01 17:14:07.357714+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-07-01T17:14:07.357720+02:00\\"}"}	\N	\N	\N	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	1	{"std::File[localhost,path=/tmp/test],v=1"}
2d6730c4-ea82-449e-a262-3c8873e5fcbd	deploy	2022-07-01 17:14:07.367659+02	2022-07-01 17:14:07.372758+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-07-01 17:14:07+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-07-01 17:14:07+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"b6499202-e776-41d3-845b-0d2ed633268b\\"}, \\"timestamp\\": \\"2022-07-01T17:14:07.366119+02:00\\"}","{\\"msg\\": \\"Start deploy b6499202-e776-41d3-845b-0d2ed633268b of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"b6499202-e776-41d3-845b-0d2ed633268b\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-07-01T17:14:07.368654+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-07-01T17:14:07.369466+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-07-01T17:14:07.370644+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpyj87xep8/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-07-01T17:14:07.370982+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy b6499202-e776-41d3-845b-0d2ed633268b\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"b6499202-e776-41d3-845b-0d2ed633268b\\"}, \\"timestamp\\": \\"2022-07-01T17:14:07.371154+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	1	{"std::File[localhost,path=/tmp/test],v=1"}
4f9a9bd6-1c79-473a-8fdb-ab9e5ddd554c	store	2022-07-01 17:14:18.334653+02	2022-07-01 17:14:18.336475+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-07-01T17:14:18.336485+02:00\\"}"}	\N	\N	\N	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
321d26b3-f61e-4403-9b63-271d97650928	pull	2022-07-01 17:14:18.34498+02	2022-07-01 17:14:18.34658+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-07-01T17:14:18.347607+02:00\\"}"}	\N	\N	\N	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2	{"std::File[localhost,path=/tmp/test],v=2"}
6dae9f4c-6954-41b7-9cf6-c64f434646ba	deploy	2022-07-01 17:14:18.346509+02	2022-07-01 17:14:18.346509+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-07-01T15:14:18.346509+00:00\\"}"}	deployed	\N	nochange	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
b88ef2f7-bd2f-4897-9499-1bac57958c05	deploy	2022-07-01 17:14:18.365061+02	2022-07-01 17:14:18.372302+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"10f48e73-f107-4bc6-8eba-b28338fc1602\\"}, \\"timestamp\\": \\"2022-07-01T17:14:18.362293+02:00\\"}","{\\"msg\\": \\"Start deploy 10f48e73-f107-4bc6-8eba-b28338fc1602 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"10f48e73-f107-4bc6-8eba-b28338fc1602\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-07-01T17:14:18.366652+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-07-01T17:14:18.367274+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-07-01T17:14:18.369471+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpyj87xep8/8e64f8fb-68bb-46b2-b0ae-6dee0a300b22/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-07-01T17:14:18.369653+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 10f48e73-f107-4bc6-8eba-b28338fc1602\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"10f48e73-f107-4bc6-8eba-b28338fc1602\\"}, \\"timestamp\\": \\"2022-07-01T17:14:18.369853+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	8e64f8fb-68bb-46b2-b0ae-6dee0a300b22	2	{"std::File[localhost,path=/tmp/test],v=2"}
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

