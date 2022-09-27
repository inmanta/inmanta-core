--
-- PostgreSQL database dump
--

-- Dumped from database version 13.6 (Ubuntu 13.6-0ubuntu0.21.10.1)
-- Dumped by pg_dump version 14.5 (Ubuntu 14.5-0ubuntu0.22.04.1)

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

-- SET default_table_access_method = heap;

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
    notify_failed_compile boolean DEFAULT false,
    failed_compile_message character varying DEFAULT ''::character varying
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
    status public.resourcestate,
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
329bf167-5e7f-469c-a44a-3b387b05116f	internal	2022-09-12 17:03:56.293241+02	f	e9feafb2-592c-4e83-b6d9-09c0615737ad	\N
329bf167-5e7f-469c-a44a-3b387b05116f	localhost	2022-09-12 17:03:58.556792+02	f	3dbb7f28-eec4-4904-8729-6c37b762f442	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
e9feafb2-592c-4e83-b6d9-09c0615737ad	1f80f6aa-32ac-11ed-a828-e9dfe4aa0a13	internal	\N	329bf167-5e7f-469c-a44a-3b387b05116f
3dbb7f28-eec4-4904-8729-6c37b762f442	1f80f6aa-32ac-11ed-a828-e9dfe4aa0a13	localhost	\N	329bf167-5e7f-469c-a44a-3b387b05116f
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
florent-Latitude-5421	329bf167-5e7f-469c-a44a-3b387b05116f	2022-09-12 17:03:56.293241+02	2022-09-12 17:04:12.903227+02	\N	1f80f6aa-32ac-11ed-a828-e9dfe4aa0a13
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
329bf167-5e7f-469c-a44a-3b387b05116f	std::Service	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::File	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::Directory	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::Package	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::Symlink	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::AgentConfig	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::Service	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::File	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::Directory	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::Package	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::Symlink	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
329bf167-5e7f-469c-a44a-3b387b05116f	std::AgentConfig	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message) FROM stdin;
2ed471ff-1d49-42d1-8c3c-d35697369109	329bf167-5e7f-469c-a44a-3b387b05116f	2022-09-12 17:03:41.20288+02	2022-09-12 17:03:56.449195+02	2022-09-12 17:03:41.142601+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	a443ce22-f97d-4747-aa30-5d1a3400e7b3	t	\N	{"errors": []}	f	{}	f	
5dbd7a07-1cf3-48ee-a2c7-7c195dc15a3a	329bf167-5e7f-469c-a44a-3b387b05116f	2022-09-12 17:04:00.463249+02	2022-09-12 17:04:12.817664+02	2022-09-12 17:04:00.460438+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	462013db-52e2-4821-a609-1193290cad77	t	\N	{"errors": []}	f	{}	f	
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	329bf167-5e7f-469c-a44a-3b387b05116f	2022-09-12 17:03:54.050951+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	329bf167-5e7f-469c-a44a-3b387b05116f	2022-09-12 17:04:12.099218+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
4fae85f8-8fec-49cd-8902-d01e58b03295	dev-2	fbe5a57e-f29d-481b-aeb5-f264fb0c7be6			{"auto_full_compile": ""}	0	f		
329bf167-5e7f-469c-a44a-3b387b05116f	dev-1	fbe5a57e-f29d-481b-aeb5-f264fb0c7be6			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
fbe5a57e-f29d-481b-aeb5-f264fb0c7be6	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
e5c41718-df06-4be3-b3e0-d25ac8684ae7	2022-09-12 17:03:41.203231+02	2022-09-12 17:03:41.204464+02		Init		Using extra environment variables during compile \n	0	2ed471ff-1d49-42d1-8c3c-d35697369109
3e5bcbaa-6488-4bcc-a936-5dd5593d32f7	2022-09-12 17:03:41.204878+02	2022-09-12 17:03:41.211443+02		Creating venv			0	2ed471ff-1d49-42d1-8c3c-d35697369109
3969e88d-eec2-4555-8305-5de1c133563f	2022-09-12 17:04:00.463536+02	2022-09-12 17:04:00.464188+02		Init		Using extra environment variables during compile \n	0	5dbd7a07-1cf3-48ee-a2c7-7c195dc15a3a
d0daae9b-28dc-4093-a7c8-6eb8315229a0	2022-09-12 17:03:41.215305+02	2022-09-12 17:03:41.506424+02	/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	2ed471ff-1d49-42d1-8c3c-d35697369109
282f989d-9328-4704-91af-75862408b106	2022-09-12 17:04:00.468996+02	2022-09-12 17:04:00.764+02	/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	5dbd7a07-1cf3-48ee-a2c7-7c195dc15a3a
b521b34e-3b99-48be-9d7c-0c7cdeb09ac0	2022-09-12 17:03:41.507349+02	2022-09-12 17:03:53.293965+02	/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.env              DEBUG   Cloning into '/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std'...\ninmanta.env              DEBUG   remote: Enumerating objects: 2462, done.\ninmanta.env              DEBUG   remote: Counting objects:   0% (1/641)        \rremote: Counting objects:   1% (7/641)        \rremote: Counting objects:   2% (13/641)        \rremote: Counting objects:   3% (20/641)        \rremote: Counting objects:   4% (26/641)        \rremote: Counting objects:   5% (33/641)        \rremote: Counting objects:   6% (39/641)        \rremote: Counting objects:   7% (45/641)        \rremote: Counting objects:   8% (52/641)        \rremote: Counting objects:   9% (58/641)        \rremote: Counting objects:  10% (65/641)        \rremote: Counting objects:  11% (71/641)        \rremote: Counting objects:  12% (77/641)        \rremote: Counting objects:  13% (84/641)        \rremote: Counting objects:  14% (90/641)        \rremote: Counting objects:  15% (97/641)        \rremote: Counting objects:  16% (103/641)        \rremote: Counting objects:  17% (109/641)        \rremote: Counting objects:  18% (116/641)        \rremote: Counting objects:  19% (122/641)        \rremote: Counting objects:  20% (129/641)        \rremote: Counting objects:  21% (135/641)        \rremote: Counting objects:  22% (142/641)        \rremote: Counting objects:  23% (148/641)        \rremote: Counting objects:  24% (154/641)        \rremote: Counting objects:  25% (161/641)        \rremote: Counting objects:  26% (167/641)        \rremote: Counting objects:  27% (174/641)        \rremote: Counting objects:  28% (180/641)        \rremote: Counting objects:  29% (186/641)        \rremote: Counting objects:  30% (193/641)        \rremote: Counting objects:  31% (199/641)        \rremote: Counting objects:  32% (206/641)        \rremote: Counting objects:  33% (212/641)        \rremote: Counting objects:  34% (218/641)        \rremote: Counting objects:  35% (225/641)        \rremote: Counting objects:  36% (231/641)        \rremote: Counting objects:  37% (238/641)        \rremote: Counting objects:  38% (244/641)        \rremote: Counting objects:  39% (250/641)        \rremote: Counting objects:  40% (257/641)        \rremote: Counting objects:  41% (263/641)        \rremote: Counting objects:  42% (270/641)        \rremote: Counting objects:  43% (276/641)        \rremote: Counting objects:  44% (283/641)        \rremote: Counting objects:  45% (289/641)        \rremote: Counting objects:  46% (295/641)        \rremote: Counting objects:  47% (302/641)        \rremote: Counting objects:  48% (308/641)        \rremote: Counting objects:  49% (315/641)        \rremote: Counting objects:  50% (321/641)        \rremote: Counting objects:  51% (327/641)        \rremote: Counting objects:  52% (334/641)        \rremote: Counting objects:  53% (340/641)        \rremote: Counting objects:  54% (347/641)        \rremote: Counting objects:  55% (353/641)        \rremote: Counting objects:  56% (359/641)        \rremote: Counting objects:  57% (366/641)        \rremote: Counting objects:  58% (372/641)        \rremote: Counting objects:  59% (379/641)        \rremote: Counting objects:  60% (385/641)        \rremote: Counting objects:  61% (392/641)        \rremote: Counting objects:  62% (398/641)        \rremote: Counting objects:  63% (404/641)        \rremote: Counting objects:  64% (411/641)        \rremote: Counting objects:  65% (417/641)        \rremote: Counting objects:  66% (424/641)        \rremote: Counting objects:  67% (430/641)        \rremote: Counting objects:  68% (436/641)        \rremote: Counting objects:  69% (443/641)        \rremote: Counting objects:  70% (449/641)        \rremote: Counting objects:  71% (456/641)        \rremote: Counting objects:  72% (462/641)        \rremote: Counting objects:  73% (468/641)        \rremote: Counting objects:  74% (475/641)        \rremote: Counting objects:  75% (481/641)        \rremote: Counting objects:  76% (488/641)        \rremote: Counting objects:  77% (494/641)        \rremote: Counting objects:  78% (500/641)        \rremote: Counting objects:  79% (507/641)        \rremote: Counting objects:  80% (513/641)        \rremote: Counting objects:  81% (520/641)        \rremote: Counting objects:  82% (526/641)        \rremote: Counting objects:  83% (533/641)        \rremote: Counting objects:  84% (539/641)        \rremote: Counting objects:  85% (545/641)        \rremote: Counting objects:  86% (552/641)        \rremote: Counting objects:  87% (558/641)        \rremote: Counting objects:  88% (565/641)        \rremote: Counting objects:  89% (571/641)        \rremote: Counting objects:  90% (577/641)        \rremote: Counting objects:  91% (584/641)        \rremote: Counting objects:  92% (590/641)        \rremote: Counting objects:  93% (597/641)        \rremote: Counting objects:  94% (603/641)        \rremote: Counting objects:  95% (609/641)        \rremote: Counting objects:  96% (616/641)        \rremote: Counting objects:  97% (622/641)        \rremote: Counting objects:  98% (629/641)        \rremote: Counting objects:  99% (635/641)        \rremote: Counting objects: 100% (641/641)        \rremote: Counting objects: 100% (641/641), done.\ninmanta.env              DEBUG   remote: Compressing objects:   0% (1/305)        \rremote: Compressing objects:   1% (4/305)        \rremote: Compressing objects:   2% (7/305)        \rremote: Compressing objects:   3% (10/305)        \rremote: Compressing objects:   4% (13/305)        \rremote: Compressing objects:   5% (16/305)        \rremote: Compressing objects:   6% (19/305)        \rremote: Compressing objects:   7% (22/305)        \rremote: Compressing objects:   8% (25/305)        \rremote: Compressing objects:   9% (28/305)        \rremote: Compressing objects:  10% (31/305)        \rremote: Compressing objects:  11% (34/305)        \rremote: Compressing objects:  12% (37/305)        \rremote: Compressing objects:  13% (40/305)        \rremote: Compressing objects:  14% (43/305)        \rremote: Compressing objects:  15% (46/305)        \rremote: Compressing objects:  16% (49/305)        \rremote: Compressing objects:  17% (52/305)        \rremote: Compressing objects:  18% (55/305)        \rremote: Compressing objects:  19% (58/305)        \rremote: Compressing objects:  20% (61/305)        \rremote: Compressing objects:  21% (65/305)        \rremote: Compressing objects:  22% (68/305)        \rremote: Compressing objects:  23% (71/305)        \rremote: Compressing objects:  24% (74/305)        \rremote: Compressing objects:  25% (77/305)        \rremote: Compressing objects:  26% (80/305)        \rremote: Compressing objects:  27% (83/305)        \rremote: Compressing objects:  28% (86/305)        \rremote: Compressing objects:  29% (89/305)        \rremote: Compressing objects:  30% (92/305)        \rremote: Compressing objects:  31% (95/305)        \rremote: Compressing objects:  32% (98/305)        \rremote: Compressing objects:  33% (101/305)        \rremote: Compressing objects:  34% (104/305)        \rremote: Compressing objects:  35% (107/305)        \rremote: Compressing objects:  36% (110/305)        \rremote: Compressing objects:  37% (113/305)        \rremote: Compressing objects:  38% (116/305)        \rremote: Compressing objects:  39% (119/305)        \rremote: Compressing objects:  40% (122/305)        \rremote: Compressing objects:  41% (126/305)        \rremote: Compressing objects:  42% (129/305)        \rremote: Compressing objects:  43% (132/305)        \rremote: Compressing objects:  44% (135/305)        \rremote: Compressing objects:  45% (138/305)        \rremote: Compressing objects:  46% (141/305)        \rremote: Compressing objects:  47% (144/305)        \rremote: Compressing objects:  48% (147/305)        \rremote: Compressing objects:  49% (150/305)        \rremote: Compressing objects:  50% (153/305)        \rremote: Compressing objects:  51% (156/305)        \rremote: Compressing objects:  52% (159/305)        \rremote: Compressing objects:  53% (162/305)        \rremote: Compressing objects:  54% (165/305)        \rremote: Compressing objects:  55% (168/305)        \rremote: Compressing objects:  56% (171/305)        \rremote: Compressing objects:  57% (174/305)        \rremote: Compressing objects:  58% (177/305)        \rremote: Compressing objects:  59% (180/305)        \rremote: Compressing objects:  60% (183/305)        \rremote: Compressing objects:  61% (187/305)        \rremote: Compressing objects:  62% (190/305)        \rremote: Compressing objects:  63% (193/305)        \rremote: Compressing objects:  64% (196/305)        \rremote: Compressing objects:  65% (199/305)        \rremote: Compressing objects:  66% (202/305)        \rremote: Compressing objects:  67% (205/305)        \rremote: Compressing objects:  68% (208/305)        \rremote: Compressing objects:  69% (211/305)        \rremote: Compressing objects:  70% (214/305)        \rremote: Compressing objects:  71% (217/305)        \rremote: Compressing objects:  72% (220/305)        \rremote: Compressing objects:  73% (223/305)        \rremote: Compressing objects:  74% (226/305)        \rremote: Compressing objects:  75% (229/305)        \rremote: Compressing objects:  76% (232/305)        \rremote: Compressing objects:  77% (235/305)        \rremote: Compressing objects:  78% (238/305)        \rremote: Compressing objects:  79% (241/305)        \rremote: Compressing objects:  80% (244/305)        \rremote: Compressing objects:  81% (248/305)        \rremote: Compressing objects:  82% (251/305)        \rremote: Compressing objects:  83% (254/305)        \rremote: Compressing objects:  84% (257/305)        \rremote: Compressing objects:  85% (260/305)        \rremote: Compressing objects:  86% (263/305)        \rremote: Compressing objects:  87% (266/305)        \rremote: Compressing objects:  88% (269/305)        \rremote: Compressing objects:  89% (272/305)        \rremote: Compressing objects:  90% (275/305)        \rremote: Compressing objects:  91% (278/305)        \rremote: Compressing objects:  92% (281/305)        \rremote: Compressing objects:  93% (284/305)        \rremote: Compressing objects:  94% (287/305)        \rremote: Compressing objects:  95% (290/305)        \rremote: Compressing objects:  96% (293/305)        \rremote: Compressing objects:  97% (296/305)        \rremote: Compressing objects:  98% (299/305)        \rremote: Compressing objects:  99% (302/305)        \rremote: Compressing objects: 100% (305/305)        \rremote: Compressing objects: 100% (305/305), done.\ninmanta.env              DEBUG   Receiving objects:   0% (1/2462)\rReceiving objects:   1% (25/2462)\rReceiving objects:   2% (50/2462)\rReceiving objects:   3% (74/2462)\rReceiving objects:   4% (99/2462)\rReceiving objects:   5% (124/2462)\rReceiving objects:   6% (148/2462)\rReceiving objects:   7% (173/2462)\rReceiving objects:   8% (197/2462)\rReceiving objects:   9% (222/2462)\rReceiving objects:  10% (247/2462)\rReceiving objects:  11% (271/2462)\rReceiving objects:  12% (296/2462)\rReceiving objects:  13% (321/2462)\rReceiving objects:  14% (345/2462)\rReceiving objects:  15% (370/2462)\rReceiving objects:  16% (394/2462)\rReceiving objects:  17% (419/2462)\rReceiving objects:  18% (444/2462)\rReceiving objects:  19% (468/2462)\rReceiving objects:  20% (493/2462)\rReceiving objects:  21% (518/2462)\rReceiving objects:  22% (542/2462)\rReceiving objects:  23% (567/2462)\rReceiving objects:  24% (591/2462)\rReceiving objects:  25% (616/2462)\rReceiving objects:  26% (641/2462)\rReceiving objects:  27% (665/2462)\rReceiving objects:  28% (690/2462)\rReceiving objects:  29% (714/2462)\rReceiving objects:  30% (739/2462)\rReceiving objects:  31% (764/2462)\rReceiving objects:  32% (788/2462)\rReceiving objects:  33% (813/2462)\rReceiving objects:  34% (838/2462)\rReceiving objects:  35% (862/2462)\rReceiving objects:  36% (887/2462)\rReceiving objects:  37% (911/2462)\rReceiving objects:  38% (936/2462)\rReceiving objects:  39% (961/2462)\rReceiving objects:  40% (985/2462)\rReceiving objects:  41% (1010/2462)\rReceiving objects:  42% (1035/2462)\rReceiving objects:  43% (1059/2462)\rReceiving objects:  44% (1084/2462)\rReceiving objects:  45% (1108/2462)\rReceiving objects:  46% (1133/2462)\rReceiving objects:  47% (1158/2462)\rReceiving objects:  48% (1182/2462)\rReceiving objects:  49% (1207/2462)\rReceiving objects:  50% (1231/2462)\rReceiving objects:  51% (1256/2462)\rReceiving objects:  52% (1281/2462)\rReceiving objects:  53% (1305/2462)\rReceiving objects:  54% (1330/2462)\rReceiving objects:  55% (1355/2462)\rReceiving objects:  56% (1379/2462)\rReceiving objects:  57% (1404/2462)\rReceiving objects:  58% (1428/2462)\rReceiving objects:  59% (1453/2462)\rReceiving objects:  60% (1478/2462)\rReceiving objects:  61% (1502/2462)\rReceiving objects:  62% (1527/2462)\rReceiving objects:  63% (1552/2462)\rReceiving objects:  64% (1576/2462)\rReceiving objects:  65% (1601/2462)\rReceiving objects:  66% (1625/2462)\rReceiving objects:  67% (1650/2462)\rReceiving objects:  68% (1675/2462)\rReceiving objects:  69% (1699/2462)\rReceiving objects:  70% (1724/2462)\rReceiving objects:  71% (1749/2462)\rReceiving objects:  72% (1773/2462)\rReceiving objects:  73% (1798/2462)\rReceiving objects:  74% (1822/2462)\rReceiving objects:  75% (1847/2462)\rReceiving objects:  76% (1872/2462)\rReceiving objects:  77% (1896/2462)\rReceiving objects:  78% (1921/2462)\rReceiving objects:  79% (1945/2462)\rReceiving objects:  80% (1970/2462)\rReceiving objects:  81% (1995/2462)\rReceiving objects:  82% (2019/2462)\rReceiving objects:  83% (2044/2462)\rReceiving objects:  84% (2069/2462)\rReceiving objects:  85% (2093/2462)\rReceiving objects:  86% (2118/2462)\rReceiving objects:  87% (2142/2462)\rReceiving objects:  88% (2167/2462)\rReceiving objects:  89% (2192/2462)\rReceiving objects:  90% (2216/2462)\rReceiving objects:  91% (2241/2462)\rReceiving objects:  92% (2266/2462)\rReceiving objects:  93% (2290/2462)\rReceiving objects:  94% (2315/2462)\rReceiving objects:  95% (2339/2462)\rReceiving objects:  96% (2364/2462)\rReceiving objects:  97% (2389/2462)\rremote: Total 2462 (delta 333), reused 562 (delta 292), pack-reused 1821\ninmanta.env              DEBUG   Receiving objects:  98% (2413/2462)\rReceiving objects:  99% (2438/2462)\rReceiving objects: 100% (2462/2462)\rReceiving objects: 100% (2462/2462), 499.54 KiB | 1.53 MiB/s, done.\ninmanta.env              DEBUG   Resolving deltas:   0% (0/1301)\rResolving deltas:   1% (14/1301)\rResolving deltas:   2% (27/1301)\rResolving deltas:   3% (40/1301)\rResolving deltas:   4% (53/1301)\rResolving deltas:   5% (66/1301)\rResolving deltas:   6% (79/1301)\rResolving deltas:   7% (92/1301)\rResolving deltas:   8% (105/1301)\rResolving deltas:   9% (118/1301)\rResolving deltas:  10% (131/1301)\rResolving deltas:  11% (144/1301)\rResolving deltas:  12% (157/1301)\rResolving deltas:  13% (170/1301)\rResolving deltas:  14% (183/1301)\rResolving deltas:  15% (196/1301)\rResolving deltas:  16% (209/1301)\rResolving deltas:  17% (222/1301)\rResolving deltas:  18% (235/1301)\rResolving deltas:  19% (248/1301)\rResolving deltas:  20% (261/1301)\rResolving deltas:  21% (274/1301)\rResolving deltas:  22% (287/1301)\rResolving deltas:  23% (300/1301)\rResolving deltas:  24% (313/1301)\rResolving deltas:  25% (326/1301)\rResolving deltas:  26% (339/1301)\rResolving deltas:  27% (352/1301)\rResolving deltas:  28% (365/1301)\rResolving deltas:  29% (378/1301)\rResolving deltas:  30% (391/1301)\rResolving deltas:  31% (405/1301)\rResolving deltas:  32% (417/1301)\rResolving deltas:  33% (430/1301)\rResolving deltas:  34% (443/1301)\rResolving deltas:  35% (456/1301)\rResolving deltas:  36% (469/1301)\rResolving deltas:  37% (482/1301)\rResolving deltas:  38% (495/1301)\rResolving deltas:  39% (508/1301)\rResolving deltas:  40% (521/1301)\rResolving deltas:  41% (534/1301)\rResolving deltas:  42% (548/1301)\rResolving deltas:  43% (560/1301)\rResolving deltas:  44% (573/1301)\rResolving deltas:  45% (586/1301)\rResolving deltas:  46% (599/1301)\rResolving deltas:  47% (612/1301)\rResolving deltas:  48% (625/1301)\rResolving deltas:  49% (638/1301)\rResolving deltas:  50% (651/1301)\rResolving deltas:  51% (664/1301)\rResolving deltas:  52% (678/1301)\rResolving deltas:  53% (690/1301)\rResolving deltas:  54% (703/1301)\rResolving deltas:  55% (716/1301)\rResolving deltas:  56% (729/1301)\rResolving deltas:  57% (742/1301)\rResolving deltas:  58% (755/1301)\rResolving deltas:  59% (768/1301)\rResolving deltas:  60% (781/1301)\rResolving deltas:  61% (794/1301)\rResolving deltas:  62% (807/1301)\rResolving deltas:  63% (820/1301)\rResolving deltas:  64% (833/1301)\rResolving deltas:  65% (846/1301)\rResolving deltas:  66% (859/1301)\rResolving deltas:  67% (872/1301)\rResolving deltas:  68% (885/1301)\rResolving deltas:  69% (898/1301)\rResolving deltas:  70% (911/1301)\rResolving deltas:  71% (924/1301)\rResolving deltas:  72% (937/1301)\rResolving deltas:  73% (950/1301)\rResolving deltas:  74% (963/1301)\rResolving deltas:  75% (976/1301)\rResolving deltas:  76% (989/1301)\rResolving deltas:  77% (1002/1301)\rResolving deltas:  78% (1015/1301)\rResolving deltas:  79% (1028/1301)\rResolving deltas:  80% (1041/1301)\rResolving deltas:  81% (1054/1301)\rResolving deltas:  82% (1067/1301)\rResolving deltas:  83% (1080/1301)\rResolving deltas:  84% (1093/1301)\rResolving deltas:  85% (1106/1301)\rResolving deltas:  86% (1119/1301)\rResolving deltas:  87% (1132/1301)\rResolving deltas:  88% (1145/1301)\rResolving deltas:  89% (1158/1301)\rResolving deltas:  90% (1171/1301)\rResolving deltas:  91% (1185/1301)\rResolving deltas:  92% (1197/1301)\rResolving deltas:  93% (1210/1301)\rResolving deltas:  94% (1223/1301)\rResolving deltas:  95% (1236/1301)\rResolving deltas:  96% (1249/1301)\rResolving deltas:  97% (1262/1301)\rResolving deltas:  98% (1275/1301)\rResolving deltas:  99% (1288/1301)\rResolving deltas: 100% (1301/1301)\rResolving deltas: 100% (1301/1301), done.\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 3.1.4 in /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std from https://github.com/inmanta/std.\ninmanta.module           DEBUG   Parsing took 0.000096 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.9.1)\ninmanta.env              DEBUG   Collecting pydantic~=1.9\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/6eb/843dcc411b6a2/pydantic-1.10.2-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.2 MB)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.6.0)\ninmanta.env              DEBUG   Collecting colorlog~=6.0\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0d3/3ca236784a1ba/colorlog-6.7.0-py2.py3-none-any.whl (11 kB)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Collecting arrow\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/5a4/9ab92e3b7b71d/arrow-1.2.3-py3-none-any.whl (66 kB)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.env              DEBUG   Collecting charset-normalizer<3,>=2\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/83e/9a75d1911279a/charset_normalizer-2.1.1-py3-none-any.whl (39 kB)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.env              DEBUG   Collecting certifi>=2017.4.17\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/43d/adad18a7f1687/certifi-2022.6.15.1-py3-none-any.whl (160 kB)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Collecting urllib3<1.27,>=1.21.1\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b93/0dd878d5a8afb/urllib3-1.26.12-py2.py3-none-any.whl (140 kB)\ninmanta.env              DEBUG   Installing collected packages: urllib3, pydantic, colorlog, charset-normalizer, certifi, arrow\ninmanta.env              DEBUG   Attempting uninstall: urllib3\ninmanta.env              DEBUG   Found existing installation: urllib3 1.26.11\ninmanta.env              DEBUG   Not uninstalling urllib3 at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env\ninmanta.env              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: pydantic\ninmanta.env              DEBUG   Found existing installation: pydantic 1.9.1\ninmanta.env              DEBUG   Not uninstalling pydantic at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env\ninmanta.env              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: colorlog\ninmanta.env              DEBUG   Found existing installation: colorlog 6.6.0\ninmanta.env              DEBUG   Not uninstalling colorlog at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env\ninmanta.env              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: charset-normalizer\ninmanta.env              DEBUG   Found existing installation: charset-normalizer 2.1.0\ninmanta.env              DEBUG   Not uninstalling charset-normalizer at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env\ninmanta.env              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: certifi\ninmanta.env              DEBUG   Found existing installation: certifi 2022.6.15\ninmanta.env              DEBUG   Not uninstalling certifi at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env\ninmanta.env              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: arrow\ninmanta.env              DEBUG   Found existing installation: arrow 1.2.2\ninmanta.env              DEBUG   Not uninstalling arrow at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env\ninmanta.env              DEBUG   Can't uninstall 'arrow'. No files were found to uninstall.\ninmanta.env              DEBUG   Successfully installed arrow-1.2.3 certifi-2022.6.15.1 charset-normalizer-2.1.1 colorlog-6.7.0 pydantic-1.10.2 urllib3-1.26.12\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000043 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.1)\ninmanta.module           INFO    verifying project\n	0	2ed471ff-1d49-42d1-8c3c-d35697369109
324af6b1-a262-4652-893b-8719bf20985d	2022-09-12 17:03:53.295327+02	2022-09-12 17:03:56.447742+02	/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env/bin/python -m inmanta.app -vvv export -X -e 329bf167-5e7f-469c-a44a-3b387b05116f --server_address localhost --server_port 50695 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpoh8kneyw	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003975 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000091 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001963)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001309)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000038)\ninmanta.execute.schedulerINFO    Total compilation time 0.003364\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50695/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50695/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50695/api/v1/file/63ae135b9a2eb874b3aa81fe5bd84283ef3617c9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50695/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50695/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50695/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50695/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50695/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	2ed471ff-1d49-42d1-8c3c-d35697369109
ac721724-4aef-4133-911a-6755c2dcbef3	2022-09-12 17:04:00.764978+02	2022-09-12 17:04:11.373804+02	/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000076 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.1)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000045 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.module           INFO    verifying project\n	0	5dbd7a07-1cf3-48ee-a2c7-7c195dc15a3a
1a83a5ed-20d0-46d5-b318-f211421793e8	2022-09-12 17:04:11.374866+02	2022-09-12 17:04:12.816237+02	/tmp/tmpocdi0h6w/server/environments/329bf167-5e7f-469c-a44a-3b387b05116f/.env/bin/python -m inmanta.app -vvv export -X -e 329bf167-5e7f-469c-a44a-3b387b05116f --server_address localhost --server_port 50695 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpntq4_l3w	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003794 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000088 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001945)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001235)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000040)\ninmanta.execute.schedulerINFO    Total compilation time 0.003270\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50695/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50695/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50695/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50695/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50695/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	5dbd7a07-1cf3-48ee-a2c7-7c195dc15a3a
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
329bf167-5e7f-469c-a44a-3b387b05116f	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-09-12 17:03:57.550638+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
329bf167-5e7f-469c-a44a-3b387b05116f	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-09-12 17:03:59.803559+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
329bf167-5e7f-469c-a44a-3b387b05116f	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-09-12 17:04:12.922838+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
329bf167-5e7f-469c-a44a-3b387b05116f	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-09-12 17:04:12.926121+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
b5271ab1-5de1-4491-9593-b76b7d3084a5	store	2022-09-12 17:03:54.05018+02	2022-09-12 17:03:55.224652+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-09-12T17:03:55.224689+02:00\\"}"}	\N	\N	\N	329bf167-5e7f-469c-a44a-3b387b05116f	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
ee015a06-8023-43cd-80a9-9617f076689d	pull	2022-09-12 17:03:56.301246+02	2022-09-12 17:03:56.91282+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-12T17:03:56.912854+02:00\\"}"}	\N	\N	\N	329bf167-5e7f-469c-a44a-3b387b05116f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
09d897e8-3228-4704-bcbc-0f7ea06f2bd0	deploy	2022-09-12 17:03:57.539453+02	2022-09-12 17:03:57.550638+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-09-12 17:03:56+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-09-12 17:03:56+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"340649b6-255a-49c8-9ff5-95a5288733ff\\"}, \\"timestamp\\": \\"2022-09-12T17:03:57.536308+02:00\\"}","{\\"msg\\": \\"Start deploy 340649b6-255a-49c8-9ff5-95a5288733ff of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"340649b6-255a-49c8-9ff5-95a5288733ff\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-09-12T17:03:57.541086+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-12T17:03:57.541788+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-12T17:03:57.544680+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 340649b6-255a-49c8-9ff5-95a5288733ff\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"340649b6-255a-49c8-9ff5-95a5288733ff\\"}, \\"timestamp\\": \\"2022-09-12T17:03:57.547145+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	329bf167-5e7f-469c-a44a-3b387b05116f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
a85965d9-6569-4942-8588-511275d9aa26	pull	2022-09-12 17:03:58.562544+02	2022-09-12 17:03:59.18897+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-12T17:03:59.189008+02:00\\"}"}	\N	\N	\N	329bf167-5e7f-469c-a44a-3b387b05116f	1	{"std::File[localhost,path=/tmp/test],v=1"}
867ccfab-8f59-40f4-aeef-2b144b4ad012	deploy	2022-09-12 17:03:59.796168+02	2022-09-12 17:03:59.803559+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-09-12 17:03:58+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-09-12 17:03:58+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"69af4c75-90f7-480d-a318-eee7523b71e4\\"}, \\"timestamp\\": \\"2022-09-12T17:03:59.794089+02:00\\"}","{\\"msg\\": \\"Start deploy 69af4c75-90f7-480d-a318-eee7523b71e4 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"69af4c75-90f7-480d-a318-eee7523b71e4\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-12T17:03:59.798036+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-12T17:03:59.798813+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-12T17:03:59.800815+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpocdi0h6w/329bf167-5e7f-469c-a44a-3b387b05116f/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-12T17:03:59.801392+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 69af4c75-90f7-480d-a318-eee7523b71e4\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"69af4c75-90f7-480d-a318-eee7523b71e4\\"}, \\"timestamp\\": \\"2022-09-12T17:03:59.801631+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	329bf167-5e7f-469c-a44a-3b387b05116f	1	{"std::File[localhost,path=/tmp/test],v=1"}
82732f5a-a8ec-4260-9381-20b2af01af90	store	2022-09-12 17:04:12.099052+02	2022-09-12 17:04:12.100719+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-09-12T17:04:12.100729+02:00\\"}"}	\N	\N	\N	329bf167-5e7f-469c-a44a-3b387b05116f	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
7eac5f86-63ff-4d2d-ad86-783d496cdb66	pull	2022-09-12 17:04:12.729554+02	2022-09-12 17:04:12.73105+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.732215+02:00\\"}"}	\N	\N	\N	329bf167-5e7f-469c-a44a-3b387b05116f	2	{"std::File[localhost,path=/tmp/test],v=2"}
4b77a6e3-6eb0-4b5d-abf7-131eef070b83	deploy	2022-09-12 17:04:12.730959+02	2022-09-12 17:04:12.730959+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-09-12T15:04:12.730959+00:00\\"}"}	deployed	\N	nochange	329bf167-5e7f-469c-a44a-3b387b05116f	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
914f0fdd-e9a5-4788-a89c-c9c281c35892	pull	2022-09-12 17:04:12.903124+02	2022-09-12 17:04:12.90448+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.904487+02:00\\"}"}	\N	\N	\N	329bf167-5e7f-469c-a44a-3b387b05116f	2	{"std::File[localhost,path=/tmp/test],v=2"}
8124b9ed-cc04-4610-a1f8-b8e16be74486	deploy	2022-09-12 17:04:12.744472+02	2022-09-12 17:04:12.751104+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"056ce67d-2f1d-483d-8c1a-ed776ab1d7f5\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.742395+02:00\\"}","{\\"msg\\": \\"Start deploy 056ce67d-2f1d-483d-8c1a-ed776ab1d7f5 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"056ce67d-2f1d-483d-8c1a-ed776ab1d7f5\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-12T17:04:12.745924+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-12T17:04:12.746361+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-12T17:04:12.748170+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpocdi0h6w/329bf167-5e7f-469c-a44a-3b387b05116f/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-12T17:04:12.748606+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 056ce67d-2f1d-483d-8c1a-ed776ab1d7f5\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"056ce67d-2f1d-483d-8c1a-ed776ab1d7f5\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.748948+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	329bf167-5e7f-469c-a44a-3b387b05116f	2	{"std::File[localhost,path=/tmp/test],v=2"}
1c9a8ba1-2a7a-4f02-8fca-baebde8b5162	pull	2022-09-12 17:04:12.903069+02	2022-09-12 17:04:12.904725+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.904730+02:00\\"}"}	\N	\N	\N	329bf167-5e7f-469c-a44a-3b387b05116f	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
1bc48cac-0134-41c0-b1a4-35c09d53cd54	deploy	2022-09-12 17:04:12.912862+02	2022-09-12 17:04:12.922838+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"2d61ec89-5fd0-48b5-b35c-f3765291017b\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.907025+02:00\\"}","{\\"msg\\": \\"Start deploy 2d61ec89-5fd0-48b5-b35c-f3765291017b of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"2d61ec89-5fd0-48b5-b35c-f3765291017b\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-12T17:04:12.915709+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-12T17:04:12.916511+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-12T17:04:12.919000+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpocdi0h6w/329bf167-5e7f-469c-a44a-3b387b05116f/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-12T17:04:12.919399+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 2d61ec89-5fd0-48b5-b35c-f3765291017b\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"2d61ec89-5fd0-48b5-b35c-f3765291017b\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.919715+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	329bf167-5e7f-469c-a44a-3b387b05116f	2	{"std::File[localhost,path=/tmp/test],v=2"}
a6653504-cc2e-45d3-be19-1be468269285	deploy	2022-09-12 17:04:12.919021+02	2022-09-12 17:04:12.926121+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"f432ded0-dc47-4921-80a4-32f1fcd59ceb\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.916171+02:00\\"}","{\\"msg\\": \\"Start deploy f432ded0-dc47-4921-80a4-32f1fcd59ceb of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"f432ded0-dc47-4921-80a4-32f1fcd59ceb\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-09-12T17:04:12.920709+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-12T17:04:12.921348+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy f432ded0-dc47-4921-80a4-32f1fcd59ceb\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"f432ded0-dc47-4921-80a4-32f1fcd59ceb\\"}, \\"timestamp\\": \\"2022-09-12T17:04:12.924205+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	329bf167-5e7f-469c-a44a-3b387b05116f	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
329bf167-5e7f-469c-a44a-3b387b05116f	b5271ab1-5de1-4491-9593-b76b7d3084a5	std::File[localhost,path=/tmp/test]	1
329bf167-5e7f-469c-a44a-3b387b05116f	b5271ab1-5de1-4491-9593-b76b7d3084a5	std::AgentConfig[internal,agentname=localhost]	1
329bf167-5e7f-469c-a44a-3b387b05116f	ee015a06-8023-43cd-80a9-9617f076689d	std::AgentConfig[internal,agentname=localhost]	1
329bf167-5e7f-469c-a44a-3b387b05116f	09d897e8-3228-4704-bcbc-0f7ea06f2bd0	std::AgentConfig[internal,agentname=localhost]	1
329bf167-5e7f-469c-a44a-3b387b05116f	a85965d9-6569-4942-8588-511275d9aa26	std::File[localhost,path=/tmp/test]	1
329bf167-5e7f-469c-a44a-3b387b05116f	867ccfab-8f59-40f4-aeef-2b144b4ad012	std::File[localhost,path=/tmp/test]	1
329bf167-5e7f-469c-a44a-3b387b05116f	82732f5a-a8ec-4260-9381-20b2af01af90	std::File[localhost,path=/tmp/test]	2
329bf167-5e7f-469c-a44a-3b387b05116f	82732f5a-a8ec-4260-9381-20b2af01af90	std::AgentConfig[internal,agentname=localhost]	2
329bf167-5e7f-469c-a44a-3b387b05116f	4b77a6e3-6eb0-4b5d-abf7-131eef070b83	std::AgentConfig[internal,agentname=localhost]	2
329bf167-5e7f-469c-a44a-3b387b05116f	7eac5f86-63ff-4d2d-ad86-783d496cdb66	std::File[localhost,path=/tmp/test]	2
329bf167-5e7f-469c-a44a-3b387b05116f	8124b9ed-cc04-4610-a1f8-b8e16be74486	std::File[localhost,path=/tmp/test]	2
329bf167-5e7f-469c-a44a-3b387b05116f	914f0fdd-e9a5-4788-a89c-c9c281c35892	std::File[localhost,path=/tmp/test]	2
329bf167-5e7f-469c-a44a-3b387b05116f	1c9a8ba1-2a7a-4f02-8fca-baebde8b5162	std::AgentConfig[internal,agentname=localhost]	2
329bf167-5e7f-469c-a44a-3b387b05116f	1bc48cac-0134-41c0-b1a4-35c09d53cd54	std::File[localhost,path=/tmp/test]	2
329bf167-5e7f-469c-a44a-3b387b05116f	a6653504-cc2e-45d3-be19-1be468269285	std::AgentConfig[internal,agentname=localhost]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090}
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

