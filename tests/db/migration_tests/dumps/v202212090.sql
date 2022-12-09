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
-- Name: environmentmetricsgauge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environmentmetricsgauge (
    metric_name character varying NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    count integer NOT NULL,
    environment uuid NOT NULL
);


--
-- Name: environmentmetricstimer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environmentmetricstimer (
    metric_name character varying NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    count integer NOT NULL,
    value double precision NOT NULL,
    environment uuid NOT NULL
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
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	internal	2022-12-09 15:29:44.346745+01	f	4f0b3ed1-46b9-4e7e-bdf9-a1a464bf0edc	\N
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	localhost	2022-12-09 15:29:47.718823+01	f	424f41b9-5671-4213-bb06-94cf3878c569	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
4f0b3ed1-46b9-4e7e-bdf9-a1a464bf0edc	ecccad46-77cd-11ed-9421-1964416f6f4a	internal	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf
424f41b9-5671-4213-bb06-94cf3878c569	ecccad46-77cd-11ed-9421-1964416f6f4a	localhost	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
florent-Latitude-5421	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2022-12-09 15:29:44.346745+01	2022-12-09 15:29:59.418072+01	\N	ecccad46-77cd-11ed-9421-1964416f6f4a
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::Service	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::File	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::Directory	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::Package	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::Symlink	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::AgentConfig	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::Service	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::File	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::Directory	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::Package	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::Symlink	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	std::AgentConfig	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
b0b5918f-616e-4459-a12c-abc8a31542e9	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2022-12-09 15:29:28.404459+01	2022-12-09 15:29:44.510808+01	2022-12-09 15:29:28.337967+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	18253b71-1e8d-428e-b203-6474e9938c89	t	\N	{"errors": []}	f	{}	\N	\N	\N
0c79315d-a3b9-47c8-853e-3fc25aff081b	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2022-12-09 15:29:49.098976+01	2022-12-09 15:29:59.369869+01	2022-12-09 15:29:49.094946+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	a690df46-ff50-4ba8-a706-195565c52316	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2022-12-09 15:29:42.14683+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2022-12-09 15:29:59.279211+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
767fe166-17cb-4f93-9fa6-aaecc05d2732	dev-2	aef22595-89b8-4707-8dc7-748ed1ed2a8b			{"auto_full_compile": ""}	0	f		
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	dev-1	aef22595-89b8-4707-8dc7-748ed1ed2a8b			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
\.


--
-- Data for Name: environmentmetricsgauge; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricsgauge (metric_name, "timestamp", count, environment) FROM stdin;
\.


--
-- Data for Name: environmentmetricstimer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricstimer (metric_name, "timestamp", count, value, environment) FROM stdin;
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
aef22595-89b8-4707-8dc7-748ed1ed2a8b	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
66ebb378-ce36-4a7a-a4ed-c932ac762ccc	2022-12-09 15:29:28.40489+01	2022-12-09 15:29:28.406498+01		Init		Using extra environment variables during compile \n	0	b0b5918f-616e-4459-a12c-abc8a31542e9
b2b1b832-62ca-4fa5-b484-3dbaa91ca9a0	2022-12-09 15:29:28.40688+01	2022-12-09 15:29:28.416324+01		Creating venv			0	b0b5918f-616e-4459-a12c-abc8a31542e9
6a2ffbbf-b5c8-4814-8726-42085bf0c257	2022-12-09 15:29:28.422441+01	2022-12-09 15:29:28.69659+01	/tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.2.0.dev0\nNot uninstalling inmanta-core at /home/florent/Desktop/inmanta-core/src, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	b0b5918f-616e-4459-a12c-abc8a31542e9
7bffeb18-2e55-4cf9-a853-c38afdce67ab	2022-12-09 15:29:28.697782+01	2022-12-09 15:29:41.368727+01	/tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000056 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade --upgrade-strategy only-if-needed inmanta-module-std inmanta-core==7.2.0.dev0 --no-index\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (4.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.25.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.7.3)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (36.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.13)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (4.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=1.9.0a1,~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.4)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   INFO: pip is looking at multiple versions of inmanta-core to determine which version is compatible with other requirements. This could take a while.\ninmanta.pip              DEBUG   ERROR: Cannot install inmanta-core==7.2.0.dev0 and inmanta-module-std==4.0.1 because these package versions have conflicting dependencies.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   The conflict is caused by:\ninmanta.pip              DEBUG   inmanta-core 7.2.0.dev0 depends on pydantic!=1.9.0a1 and ~=1.0\ninmanta.pip              DEBUG   inmanta-module-std 4.0.1 depends on pydantic~=1.10\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   To fix this you could try to:\ninmanta.pip              DEBUG   1. loosen the range of package versions you've specified\ninmanta.pip              DEBUG   2. remove package versions to allow pip attempt to solve the dependency conflict\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/user_guide/#fixing-conflicting-dependencies\ninmanta.moduletool       INFO    The model is not currently in an executable state, performing intermediate updates\ninmanta.pip              DEBUG   Pip command: /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 pydantic~=1.10 email_validator~=1.3 dataclasses~=0.7; python_version < "3.7" inmanta-core==7.2.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Collecting Jinja2~=3.1\ninmanta.pip              DEBUG   Using cached Jinja2-3.1.2-py3-none-any.whl (133 kB)\ninmanta.pip              DEBUG   Collecting pydantic~=1.10\ninmanta.pip              DEBUG   Using cached pydantic-1.10.2-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.2 MB)\ninmanta.pip              DEBUG   Collecting email_validator~=1.3\ninmanta.pip              DEBUG   Using cached email_validator-1.3.0-py2.py3-none-any.whl (22 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.25.0)\ninmanta.pip              DEBUG   Collecting asyncpg~=0.25\ninmanta.pip              DEBUG   Using cached asyncpg-0.27.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_28_x86_64.whl (2.7 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.0.3)\ninmanta.pip              DEBUG   Collecting click<8.2,>=8.0\ninmanta.pip              DEBUG   Using cached click-8.1.3-py3-none-any.whl (96 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.6.0)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4\ninmanta.pip              DEBUG   Using cached colorlog-6.7.0-py2.py3-none-any.whl (11 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.7.3)\ninmanta.pip              DEBUG   Collecting cookiecutter<3,>=1\ninmanta.pip              DEBUG   Using cached cookiecutter-2.1.1-py2.py3-none-any.whl (36 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (36.0.1)\ninmanta.pip              DEBUG   Collecting cryptography<39,>=36\ninmanta.pip              DEBUG   Using cached cryptography-38.0.4-cp36-abi3-manylinux_2_28_x86_64.whl (4.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.13)\ninmanta.pip              DEBUG   Collecting docstring-parser<0.16,>=0.10\ninmanta.pip              DEBUG   Using cached docstring_parser-0.15-py3-none-any.whl (36 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (4.8.2)\ninmanta.pip              DEBUG   Collecting importlib_metadata<6,>=4\ninmanta.pip              DEBUG   Using cached importlib_metadata-5.1.0-py3-none-any.whl (21 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.12.0)\ninmanta.pip              DEBUG   Collecting more-itertools<10,>=8\ninmanta.pip              DEBUG   Using cached more_itertools-9.0.0-py3-none-any.whl (52 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3\ninmanta.pip              DEBUG   Using cached pip-22.3.1-py3-none-any.whl (2.1 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Collecting PyJWT~=2.0\ninmanta.pip              DEBUG   Using cached PyJWT-2.6.0-py3-none-any.whl (20 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.4)\ninmanta.pip              DEBUG   Collecting texttable~=1.0\ninmanta.pip              DEBUG   Using cached texttable-1.6.7-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.1)\ninmanta.pip              DEBUG   Collecting tornado~=6.0\ninmanta.pip              DEBUG   Using cached tornado-6.2-cp37-abi3-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl (423 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Collecting typing_inspect~=0.7\ninmanta.pip              DEBUG   Using cached typing_inspect-0.8.0-py3-none-any.whl (8.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting build~=0.7\ninmanta.pip              DEBUG   Using cached build-0.9.0-py3-none-any.whl (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0\ninmanta.pip              DEBUG   Using cached python_slugify-7.0.0-py2.py3-none-any.whl (9.4 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.9.0)\ninmanta.pip              DEBUG   Collecting zipp>=0.5\ninmanta.pip              DEBUG   Using cached zipp-3.11.0-py3-none-any.whl (6.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.6)\ninmanta.pip              DEBUG   Collecting ruamel.yaml.clib>=0.2.6\ninmanta.pip              DEBUG   Using cached ruamel.yaml.clib-0.2.7-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_24_x86_64.whl (519 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.0.0)\ninmanta.pip              DEBUG   Collecting chardet>=3.0.2\ninmanta.pip              DEBUG   Using cached chardet-5.1.0-py3-none-any.whl (199 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Collecting certifi>=2017.4.17\ninmanta.pip              DEBUG   Downloading certifi-2022.12.7-py3-none-any.whl (155 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.12)\ninmanta.pip              DEBUG   Collecting urllib3<1.27,>=1.21.1\ninmanta.pip              DEBUG   Using cached urllib3-1.26.13-py2.py3-none-any.whl (140 kB)\ninmanta.pip              DEBUG   Installing collected packages: urllib3, Jinja2, chardet, certifi, zipp, ruamel.yaml.clib, python-slugify, click, typing-inspect, tornado, texttable, PyJWT, pydantic, pip, more-itertools, importlib-metadata, email-validator, docstring-parser, cryptography, cookiecutter, colorlog, build, asyncpg\ninmanta.pip              DEBUG   Attempting uninstall: urllib3\ninmanta.pip              DEBUG   Found existing installation: urllib3 1.26.12\ninmanta.pip              DEBUG   Not uninstalling urllib3 at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: Jinja2\ninmanta.pip              DEBUG   Found existing installation: Jinja2 3.0.3\ninmanta.pip              DEBUG   Not uninstalling jinja2 at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'Jinja2'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: chardet\ninmanta.pip              DEBUG   Found existing installation: chardet 5.0.0\ninmanta.pip              DEBUG   Not uninstalling chardet at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'chardet'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: certifi\ninmanta.pip              DEBUG   Found existing installation: certifi 2022.9.24\ninmanta.pip              DEBUG   Not uninstalling certifi at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: zipp\ninmanta.pip              DEBUG   Found existing installation: zipp 3.9.0\ninmanta.pip              DEBUG   Not uninstalling zipp at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'zipp'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: ruamel.yaml.clib\ninmanta.pip              DEBUG   Found existing installation: ruamel.yaml.clib 0.2.6\ninmanta.pip              DEBUG   Not uninstalling ruamel.yaml.clib at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'ruamel.yaml.clib'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: click\ninmanta.pip              DEBUG   Found existing installation: click 8.0.3\ninmanta.pip              DEBUG   Not uninstalling click at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'click'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: typing-inspect\ninmanta.pip              DEBUG   Found existing installation: typing-inspect 0.7.1\ninmanta.pip              DEBUG   Not uninstalling typing-inspect at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'typing-inspect'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.1\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.6.4\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: PyJWT\ninmanta.pip              DEBUG   Found existing installation: PyJWT 2.3.0\ninmanta.pip              DEBUG   Not uninstalling pyjwt at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'PyJWT'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 1.9.0\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 21.3.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 8.12.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: importlib-metadata\ninmanta.pip              DEBUG   Found existing installation: importlib-metadata 4.8.2\ninmanta.pip              DEBUG   Not uninstalling importlib-metadata at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'importlib-metadata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: email-validator\ninmanta.pip              DEBUG   Found existing installation: email-validator 1.1.3\ninmanta.pip              DEBUG   Not uninstalling email-validator at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'email-validator'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: docstring-parser\ninmanta.pip              DEBUG   Found existing installation: docstring-parser 0.13\ninmanta.pip              DEBUG   Not uninstalling docstring-parser at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'docstring-parser'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cryptography\ninmanta.pip              DEBUG   Found existing installation: cryptography 36.0.1\ninmanta.pip              DEBUG   Not uninstalling cryptography at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'cryptography'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cookiecutter\ninmanta.pip              DEBUG   Found existing installation: cookiecutter 1.7.3\ninmanta.pip              DEBUG   Not uninstalling cookiecutter at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'cookiecutter'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.6.0\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 0.8.0\ninmanta.pip              DEBUG   Not uninstalling build at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: asyncpg\ninmanta.pip              DEBUG   Found existing installation: asyncpg 0.25.0\ninmanta.pip              DEBUG   Not uninstalling asyncpg at /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\ninmanta.pip              DEBUG   Can't uninstall 'asyncpg'. No files were found to uninstall.\ninmanta.pip              DEBUG   Successfully installed Jinja2-3.1.2 PyJWT-2.6.0 asyncpg-0.27.0 build-0.9.0 certifi-2022.12.7 chardet-5.1.0 click-8.1.3 colorlog-6.7.0 cookiecutter-2.1.1 cryptography-38.0.4 docstring-parser-0.15 email-validator-1.3.0 importlib-metadata-5.1.0 more-itertools-9.0.0 pip-22.3.1 pydantic-1.10.2 python-slugify-7.0.0 ruamel.yaml.clib-0.2.7 texttable-1.6.7 tornado-6.2 typing-inspect-0.8.0 urllib3-1.26.13 zipp-3.11.0\ninmanta.pip              DEBUG   WARNING: You are using pip version 21.3.1; however, version 22.3.1 is available.\ninmanta.pip              DEBUG   You should consider upgrading via the '/tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade pip' command.\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000047 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade --upgrade-strategy only-if-needed inmanta-module-std inmanta-core==7.2.0.dev0 --no-index\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (4.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=1.9.0a1,~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2~=3.0->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic!=1.9.0a1,~=1.0->inmanta-core==7.2.0.dev0) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 pydantic~=1.10 email_validator~=1.3 dataclasses~=0.7; python_version < "3.7" inmanta-core==7.2.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in ./.env/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\n	0	b0b5918f-616e-4459-a12c-abc8a31542e9
6b6ff883-827f-4c71-b624-3472229f5be8	2022-12-09 15:29:49.099405+01	2022-12-09 15:29:49.1005+01		Init		Using extra environment variables during compile \n	0	0c79315d-a3b9-47c8-853e-3fc25aff081b
20722d3a-a10f-4787-be2d-819f5f97dfc3	2022-12-09 15:29:41.370324+01	2022-12-09 15:29:44.509624+01	/tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m inmanta.app -vvv export -X -e bba18e6b-7c0e-4ede-bf3a-da7219c95adf --server_address localhost --server_port 33071 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpn2_3go7_ --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.004094 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000062 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V2 modules:\ninmanta.module           INFO      std: 4.0.1\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002080)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001627)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000266)\ninmanta.execute.schedulerINFO    Total compilation time 0.004150\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33071/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33071/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33071/api/v1/file/5309d4b5db445e9c423dc60125f5b50b2926239e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33071/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33071/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33071/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33071/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33071/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	b0b5918f-616e-4459-a12c-abc8a31542e9
e281dc95-9a11-444a-9abc-fa65c4a70592	2022-12-09 15:29:49.106243+01	2022-12-09 15:29:49.415334+01	/tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.2.0.dev0\nNot uninstalling inmanta-core at /home/florent/Desktop/inmanta-core/src, outside environment /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	0c79315d-a3b9-47c8-853e-3fc25aff081b
b2b7ca44-8517-4e52-a22b-512da2988e4a	2022-12-09 15:29:58.516789+01	2022-12-09 15:29:59.368062+01	/tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m inmanta.app -vvv export -X -e bba18e6b-7c0e-4ede-bf3a-da7219c95adf --server_address localhost --server_port 33071 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpa_pp4kr7 --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.004044 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000062 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V2 modules:\ninmanta.module           INFO      std: 4.0.1\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002043)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001857)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000283)\ninmanta.execute.schedulerINFO    Total compilation time 0.004364\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33071/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33071/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33071/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:33071/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:33071/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	0c79315d-a3b9-47c8-853e-3fc25aff081b
0342ddac-5824-491f-a82e-5b0add68f0e7	2022-12-09 15:29:49.416346+01	2022-12-09 15:29:58.515037+01	/tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000041 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade --upgrade-strategy only-if-needed inmanta-module-std inmanta-core==7.2.0.dev0 --no-index\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (4.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=1.9.0a1,~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2~=3.0->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic!=1.9.0a1,~=1.0->inmanta-core==7.2.0.dev0) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade --upgrade-strategy eager dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 email_validator~=1.3 pydantic~=1.10 inmanta-core==7.2.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in ./.env/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000036 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade --upgrade-strategy only-if-needed inmanta-module-std inmanta-core==7.2.0.dev0 --no-index\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (4.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=1.9.0a1,~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email-validator~=1.0->inmanta-core==7.2.0.dev0) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2~=3.0->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic!=1.9.0a1,~=1.0->inmanta-core==7.2.0.dev0) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Pip command: /tmp/tmpsy9gdoe5/server/environments/bba18e6b-7c0e-4ede-bf3a-da7219c95adf/.env/bin/python -m pip install --upgrade --upgrade-strategy eager dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 email_validator~=1.3 pydantic~=1.10 inmanta-core==7.2.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in ./.env/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==7.2.0.dev0 in /home/florent/Desktop/inmanta-core/src (7.2.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<39,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (38.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<6,>=4 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (21.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from inmanta-core==7.2.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (0.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.2.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.28.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.2.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<6,>=4->inmanta-core==7.2.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.2.0.dev0) (3.0.9)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.2.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.2.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.2.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.2.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (1.26.13)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.2.0.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\n	0	0c79315d-a3b9-47c8-853e-3fc25aff081b
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	std::AgentConfig[internal,agentname=localhost]	internal	2022-12-09 15:29:47.965842+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	std::File[localhost,path=/tmp/test]	localhost	2022-12-09 15:29:49.03517+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2	std::AgentConfig[internal,agentname=localhost]	internal	2022-12-09 15:29:59.293981+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2	std::File[localhost,path=/tmp/test]	localhost	2022-12-09 15:29:59.435709+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
ac629ca0-3239-4e38-8b06-4db4037c4f7c	store	2022-12-09 15:29:42.145879+01	2022-12-09 15:29:43.325212+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-12-09T15:29:43.325228+01:00\\"}"}	\N	\N	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
37a391c4-5ad6-4695-803d-afc534890cb5	pull	2022-12-09 15:29:44.354826+01	2022-12-09 15:29:44.357367+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-12-09T15:29:44.357378+01:00\\"}"}	\N	\N	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
927c6c92-7776-4714-8e9d-9c94938e87f4	pull	2022-12-09 15:29:46.098789+01	2022-12-09 15:29:46.100522+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-12-09T15:29:46.101304+01:00\\"}"}	\N	\N	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
d886aee2-572f-4adc-ade9-1855d641e6af	deploy	2022-12-09 15:29:46.099679+01	2022-12-09 15:29:46.712496+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-12-09 15:29:44+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-12-09 15:29:44+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"d6c82b6a-ffb3-4b83-970f-ada9c6d6054e\\"}, \\"timestamp\\": \\"2022-12-09T15:29:46.095796+01:00\\"}","{\\"msg\\": \\"Start deploy d6c82b6a-ffb3-4b83-970f-ada9c6d6054e of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"d6c82b6a-ffb3-4b83-970f-ada9c6d6054e\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:46.698791+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-09T15:29:46.700234+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-09T15:29:46.704091+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy d6c82b6a-ffb3-4b83-970f-ada9c6d6054e\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"d6c82b6a-ffb3-4b83-970f-ada9c6d6054e\\"}, \\"timestamp\\": \\"2022-12-09T15:29:46.707182+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
b0d4753a-3adc-41d6-b73a-7fe07a8fd6ea	deploy	2022-12-09 15:29:46.719776+01	2022-12-09 15:29:46.729924+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"9266fbec-22f6-4dc0-9f12-111c61ea82dc\\"}, \\"timestamp\\": \\"2022-12-09T15:29:46.716550+01:00\\"}","{\\"msg\\": \\"Start deploy 9266fbec-22f6-4dc0-9f12-111c61ea82dc of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"9266fbec-22f6-4dc0-9f12-111c61ea82dc\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:46.722904+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-09T15:29:46.723299+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 9266fbec-22f6-4dc0-9f12-111c61ea82dc\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"9266fbec-22f6-4dc0-9f12-111c61ea82dc\\"}, \\"timestamp\\": \\"2022-12-09T15:29:46.726826+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
0096ae9e-6a2c-4932-b187-2646f80d9ad6	pull	2022-12-09 15:29:46.735578+01	2022-12-09 15:29:47.335174+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-12-09T15:29:47.335188+01:00\\"}"}	\N	\N	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
42c22477-d19d-42d5-91e8-a4b48f2df8c4	pull	2022-12-09 15:29:59.418794+01	2022-12-09 15:29:59.420426+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-12-09T15:29:59.420437+01:00\\"}"}	\N	\N	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2	{"std::File[localhost,path=/tmp/test],v=2"}
2464339b-5fb0-4d60-a0ef-e1cfe9fb6423	deploy	2022-12-09 15:29:59.428649+01	2022-12-09 15:29:59.435709+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"f900ceb1-7212-44e8-b05f-277a07029ebb\\"}, \\"timestamp\\": \\"2022-12-09T15:29:59.426543+01:00\\"}","{\\"msg\\": \\"Start deploy f900ceb1-7212-44e8-b05f-277a07029ebb of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"f900ceb1-7212-44e8-b05f-277a07029ebb\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:59.430238+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-09T15:29:59.430840+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-12-09T15:29:59.432786+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:59.433037+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy f900ceb1-7212-44e8-b05f-277a07029ebb\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"f900ceb1-7212-44e8-b05f-277a07029ebb\\"}, \\"timestamp\\": \\"2022-12-09T15:29:59.433269+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2	{"std::File[localhost,path=/tmp/test],v=2"}
d71fd433-2435-4f43-80ef-4f64a79d4552	deploy	2022-12-09 15:29:47.957369+01	2022-12-09 15:29:47.965842+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2022-12-09 15:29:44+0100', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2022-12-09 15:29:44+0100', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b4586555-10a1-49f5-9b87-73ba158ff300\\"}, \\"timestamp\\": \\"2022-12-09T15:29:47.954341+01:00\\"}","{\\"msg\\": \\"Start deploy b4586555-10a1-49f5-9b87-73ba158ff300 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"b4586555-10a1-49f5-9b87-73ba158ff300\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:47.959420+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-09T15:29:47.960160+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy b4586555-10a1-49f5-9b87-73ba158ff300\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b4586555-10a1-49f5-9b87-73ba158ff300\\"}, \\"timestamp\\": \\"2022-12-09T15:29:47.963802+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
afe8b0a2-2a1e-433c-8aee-a892044299cb	pull	2022-12-09 15:29:47.726871+01	2022-12-09 15:29:48.364192+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-12-09T15:29:48.364211+01:00\\"}"}	\N	\N	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::File[localhost,path=/tmp/test],v=1"}
57545119-8e30-435a-9b5c-76561f7ec096	deploy	2022-12-09 15:29:49.0165+01	2022-12-09 15:29:49.03517+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-12-09 15:29:47+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-12-09 15:29:47+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"e1fbcf01-2443-45d2-a83f-1c00fc39111f\\"}, \\"timestamp\\": \\"2022-12-09T15:29:49.014505+01:00\\"}","{\\"msg\\": \\"Start deploy e1fbcf01-2443-45d2-a83f-1c00fc39111f of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"e1fbcf01-2443-45d2-a83f-1c00fc39111f\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:49.018328+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-09T15:29:49.019227+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-12-09T15:29:49.030494+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:49.031230+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy e1fbcf01-2443-45d2-a83f-1c00fc39111f\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"e1fbcf01-2443-45d2-a83f-1c00fc39111f\\"}, \\"timestamp\\": \\"2022-12-09T15:29:49.031641+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	1	{"std::File[localhost,path=/tmp/test],v=1"}
ee2bb546-c7d6-43c4-9d64-d5a75209146c	store	2022-12-09 15:29:59.279003+01	2022-12-09 15:29:59.280705+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-12-09T15:29:59.280713+01:00\\"}"}	\N	\N	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
bb49c6cf-40dc-4344-9320-f4802c781062	pull	2022-12-09 15:29:59.291869+01	2022-12-09 15:29:59.293869+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-12-09T15:29:59.294770+01:00\\"}"}	\N	\N	\N	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2	{"std::File[localhost,path=/tmp/test],v=2"}
375b39ed-c43a-4462-b792-aaa468afce88	deploy	2022-12-09 15:29:59.293981+01	2022-12-09 15:29:59.293981+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-12-09T14:29:59.293981+00:00\\"}"}	deployed	\N	nochange	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
3b559fd9-b40a-4ca5-bf85-fbe1d5369f26	deploy	2022-12-09 15:29:59.364199+01	2022-12-09 15:29:59.373378+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"6188a267-3c12-42f2-a016-5de399ff9231\\"}, \\"timestamp\\": \\"2022-12-09T15:29:59.359087+01:00\\"}","{\\"msg\\": \\"Start deploy 6188a267-3c12-42f2-a016-5de399ff9231 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"6188a267-3c12-42f2-a016-5de399ff9231\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:59.366401+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-12-09T15:29:59.367378+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-12-09T15:29:59.370292+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/home/florent/.virtualenvs/inmanta-core-new/lib/python3.9/site-packages/inmanta_plugins/std/resources.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-12-09T15:29:59.370561+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 6188a267-3c12-42f2-a016-5de399ff9231\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"6188a267-3c12-42f2-a016-5de399ff9231\\"}, \\"timestamp\\": \\"2022-12-09T15:29:59.370967+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	ac629ca0-3239-4e38-8b06-4db4037c4f7c	std::File[localhost,path=/tmp/test]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	ac629ca0-3239-4e38-8b06-4db4037c4f7c	std::AgentConfig[internal,agentname=localhost]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	37a391c4-5ad6-4695-803d-afc534890cb5	std::AgentConfig[internal,agentname=localhost]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	927c6c92-7776-4714-8e9d-9c94938e87f4	std::AgentConfig[internal,agentname=localhost]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	d886aee2-572f-4adc-ade9-1855d641e6af	std::AgentConfig[internal,agentname=localhost]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	b0d4753a-3adc-41d6-b73a-7fe07a8fd6ea	std::AgentConfig[internal,agentname=localhost]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	0096ae9e-6a2c-4932-b187-2646f80d9ad6	std::AgentConfig[internal,agentname=localhost]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	d71fd433-2435-4f43-80ef-4f64a79d4552	std::AgentConfig[internal,agentname=localhost]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	afe8b0a2-2a1e-433c-8aee-a892044299cb	std::File[localhost,path=/tmp/test]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	57545119-8e30-435a-9b5c-76561f7ec096	std::File[localhost,path=/tmp/test]	1
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	ee2bb546-c7d6-43c4-9d64-d5a75209146c	std::File[localhost,path=/tmp/test]	2
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	ee2bb546-c7d6-43c4-9d64-d5a75209146c	std::AgentConfig[internal,agentname=localhost]	2
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	bb49c6cf-40dc-4344-9320-f4802c781062	std::File[localhost,path=/tmp/test]	2
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	375b39ed-c43a-4462-b792-aaa468afce88	std::AgentConfig[internal,agentname=localhost]	2
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	3b559fd9-b40a-4ca5-bf85-fbe1d5369f26	std::File[localhost,path=/tmp/test]	2
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	42c22477-d19d-42d5-91e8-a4b48f2df8c4	std::File[localhost,path=/tmp/test]	2
bba18e6b-7c0e-4ede-bf3a-da7219c95adf	2464339b-5fb0-4d60-a0ef-e1cfe9fb6423	std::File[localhost,path=/tmp/test]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202212090}
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
-- Name: environmentmetricsgauge environmentmetricsgauge_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricsgauge
    ADD CONSTRAINT environmentmetricsgauge_pkey PRIMARY KEY (environment, metric_name, "timestamp");


--
-- Name: environmentmetricstimer environmentmetricstimer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricstimer
    ADD CONSTRAINT environmentmetricstimer_pkey PRIMARY KEY (environment, metric_name, "timestamp");


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
-- Name: environmentmetricsgauge environmentmetricsgauge_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricsgauge
    ADD CONSTRAINT environmentmetricsgauge_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: environmentmetricstimer environmentmetricstimer_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricstimer
    ADD CONSTRAINT environmentmetricstimer_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


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

