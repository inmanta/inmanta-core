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
-- Name: resource_id_version_pair; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resource_id_version_pair AS (
	resource_id character varying,
	version integer
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
-- Name: environmentmetricscounter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environmentmetricscounter (
    metric_name character varying NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    count integer NOT NULL
);


--
-- Name: environmentmetricsnoncounter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environmentmetricsnoncounter (
    metric_name character varying NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    count integer NOT NULL,
    value double precision NOT NULL
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
abc2ab94-401d-4589-8aa6-281a43ef1b78	internal	2022-12-06 16:01:41.229089+01	f	db4439cb-7c12-415a-8ba5-b9617ef24b4b	\N
abc2ab94-401d-4589-8aa6-281a43ef1b78	localhost	2022-12-06 16:01:44.753247+01	f	be4aab6c-bfbb-4d57-a933-d7f8e94d930e	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
db4439cb-7c12-415a-8ba5-b9617ef24b4b	e41cf95c-7576-11ed-9421-1964416f6f4a	internal	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78
be4aab6c-bfbb-4d57-a933-d7f8e94d930e	e41cf95c-7576-11ed-9421-1964416f6f4a	localhost	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
florent-Latitude-5421	abc2ab94-401d-4589-8aa6-281a43ef1b78	2022-12-06 16:01:41.229089+01	2022-12-06 16:01:53.328038+01	\N	e41cf95c-7576-11ed-9421-1964416f6f4a
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::Service	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::File	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::Directory	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::Package	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::Symlink	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::AgentConfig	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::Service	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::File	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::Directory	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::Package	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::Symlink	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
abc2ab94-401d-4589-8aa6-281a43ef1b78	std::AgentConfig	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
d9be1e38-06b5-459d-aa77-0b8826310fb6	abc2ab94-401d-4589-8aa6-281a43ef1b78	2022-12-06 16:01:28.504736+01	2022-12-06 16:01:41.356154+01	2022-12-06 16:01:28.448593+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	94ce92c2-1fe9-4862-ae60-4a8640b8df2c	t	\N	{"errors": []}	f	{}	\N	\N	\N
7f5adc23-d771-4cd9-9a23-f9ceb0b21343	abc2ab94-401d-4589-8aa6-281a43ef1b78	2022-12-06 16:01:44.892107+01	2022-12-06 16:01:53.249872+01	2022-12-06 16:01:44.888926+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	7e90cd49-2e4a-4004-a2da-6b2af82262e3	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	abc2ab94-401d-4589-8aa6-281a43ef1b78	2022-12-06 16:01:39.251874+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	abc2ab94-401d-4589-8aa6-281a43ef1b78	2022-12-06 16:01:53.108632+01	t	t	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
3b0fee25-ac61-4c87-962e-08a5f3527b8c	dev-2	23ed5dab-107d-4db6-99cd-cc320fe08ed7			{"auto_full_compile": ""}	0	f		
abc2ab94-401d-4589-8aa6-281a43ef1b78	dev-1	23ed5dab-107d-4db6-99cd-cc320fe08ed7			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
\.


--
-- Data for Name: environmentmetricscounter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricscounter (metric_name, "timestamp", count) FROM stdin;
\.


--
-- Data for Name: environmentmetricsnoncounter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricsnoncounter (metric_name, "timestamp", count, value) FROM stdin;
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
23ed5dab-107d-4db6-99cd-cc320fe08ed7	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
4349ae69-542f-403b-9efd-850390078080	2022-12-06 16:01:28.50508+01	2022-12-06 16:01:28.506135+01		Init		Using extra environment variables during compile \n	0	d9be1e38-06b5-459d-aa77-0b8826310fb6
7ecf1665-6366-48f7-a06b-686af4aab0b1	2022-12-06 16:01:28.506419+01	2022-12-06 16:01:28.512863+01		Creating venv			0	d9be1e38-06b5-459d-aa77-0b8826310fb6
5e5e257f-2578-43fc-8341-8c15402430c9	2022-12-06 16:01:28.517343+01	2022-12-06 16:01:28.753672+01	/tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.2.0.dev0\nNot uninstalling inmanta-core at /home/florent/Desktop/inmanta-core/src, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	d9be1e38-06b5-459d-aa77-0b8826310fb6
ce0ffad1-5bd0-4891-b8f9-b5a2edf730c8	2022-12-06 16:01:28.755181+01	2022-12-06 16:01:38.574923+01	/tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000033 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade --upgrade-strategy only-if-needed inmanta-module-std inmanta-core==7.2.0.dev0 --no-index\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (4.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.25.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.7.3)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (36.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.13)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (4.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=1.9.0a1,~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   INFO: pip is looking at multiple versions of inmanta-core to determine which version is compatible with other requirements. This could take a while.\ninmanta.pip              DEBUG   ERROR: Cannot install inmanta-core==7.2.0.dev0 and inmanta-module-std==4.0.1 because these package versions have conflicting dependencies.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   The conflict is caused by:\ninmanta.pip              DEBUG   inmanta-core 7.2.0.dev0 depends on email-validator~=1.0\ninmanta.pip              DEBUG   inmanta-module-std 4.0.1 depends on email-validator~=1.3\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   To fix this you could try to:\ninmanta.pip              DEBUG   1. loosen the range of package versions you've specified\ninmanta.pip              DEBUG   2. remove package versions to allow pip attempt to solve the dependency conflict\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/user_guide/#fixing-conflicting-dependencies\ninmanta.moduletool       INFO    The model is not currently in an executable state, performing intermediate updates\ninmanta.pip              DEBUG   Pip command: /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade --upgrade-strategy eager dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 email_validator~=1.3 pydantic~=1.10 inmanta-core==7.2.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Collecting Jinja2~=3.1\ninmanta.pip              DEBUG   Using cached Jinja2-3.1.2-py3-none-any.whl (133 kB)\ninmanta.pip              DEBUG   Collecting email_validator~=1.3\ninmanta.pip              DEBUG   Using cached email_validator-1.3.0-py2.py3-none-any.whl (22 kB)\ninmanta.pip              DEBUG   Collecting pydantic~=1.10\ninmanta.pip              DEBUG   Using cached pydantic-1.10.2-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.25.0)\ninmanta.pip              DEBUG   Collecting asyncpg~=0.25\ninmanta.pip              DEBUG   Using cached asyncpg-0.27.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_28_x86_64.whl (2.7 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.0.3)\ninmanta.pip              DEBUG   Collecting click<8.2,>=8.0\ninmanta.pip              DEBUG   Using cached click-8.1.3-py3-none-any.whl (96 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.6.0)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4\ninmanta.pip              DEBUG   Using cached colorlog-6.7.0-py2.py3-none-any.whl (11 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.7.3)\ninmanta.pip              DEBUG   Collecting cookiecutter<3,>=1\ninmanta.pip              DEBUG   Using cached cookiecutter-2.1.1-py2.py3-none-any.whl (36 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (36.0.1)\ninmanta.pip              DEBUG   Collecting cryptography<39,>=36\ninmanta.pip              DEBUG   Using cached cryptography-38.0.4-cp36-abi3-manylinux_2_28_x86_64.whl (4.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.13)\ninmanta.pip              DEBUG   Collecting docstring-parser<0.16,>=0.10\ninmanta.pip              DEBUG   Using cached docstring_parser-0.15-py3-none-any.whl (36 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (4.8.2)\ninmanta.pip              DEBUG   Collecting importlib_metadata<6,>=4\ninmanta.pip              DEBUG   Using cached importlib_metadata-5.1.0-py3-none-any.whl (21 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.12.0)\ninmanta.pip              DEBUG   Collecting more-itertools<10,>=8\ninmanta.pip              DEBUG   Using cached more_itertools-9.0.0-py3-none-any.whl (52 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3\ninmanta.pip              DEBUG   Using cached pip-22.3.1-py3-none-any.whl (2.1 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Collecting PyJWT~=2.0\ninmanta.pip              DEBUG   Using cached PyJWT-2.6.0-py3-none-any.whl (20 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.4)\ninmanta.pip              DEBUG   Collecting texttable~=1.0\ninmanta.pip              DEBUG   Using cached texttable-1.6.7-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.1)\ninmanta.pip              DEBUG   Collecting tornado~=6.0\ninmanta.pip              DEBUG   Using cached tornado-6.2-cp37-abi3-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl (423 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Collecting typing_inspect~=0.7\ninmanta.pip              DEBUG   Using cached typing_inspect-0.8.0-py3-none-any.whl (8.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting build~=0.7\ninmanta.pip              DEBUG   Using cached build-0.9.0-py3-none-any.whl (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0\ninmanta.pip              DEBUG   Using cached python_slugify-7.0.0-py2.py3-none-any.whl (9.4 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.9.0)\ninmanta.pip              DEBUG   Collecting zipp>=0.5\ninmanta.pip              DEBUG   Using cached zipp-3.11.0-py3-none-any.whl (6.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.6)\ninmanta.pip              DEBUG   Collecting ruamel.yaml.clib>=0.2.6\ninmanta.pip              DEBUG   Using cached ruamel.yaml.clib-0.2.7-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_24_x86_64.whl (519 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Collecting chardet>=3.0.2\ninmanta.pip              DEBUG   Using cached chardet-5.1.0-py3-none-any.whl (199 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.12)\ninmanta.pip              DEBUG   Collecting urllib3<1.27,>=1.21.1\ninmanta.pip              DEBUG   Using cached urllib3-1.26.13-py2.py3-none-any.whl (140 kB)\ninmanta.pip              DEBUG   Installing collected packages: urllib3, Jinja2, chardet, zipp, ruamel.yaml.clib, python-slugify, click, typing-inspect, tornado, texttable, PyJWT, pydantic, pip, more-itertools, importlib-metadata, email-validator, docstring-parser, cryptography, cookiecutter, colorlog, build, asyncpg\ninmanta.pip              DEBUG   Attempting uninstall: urllib3\ninmanta.pip              DEBUG   Found existing installation: urllib3 1.26.12\ninmanta.pip              DEBUG   Not uninstalling urllib3 at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: Jinja2\ninmanta.pip              DEBUG   Found existing installation: Jinja2 3.0.3\ninmanta.pip              DEBUG   Not uninstalling jinja2 at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'Jinja2'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: chardet\ninmanta.pip              DEBUG   Found existing installation: chardet 5.0.0\ninmanta.pip              DEBUG   Not uninstalling chardet at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'chardet'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: zipp\ninmanta.pip              DEBUG   Found existing installation: zipp 3.9.0\ninmanta.pip              DEBUG   Not uninstalling zipp at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'zipp'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: ruamel.yaml.clib\ninmanta.pip              DEBUG   Found existing installation: ruamel.yaml.clib 0.2.6\ninmanta.pip              DEBUG   Not uninstalling ruamel.yaml.clib at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'ruamel.yaml.clib'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: click\ninmanta.pip              DEBUG   Found existing installation: click 8.0.3\ninmanta.pip              DEBUG   Not uninstalling click at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'click'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: typing-inspect\ninmanta.pip              DEBUG   Found existing installation: typing-inspect 0.7.1\ninmanta.pip              DEBUG   Not uninstalling typing-inspect at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'typing-inspect'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.1\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.6.4\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: PyJWT\ninmanta.pip              DEBUG   Found existing installation: PyJWT 2.3.0\ninmanta.pip              DEBUG   Not uninstalling pyjwt at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'PyJWT'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 1.9.0\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 21.3.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 8.12.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: importlib-metadata\ninmanta.pip              DEBUG   Found existing installation: importlib-metadata 4.8.2\ninmanta.pip              DEBUG   Not uninstalling importlib-metadata at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'importlib-metadata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: email-validator\ninmanta.pip              DEBUG   Found existing installation: email-validator 1.1.3\ninmanta.pip              DEBUG   Not uninstalling email-validator at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'email-validator'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: docstring-parser\ninmanta.pip              DEBUG   Found existing installation: docstring-parser 0.13\ninmanta.pip              DEBUG   Not uninstalling docstring-parser at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'docstring-parser'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cryptography\ninmanta.pip              DEBUG   Found existing installation: cryptography 36.0.1\ninmanta.pip              DEBUG   Not uninstalling cryptography at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'cryptography'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cookiecutter\ninmanta.pip              DEBUG   Found existing installation: cookiecutter 1.7.3\ninmanta.pip              DEBUG   Not uninstalling cookiecutter at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'cookiecutter'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.6.0\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 0.8.0\ninmanta.pip              DEBUG   Not uninstalling build at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: asyncpg\ninmanta.pip              DEBUG   Found existing installation: asyncpg 0.25.0\ninmanta.pip              DEBUG   Not uninstalling asyncpg at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\ninmanta.pip              DEBUG   Can't uninstall 'asyncpg'. No files were found to uninstall.\ninmanta.pip              DEBUG   Successfully installed Jinja2-3.1.2 PyJWT-2.6.0 asyncpg-0.27.0 build-0.9.0 chardet-5.1.0 click-8.1.3 colorlog-6.7.0 cookiecutter-2.1.1 cryptography-38.0.4 docstring-parser-0.15 email-validator-1.3.0 importlib-metadata-5.1.0 more-itertools-9.0.0 pip-22.3.1 pydantic-1.10.2 python-slugify-7.0.0 ruamel.yaml.clib-0.2.7 texttable-1.6.7 tornado-6.2 typing-inspect-0.8.0 urllib3-1.26.13 zipp-3.11.0\ninmanta.pip              DEBUG   WARNING: You are using pip version 21.3.1; however, version 22.3.1 is available.\ninmanta.pip              DEBUG   You should consider upgrading via the '/tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade pip' command.\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000028 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade --upgrade-strategy only-if-needed inmanta-module-std inmanta-core==7.2.0.dev0 --no-index\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (4.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=1.9.0a1,~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2~=3.0->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic!=1.9.0a1,~=1.0->inmanta-core==7.2.0.dev0) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade --upgrade-strategy eager dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 email_validator~=1.3 pydantic~=1.10 inmanta-core==7.2.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in ./.env/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\n	0	d9be1e38-06b5-459d-aa77-0b8826310fb6
3fc3f554-b054-4723-8d6a-7bd8c9fb372d	2022-12-06 16:01:38.576216+01	2022-12-06 16:01:41.354656+01	/tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m inmanta.app -vvv export -X -e abc2ab94-401d-4589-8aa6-281a43ef1b78 --server_address localhost --server_port 54763 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpfn6ikxrt	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003715 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000052 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V2 modules:\ninmanta.module           INFO      std: 4.0.1\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001774)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001420)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000206)\ninmanta.execute.schedulerINFO    Total compilation time 0.003530\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:54763/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:54763/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:54763/api/v1/file/5309d4b5db445e9c423dc60125f5b50b2926239e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:54763/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:54763/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:54763/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:54763/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:54763/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	d9be1e38-06b5-459d-aa77-0b8826310fb6
967874d9-a5a3-4fae-99bc-406824e5542c	2022-12-06 16:01:44.892441+01	2022-12-06 16:01:44.893312+01		Init		Using extra environment variables during compile \n	0	7f5adc23-d771-4cd9-9a23-f9ceb0b21343
e08f0fe9-60bb-42a6-821b-f3182213df90	2022-12-06 16:01:44.897224+01	2022-12-06 16:01:45.179485+01	/tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.2.0.dev0\nNot uninstalling inmanta-core at /home/florent/Desktop/inmanta-core/src, outside environment /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	7f5adc23-d771-4cd9-9a23-f9ceb0b21343
51807d97-5b56-4ebf-bd55-98d310389b1b	2022-12-06 16:01:52.40969+01	2022-12-06 16:01:53.249427+01	/tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m inmanta.app -vvv export -X -e abc2ab94-401d-4589-8aa6-281a43ef1b78 --server_address localhost --server_port 54763 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp7e8730kq	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.004117 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000082 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V2 modules:\ninmanta.module           INFO      std: 4.0.1\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002226)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001720)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000232)\ninmanta.execute.schedulerINFO    Total compilation time 0.004383\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:54763/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:54763/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:54763/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:54763/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:54763/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	7f5adc23-d771-4cd9-9a23-f9ceb0b21343
c35423b2-9a13-4ccd-9778-769b82371866	2022-12-06 16:01:45.180403+01	2022-12-06 16:01:52.408774+01	/tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000037 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade --upgrade-strategy only-if-needed inmanta-module-std inmanta-core==7.2.0.dev0 --no-index\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (4.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=1.9.0a1,~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2~=3.0->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic!=1.9.0a1,~=1.0->inmanta-core==7.2.0.dev0) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic~=1.10 email_validator~=1.3 dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 inmanta-core==7.2.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in ./.env/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000025 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade --upgrade-strategy only-if-needed inmanta-module-std inmanta-core==7.2.0.dev0 --no-index\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (4.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=1.9.0a1,~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2~=3.0->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic!=1.9.0a1,~=1.0->inmanta-core==7.2.0.dev0) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpfzmi_g93/server/environments/abc2ab94-401d-4589-8aa6-281a43ef1b78/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic~=1.10 email_validator~=1.3 dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 inmanta-core==7.2.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in ./.env/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.module           INFO    verifying project\n	0	7f5adc23-d771-4cd9-9a23-f9ceb0b21343
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
abc2ab94-401d-4589-8aa6-281a43ef1b78	1	std::AgentConfig[internal,agentname=localhost]	internal	2022-12-06 16:01:43.748756+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
abc2ab94-401d-4589-8aa6-281a43ef1b78	1	std::File[localhost,path=/tmp/test]	localhost	2022-12-06 16:01:44.800609+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
abc2ab94-401d-4589-8aa6-281a43ef1b78	2	std::AgentConfig[internal,agentname=localhost]	internal	2022-12-06 16:01:53.170246+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
abc2ab94-401d-4589-8aa6-281a43ef1b78	2	std::File[localhost,path=/tmp/test]	localhost	2022-12-06 16:01:53.24598+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	deploying	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
d01ab24a-195c-4fc0-a36f-7a031c74830f	store	2022-12-06 16:01:39.251087+01	2022-12-06 16:01:40.313687+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-12-06T16:01:40.313703+01:00\\"}"}	\N	\N	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
df2774dc-28cf-4309-964f-80b2384df489	pull	2022-12-06 16:01:41.236338+01	2022-12-06 16:01:41.802866+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-12-06T16:01:41.802887+01:00\\"}"}	\N	\N	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
f6461e50-d1e5-4429-a5ce-ae9e8125f88a	deploy	2022-12-06 16:01:43.737091+01	2022-12-06 16:01:43.748756+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-12-06 16:01:41+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-12-06 16:01:41+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"ed284efd-e481-4ea5-a7c0-359b662ed0c3\\"}, \\"timestamp\\": \\"2022-12-06T16:01:43.734922+01:00\\"}","{\\"msg\\": \\"Start deploy ed284efd-e481-4ea5-a7c0-359b662ed0c3 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"ed284efd-e481-4ea5-a7c0-359b662ed0c3\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-12-06T16:01:43.738643+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-06T16:01:43.739438+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-06T16:01:43.741839+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy ed284efd-e481-4ea5-a7c0-359b662ed0c3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"ed284efd-e481-4ea5-a7c0-359b662ed0c3\\"}, \\"timestamp\\": \\"2022-12-06T16:01:43.744503+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	abc2ab94-401d-4589-8aa6-281a43ef1b78	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c733fc97-8f38-4a1f-b76c-b4872009576f	pull	2022-12-06 16:01:44.757645+01	2022-12-06 16:01:44.758545+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-12-06T16:01:44.758552+01:00\\"}"}	\N	\N	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78	1	{"std::File[localhost,path=/tmp/test],v=1"}
ee861a86-223f-4995-adc5-e22d8d853724	deploy	2022-12-06 16:01:44.793637+01	2022-12-06 16:01:44.800609+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-12-06 16:01:44+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-12-06 16:01:44+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"2b219da4-318c-412a-a8f9-3bcf7a13255f\\"}, \\"timestamp\\": \\"2022-12-06T16:01:44.791358+01:00\\"}","{\\"msg\\": \\"Start deploy 2b219da4-318c-412a-a8f9-3bcf7a13255f of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"2b219da4-318c-412a-a8f9-3bcf7a13255f\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-06T16:01:44.795039+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-06T16:01:44.795848+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-12-06T16:01:44.797356+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-06T16:01:44.797776+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 2b219da4-318c-412a-a8f9-3bcf7a13255f\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"2b219da4-318c-412a-a8f9-3bcf7a13255f\\"}, \\"timestamp\\": \\"2022-12-06T16:01:44.798170+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	abc2ab94-401d-4589-8aa6-281a43ef1b78	1	{"std::File[localhost,path=/tmp/test],v=1"}
2b453b99-fb39-423c-bfa8-9cab9666024b	store	2022-12-06 16:01:53.108426+01	2022-12-06 16:01:53.110067+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-12-06T16:01:53.110077+01:00\\"}"}	\N	\N	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
67d31093-02cf-4f4e-84f7-9992312a64b7	pull	2022-12-06 16:01:53.168923+01	2022-12-06 16:01:53.170427+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-12-06T16:01:53.171833+01:00\\"}"}	\N	\N	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78	2	{"std::File[localhost,path=/tmp/test],v=2"}
991cef33-b950-42d3-a706-da2b3f8d5d32	deploy	2022-12-06 16:01:53.170246+01	2022-12-06 16:01:53.170246+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-12-06T15:01:53.170246+00:00\\"}"}	deployed	\N	nochange	abc2ab94-401d-4589-8aa6-281a43ef1b78	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
93245351-4fbd-4386-baa6-e664a19cf622	deploy	2022-12-06 16:01:53.236402+01	2022-12-06 16:01:53.24598+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"338567f5-2068-4ad0-ad32-49758ecb0777\\"}, \\"timestamp\\": \\"2022-12-06T16:01:53.232212+01:00\\"}","{\\"msg\\": \\"Start deploy 338567f5-2068-4ad0-ad32-49758ecb0777 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"338567f5-2068-4ad0-ad32-49758ecb0777\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-06T16:01:53.239056+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-06T16:01:53.239692+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-12-06T16:01:53.242279+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-06T16:01:53.242576+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 338567f5-2068-4ad0-ad32-49758ecb0777\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"338567f5-2068-4ad0-ad32-49758ecb0777\\"}, \\"timestamp\\": \\"2022-12-06T16:01:53.242901+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	abc2ab94-401d-4589-8aa6-281a43ef1b78	2	{"std::File[localhost,path=/tmp/test],v=2"}
ac5de1d5-62e7-4471-8188-b4f8c503a57d	pull	2022-12-06 16:01:53.327978+01	2022-12-06 16:01:53.329339+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-12-06T16:01:53.329349+01:00\\"}"}	\N	\N	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78	2	{"std::File[localhost,path=/tmp/test],v=2"}
105515da-dec9-48cd-ac43-7e2203fc7579	deploy	2022-12-06 16:01:53.33662+01	\N	{"{\\"msg\\": \\"Resource deploy started on agent localhost, setting status to deploying\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-12-06T16:01:53.336629+01:00\\"}"}	deploying	\N	\N	abc2ab94-401d-4589-8aa6-281a43ef1b78	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
abc2ab94-401d-4589-8aa6-281a43ef1b78	d01ab24a-195c-4fc0-a36f-7a031c74830f	std::File[localhost,path=/tmp/test]	1
abc2ab94-401d-4589-8aa6-281a43ef1b78	d01ab24a-195c-4fc0-a36f-7a031c74830f	std::AgentConfig[internal,agentname=localhost]	1
abc2ab94-401d-4589-8aa6-281a43ef1b78	df2774dc-28cf-4309-964f-80b2384df489	std::AgentConfig[internal,agentname=localhost]	1
abc2ab94-401d-4589-8aa6-281a43ef1b78	f6461e50-d1e5-4429-a5ce-ae9e8125f88a	std::AgentConfig[internal,agentname=localhost]	1
abc2ab94-401d-4589-8aa6-281a43ef1b78	c733fc97-8f38-4a1f-b76c-b4872009576f	std::File[localhost,path=/tmp/test]	1
abc2ab94-401d-4589-8aa6-281a43ef1b78	ee861a86-223f-4995-adc5-e22d8d853724	std::File[localhost,path=/tmp/test]	1
abc2ab94-401d-4589-8aa6-281a43ef1b78	2b453b99-fb39-423c-bfa8-9cab9666024b	std::File[localhost,path=/tmp/test]	2
abc2ab94-401d-4589-8aa6-281a43ef1b78	2b453b99-fb39-423c-bfa8-9cab9666024b	std::AgentConfig[internal,agentname=localhost]	2
abc2ab94-401d-4589-8aa6-281a43ef1b78	67d31093-02cf-4f4e-84f7-9992312a64b7	std::File[localhost,path=/tmp/test]	2
abc2ab94-401d-4589-8aa6-281a43ef1b78	991cef33-b950-42d3-a706-da2b3f8d5d32	std::AgentConfig[internal,agentname=localhost]	2
abc2ab94-401d-4589-8aa6-281a43ef1b78	93245351-4fbd-4386-baa6-e664a19cf622	std::File[localhost,path=/tmp/test]	2
abc2ab94-401d-4589-8aa6-281a43ef1b78	ac5de1d5-62e7-4471-8188-b4f8c503a57d	std::File[localhost,path=/tmp/test]	2
abc2ab94-401d-4589-8aa6-281a43ef1b78	105515da-dec9-48cd-ac43-7e2203fc7579	std::File[localhost,path=/tmp/test]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010}
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
-- Name: environmentmetricscounter environmentmetricscounter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricscounter
    ADD CONSTRAINT environmentmetricscounter_pkey PRIMARY KEY (metric_name, "timestamp");


--
-- Name: environmentmetricsnoncounter environmentmetricsnoncounter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricsnoncounter
    ADD CONSTRAINT environmentmetricsnoncounter_pkey PRIMARY KEY (metric_name, "timestamp");


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
    ADD CONSTRAINT resource_pkey PRIMARY KEY (environment, model, resource_id);


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

