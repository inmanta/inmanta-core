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
    environment uuid NOT NULL,
    metric_name character varying NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    count integer NOT NULL,
    grouped_by character varying DEFAULT '__None__'::character varying NOT NULL
);


--
-- Name: environmentmetricstimer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environmentmetricstimer (
    environment uuid NOT NULL,
    metric_name character varying NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    count integer NOT NULL,
    value double precision NOT NULL,
    grouped_by character varying DEFAULT '__None__'::character varying NOT NULL
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
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	internal	2023-01-17 11:59:01.092963+01	f	1a68a5a4-bb4c-4160-9a0e-f41e0299d10f	\N
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	localhost	2023-01-17 11:59:03.615087+01	f	58286f27-308d-48b9-86b5-db8854b9f5f7	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
1a68a5a4-bb4c-4160-9a0e-f41e0299d10f	f2ee4120-9655-11ed-86d2-dd6535f336b8	internal	\N	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d
58286f27-308d-48b9-86b5-db8854b9f5f7	f2ee4120-9655-11ed-86d2-dd6535f336b8	localhost	\N	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2023-01-17 11:59:01.092963+01	2023-01-17 11:59:27.499197+01	\N	f2ee4120-9655-11ed-86d2-dd6535f336b8
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::Service	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::File	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::Directory	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::Package	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::Symlink	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::AgentConfig	1	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::Service	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::File	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::Directory	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::Package	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::Symlink	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	std::AgentConfig	2	{"5309d4b5db445e9c423dc60125f5b50b2926239e": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
a236c634-5fd9-49f6-a57d-c0bd4859ea9f	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2023-01-17 11:58:32.86389+01	2023-01-17 11:59:01.232358+01	2023-01-17 11:58:32.725918+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	eeba18ce-1bfb-4444-b110-3904df3bbdc4	t	\N	{"errors": []}	f	{}	\N	\N	\N
023e0c03-f79d-4b28-9550-9623524399ff	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2023-01-17 11:59:04.631146+01	2023-01-17 11:59:27.358936+01	2023-01-17 11:59:04.617709+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	4c8ae0c8-5898-4418-9c0a-9c05189ef7dc	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2023-01-17 11:58:58.375516+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2023-01-17 11:59:27.257248+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
0b650459-35b9-472a-bb5b-ee22aa315272	dev-2	9aed5360-be2b-4ee8-8422-3278e22953d7			{"auto_full_compile": ""}	0	f		
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	dev-1	9aed5360-be2b-4ee8-8422-3278e22953d7			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
\.


--
-- Data for Name: environmentmetricsgauge; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricsgauge (environment, metric_name, "timestamp", count, grouped_by) FROM stdin;
\.


--
-- Data for Name: environmentmetricstimer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricstimer (environment, metric_name, "timestamp", count, value, grouped_by) FROM stdin;
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
9aed5360-be2b-4ee8-8422-3278e22953d7	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
fbf34bea-5b81-4cf4-a071-d68b8722d32b	2023-01-17 11:58:32.864233+01	2023-01-17 11:58:32.865291+01		Init		Using extra environment variables during compile \n	0	a236c634-5fd9-49f6-a57d-c0bd4859ea9f
f3c728d9-e85f-4f78-99d7-eca75ea2065b	2023-01-17 11:58:32.86557+01	2023-01-17 11:58:32.883075+01		Creating venv			0	a236c634-5fd9-49f6-a57d-c0bd4859ea9f
39bab719-eb22-412e-a7fa-b03794eb2fc4	2023-01-17 11:58:32.891626+01	2023-01-17 11:58:33.297806+01	/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.0.1.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	a236c634-5fd9-49f6-a57d-c0bd4859ea9f
47374bfa-4c3c-4bf9-9d09-78b1dc12df1a	2023-01-17 11:58:33.298847+01	2023-01-17 11:58:57.48142+01	/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.0.2 on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.0.2 in /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000077 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.module           INFO    Checking out 4.0.2 on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 email_validator~=1.3 inmanta-core==8.0.1.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.0.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (38.0.1)\ninmanta.pip              DEBUG   Collecting cryptography<40,>=36\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/875/aea1039d78557/cryptography-39.0.0-cp36-abi3-manylinux_2_28_x86_64.whl (4.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<24.0,>=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (22.2.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/908/c78e6bc29b676/pip-22.3.1-py3-none-any.whl (2.1 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.2.1)\ninmanta.pip              DEBUG   Collecting dnspython>=1.15.0\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/891/41536394f9090/dnspython-2.3.0-py3-none-any.whl (283 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.0.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.0.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2.28.1)\ninmanta.pip              DEBUG   Collecting requests>=2.23.0\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/642/99f4909223da7/requests-2.28.2-py3-none-any.whl (62 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/003/aee64f9fd955d/python_slugify-7.0.0-py2.py3-none-any.whl (9.4 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.0.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.0.1.dev0) (3.8.1)\ninmanta.pip              DEBUG   Collecting zipp>=0.5\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/83a/28fcb75844b5c/zipp-3.11.0-py3-none-any.whl (6.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.0.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.0.1.dev0) (0.2.6)\ninmanta.pip              DEBUG   Collecting ruamel.yaml.clib>=0.2.6\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/a7b/301ff08055d73/ruamel.yaml.clib-0.2.7-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.manylinux_2_24_x86_64.whl (519 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.0.1.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (5.0.0)\ninmanta.pip              DEBUG   Collecting chardet>=3.0.2\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/362/777fb014af596/chardet-5.1.0-py3-none-any.whl (199 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.0.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.2.2)\ninmanta.pip              DEBUG   Collecting arrow\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/5a4/9ab92e3b7b71d/arrow-1.2.3-py3-none-any.whl (66 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2022.9.24)\ninmanta.pip              DEBUG   Collecting certifi>=2017.4.17\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/4ad/3232f5e926d67/certifi-2022.12.7-py3-none-any.whl (155 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.26.13)\ninmanta.pip              DEBUG   Collecting urllib3<1.27,>=1.21.1\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/75e/dcdc2f7d85b13/urllib3-1.26.14-py2.py3-none-any.whl (140 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2.1.0)\ninmanta.pip              DEBUG   Collecting charset-normalizer<4,>=2\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/3ae/1de54a77dc0d6/charset_normalizer-3.0.1-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (198 kB)\ninmanta.pip              DEBUG   Installing collected packages: charset-normalizer, zipp, urllib3, ruamel.yaml.clib, python-slugify, pip, dnspython, chardet, certifi, requests, cryptography, arrow\ninmanta.pip              DEBUG   Attempting uninstall: charset-normalizer\ninmanta.pip              DEBUG   Found existing installation: charset-normalizer 2.1.0\ninmanta.pip              DEBUG   Not uninstalling charset-normalizer at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: zipp\ninmanta.pip              DEBUG   Found existing installation: zipp 3.8.1\ninmanta.pip              DEBUG   Not uninstalling zipp at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'zipp'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: urllib3\ninmanta.pip              DEBUG   Found existing installation: urllib3 1.26.13\ninmanta.pip              DEBUG   Not uninstalling urllib3 at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: ruamel.yaml.clib\ninmanta.pip              DEBUG   Found existing installation: ruamel.yaml.clib 0.2.6\ninmanta.pip              DEBUG   Not uninstalling ruamel-yaml-clib at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'ruamel.yaml.clib'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 22.2.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: dnspython\ninmanta.pip              DEBUG   Found existing installation: dnspython 2.2.1\ninmanta.pip              DEBUG   Not uninstalling dnspython at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'dnspython'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: chardet\ninmanta.pip              DEBUG   Found existing installation: chardet 5.0.0\ninmanta.pip              DEBUG   Not uninstalling chardet at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'chardet'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: certifi\ninmanta.pip              DEBUG   Found existing installation: certifi 2022.9.24\ninmanta.pip              DEBUG   Not uninstalling certifi at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: requests\ninmanta.pip              DEBUG   Found existing installation: requests 2.28.1\ninmanta.pip              DEBUG   Not uninstalling requests at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'requests'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cryptography\ninmanta.pip              DEBUG   Found existing installation: cryptography 38.0.1\ninmanta.pip              DEBUG   Not uninstalling cryptography at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'cryptography'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: arrow\ninmanta.pip              DEBUG   Found existing installation: arrow 1.2.2\ninmanta.pip              DEBUG   Not uninstalling arrow at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\ninmanta.pip              DEBUG   Can't uninstall 'arrow'. No files were found to uninstall.\ninmanta.pip              DEBUG   Successfully installed arrow-1.2.3 certifi-2022.12.7 chardet-5.1.0 charset-normalizer-3.0.1 cryptography-39.0.0 dnspython-2.3.0 pip-22.3.1 python-slugify-7.0.0 requests-2.28.2 ruamel.yaml.clib-0.2.7 urllib3-1.26.14 zipp-3.11.0\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   [notice] A new release of pip available: 22.2.1 -> 22.3.1\ninmanta.pip              DEBUG   [notice] To update, run: /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m pip install --upgrade pip\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000041 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.module           INFO    Checking out 4.0.2 on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m pip install --upgrade --upgrade-strategy eager pydantic~=1.10 dataclasses~=0.7; python_version < "3.7" Jinja2~=3.1 email_validator~=1.3 inmanta-core==8.0.1.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.0.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (39.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<24.0,>=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.0.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.0.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.0.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.0.1.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.0.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.0.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.0.1.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.0.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (3.0.1)\ninmanta.module           INFO    verifying project\n	0	a236c634-5fd9-49f6-a57d-c0bd4859ea9f
0edfedbe-75f3-4a36-ba39-909a8922fd39	2023-01-17 11:59:04.637942+01	2023-01-17 11:59:04.987602+01	/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.0.1.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	023e0c03-f79d-4b28-9550-9623524399ff
2826ff0b-ee6f-42c5-9a18-faa1b2a0675b	2023-01-17 11:58:57.482456+01	2023-01-17 11:59:01.231216+01	/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m inmanta.app -vvv export -X -e c8a0c94a-ac9b-4667-ad76-f8a07a7d022d --server_address localhost --server_port 55659 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpq8nbk4su --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.003899 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000091 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.0.2\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001917)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001495)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000227)\ninmanta.execute.schedulerINFO    Total compilation time 0.003786\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55659/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55659/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55659/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55659/api/v1/file/5309d4b5db445e9c423dc60125f5b50b2926239e\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55659/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55659/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55659/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55659/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	a236c634-5fd9-49f6-a57d-c0bd4859ea9f
79db1e6e-baa3-4918-a26c-9f648470bd5e	2023-01-17 11:59:04.632526+01	2023-01-17 11:59:04.634235+01		Init		Using extra environment variables during compile \n	0	023e0c03-f79d-4b28-9550-9623524399ff
fb942720-986c-4d1f-aeeb-51747e114188	2023-01-17 11:59:04.988472+01	2023-01-17 11:59:26.36552+01	/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000068 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.module           INFO    Checking out 4.0.2 on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m pip install --upgrade --upgrade-strategy eager dataclasses~=0.7; python_version < "3.7" pydantic~=1.10 email_validator~=1.3 Jinja2~=3.1 inmanta-core==8.0.1.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.0.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (39.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<24.0,>=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.0.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.0.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.0.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.0.1.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.0.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.0.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.0.1.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.0.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (3.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2022.12.7)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000044 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.module           INFO    Checking out 4.0.2 on /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m pip install --upgrade --upgrade-strategy eager dataclasses~=0.7; python_version < "3.7" pydantic~=1.10 email_validator~=1.3 Jinja2~=3.1 inmanta-core==8.0.1.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (8.0.1.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (39.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<24.0,>=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.0.1.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.0.1.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.0.1.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.0.1.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in ./.env/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.0.1.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.0.1.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in ./.env/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.0.1.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.0.1.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in ./.env/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.0.1.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.0.1.dev0) (3.0.1)\ninmanta.module           INFO    verifying project\n	0	023e0c03-f79d-4b28-9550-9623524399ff
abff681c-1cbe-4755-91df-bd0e5e142a97	2023-01-17 11:59:26.366483+01	2023-01-17 11:59:27.35778+01	/tmp/tmpjazrvh4s/server/environments/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/.env/bin/python -m inmanta.app -vvv export -X -e c8a0c94a-ac9b-4667-ad76-f8a07a7d022d --server_address localhost --server_port 55659 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmphdac9fqb --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004223 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000092 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.0.2\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001881)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001553)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000223)\ninmanta.execute.schedulerINFO    Total compilation time 0.003797\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55659/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55659/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55659/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55659/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55659/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	023e0c03-f79d-4b28-9550-9623524399ff
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	1	std::AgentConfig[internal,agentname=localhost]	internal	2023-01-17 11:59:02.601065+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	1	std::File[localhost,path=/tmp/test]	localhost	2023-01-17 11:59:04.439196+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2	std::AgentConfig[internal,agentname=localhost]	internal	2023-01-17 11:59:27.268443+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2	std::File[localhost,path=/tmp/test]	localhost	2023-01-17 11:59:27.509926+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
a19f4706-de12-4466-a052-3cedebaf3320	store	2023-01-17 11:58:58.374805+01	2023-01-17 11:58:59.797413+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2023-01-17T11:58:59.797435+01:00\\"}"}	\N	\N	\N	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
37925abb-8e03-485d-bbea-3f735b23a5ae	pull	2023-01-17 11:59:01.102713+01	2023-01-17 11:59:01.845828+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-01-17T11:59:01.845849+01:00\\"}"}	\N	\N	\N	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
221d6eac-944b-4e99-b0e1-df60fe4e32c0	deploy	2023-01-17 11:59:02.579879+01	2023-01-17 11:59:02.601065+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-01-17 11:59:01+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-01-17 11:59:01+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"8714cd05-7a5c-44fd-b56a-2ecc3bfcd51e\\"}, \\"timestamp\\": \\"2023-01-17T11:59:02.577212+01:00\\"}","{\\"msg\\": \\"Start deploy 8714cd05-7a5c-44fd-b56a-2ecc3bfcd51e of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"8714cd05-7a5c-44fd-b56a-2ecc3bfcd51e\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-01-17T11:59:02.582755+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-17T11:59:02.583631+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-17T11:59:02.587041+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 8714cd05-7a5c-44fd-b56a-2ecc3bfcd51e\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"8714cd05-7a5c-44fd-b56a-2ecc3bfcd51e\\"}, \\"timestamp\\": \\"2023-01-17T11:59:02.591946+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
bce1cdf0-ddf6-48b2-99f9-76a00964d38a	pull	2023-01-17 11:59:03.630324+01	2023-01-17 11:59:03.634089+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-01-17T11:59:03.634116+01:00\\"}"}	\N	\N	\N	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	1	{"std::File[localhost,path=/tmp/test],v=1"}
8c00ace0-cbcf-4319-9221-93b5fea1d0b7	deploy	2023-01-17 11:59:04.383539+01	2023-01-17 11:59:04.439196+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2023-01-17 11:59:03+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2023-01-17 11:59:03+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"b9b379ad-8fea-447a-8358-3c695136f865\\"}, \\"timestamp\\": \\"2023-01-17T11:59:04.380592+01:00\\"}","{\\"msg\\": \\"Start deploy b9b379ad-8fea-447a-8358-3c695136f865 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"b9b379ad-8fea-447a-8358-3c695136f865\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-17T11:59:04.434116+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-17T11:59:04.434781+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-17T11:59:04.434883+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 929, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpjazrvh4s/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-17T11:59:04.436836+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy b9b379ad-8fea-447a-8358-3c695136f865\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"b9b379ad-8fea-447a-8358-3c695136f865\\"}, \\"timestamp\\": \\"2023-01-17T11:59:04.437047+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	1	{"std::File[localhost,path=/tmp/test],v=1"}
7c96798f-9e57-4d1e-8f7f-71df35589c5e	store	2023-01-17 11:59:27.257039+01	2023-01-17 11:59:27.258545+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2023-01-17T11:59:27.258556+01:00\\"}"}	\N	\N	\N	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
8a0f86da-74f5-4e26-a6ad-0f4df0fb816f	pull	2023-01-17 11:59:27.266988+01	2023-01-17 11:59:27.268618+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-01-17T11:59:27.269536+01:00\\"}"}	\N	\N	\N	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2	{"std::File[localhost,path=/tmp/test],v=2"}
81fd006d-3d5a-4be9-a5cb-c9392ca5b603	deploy	2023-01-17 11:59:27.268443+01	2023-01-17 11:59:27.268443+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-01-17T10:59:27.268443+00:00\\"}"}	deployed	\N	nochange	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
3b961314-51b5-437b-b038-91b6678f785a	deploy	2023-01-17 11:59:27.333853+01	2023-01-17 11:59:27.339753+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"78a36f22-be35-4266-93ea-185c266b6057\\"}, \\"timestamp\\": \\"2023-01-17T11:59:27.330572+01:00\\"}","{\\"msg\\": \\"Start deploy 78a36f22-be35-4266-93ea-185c266b6057 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"78a36f22-be35-4266-93ea-185c266b6057\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-17T11:59:27.335368+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-17T11:59:27.335722+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-01-17T11:59:27.337382+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpjazrvh4s/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-17T11:59:27.337542+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 78a36f22-be35-4266-93ea-185c266b6057\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"78a36f22-be35-4266-93ea-185c266b6057\\"}, \\"timestamp\\": \\"2023-01-17T11:59:27.337726+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2	{"std::File[localhost,path=/tmp/test],v=2"}
422f68dc-58bb-4d99-b645-f8a029d5ba41	pull	2023-01-17 11:59:27.499289+01	2023-01-17 11:59:27.500073+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-01-17T11:59:27.500083+01:00\\"}"}	\N	\N	\N	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2	{"std::File[localhost,path=/tmp/test],v=2"}
70baf299-01cd-4e3d-af58-6128ca0cad79	deploy	2023-01-17 11:59:27.505466+01	2023-01-17 11:59:27.509926+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"ea461fb4-2a4b-43f5-8236-1c6abe87c98f\\"}, \\"timestamp\\": \\"2023-01-17T11:59:27.503905+01:00\\"}","{\\"msg\\": \\"Start deploy ea461fb4-2a4b-43f5-8236-1c6abe87c98f of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"ea461fb4-2a4b-43f5-8236-1c6abe87c98f\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-17T11:59:27.506555+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-17T11:59:27.506875+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-01-17T11:59:27.507958+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpjazrvh4s/c8a0c94a-ac9b-4667-ad76-f8a07a7d022d/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-17T11:59:27.508104+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy ea461fb4-2a4b-43f5-8236-1c6abe87c98f\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"ea461fb4-2a4b-43f5-8236-1c6abe87c98f\\"}, \\"timestamp\\": \\"2023-01-17T11:59:27.508256+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	a19f4706-de12-4466-a052-3cedebaf3320	std::File[localhost,path=/tmp/test]	1
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	a19f4706-de12-4466-a052-3cedebaf3320	std::AgentConfig[internal,agentname=localhost]	1
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	37925abb-8e03-485d-bbea-3f735b23a5ae	std::AgentConfig[internal,agentname=localhost]	1
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	221d6eac-944b-4e99-b0e1-df60fe4e32c0	std::AgentConfig[internal,agentname=localhost]	1
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	bce1cdf0-ddf6-48b2-99f9-76a00964d38a	std::File[localhost,path=/tmp/test]	1
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	8c00ace0-cbcf-4319-9221-93b5fea1d0b7	std::File[localhost,path=/tmp/test]	1
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	7c96798f-9e57-4d1e-8f7f-71df35589c5e	std::File[localhost,path=/tmp/test]	2
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	7c96798f-9e57-4d1e-8f7f-71df35589c5e	std::AgentConfig[internal,agentname=localhost]	2
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	8a0f86da-74f5-4e26-a6ad-0f4df0fb816f	std::File[localhost,path=/tmp/test]	2
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	81fd006d-3d5a-4be9-a5cb-c9392ca5b603	std::AgentConfig[internal,agentname=localhost]	2
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	3b961314-51b5-437b-b038-91b6678f785a	std::File[localhost,path=/tmp/test]	2
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	422f68dc-58bb-4d99-b645-f8a029d5ba41	std::File[localhost,path=/tmp/test]	2
c8a0c94a-ac9b-4667-ad76-f8a07a7d022d	70baf299-01cd-4e3d-af58-6128ca0cad79	std::File[localhost,path=/tmp/test]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301170}
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
    ADD CONSTRAINT environmentmetricsgauge_pkey PRIMARY KEY (environment, metric_name, grouped_by, "timestamp");


--
-- Name: environmentmetricstimer environmentmetricstimer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricstimer
    ADD CONSTRAINT environmentmetricstimer_pkey PRIMARY KEY (environment, metric_name, grouped_by, "timestamp");


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
-- Name: compile_environment_completed_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_environment_completed_idx ON public.compile USING btree (environment, completed DESC);


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
-- Name: resource_environment_status_model_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_status_model_idx ON public.resource USING btree (environment, status, model DESC);


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

