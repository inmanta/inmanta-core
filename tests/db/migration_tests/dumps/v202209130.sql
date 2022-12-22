--
-- PostgreSQL database dump
--

-- Dumped from database version 14.5
-- Dumped by pg_dump version 14.5

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
cf570440-fc59-49a9-bf93-773aff5b4371	internal	2022-09-14 11:43:50.797394+02	f	c948a607-ccc2-4af9-99b9-3a8455927319	\N
cf570440-fc59-49a9-bf93-773aff5b4371	localhost	2022-09-14 11:43:53.386872+02	f	398465ca-6ff4-4fef-b57c-9145f4311cde	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
c948a607-ccc2-4af9-99b9-3a8455927319	bcf69082-3411-11ed-b0e8-50e0859859ea	internal	\N	cf570440-fc59-49a9-bf93-773aff5b4371
398465ca-6ff4-4fef-b57c-9145f4311cde	bcf69082-3411-11ed-b0e8-50e0859859ea	localhost	\N	cf570440-fc59-49a9-bf93-773aff5b4371
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
bedevere	cf570440-fc59-49a9-bf93-773aff5b4371	2022-09-14 11:43:50.797394+02	2022-09-14 11:44:04.030547+02	\N	bcf69082-3411-11ed-b0e8-50e0859859ea
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
cf570440-fc59-49a9-bf93-773aff5b4371	std::Service	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::File	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::Directory	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::Package	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::Symlink	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::AgentConfig	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::Service	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::File	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::Directory	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::Package	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::Symlink	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
cf570440-fc59-49a9-bf93-773aff5b4371	std::AgentConfig	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets) FROM stdin;
b46d9e29-cec7-48b6-b3b4-32a618d27679	cf570440-fc59-49a9-bf93-773aff5b4371	2022-09-14 11:43:35.686987+02	2022-09-14 11:43:50.972845+02	2022-09-14 11:43:35.606776+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	16abdf54-cfa7-4b55-b7ba-a6a7f3cf975d	t	\N	{"errors": []}	f	{}
b82029e3-7514-48e7-aad9-622935165318	cf570440-fc59-49a9-bf93-773aff5b4371	2022-09-14 11:43:53.582499+02	2022-09-14 11:44:03.869465+02	2022-09-14 11:43:53.570692+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	422adbd3-c88e-449b-90e1-cca36ee33118	t	\N	{"errors": []}	f	{}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	cf570440-fc59-49a9-bf93-773aff5b4371	2022-09-14 11:43:48.585352+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "bedevere", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	cf570440-fc59-49a9-bf93-773aff5b4371	2022-09-14 11:44:03.751477+02	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "bedevere", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
a2d6b230-cd07-4855-8a87-6fcabac83a87	dev-2	f92ebb79-59c3-4856-b541-4296d332e33a			{"auto_full_compile": ""}	0	f		
cf570440-fc59-49a9-bf93-773aff5b4371	dev-1	f92ebb79-59c3-4856-b541-4296d332e33a			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
f92ebb79-59c3-4856-b541-4296d332e33a	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
46f9ca94-60cb-4223-a2fe-41015f12eaee	2022-09-14 11:43:35.687543+02	2022-09-14 11:43:35.689415+02		Init		Using extra environment variables during compile \n	0	b46d9e29-cec7-48b6-b3b4-32a618d27679
f0fec30a-597b-4c57-885e-9238c663da12	2022-09-14 11:43:35.689845+02	2022-09-14 11:43:35.690898+02		Creating venv			0	b46d9e29-cec7-48b6-b3b4-32a618d27679
231e7b15-1304-4dff-b891-11b1bb5ea3dd	2022-09-14 11:43:35.70421+02	2022-09-14 11:43:36.104864+02	/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	b46d9e29-cec7-48b6-b3b4-32a618d27679
b8b15859-d004-40bc-8127-7ff19a508116	2022-09-14 11:43:36.105604+02	2022-09-14 11:43:47.473887+02	/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.env              DEBUG   Cloning into '/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std'...\ninmanta.env              DEBUG   remote: Enumerating objects: 2462, done.\ninmanta.env              DEBUG   remote: Counting objects:   0% (1/641)        \rremote: Counting objects:   1% (7/641)        \rremote: Counting objects:   2% (13/641)        \rremote: Counting objects:   3% (20/641)        \rremote: Counting objects:   4% (26/641)        \rremote: Counting objects:   5% (33/641)        \rremote: Counting objects:   6% (39/641)        \rremote: Counting objects:   7% (45/641)        \rremote: Counting objects:   8% (52/641)        \rremote: Counting objects:   9% (58/641)        \rremote: Counting objects:  10% (65/641)        \rremote: Counting objects:  11% (71/641)        \rremote: Counting objects:  12% (77/641)        \rremote: Counting objects:  13% (84/641)        \rremote: Counting objects:  14% (90/641)        \rremote: Counting objects:  15% (97/641)        \rremote: Counting objects:  16% (103/641)        \rremote: Counting objects:  17% (109/641)        \rremote: Counting objects:  18% (116/641)        \rremote: Counting objects:  19% (122/641)        \rremote: Counting objects:  20% (129/641)        \rremote: Counting objects:  21% (135/641)        \rremote: Counting objects:  22% (142/641)        \rremote: Counting objects:  23% (148/641)        \rremote: Counting objects:  24% (154/641)        \rremote: Counting objects:  25% (161/641)        \rremote: Counting objects:  26% (167/641)        \rremote: Counting objects:  27% (174/641)        \rremote: Counting objects:  28% (180/641)        \rremote: Counting objects:  29% (186/641)        \rremote: Counting objects:  30% (193/641)        \rremote: Counting objects:  31% (199/641)        \rremote: Counting objects:  32% (206/641)        \rremote: Counting objects:  33% (212/641)        \rremote: Counting objects:  34% (218/641)        \rremote: Counting objects:  35% (225/641)        \rremote: Counting objects:  36% (231/641)        \rremote: Counting objects:  37% (238/641)        \rremote: Counting objects:  38% (244/641)        \rremote: Counting objects:  39% (250/641)        \rremote: Counting objects:  40% (257/641)        \rremote: Counting objects:  41% (263/641)        \rremote: Counting objects:  42% (270/641)        \rremote: Counting objects:  43% (276/641)        \rremote: Counting objects:  44% (283/641)        \rremote: Counting objects:  45% (289/641)        \rremote: Counting objects:  46% (295/641)        \rremote: Counting objects:  47% (302/641)        \rremote: Counting objects:  48% (308/641)        \rremote: Counting objects:  49% (315/641)        \rremote: Counting objects:  50% (321/641)        \rremote: Counting objects:  51% (327/641)        \rremote: Counting objects:  52% (334/641)        \rremote: Counting objects:  53% (340/641)        \rremote: Counting objects:  54% (347/641)        \rremote: Counting objects:  55% (353/641)        \rremote: Counting objects:  56% (359/641)        \rremote: Counting objects:  57% (366/641)        \rremote: Counting objects:  58% (372/641)        \rremote: Counting objects:  59% (379/641)        \rremote: Counting objects:  60% (385/641)        \rremote: Counting objects:  61% (392/641)        \rremote: Counting objects:  62% (398/641)        \rremote: Counting objects:  63% (404/641)        \rremote: Counting objects:  64% (411/641)        \rremote: Counting objects:  65% (417/641)        \rremote: Counting objects:  66% (424/641)        \rremote: Counting objects:  67% (430/641)        \rremote: Counting objects:  68% (436/641)        \rremote: Counting objects:  69% (443/641)        \rremote: Counting objects:  70% (449/641)        \rremote: Counting objects:  71% (456/641)        \rremote: Counting objects:  72% (462/641)        \rremote: Counting objects:  73% (468/641)        \rremote: Counting objects:  74% (475/641)        \rremote: Counting objects:  75% (481/641)        \rremote: Counting objects:  76% (488/641)        \rremote: Counting objects:  77% (494/641)        \rremote: Counting objects:  78% (500/641)        \rremote: Counting objects:  79% (507/641)        \rremote: Counting objects:  80% (513/641)        \rremote: Counting objects:  81% (520/641)        \rremote: Counting objects:  82% (526/641)        \rremote: Counting objects:  83% (533/641)        \rremote: Counting objects:  84% (539/641)        \rremote: Counting objects:  85% (545/641)        \rremote: Counting objects:  86% (552/641)        \rremote: Counting objects:  87% (558/641)        \rremote: Counting objects:  88% (565/641)        \rremote: Counting objects:  89% (571/641)        \rremote: Counting objects:  90% (577/641)        \rremote: Counting objects:  91% (584/641)        \rremote: Counting objects:  92% (590/641)        \rremote: Counting objects:  93% (597/641)        \rremote: Counting objects:  94% (603/641)        \rremote: Counting objects:  95% (609/641)        \rremote: Counting objects:  96% (616/641)        \rremote: Counting objects:  97% (622/641)        \rremote: Counting objects:  98% (629/641)        \rremote: Counting objects:  99% (635/641)        \rremote: Counting objects: 100% (641/641)        \rremote: Counting objects: 100% (641/641), done.\ninmanta.env              DEBUG   remote: Compressing objects:   0% (1/305)        \rremote: Compressing objects:   1% (4/305)        \rremote: Compressing objects:   2% (7/305)        \rremote: Compressing objects:   3% (10/305)        \rremote: Compressing objects:   4% (13/305)        \rremote: Compressing objects:   5% (16/305)        \rremote: Compressing objects:   6% (19/305)        \rremote: Compressing objects:   7% (22/305)        \rremote: Compressing objects:   8% (25/305)        \rremote: Compressing objects:   9% (28/305)        \rremote: Compressing objects:  10% (31/305)        \rremote: Compressing objects:  11% (34/305)        \rremote: Compressing objects:  12% (37/305)        \rremote: Compressing objects:  13% (40/305)        \rremote: Compressing objects:  14% (43/305)        \rremote: Compressing objects:  15% (46/305)        \rremote: Compressing objects:  16% (49/305)        \rremote: Compressing objects:  17% (52/305)        \rremote: Compressing objects:  18% (55/305)        \rremote: Compressing objects:  19% (58/305)        \rremote: Compressing objects:  20% (61/305)        \rremote: Compressing objects:  21% (65/305)        \rremote: Compressing objects:  22% (68/305)        \rremote: Compressing objects:  23% (71/305)        \rremote: Compressing objects:  24% (74/305)        \rremote: Compressing objects:  25% (77/305)        \rremote: Compressing objects:  26% (80/305)        \rremote: Compressing objects:  27% (83/305)        \rremote: Compressing objects:  28% (86/305)        \rremote: Compressing objects:  29% (89/305)        \rremote: Compressing objects:  30% (92/305)        \rremote: Compressing objects:  31% (95/305)        \rremote: Compressing objects:  32% (98/305)        \rremote: Compressing objects:  33% (101/305)        \rremote: Compressing objects:  34% (104/305)        \rremote: Compressing objects:  35% (107/305)        \rremote: Compressing objects:  36% (110/305)        \rremote: Compressing objects:  37% (113/305)        \rremote: Compressing objects:  38% (116/305)        \rremote: Compressing objects:  39% (119/305)        \rremote: Compressing objects:  40% (122/305)        \rremote: Compressing objects:  41% (126/305)        \rremote: Compressing objects:  42% (129/305)        \rremote: Compressing objects:  43% (132/305)        \rremote: Compressing objects:  44% (135/305)        \rremote: Compressing objects:  45% (138/305)        \rremote: Compressing objects:  46% (141/305)        \rremote: Compressing objects:  47% (144/305)        \rremote: Compressing objects:  48% (147/305)        \rremote: Compressing objects:  49% (150/305)        \rremote: Compressing objects:  50% (153/305)        \rremote: Compressing objects:  51% (156/305)        \rremote: Compressing objects:  52% (159/305)        \rremote: Compressing objects:  53% (162/305)        \rremote: Compressing objects:  54% (165/305)        \rremote: Compressing objects:  55% (168/305)        \rremote: Compressing objects:  56% (171/305)        \rremote: Compressing objects:  57% (174/305)        \rremote: Compressing objects:  58% (177/305)        \rremote: Compressing objects:  59% (180/305)        \rremote: Compressing objects:  60% (183/305)        \rremote: Compressing objects:  61% (187/305)        \rremote: Compressing objects:  62% (190/305)        \rremote: Compressing objects:  63% (193/305)        \rremote: Compressing objects:  64% (196/305)        \rremote: Compressing objects:  65% (199/305)        \rremote: Compressing objects:  66% (202/305)        \rremote: Compressing objects:  67% (205/305)        \rremote: Compressing objects:  68% (208/305)        \rremote: Compressing objects:  69% (211/305)        \rremote: Compressing objects:  70% (214/305)        \rremote: Compressing objects:  71% (217/305)        \rremote: Compressing objects:  72% (220/305)        \rremote: Compressing objects:  73% (223/305)        \rremote: Compressing objects:  74% (226/305)        \rremote: Compressing objects:  75% (229/305)        \rremote: Compressing objects:  76% (232/305)        \rremote: Compressing objects:  77% (235/305)        \rremote: Compressing objects:  78% (238/305)        \rremote: Compressing objects:  79% (241/305)        \rremote: Compressing objects:  80% (244/305)        \rremote: Compressing objects:  81% (248/305)        \rremote: Compressing objects:  82% (251/305)        \rremote: Compressing objects:  83% (254/305)        \rremote: Compressing objects:  84% (257/305)        \rremote: Compressing objects:  85% (260/305)        \rremote: Compressing objects:  86% (263/305)        \rremote: Compressing objects:  87% (266/305)        \rremote: Compressing objects:  88% (269/305)        \rremote: Compressing objects:  89% (272/305)        \rremote: Compressing objects:  90% (275/305)        \rremote: Compressing objects:  91% (278/305)        \rremote: Compressing objects:  92% (281/305)        \rremote: Compressing objects:  93% (284/305)        \rremote: Compressing objects:  94% (287/305)        \rremote: Compressing objects:  95% (290/305)        \rremote: Compressing objects:  96% (293/305)        \rremote: Compressing objects:  97% (296/305)        \rremote: Compressing objects:  98% (299/305)        \rremote: Compressing objects:  99% (302/305)        \rremote: Compressing objects: 100% (305/305)        \rremote: Compressing objects: 100% (305/305), done.\ninmanta.env              DEBUG   Receiving objects:   0% (1/2462)\rReceiving objects:   1% (25/2462)\rReceiving objects:   2% (50/2462)\rReceiving objects:   3% (74/2462)\rReceiving objects:   4% (99/2462)\rReceiving objects:   5% (124/2462)\rReceiving objects:   6% (148/2462)\rReceiving objects:   7% (173/2462)\rReceiving objects:   8% (197/2462)\rReceiving objects:   9% (222/2462)\rReceiving objects:  10% (247/2462)\rReceiving objects:  11% (271/2462)\rReceiving objects:  12% (296/2462)\rReceiving objects:  13% (321/2462)\rReceiving objects:  14% (345/2462)\rReceiving objects:  15% (370/2462)\rReceiving objects:  16% (394/2462)\rReceiving objects:  17% (419/2462)\rReceiving objects:  18% (444/2462)\rReceiving objects:  19% (468/2462)\rReceiving objects:  20% (493/2462)\rReceiving objects:  21% (518/2462)\rReceiving objects:  22% (542/2462)\rReceiving objects:  23% (567/2462)\rReceiving objects:  24% (591/2462)\rReceiving objects:  25% (616/2462)\rReceiving objects:  26% (641/2462)\rReceiving objects:  27% (665/2462)\rReceiving objects:  28% (690/2462)\rReceiving objects:  29% (714/2462)\rReceiving objects:  30% (739/2462)\rReceiving objects:  31% (764/2462)\rReceiving objects:  32% (788/2462)\rReceiving objects:  33% (813/2462)\rReceiving objects:  34% (838/2462)\rReceiving objects:  35% (862/2462)\rReceiving objects:  36% (887/2462)\rReceiving objects:  37% (911/2462)\rReceiving objects:  38% (936/2462)\rReceiving objects:  39% (961/2462)\rReceiving objects:  40% (985/2462)\rReceiving objects:  41% (1010/2462)\rReceiving objects:  42% (1035/2462)\rReceiving objects:  43% (1059/2462)\rReceiving objects:  44% (1084/2462)\rReceiving objects:  45% (1108/2462)\rReceiving objects:  46% (1133/2462)\rReceiving objects:  47% (1158/2462)\rReceiving objects:  48% (1182/2462)\rReceiving objects:  49% (1207/2462)\rReceiving objects:  50% (1231/2462)\rReceiving objects:  51% (1256/2462)\rReceiving objects:  52% (1281/2462)\rReceiving objects:  53% (1305/2462)\rReceiving objects:  54% (1330/2462)\rReceiving objects:  55% (1355/2462)\rReceiving objects:  56% (1379/2462)\rReceiving objects:  57% (1404/2462)\rReceiving objects:  58% (1428/2462)\rReceiving objects:  59% (1453/2462)\rReceiving objects:  60% (1478/2462)\rReceiving objects:  61% (1502/2462)\rReceiving objects:  62% (1527/2462)\rReceiving objects:  63% (1552/2462)\rReceiving objects:  64% (1576/2462)\rReceiving objects:  65% (1601/2462)\rReceiving objects:  66% (1625/2462)\rReceiving objects:  67% (1650/2462)\rReceiving objects:  68% (1675/2462)\rReceiving objects:  69% (1699/2462)\rReceiving objects:  70% (1724/2462)\rReceiving objects:  71% (1749/2462)\rReceiving objects:  72% (1773/2462)\rReceiving objects:  73% (1798/2462)\rReceiving objects:  74% (1822/2462)\rReceiving objects:  75% (1847/2462)\rReceiving objects:  76% (1872/2462)\rReceiving objects:  77% (1896/2462)\rReceiving objects:  78% (1921/2462)\rReceiving objects:  79% (1945/2462)\rReceiving objects:  80% (1970/2462)\rReceiving objects:  81% (1995/2462)\rremote: Total 2462 (delta 334), reused 561 (delta 292), pack-reused 1821\ninmanta.env              DEBUG   Receiving objects:  82% (2019/2462)\rReceiving objects:  83% (2044/2462)\rReceiving objects:  84% (2069/2462)\rReceiving objects:  85% (2093/2462)\rReceiving objects:  86% (2118/2462)\rReceiving objects:  87% (2142/2462)\rReceiving objects:  88% (2167/2462)\rReceiving objects:  89% (2192/2462)\rReceiving objects:  90% (2216/2462)\rReceiving objects:  91% (2241/2462)\rReceiving objects:  92% (2266/2462)\rReceiving objects:  93% (2290/2462)\rReceiving objects:  94% (2315/2462)\rReceiving objects:  95% (2339/2462)\rReceiving objects:  96% (2364/2462)\rReceiving objects:  97% (2389/2462)\rReceiving objects:  98% (2413/2462)\rReceiving objects:  99% (2438/2462)\rReceiving objects: 100% (2462/2462)\rReceiving objects: 100% (2462/2462), 499.43 KiB | 8.19 MiB/s, done.\ninmanta.env              DEBUG   Resolving deltas:   0% (0/1302)\rResolving deltas:   1% (14/1302)\rResolving deltas:   2% (27/1302)\rResolving deltas:   3% (40/1302)\rResolving deltas:   4% (53/1302)\rResolving deltas:   5% (66/1302)\rResolving deltas:   6% (79/1302)\rResolving deltas:   7% (92/1302)\rResolving deltas:   8% (105/1302)\rResolving deltas:   9% (118/1302)\rResolving deltas:  10% (131/1302)\rResolving deltas:  11% (144/1302)\rResolving deltas:  12% (157/1302)\rResolving deltas:  13% (171/1302)\rResolving deltas:  14% (183/1302)\rResolving deltas:  15% (196/1302)\rResolving deltas:  16% (209/1302)\rResolving deltas:  17% (222/1302)\rResolving deltas:  18% (235/1302)\rResolving deltas:  19% (248/1302)\rResolving deltas:  20% (261/1302)\rResolving deltas:  21% (275/1302)\rResolving deltas:  22% (287/1302)\rResolving deltas:  23% (300/1302)\rResolving deltas:  24% (313/1302)\rResolving deltas:  25% (326/1302)\rResolving deltas:  26% (340/1302)\rResolving deltas:  27% (352/1302)\rResolving deltas:  28% (365/1302)\rResolving deltas:  29% (378/1302)\rResolving deltas:  30% (392/1302)\rResolving deltas:  31% (404/1302)\rResolving deltas:  32% (417/1302)\rResolving deltas:  33% (431/1302)\rResolving deltas:  34% (443/1302)\rResolving deltas:  35% (456/1302)\rResolving deltas:  36% (469/1302)\rResolving deltas:  37% (482/1302)\rResolving deltas:  38% (495/1302)\rResolving deltas:  39% (508/1302)\rResolving deltas:  40% (523/1302)\rResolving deltas:  41% (534/1302)\rResolving deltas:  42% (547/1302)\rResolving deltas:  43% (560/1302)\rResolving deltas:  44% (573/1302)\rResolving deltas:  45% (586/1302)\rResolving deltas:  46% (599/1302)\rResolving deltas:  47% (612/1302)\rResolving deltas:  48% (625/1302)\rResolving deltas:  49% (638/1302)\rResolving deltas:  50% (651/1302)\rResolving deltas:  51% (665/1302)\rResolving deltas:  52% (678/1302)\rResolving deltas:  53% (691/1302)\rResolving deltas:  54% (704/1302)\rResolving deltas:  55% (717/1302)\rResolving deltas:  56% (731/1302)\rResolving deltas:  57% (743/1302)\rResolving deltas:  58% (756/1302)\rResolving deltas:  59% (770/1302)\rResolving deltas:  60% (782/1302)\rResolving deltas:  61% (796/1302)\rResolving deltas:  62% (808/1302)\rResolving deltas:  63% (821/1302)\rResolving deltas:  64% (834/1302)\rResolving deltas:  65% (847/1302)\rResolving deltas:  66% (860/1302)\rResolving deltas:  67% (873/1302)\rResolving deltas:  68% (886/1302)\rResolving deltas:  69% (899/1302)\rResolving deltas:  70% (912/1302)\rResolving deltas:  71% (925/1302)\rResolving deltas:  72% (938/1302)\rResolving deltas:  73% (951/1302)\rResolving deltas:  74% (964/1302)\rResolving deltas:  75% (977/1302)\rResolving deltas:  76% (990/1302)\rResolving deltas:  77% (1003/1302)\rResolving deltas:  78% (1016/1302)\rResolving deltas:  79% (1029/1302)\rResolving deltas:  80% (1042/1302)\rResolving deltas:  81% (1055/1302)\rResolving deltas:  82% (1068/1302)\rResolving deltas:  83% (1081/1302)\rResolving deltas:  84% (1094/1302)\rResolving deltas:  85% (1107/1302)\rResolving deltas:  86% (1120/1302)\rResolving deltas:  87% (1133/1302)\rResolving deltas:  88% (1146/1302)\rResolving deltas:  89% (1159/1302)\rResolving deltas:  90% (1172/1302)\rResolving deltas:  91% (1185/1302)\rResolving deltas:  92% (1198/1302)\rResolving deltas:  93% (1211/1302)\rResolving deltas:  94% (1225/1302)\rResolving deltas:  95% (1237/1302)\rResolving deltas:  96% (1250/1302)\rResolving deltas:  97% (1263/1302)\rResolving deltas:  98% (1276/1302)\rResolving deltas:  99% (1290/1302)\rResolving deltas: 100% (1302/1302)\rResolving deltas: 100% (1302/1302), done.\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 3.1.4 in /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std from https://github.com/inmanta/std.\ninmanta.module           DEBUG   Parsing took 0.000119 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.9.1)\ninmanta.env              DEBUG   Collecting pydantic~=1.9\ninmanta.env              DEBUG   Using cached pydantic-1.10.2-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.2 MB)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.7.1)\ninmanta.env              DEBUG   Collecting typing-inspect~=0.7\ninmanta.env              DEBUG   Using cached typing_inspect-0.8.0-py3-none-any.whl (8.7 kB)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.6.0)\ninmanta.env              DEBUG   Collecting colorlog~=6.0\ninmanta.env              DEBUG   Using cached colorlog-6.7.0-py2.py3-none-any.whl (11 kB)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Collecting idna>=2.0.0\ninmanta.env              DEBUG   Downloading idna-3.4-py3-none-any.whl (61 kB)\ninmanta.env              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 61.5/61.5 kB 7.7 MB/s eta 0:00:00\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Collecting arrow\ninmanta.env              DEBUG   Using cached arrow-1.2.3-py3-none-any.whl (66 kB)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.env              DEBUG   Collecting certifi>=2017.4.17\ninmanta.env              DEBUG   Downloading certifi-2022.6.15.2-py3-none-any.whl (160 kB)\ninmanta.env              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 160.4/160.4 kB 19.1 MB/s eta 0:00:00\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Collecting urllib3<1.27,>=1.21.1\ninmanta.env              DEBUG   Using cached urllib3-1.26.12-py2.py3-none-any.whl (140 kB)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.env              DEBUG   Collecting charset-normalizer<3,>=2\ninmanta.env              DEBUG   Using cached charset_normalizer-2.1.1-py3-none-any.whl (39 kB)\ninmanta.env              DEBUG   Installing collected packages: urllib3, typing-inspect, pydantic, idna, colorlog, charset-normalizer, certifi, arrow\ninmanta.env              DEBUG   Attempting uninstall: urllib3\ninmanta.env              DEBUG   Found existing installation: urllib3 1.26.11\ninmanta.env              DEBUG   Not uninstalling urllib3 at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\ninmanta.env              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: typing-inspect\ninmanta.env              DEBUG   Found existing installation: typing-inspect 0.7.1\ninmanta.env              DEBUG   Not uninstalling typing-inspect at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\ninmanta.env              DEBUG   Can't uninstall 'typing-inspect'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: pydantic\ninmanta.env              DEBUG   Found existing installation: pydantic 1.9.1\ninmanta.env              DEBUG   Not uninstalling pydantic at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\ninmanta.env              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: idna\ninmanta.env              DEBUG   Found existing installation: idna 3.3\ninmanta.env              DEBUG   Not uninstalling idna at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\ninmanta.env              DEBUG   Can't uninstall 'idna'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: colorlog\ninmanta.env              DEBUG   Found existing installation: colorlog 6.6.0\ninmanta.env              DEBUG   Not uninstalling colorlog at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\ninmanta.env              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: charset-normalizer\ninmanta.env              DEBUG   Found existing installation: charset-normalizer 2.1.0\ninmanta.env              DEBUG   Not uninstalling charset-normalizer at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\ninmanta.env              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: certifi\ninmanta.env              DEBUG   Found existing installation: certifi 2022.6.15\ninmanta.env              DEBUG   Not uninstalling certifi at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\ninmanta.env              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: arrow\ninmanta.env              DEBUG   Found existing installation: arrow 1.2.2\ninmanta.env              DEBUG   Not uninstalling arrow at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\ninmanta.env              DEBUG   Can't uninstall 'arrow'. No files were found to uninstall.\ninmanta.env              DEBUG   Successfully installed arrow-1.2.3 certifi-2022.6.15.2 charset-normalizer-2.1.1 colorlog-6.7.0 idna-3.4 pydantic-1.10.2 typing-inspect-0.8.0 urllib3-1.26.12\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000069 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.2)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.module           INFO    verifying project\n	0	b46d9e29-cec7-48b6-b3b4-32a618d27679
344b6305-3662-4a84-b284-81acbd196f15	2022-09-14 11:43:47.474732+02	2022-09-14 11:43:50.971806+02	/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env/bin/python -m inmanta.app -vvv export -X -e cf570440-fc59-49a9-bf93-773aff5b4371 --server_address localhost --server_port 44161 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpizk03zu8	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.005015 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000183 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003047)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001875)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000062)\ninmanta.execute.schedulerINFO    Total compilation time 0.005054\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:44161/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:44161/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:44161/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:44161/api/v1/file/63ae135b9a2eb874b3aa81fe5bd84283ef3617c9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:44161/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:44161/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:44161/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:44161/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	b46d9e29-cec7-48b6-b3b4-32a618d27679
8e3d0a47-383b-44b9-a643-db34c01d61bd	2022-09-14 11:43:53.583587+02	2022-09-14 11:43:53.587102+02		Init		Using extra environment variables during compile \n	0	b82029e3-7514-48e7-aad9-622935165318
55df58ee-efbc-49fe-87cf-26dfe4252678	2022-09-14 11:43:53.596694+02	2022-09-14 11:43:53.95645+02	/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	b82029e3-7514-48e7-aad9-622935165318
f634b21a-5c7f-4773-9160-0b5f0825c3a2	2022-09-14 11:44:02.633844+02	2022-09-14 11:44:03.868607+02	/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env/bin/python -m inmanta.app -vvv export -X -e cf570440-fc59-49a9-bf93-773aff5b4371 --server_address localhost --server_port 44161 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmphivfqn3z	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.005173 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000102 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003173)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002019)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000062)\ninmanta.execute.schedulerINFO    Total compilation time 0.005326\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:44161/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:44161/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:44161/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:44161/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:44161/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	b82029e3-7514-48e7-aad9-622935165318
aedeba61-86ed-4a9e-837c-5acc10516cfc	2022-09-14 11:43:53.957193+02	2022-09-14 11:44:02.632718+02	/tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000093 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.2)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000070 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmp8mro75qh/server/environments/cf570440-fc59-49a9-bf93-773aff5b4371/libs/std\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in ./.env/lib/python3.9/site-packages (from email_validator~=1.1) (3.4)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.2)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\n	0	b82029e3-7514-48e7-aad9-622935165318
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
cf570440-fc59-49a9-bf93-773aff5b4371	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-09-14 11:43:52.374074+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
cf570440-fc59-49a9-bf93-773aff5b4371	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-09-14 11:43:53.491125+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
cf570440-fc59-49a9-bf93-773aff5b4371	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-09-14 11:44:03.76766+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
cf570440-fc59-49a9-bf93-773aff5b4371	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-09-14 11:44:03.793745+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
977786bf-6856-4f30-a161-f77dc24b49fa	store	2022-09-14 11:43:48.58474+02	2022-09-14 11:43:49.400977+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-09-14T11:43:49.400997+02:00\\"}"}	\N	\N	\N	cf570440-fc59-49a9-bf93-773aff5b4371	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
87c5331e-c949-4793-ae6d-995cf86e0733	pull	2022-09-14 11:43:50.807023+02	2022-09-14 11:43:51.566178+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-14T11:43:51.566196+02:00\\"}"}	\N	\N	\N	cf570440-fc59-49a9-bf93-773aff5b4371	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
bf755bb4-7089-421f-827b-3539d0741562	deploy	2022-09-14 11:43:52.357716+02	2022-09-14 11:43:52.374074+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-09-14 11:43:50+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-09-14 11:43:50+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"eb3d88cc-439e-4b9b-9491-f4897c50a575\\"}, \\"timestamp\\": \\"2022-09-14T11:43:52.354529+02:00\\"}","{\\"msg\\": \\"Start deploy eb3d88cc-439e-4b9b-9491-f4897c50a575 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"eb3d88cc-439e-4b9b-9491-f4897c50a575\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-09-14T11:43:52.360041+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-14T11:43:52.360637+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-14T11:43:52.364379+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy eb3d88cc-439e-4b9b-9491-f4897c50a575\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"eb3d88cc-439e-4b9b-9491-f4897c50a575\\"}, \\"timestamp\\": \\"2022-09-14T11:43:52.367984+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	cf570440-fc59-49a9-bf93-773aff5b4371	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
02967d4e-0c4c-4616-b599-5e94c6fe9c08	pull	2022-09-14 11:43:53.402741+02	2022-09-14 11:43:53.404431+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-14T11:43:53.404439+02:00\\"}"}	\N	\N	\N	cf570440-fc59-49a9-bf93-773aff5b4371	1	{"std::File[localhost,path=/tmp/test],v=1"}
0320ed23-5a39-44ab-8785-be52e7aa446f	deploy	2022-09-14 11:43:53.482539+02	2022-09-14 11:43:53.491125+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-09-14 11:43:53+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-09-14 11:43:53+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"8ec883e8-3b68-4ab2-82d5-4e1569369458\\"}, \\"timestamp\\": \\"2022-09-14T11:43:53.479670+02:00\\"}","{\\"msg\\": \\"Start deploy 8ec883e8-3b68-4ab2-82d5-4e1569369458 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"8ec883e8-3b68-4ab2-82d5-4e1569369458\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-14T11:43:53.484822+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-14T11:43:53.485368+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-14T11:43:53.485464+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 929, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmp8mro75qh/cf570440-fc59-49a9-bf93-773aff5b4371/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-14T11:43:53.488022+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 8ec883e8-3b68-4ab2-82d5-4e1569369458\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"8ec883e8-3b68-4ab2-82d5-4e1569369458\\"}, \\"timestamp\\": \\"2022-09-14T11:43:53.488284+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	cf570440-fc59-49a9-bf93-773aff5b4371	1	{"std::File[localhost,path=/tmp/test],v=1"}
ec8a0724-db98-4657-9dc5-a5c8739ac638	store	2022-09-14 11:44:03.751262+02	2022-09-14 11:44:03.753067+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-09-14T11:44:03.753078+02:00\\"}"}	\N	\N	\N	cf570440-fc59-49a9-bf93-773aff5b4371	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
e72b0d30-2ce1-4fd4-a273-cb0d862ef2e5	pull	2022-09-14 11:44:03.765451+02	2022-09-14 11:44:03.767559+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-14T11:44:03.768793+02:00\\"}"}	\N	\N	\N	cf570440-fc59-49a9-bf93-773aff5b4371	2	{"std::File[localhost,path=/tmp/test],v=2"}
3ad5e501-6a67-4ccd-aa41-8cdf49029ceb	deploy	2022-09-14 11:44:03.76766+02	2022-09-14 11:44:03.76766+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-09-14T09:44:03.767660+00:00\\"}"}	deployed	\N	nochange	cf570440-fc59-49a9-bf93-773aff5b4371	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
4239ad82-3cf6-41ef-adff-15452abf1619	pull	2022-09-14 11:44:04.030161+02	2022-09-14 11:44:04.032101+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-14T11:44:04.032109+02:00\\"}"}	\N	\N	\N	cf570440-fc59-49a9-bf93-773aff5b4371	2	{"std::File[localhost,path=/tmp/test],v=2"}
56267297-e006-4bf2-bc90-0e4f16308db5	deploy	2022-09-14 11:44:03.78458+02	2022-09-14 11:44:03.793745+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"f0b15b45-5c03-43bc-b195-27f0b825f55b\\"}, \\"timestamp\\": \\"2022-09-14T11:44:03.781014+02:00\\"}","{\\"msg\\": \\"Start deploy f0b15b45-5c03-43bc-b195-27f0b825f55b of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"f0b15b45-5c03-43bc-b195-27f0b825f55b\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-14T11:44:03.786658+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-14T11:44:03.787122+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-14T11:44:03.789827+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp8mro75qh/cf570440-fc59-49a9-bf93-773aff5b4371/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-14T11:44:03.790094+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy f0b15b45-5c03-43bc-b195-27f0b825f55b\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"f0b15b45-5c03-43bc-b195-27f0b825f55b\\"}, \\"timestamp\\": \\"2022-09-14T11:44:03.790372+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	cf570440-fc59-49a9-bf93-773aff5b4371	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
cf570440-fc59-49a9-bf93-773aff5b4371	977786bf-6856-4f30-a161-f77dc24b49fa	std::File[localhost,path=/tmp/test]	1
cf570440-fc59-49a9-bf93-773aff5b4371	977786bf-6856-4f30-a161-f77dc24b49fa	std::AgentConfig[internal,agentname=localhost]	1
cf570440-fc59-49a9-bf93-773aff5b4371	87c5331e-c949-4793-ae6d-995cf86e0733	std::AgentConfig[internal,agentname=localhost]	1
cf570440-fc59-49a9-bf93-773aff5b4371	bf755bb4-7089-421f-827b-3539d0741562	std::AgentConfig[internal,agentname=localhost]	1
cf570440-fc59-49a9-bf93-773aff5b4371	02967d4e-0c4c-4616-b599-5e94c6fe9c08	std::File[localhost,path=/tmp/test]	1
cf570440-fc59-49a9-bf93-773aff5b4371	0320ed23-5a39-44ab-8785-be52e7aa446f	std::File[localhost,path=/tmp/test]	1
cf570440-fc59-49a9-bf93-773aff5b4371	ec8a0724-db98-4657-9dc5-a5c8739ac638	std::File[localhost,path=/tmp/test]	2
cf570440-fc59-49a9-bf93-773aff5b4371	ec8a0724-db98-4657-9dc5-a5c8739ac638	std::AgentConfig[internal,agentname=localhost]	2
cf570440-fc59-49a9-bf93-773aff5b4371	e72b0d30-2ce1-4fd4-a273-cb0d862ef2e5	std::File[localhost,path=/tmp/test]	2
cf570440-fc59-49a9-bf93-773aff5b4371	3ad5e501-6a67-4ccd-aa41-8cdf49029ceb	std::AgentConfig[internal,agentname=localhost]	2
cf570440-fc59-49a9-bf93-773aff5b4371	56267297-e006-4bf2-bc90-0e4f16308db5	std::File[localhost,path=/tmp/test]	2
cf570440-fc59-49a9-bf93-773aff5b4371	4239ad82-3cf6-41ef-adff-15452abf1619	std::File[localhost,path=/tmp/test]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209130}
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

