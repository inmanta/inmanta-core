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
    compile_data jsonb,
    partial boolean DEFAULT false,
    removed_resource_sets character varying[] DEFAULT ARRAY[]::character varying[],
    exporter_plugin character varying DEFAULT ''::character varying
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
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	internal	2022-09-20 10:50:03.410742+02	f	08cc840b-9f99-4501-b787-bdac42394101	\N
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	localhost	2022-09-20 10:50:05.998065+02	f	2924a2ce-3779-4f92-b515-4037125723b5	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
08cc840b-9f99-4501-b787-bdac42394101	37c2b1a2-38c1-11ed-9a4f-3724d52cf7da	internal	\N	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd
2924a2ce-3779-4f92-b515-4037125723b5	37c2b1a2-38c1-11ed-9a4f-3724d52cf7da	localhost	\N	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2022-09-20 10:50:03.410742+02	2022-09-20 10:50:18.670109+02	\N	37c2b1a2-38c1-11ed-9a4f-3724d52cf7da
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::Service	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::File	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::Directory	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::Package	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::Symlink	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::AgentConfig	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::Service	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::File	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::Directory	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::Package	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::Symlink	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	std::AgentConfig	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, exporter_plugin) FROM stdin;
755da0cd-1fd6-468a-98f9-1b6289f6dd4c	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2022-09-20 10:49:49.258701+02	2022-09-20 10:50:03.601707+02	2022-09-20 10:49:49.121998+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	13875782-03cb-4521-8983-d204d11c20c4	t	\N	{"errors": []}	f	{}	\N
3bea5eb7-5903-4af5-a1ca-62b7281c3a75	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2022-09-20 10:50:08.333221+02	2022-09-20 10:50:18.610607+02	2022-09-20 10:50:08.321246+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	64e6d0cb-5f1b-4574-b4ba-ce9ccfbabe39	t	\N	{"errors": []}	f	{}	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2022-09-20 10:50:01.319416+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2022-09-20 10:50:18.518812+02	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
cdb5f7eb-fed3-492e-8704-189af095525e	dev-2	c27ccfa3-81f6-4eb7-a607-ae8b29e898be			{"auto_full_compile": ""}	0	f		
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	dev-1	c27ccfa3-81f6-4eb7-a607-ae8b29e898be			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
c27ccfa3-81f6-4eb7-a607-ae8b29e898be	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
b93e2332-ec2a-4f45-aedd-b426cc447b77	2022-09-20 10:49:49.259084+02	2022-09-20 10:49:49.260302+02		Init		Using extra environment variables during compile \n	0	755da0cd-1fd6-468a-98f9-1b6289f6dd4c
5a32f4a8-61f8-4f16-baf7-f92d95c83fdd	2022-09-20 10:49:49.260588+02	2022-09-20 10:49:49.266922+02		Creating venv			0	755da0cd-1fd6-468a-98f9-1b6289f6dd4c
cef57d41-c00e-4d00-b02a-3bad50ad9c68	2022-09-20 10:49:49.271714+02	2022-09-20 10:49:49.617318+02	/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	755da0cd-1fd6-468a-98f9-1b6289f6dd4c
0470be6e-1893-4760-b81e-2f1d7ba2e1b0	2022-09-20 10:49:49.61828+02	2022-09-20 10:50:00.42194+02	/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.env              DEBUG   Cloning into '/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std'...\ninmanta.env              DEBUG   remote: Enumerating objects: 2468, done.\ninmanta.env              DEBUG   remote: Counting objects:   0% (1/647)        \rremote: Counting objects:   1% (7/647)        \rremote: Counting objects:   2% (13/647)        \rremote: Counting objects:   3% (20/647)        \rremote: Counting objects:   4% (26/647)        \rremote: Counting objects:   5% (33/647)        \rremote: Counting objects:   6% (39/647)        \rremote: Counting objects:   7% (46/647)        \rremote: Counting objects:   8% (52/647)        \rremote: Counting objects:   9% (59/647)        \rremote: Counting objects:  10% (65/647)        \rremote: Counting objects:  11% (72/647)        \rremote: Counting objects:  12% (78/647)        \rremote: Counting objects:  13% (85/647)        \rremote: Counting objects:  14% (91/647)        \rremote: Counting objects:  15% (98/647)        \rremote: Counting objects:  16% (104/647)        \rremote: Counting objects:  17% (110/647)        \rremote: Counting objects:  18% (117/647)        \rremote: Counting objects:  19% (123/647)        \rremote: Counting objects:  20% (130/647)        \rremote: Counting objects:  21% (136/647)        \rremote: Counting objects:  22% (143/647)        \rremote: Counting objects:  23% (149/647)        \rremote: Counting objects:  24% (156/647)        \rremote: Counting objects:  25% (162/647)        \rremote: Counting objects:  26% (169/647)        \rremote: Counting objects:  27% (175/647)        \rremote: Counting objects:  28% (182/647)        \rremote: Counting objects:  29% (188/647)        \rremote: Counting objects:  30% (195/647)        \rremote: Counting objects:  31% (201/647)        \rremote: Counting objects:  32% (208/647)        \rremote: Counting objects:  33% (214/647)        \rremote: Counting objects:  34% (220/647)        \rremote: Counting objects:  35% (227/647)        \rremote: Counting objects:  36% (233/647)        \rremote: Counting objects:  37% (240/647)        \rremote: Counting objects:  38% (246/647)        \rremote: Counting objects:  39% (253/647)        \rremote: Counting objects:  40% (259/647)        \rremote: Counting objects:  41% (266/647)        \rremote: Counting objects:  42% (272/647)        \rremote: Counting objects:  43% (279/647)        \rremote: Counting objects:  44% (285/647)        \rremote: Counting objects:  45% (292/647)        \rremote: Counting objects:  46% (298/647)        \rremote: Counting objects:  47% (305/647)        \rremote: Counting objects:  48% (311/647)        \rremote: Counting objects:  49% (318/647)        \rremote: Counting objects:  50% (324/647)        \rremote: Counting objects:  51% (330/647)        \rremote: Counting objects:  52% (337/647)        \rremote: Counting objects:  53% (343/647)        \rremote: Counting objects:  54% (350/647)        \rremote: Counting objects:  55% (356/647)        \rremote: Counting objects:  56% (363/647)        \rremote: Counting objects:  57% (369/647)        \rremote: Counting objects:  58% (376/647)        \rremote: Counting objects:  59% (382/647)        \rremote: Counting objects:  60% (389/647)        \rremote: Counting objects:  61% (395/647)        \rremote: Counting objects:  62% (402/647)        \rremote: Counting objects:  63% (408/647)        \rremote: Counting objects:  64% (415/647)        \rremote: Counting objects:  65% (421/647)        \rremote: Counting objects:  66% (428/647)        \rremote: Counting objects:  67% (434/647)        \rremote: Counting objects:  68% (440/647)        \rremote: Counting objects:  69% (447/647)        \rremote: Counting objects:  70% (453/647)        \rremote: Counting objects:  71% (460/647)        \rremote: Counting objects:  72% (466/647)        \rremote: Counting objects:  73% (473/647)        \rremote: Counting objects:  74% (479/647)        \rremote: Counting objects:  75% (486/647)        \rremote: Counting objects:  76% (492/647)        \rremote: Counting objects:  77% (499/647)        \rremote: Counting objects:  78% (505/647)        \rremote: Counting objects:  79% (512/647)        \rremote: Counting objects:  80% (518/647)        \rremote: Counting objects:  81% (525/647)        \rremote: Counting objects:  82% (531/647)        \rremote: Counting objects:  83% (538/647)        \rremote: Counting objects:  84% (544/647)        \rremote: Counting objects:  85% (550/647)        \rremote: Counting objects:  86% (557/647)        \rremote: Counting objects:  87% (563/647)        \rremote: Counting objects:  88% (570/647)        \rremote: Counting objects:  89% (576/647)        \rremote: Counting objects:  90% (583/647)        \rremote: Counting objects:  91% (589/647)        \rremote: Counting objects:  92% (596/647)        \rremote: Counting objects:  93% (602/647)        \rremote: Counting objects:  94% (609/647)        \rremote: Counting objects:  95% (615/647)        \rremote: Counting objects:  96% (622/647)        \rremote: Counting objects:  97% (628/647)        \rremote: Counting objects:  98% (635/647)        \rremote: Counting objects:  99% (641/647)        \rremote: Counting objects: 100% (647/647)        \rremote: Counting objects: 100% (647/647), done.\ninmanta.env              DEBUG   remote: Compressing objects:   0% (1/311)        \rremote: Compressing objects:   1% (4/311)        \rremote: Compressing objects:   2% (7/311)        \rremote: Compressing objects:   3% (10/311)        \rremote: Compressing objects:   4% (13/311)        \rremote: Compressing objects:   5% (16/311)        \rremote: Compressing objects:   6% (19/311)        \rremote: Compressing objects:   7% (22/311)        \rremote: Compressing objects:   8% (25/311)        \rremote: Compressing objects:   9% (28/311)        \rremote: Compressing objects:  10% (32/311)        \rremote: Compressing objects:  11% (35/311)        \rremote: Compressing objects:  12% (38/311)        \rremote: Compressing objects:  13% (41/311)        \rremote: Compressing objects:  14% (44/311)        \rremote: Compressing objects:  15% (47/311)        \rremote: Compressing objects:  16% (50/311)        \rremote: Compressing objects:  17% (53/311)        \rremote: Compressing objects:  18% (56/311)        \rremote: Compressing objects:  19% (60/311)        \rremote: Compressing objects:  20% (63/311)        \rremote: Compressing objects:  21% (66/311)        \rremote: Compressing objects:  22% (69/311)        \rremote: Compressing objects:  23% (72/311)        \rremote: Compressing objects:  24% (75/311)        \rremote: Compressing objects:  25% (78/311)        \rremote: Compressing objects:  26% (81/311)        \rremote: Compressing objects:  27% (84/311)        \rremote: Compressing objects:  28% (88/311)        \rremote: Compressing objects:  29% (91/311)        \rremote: Compressing objects:  30% (94/311)        \rremote: Compressing objects:  31% (97/311)        \rremote: Compressing objects:  32% (100/311)        \rremote: Compressing objects:  33% (103/311)        \rremote: Compressing objects:  34% (106/311)        \rremote: Compressing objects:  35% (109/311)        \rremote: Compressing objects:  36% (112/311)        \rremote: Compressing objects:  37% (116/311)        \rremote: Compressing objects:  38% (119/311)        \rremote: Compressing objects:  39% (122/311)        \rremote: Compressing objects:  40% (125/311)        \rremote: Compressing objects:  41% (128/311)        \rremote: Compressing objects:  42% (131/311)        \rremote: Compressing objects:  43% (134/311)        \rremote: Compressing objects:  44% (137/311)        \rremote: Compressing objects:  45% (140/311)        \rremote: Compressing objects:  46% (144/311)        \rremote: Compressing objects:  47% (147/311)        \rremote: Compressing objects:  48% (150/311)        \rremote: Compressing objects:  49% (153/311)        \rremote: Compressing objects:  50% (156/311)        \rremote: Compressing objects:  51% (159/311)        \rremote: Compressing objects:  52% (162/311)        \rremote: Compressing objects:  53% (165/311)        \rremote: Compressing objects:  54% (168/311)        \rremote: Compressing objects:  55% (172/311)        \rremote: Compressing objects:  56% (175/311)        \rremote: Compressing objects:  57% (178/311)        \rremote: Compressing objects:  58% (181/311)        \rremote: Compressing objects:  59% (184/311)        \rremote: Compressing objects:  60% (187/311)        \rremote: Compressing objects:  61% (190/311)        \rremote: Compressing objects:  62% (193/311)        \rremote: Compressing objects:  63% (196/311)        \rremote: Compressing objects:  64% (200/311)        \rremote: Compressing objects:  65% (203/311)        \rremote: Compressing objects:  66% (206/311)        \rremote: Compressing objects:  67% (209/311)        \rremote: Compressing objects:  68% (212/311)        \rremote: Compressing objects:  69% (215/311)        \rremote: Compressing objects:  70% (218/311)        \rremote: Compressing objects:  71% (221/311)        \rremote: Compressing objects:  72% (224/311)        \rremote: Compressing objects:  73% (228/311)        \rremote: Compressing objects:  74% (231/311)        \rremote: Compressing objects:  75% (234/311)        \rremote: Compressing objects:  76% (237/311)        \rremote: Compressing objects:  77% (240/311)        \rremote: Compressing objects:  78% (243/311)        \rremote: Compressing objects:  79% (246/311)        \rremote: Compressing objects:  80% (249/311)        \rremote: Compressing objects:  81% (252/311)        \rremote: Compressing objects:  82% (256/311)        \rremote: Compressing objects:  83% (259/311)        \rremote: Compressing objects:  84% (262/311)        \rremote: Compressing objects:  85% (265/311)        \rremote: Compressing objects:  86% (268/311)        \rremote: Compressing objects:  87% (271/311)        \rremote: Compressing objects:  88% (274/311)        \rremote: Compressing objects:  89% (277/311)        \rremote: Compressing objects:  90% (280/311)        \rremote: Compressing objects:  91% (284/311)        \rremote: Compressing objects:  92% (287/311)        \rremote: Compressing objects:  93% (290/311)        \rremote: Compressing objects:  94% (293/311)        \rremote: Compressing objects:  95% (296/311)        \rremote: Compressing objects:  96% (299/311)        \rremote: Compressing objects:  97% (302/311)        \rremote: Compressing objects:  98% (305/311)        \rremote: Compressing objects:  99% (308/311)        \rremote: Compressing objects: 100% (311/311)        \rremote: Compressing objects: 100% (311/311), done.\ninmanta.env              DEBUG   Receiving objects:   0% (1/2468)\rReceiving objects:   1% (25/2468)\rReceiving objects:   2% (50/2468)\rReceiving objects:   3% (75/2468)\rReceiving objects:   4% (99/2468)\rReceiving objects:   5% (124/2468)\rReceiving objects:   6% (149/2468)\rReceiving objects:   7% (173/2468)\rReceiving objects:   8% (198/2468)\rReceiving objects:   9% (223/2468)\rReceiving objects:  10% (247/2468)\rReceiving objects:  11% (272/2468)\rReceiving objects:  12% (297/2468)\rReceiving objects:  13% (321/2468)\rReceiving objects:  14% (346/2468)\rReceiving objects:  15% (371/2468)\rReceiving objects:  16% (395/2468)\rReceiving objects:  17% (420/2468)\rReceiving objects:  18% (445/2468)\rReceiving objects:  19% (469/2468)\rReceiving objects:  20% (494/2468)\rReceiving objects:  21% (519/2468)\rReceiving objects:  22% (543/2468)\rReceiving objects:  23% (568/2468)\rReceiving objects:  24% (593/2468)\rReceiving objects:  25% (617/2468)\rReceiving objects:  26% (642/2468)\rReceiving objects:  27% (667/2468)\rReceiving objects:  28% (692/2468)\rReceiving objects:  29% (716/2468)\rReceiving objects:  30% (741/2468)\rReceiving objects:  31% (766/2468)\rReceiving objects:  32% (790/2468)\rReceiving objects:  33% (815/2468)\rReceiving objects:  34% (840/2468)\rReceiving objects:  35% (864/2468)\rReceiving objects:  36% (889/2468)\rReceiving objects:  37% (914/2468)\rReceiving objects:  38% (938/2468)\rReceiving objects:  39% (963/2468)\rReceiving objects:  40% (988/2468)\rReceiving objects:  41% (1012/2468)\rReceiving objects:  42% (1037/2468)\rReceiving objects:  43% (1062/2468)\rReceiving objects:  44% (1086/2468)\rReceiving objects:  45% (1111/2468)\rReceiving objects:  46% (1136/2468)\rReceiving objects:  47% (1160/2468)\rReceiving objects:  48% (1185/2468)\rReceiving objects:  49% (1210/2468)\rReceiving objects:  50% (1234/2468)\rReceiving objects:  51% (1259/2468)\rReceiving objects:  52% (1284/2468)\rReceiving objects:  53% (1309/2468)\rReceiving objects:  54% (1333/2468)\rReceiving objects:  55% (1358/2468)\rReceiving objects:  56% (1383/2468)\rReceiving objects:  57% (1407/2468)\rReceiving objects:  58% (1432/2468)\rReceiving objects:  59% (1457/2468)\rReceiving objects:  60% (1481/2468)\rReceiving objects:  61% (1506/2468)\rReceiving objects:  62% (1531/2468)\rReceiving objects:  63% (1555/2468)\rReceiving objects:  64% (1580/2468)\rReceiving objects:  65% (1605/2468)\rReceiving objects:  66% (1629/2468)\rReceiving objects:  67% (1654/2468)\rReceiving objects:  68% (1679/2468)\rReceiving objects:  69% (1703/2468)\rReceiving objects:  70% (1728/2468)\rReceiving objects:  71% (1753/2468)\rReceiving objects:  72% (1777/2468)\rReceiving objects:  73% (1802/2468)\rReceiving objects:  74% (1827/2468)\rReceiving objects:  75% (1851/2468)\rReceiving objects:  76% (1876/2468)\rReceiving objects:  77% (1901/2468)\rReceiving objects:  78% (1926/2468)\rReceiving objects:  79% (1950/2468)\rReceiving objects:  80% (1975/2468)\rReceiving objects:  81% (2000/2468)\rReceiving objects:  82% (2024/2468)\rReceiving objects:  83% (2049/2468)\rReceiving objects:  84% (2074/2468)\rReceiving objects:  85% (2098/2468)\rReceiving objects:  86% (2123/2468)\rReceiving objects:  87% (2148/2468)\rReceiving objects:  88% (2172/2468)\rReceiving objects:  89% (2197/2468)\rReceiving objects:  90% (2222/2468)\rReceiving objects:  91% (2246/2468)\rReceiving objects:  92% (2271/2468)\rReceiving objects:  93% (2296/2468)\rReceiving objects:  94% (2320/2468)\rReceiving objects:  95% (2345/2468)\rremote: Total 2468 (delta 339), reused 563 (delta 292), pack-reused 1821\ninmanta.env              DEBUG   Receiving objects:  96% (2370/2468)\rReceiving objects:  97% (2394/2468)\rReceiving objects:  98% (2419/2468)\rReceiving objects:  99% (2444/2468)\rReceiving objects: 100% (2468/2468)\rReceiving objects: 100% (2468/2468), 500.80 KiB | 4.68 MiB/s, done.\ninmanta.env              DEBUG   Resolving deltas:   0% (0/1307)\rResolving deltas:   1% (14/1307)\rResolving deltas:   5% (78/1307)\rResolving deltas:   6% (91/1307)\rResolving deltas:   7% (100/1307)\rResolving deltas:  12% (164/1307)\rResolving deltas:  13% (181/1307)\rResolving deltas:  14% (189/1307)\rResolving deltas:  15% (201/1307)\rResolving deltas:  17% (226/1307)\rResolving deltas:  18% (238/1307)\rResolving deltas:  19% (256/1307)\rResolving deltas:  22% (298/1307)\rResolving deltas:  23% (312/1307)\rResolving deltas:  24% (323/1307)\rResolving deltas:  31% (413/1307)\rResolving deltas:  34% (446/1307)\rResolving deltas:  39% (520/1307)\rResolving deltas:  40% (523/1307)\rResolving deltas:  41% (539/1307)\rResolving deltas:  43% (567/1307)\rResolving deltas:  44% (577/1307)\rResolving deltas:  45% (589/1307)\rResolving deltas:  47% (625/1307)\rResolving deltas:  48% (630/1307)\rResolving deltas:  49% (641/1307)\rResolving deltas:  50% (654/1307)\rResolving deltas:  51% (669/1307)\rResolving deltas:  52% (681/1307)\rResolving deltas:  53% (696/1307)\rResolving deltas:  54% (717/1307)\rResolving deltas:  57% (745/1307)\rResolving deltas:  59% (783/1307)\rResolving deltas:  60% (785/1307)\rResolving deltas:  61% (803/1307)\rResolving deltas:  62% (812/1307)\rResolving deltas:  63% (825/1307)\rResolving deltas:  64% (839/1307)\rResolving deltas:  65% (851/1307)\rResolving deltas:  66% (865/1307)\rResolving deltas:  67% (876/1307)\rResolving deltas:  68% (897/1307)\rResolving deltas:  69% (902/1307)\rResolving deltas:  74% (968/1307)\rResolving deltas:  76% (995/1307)\rResolving deltas:  85% (1113/1307)\rResolving deltas:  88% (1154/1307)\rResolving deltas:  90% (1183/1307)\rResolving deltas:  92% (1207/1307)\rResolving deltas:  93% (1220/1307)\rResolving deltas:  94% (1234/1307)\rResolving deltas:  95% (1245/1307)\rResolving deltas:  96% (1255/1307)\rResolving deltas: 100% (1307/1307)\rResolving deltas: 100% (1307/1307), done.\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 3.1.4 in /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std from https://github.com/inmanta/std.\ninmanta.module           DEBUG   Parsing took 0.000280 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Collecting email_validator~=1.1\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/816/073f2a7cffef7/email_validator-1.3.0-py2.py3-none-any.whl (22 kB)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (38.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.15)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib_metadata~=4.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.1)\ninmanta.env              DEBUG   Collecting pip>=21.3\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b61/a374b5bc40a6e/pip-22.2.2-py3-none-any.whl (2.0 MB)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Collecting PyJWT~=2.0\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/8d8/2e7087868e94d/PyJWT-2.5.0-py3-none-any.whl (20 kB)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Collecting idna>=2.0.0\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/90b/77e79eaa3eba6/idna-3.4-py3-none-any.whl (61 kB)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.12.0)\ninmanta.env              DEBUG   Collecting pep517>=0.9.1\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/4ba/4446d80aed5b5/pep517-0.13.0-py3-none-any.whl (18 kB)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Collecting arrow\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/5a4/9ab92e3b7b71d/arrow-1.2.3-py3-none-any.whl (66 kB)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Collecting urllib3<1.27,>=1.21.1\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b93/0dd878d5a8afb/urllib3-1.26.12-py2.py3-none-any.whl (140 kB)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.env              DEBUG   Collecting charset-normalizer<3,>=2\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/83e/9a75d1911279a/charset_normalizer-2.1.1-py3-none-any.whl (39 kB)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.env              DEBUG   Collecting certifi>=2017.4.17\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/e23/2343de1ab72c2/certifi-2022.9.14-py3-none-any.whl (162 kB)\ninmanta.env              DEBUG   Installing collected packages: urllib3, PyJWT, pip, pep517, idna, charset-normalizer, certifi, email_validator, arrow\ninmanta.env              DEBUG   Attempting uninstall: urllib3\ninmanta.env              DEBUG   Found existing installation: urllib3 1.26.11\ninmanta.env              DEBUG   Not uninstalling urllib3 at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: PyJWT\ninmanta.env              DEBUG   Found existing installation: PyJWT 2.4.0\ninmanta.env              DEBUG   Not uninstalling pyjwt at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'PyJWT'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: pip\ninmanta.env              DEBUG   Found existing installation: pip 22.2.1\ninmanta.env              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: pep517\ninmanta.env              DEBUG   Found existing installation: pep517 0.12.0\ninmanta.env              DEBUG   Not uninstalling pep517 at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'pep517'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: idna\ninmanta.env              DEBUG   Found existing installation: idna 3.3\ninmanta.env              DEBUG   Not uninstalling idna at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'idna'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: charset-normalizer\ninmanta.env              DEBUG   Found existing installation: charset-normalizer 2.1.0\ninmanta.env              DEBUG   Not uninstalling charset-normalizer at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: certifi\ninmanta.env              DEBUG   Found existing installation: certifi 2022.6.15\ninmanta.env              DEBUG   Not uninstalling certifi at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: email_validator\ninmanta.env              DEBUG   Found existing installation: email-validator 1.2.1\ninmanta.env              DEBUG   Not uninstalling email-validator at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'email-validator'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: arrow\ninmanta.env              DEBUG   Found existing installation: arrow 1.2.2\ninmanta.env              DEBUG   Not uninstalling arrow at /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\ninmanta.env              DEBUG   Can't uninstall 'arrow'. No files were found to uninstall.\ninmanta.env              DEBUG   Successfully installed PyJWT-2.5.0 arrow-1.2.3 certifi-2022.9.14 charset-normalizer-2.1.1 email_validator-1.3.0 idna-3.4 pep517-0.13.0 pip-22.2.2 urllib3-1.26.12\ninmanta.env              DEBUG   \ninmanta.env              DEBUG   [notice] A new release of pip available: 22.2.1 -> 22.2.2\ninmanta.env              DEBUG   [notice] To update, run: /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env/bin/python -m pip install --upgrade pip\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000040 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (38.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.15)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib_metadata~=4.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.5.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.9.14)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.module           INFO    verifying project\n	0	755da0cd-1fd6-468a-98f9-1b6289f6dd4c
48a202bf-e096-4fec-8dd1-35586a27babf	2022-09-20 10:50:00.422757+02	2022-09-20 10:50:03.600406+02	/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env/bin/python -m inmanta.app -vvv export -X -e 11eda7dd-97d8-44ba-ba90-152d5f9ffcbd --server_address localhost --server_port 50149 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp6klk1v3p	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003265 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000093 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001904)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001253)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000039)\ninmanta.execute.schedulerINFO    Total compilation time 0.003248\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50149/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50149/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50149/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50149/api/v1/file/63ae135b9a2eb874b3aa81fe5bd84283ef3617c9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50149/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50149/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50149/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50149/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	755da0cd-1fd6-468a-98f9-1b6289f6dd4c
9478df25-8a93-4567-a801-81425c83363a	2022-09-20 10:50:08.334355+02	2022-09-20 10:50:08.336802+02		Init		Using extra environment variables during compile \n	0	3bea5eb7-5903-4af5-a1ca-62b7281c3a75
475f229a-11b2-4f0e-9799-9f244ae5dab4	2022-09-20 10:50:08.346149+02	2022-09-20 10:50:08.711783+02	/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	3bea5eb7-5903-4af5-a1ca-62b7281c3a75
928bc7bb-44df-409e-9a21-81d6fbe65907	2022-09-20 10:50:17.639792+02	2022-09-20 10:50:18.609383+02	/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env/bin/python -m inmanta.app -vvv export -X -e 11eda7dd-97d8-44ba-ba90-152d5f9ffcbd --server_address localhost --server_port 50149 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmppbifn9pl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003185 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000089 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001863)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001258)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000039)\ninmanta.execute.schedulerINFO    Total compilation time 0.003211\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50149/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50149/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50149/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:50149/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:50149/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	3bea5eb7-5903-4af5-a1ca-62b7281c3a75
429e3d9f-95e1-4fe9-bb4b-2ba5d900cfaa	2022-09-20 10:50:08.712646+02	2022-09-20 10:50:17.638894+02	/tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000068 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (38.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.15)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib_metadata~=4.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.5.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.9.14)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000041 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpicuidbvv/server/environments/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in ./.env/lib/python3.9/site-packages (1.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<39,>=36 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (38.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.15)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib_metadata~=4.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.5.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in ./.env/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cryptography<39,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from importlib_metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<39,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/inmanta-core/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.9.14)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\n	0	3bea5eb7-5903-4af5-a1ca-62b7281c3a75
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-09-20 10:50:04.985393+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-09-20 10:50:07.521347+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-09-20 10:50:18.683414+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-09-20 10:50:19.270211+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
c2c50ab3-c020-466b-9072-e9ec0d8c17f2	store	2022-09-20 10:50:01.318891+02	2022-09-20 10:50:02.074796+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-09-20T10:50:02.074818+02:00\\"}"}	\N	\N	\N	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
0ce039e9-1c6e-49d8-b816-619e61d49bec	pull	2022-09-20 10:50:03.41896+02	2022-09-20 10:50:04.21671+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-20T10:50:04.216730+02:00\\"}"}	\N	\N	\N	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
4c224832-fb75-40b8-9af2-152729e6b31a	deploy	2022-09-20 10:50:04.973419+02	2022-09-20 10:50:04.985393+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-09-20 10:50:03+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-09-20 10:50:03+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"cde83ccb-7ee1-446a-acf5-8c1ece312fe0\\"}, \\"timestamp\\": \\"2022-09-20T10:50:04.970605+02:00\\"}","{\\"msg\\": \\"Start deploy cde83ccb-7ee1-446a-acf5-8c1ece312fe0 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"cde83ccb-7ee1-446a-acf5-8c1ece312fe0\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-09-20T10:50:04.975317+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-20T10:50:04.975901+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-20T10:50:04.978658+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy cde83ccb-7ee1-446a-acf5-8c1ece312fe0\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"cde83ccb-7ee1-446a-acf5-8c1ece312fe0\\"}, \\"timestamp\\": \\"2022-09-20T10:50:04.981579+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
e3f5a642-ab9a-4c1b-941e-6cc800600412	pull	2022-09-20 10:50:06.013011+02	2022-09-20 10:50:06.794141+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-20T10:50:06.794158+02:00\\"}"}	\N	\N	\N	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	1	{"std::File[localhost,path=/tmp/test],v=1"}
ba5ea071-6e4f-404b-a731-1f0baf166b4d	deploy	2022-09-20 10:50:07.515516+02	2022-09-20 10:50:07.521347+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-09-20 10:50:06+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-09-20 10:50:06+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"1fb9d775-68ee-4632-9016-8fc7931adebe\\"}, \\"timestamp\\": \\"2022-09-20T10:50:07.513743+02:00\\"}","{\\"msg\\": \\"Start deploy 1fb9d775-68ee-4632-9016-8fc7931adebe of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"1fb9d775-68ee-4632-9016-8fc7931adebe\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-20T10:50:07.517130+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-20T10:50:07.517695+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-20T10:50:07.517804+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 929, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpicuidbvv/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-20T10:50:07.519383+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 1fb9d775-68ee-4632-9016-8fc7931adebe\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"1fb9d775-68ee-4632-9016-8fc7931adebe\\"}, \\"timestamp\\": \\"2022-09-20T10:50:07.519570+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	1	{"std::File[localhost,path=/tmp/test],v=1"}
68c99ab9-0903-481d-8c89-a6f770813cb6	store	2022-09-20 10:50:18.518656+02	2022-09-20 10:50:18.52014+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-09-20T10:50:18.520150+02:00\\"}"}	\N	\N	\N	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
636b01a3-3eae-4051-b396-6c42c6cd3ae3	deploy	2022-09-20 10:50:18.530572+02	2022-09-20 10:50:18.530572+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-09-20T08:50:18.530572+00:00\\"}"}	deployed	\N	nochange	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
65c69a8c-2ef8-409f-ad67-18be24c6cb39	pull	2022-09-20 10:50:18.670211+02	2022-09-20 10:50:18.670957+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-20T10:50:18.670964+02:00\\"}"}	\N	\N	\N	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
395731b2-62b4-4e12-b62c-5f8dc1399c37	deploy	2022-09-20 10:50:18.677944+02	2022-09-20 10:50:18.683414+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"148fc1ab-4fc1-42b8-9dab-090252f6ca11\\"}, \\"timestamp\\": \\"2022-09-20T10:50:18.676405+02:00\\"}","{\\"msg\\": \\"Start deploy 148fc1ab-4fc1-42b8-9dab-090252f6ca11 of resource std::AgentConfig[internal,agentname=localhost],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"148fc1ab-4fc1-42b8-9dab-090252f6ca11\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-09-20T10:50:18.679094+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-20T10:50:18.679598+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=2 in deploy 148fc1ab-4fc1-42b8-9dab-090252f6ca11\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=2\\", \\"deploy_id\\": \\"148fc1ab-4fc1-42b8-9dab-090252f6ca11\\"}, \\"timestamp\\": \\"2022-09-20T10:50:18.681855+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=2": {"std::AgentConfig[internal,agentname=localhost],v=2": {"current": null, "desired": null}}}	nochange	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
22b7161a-feaa-4250-8bd6-e4d69ab5cb02	pull	2022-09-20 10:50:18.529348+02	2022-09-20 10:50:18.530644+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-20T10:50:18.531711+02:00\\"}"}	\N	\N	\N	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2	{"std::File[localhost,path=/tmp/test],v=2"}
60f5b35d-4edf-4a5b-8ee8-f9f876fe3561	deploy	2022-09-20 10:50:19.264992+02	2022-09-20 10:50:19.270211+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"4afa998a-e38f-4c0f-ae8d-17ece47009f0\\"}, \\"timestamp\\": \\"2022-09-20T10:50:19.263159+02:00\\"}","{\\"msg\\": \\"Start deploy 4afa998a-e38f-4c0f-ae8d-17ece47009f0 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"4afa998a-e38f-4c0f-ae8d-17ece47009f0\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-20T10:50:19.266382+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-20T10:50:19.266790+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"hugo\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-20T10:50:19.268121+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpicuidbvv/11eda7dd-97d8-44ba-ba90-152d5f9ffcbd/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-20T10:50:19.268280+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 4afa998a-e38f-4c0f-ae8d-17ece47009f0\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"4afa998a-e38f-4c0f-ae8d-17ece47009f0\\"}, \\"timestamp\\": \\"2022-09-20T10:50:19.268514+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	c2c50ab3-c020-466b-9072-e9ec0d8c17f2	std::File[localhost,path=/tmp/test]	1
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	c2c50ab3-c020-466b-9072-e9ec0d8c17f2	std::AgentConfig[internal,agentname=localhost]	1
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	0ce039e9-1c6e-49d8-b816-619e61d49bec	std::AgentConfig[internal,agentname=localhost]	1
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	4c224832-fb75-40b8-9af2-152729e6b31a	std::AgentConfig[internal,agentname=localhost]	1
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	e3f5a642-ab9a-4c1b-941e-6cc800600412	std::File[localhost,path=/tmp/test]	1
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	ba5ea071-6e4f-404b-a731-1f0baf166b4d	std::File[localhost,path=/tmp/test]	1
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	68c99ab9-0903-481d-8c89-a6f770813cb6	std::File[localhost,path=/tmp/test]	2
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	68c99ab9-0903-481d-8c89-a6f770813cb6	std::AgentConfig[internal,agentname=localhost]	2
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	636b01a3-3eae-4051-b396-6c42c6cd3ae3	std::AgentConfig[internal,agentname=localhost]	2
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	65c69a8c-2ef8-409f-ad67-18be24c6cb39	std::AgentConfig[internal,agentname=localhost]	2
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	395731b2-62b4-4e12-b62c-5f8dc1399c37	std::AgentConfig[internal,agentname=localhost]	2
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	22b7161a-feaa-4250-8bd6-e4d69ab5cb02	std::File[localhost,path=/tmp/test]	2
11eda7dd-97d8-44ba-ba90-152d5f9ffcbd	60f5b35d-4edf-4a5b-8ee8-f9f876fe3561	std::File[localhost,path=/tmp/test]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209160}
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

