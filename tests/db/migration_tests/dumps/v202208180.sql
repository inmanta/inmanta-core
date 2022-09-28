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
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	localhost	2022-08-19 11:18:41.877506+02	f	322e0fdd-5589-4291-8feb-3f170a997437	\N
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	internal	2022-08-19 11:18:43.030354+02	f	b64f6d84-9e4d-4c1d-9f8d-d777a7f70371	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
322e0fdd-5589-4291-8feb-3f170a997437	ead5774c-1f9f-11ed-99e2-50e0859859ea	localhost	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511
b64f6d84-9e4d-4c1d-9f8d-d777a7f70371	ead5774c-1f9f-11ed-99e2-50e0859859ea	internal	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511
a9dc6bb9-47fa-43d0-84d4-c2ab333ece4f	ea3b66de-1f9f-11ed-a893-50e0859859ea	internal	2022-08-19 11:18:43.030354+02	f0a8a1e8-59a8-4f86-861a-67dedcc3f511
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
bedevere	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2022-08-19 11:18:40.866186+02	2022-08-19 11:18:41.029653+02	2022-08-19 11:18:43.030354+02	ea3b66de-1f9f-11ed-a893-50e0859859ea
bedevere	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2022-08-19 11:18:41.877506+02	2022-08-19 11:18:55.963596+02	\N	ead5774c-1f9f-11ed-99e2-50e0859859ea
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::Service	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::File	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::Directory	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::Package	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::Symlink	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::AgentConfig	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::Service	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::File	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::Directory	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::Package	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::Symlink	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	std::AgentConfig	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets) FROM stdin;
0658c339-41e1-4d40-aa5e-78ad9801f3e6	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2022-08-19 11:18:25.273232+02	2022-08-19 11:18:41.093032+02	2022-08-19 11:18:25.190616+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	6a832a9d-6347-4973-9672-775813ae35d9	t	\N	{"errors": []}	f	{}
2c07c873-07b0-48ca-8931-53036a653ba3	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2022-08-19 11:18:44.452002+02	2022-08-19 11:18:55.830925+02	2022-08-19 11:18:44.446228+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	49fe8266-5634-479c-9ca4-352b15ee92b0	t	\N	{"errors": []}	f	{}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2022-08-19 11:18:37.837911+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "bedevere", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2022-08-19 11:18:55.709728+02	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "hostname": "bedevere", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
b1136e46-2260-4d8b-9037-8f5fe12508e9	dev-2	be557701-5ae4-4b71-b132-6119e81ccdb5			{"auto_full_compile": ""}	0	f		
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	dev-1	be557701-5ae4-4b71-b132-6119e81ccdb5			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
be557701-5ae4-4b71-b132-6119e81ccdb5	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
918e958e-17b8-4193-b6d9-0214d2684bfd	2022-08-19 11:18:25.273752+02	2022-08-19 11:18:25.27573+02		Init		Using extra environment variables during compile \n	0	0658c339-41e1-4d40-aa5e-78ad9801f3e6
414b94ad-d10e-4890-b5aa-2550d5bbec5a	2022-08-19 11:18:25.276242+02	2022-08-19 11:18:25.277398+02		Creating venv			0	0658c339-41e1-4d40-aa5e-78ad9801f3e6
96eeca15-2426-4d4e-8eda-fe24594da569	2022-08-19 11:18:25.28194+02	2022-08-19 11:18:36.579935+02	/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.env              DEBUG   Cloning into '/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std'...\ninmanta.env              DEBUG   remote: Enumerating objects: 2450, done.\ninmanta.env              DEBUG   remote: Counting objects:   0% (1/629)        \rremote: Counting objects:   1% (7/629)        \rremote: Counting objects:   2% (13/629)        \rremote: Counting objects:   3% (19/629)        \rremote: Counting objects:   4% (26/629)        \rremote: Counting objects:   5% (32/629)        \rremote: Counting objects:   6% (38/629)        \rremote: Counting objects:   7% (45/629)        \rremote: Counting objects:   8% (51/629)        \rremote: Counting objects:   9% (57/629)        \rremote: Counting objects:  10% (63/629)        \rremote: Counting objects:  11% (70/629)        \rremote: Counting objects:  12% (76/629)        \rremote: Counting objects:  13% (82/629)        \rremote: Counting objects:  14% (89/629)        \rremote: Counting objects:  15% (95/629)        \rremote: Counting objects:  16% (101/629)        \rremote: Counting objects:  17% (107/629)        \rremote: Counting objects:  18% (114/629)        \rremote: Counting objects:  19% (120/629)        \rremote: Counting objects:  20% (126/629)        \rremote: Counting objects:  21% (133/629)        \rremote: Counting objects:  22% (139/629)        \rremote: Counting objects:  23% (145/629)        \rremote: Counting objects:  24% (151/629)        \rremote: Counting objects:  25% (158/629)        \rremote: Counting objects:  26% (164/629)        \rremote: Counting objects:  27% (170/629)        \rremote: Counting objects:  28% (177/629)        \rremote: Counting objects:  29% (183/629)        \rremote: Counting objects:  30% (189/629)        \rremote: Counting objects:  31% (195/629)        \rremote: Counting objects:  32% (202/629)        \rremote: Counting objects:  33% (208/629)        \rremote: Counting objects:  34% (214/629)        \rremote: Counting objects:  35% (221/629)        \rremote: Counting objects:  36% (227/629)        \rremote: Counting objects:  37% (233/629)        \rremote: Counting objects:  38% (240/629)        \rremote: Counting objects:  39% (246/629)        \rremote: Counting objects:  40% (252/629)        \rremote: Counting objects:  41% (258/629)        \rremote: Counting objects:  42% (265/629)        \rremote: Counting objects:  43% (271/629)        \rremote: Counting objects:  44% (277/629)        \rremote: Counting objects:  45% (284/629)        \rremote: Counting objects:  46% (290/629)        \rremote: Counting objects:  47% (296/629)        \rremote: Counting objects:  48% (302/629)        \rremote: Counting objects:  49% (309/629)        \rremote: Counting objects:  50% (315/629)        \rremote: Counting objects:  51% (321/629)        \rremote: Counting objects:  52% (328/629)        \rremote: Counting objects:  53% (334/629)        \rremote: Counting objects:  54% (340/629)        \rremote: Counting objects:  55% (346/629)        \rremote: Counting objects:  56% (353/629)        \rremote: Counting objects:  57% (359/629)        \rremote: Counting objects:  58% (365/629)        \rremote: Counting objects:  59% (372/629)        \rremote: Counting objects:  60% (378/629)        \rremote: Counting objects:  61% (384/629)        \rremote: Counting objects:  62% (390/629)        \rremote: Counting objects:  63% (397/629)        \rremote: Counting objects:  64% (403/629)        \rremote: Counting objects:  65% (409/629)        \rremote: Counting objects:  66% (416/629)        \rremote: Counting objects:  67% (422/629)        \rremote: Counting objects:  68% (428/629)        \rremote: Counting objects:  69% (435/629)        \rremote: Counting objects:  70% (441/629)        \rremote: Counting objects:  71% (447/629)        \rremote: Counting objects:  72% (453/629)        \rremote: Counting objects:  73% (460/629)        \rremote: Counting objects:  74% (466/629)        \rremote: Counting objects:  75% (472/629)        \rremote: Counting objects:  76% (479/629)        \rremote: Counting objects:  77% (485/629)        \rremote: Counting objects:  78% (491/629)        \rremote: Counting objects:  79% (497/629)        \rremote: Counting objects:  80% (504/629)        \rremote: Counting objects:  81% (510/629)        \rremote: Counting objects:  82% (516/629)        \rremote: Counting objects:  83% (523/629)        \rremote: Counting objects:  84% (529/629)        \rremote: Counting objects:  85% (535/629)        \rremote: Counting objects:  86% (541/629)        \rremote: Counting objects:  87% (548/629)        \rremote: Counting objects:  88% (554/629)        \rremote: Counting objects:  89% (560/629)        \rremote: Counting objects:  90% (567/629)        \rremote: Counting objects:  91% (573/629)        \rremote: Counting objects:  92% (579/629)        \rremote: Counting objects:  93% (585/629)        \rremote: Counting objects:  94% (592/629)        \rremote: Counting objects:  95% (598/629)        \rremote: Counting objects:  96% (604/629)        \rremote: Counting objects:  97% (611/629)        \rremote: Counting objects:  98% (617/629)        \rremote: Counting objects:  99% (623/629)        \rremote: Counting objects: 100% (629/629)        \rremote: Counting objects: 100% (629/629), done.\ninmanta.env              DEBUG   remote: Compressing objects:   0% (1/293)        \rremote: Compressing objects:   1% (3/293)        \rremote: Compressing objects:   2% (6/293)        \rremote: Compressing objects:   3% (9/293)        \rremote: Compressing objects:   4% (12/293)        \rremote: Compressing objects:   5% (15/293)        \rremote: Compressing objects:   6% (18/293)        \rremote: Compressing objects:   7% (21/293)        \rremote: Compressing objects:   8% (24/293)        \rremote: Compressing objects:   9% (27/293)        \rremote: Compressing objects:  10% (30/293)        \rremote: Compressing objects:  11% (33/293)        \rremote: Compressing objects:  12% (36/293)        \rremote: Compressing objects:  13% (39/293)        \rremote: Compressing objects:  14% (42/293)        \rremote: Compressing objects:  15% (44/293)        \rremote: Compressing objects:  16% (47/293)        \rremote: Compressing objects:  17% (50/293)        \rremote: Compressing objects:  18% (53/293)        \rremote: Compressing objects:  19% (56/293)        \rremote: Compressing objects:  20% (59/293)        \rremote: Compressing objects:  21% (62/293)        \rremote: Compressing objects:  22% (65/293)        \rremote: Compressing objects:  23% (68/293)        \rremote: Compressing objects:  24% (71/293)        \rremote: Compressing objects:  25% (74/293)        \rremote: Compressing objects:  26% (77/293)        \rremote: Compressing objects:  27% (80/293)        \rremote: Compressing objects:  28% (83/293)        \rremote: Compressing objects:  29% (85/293)        \rremote: Compressing objects:  30% (88/293)        \rremote: Compressing objects:  31% (91/293)        \rremote: Compressing objects:  32% (94/293)        \rremote: Compressing objects:  33% (97/293)        \rremote: Compressing objects:  34% (100/293)        \rremote: Compressing objects:  35% (103/293)        \rremote: Compressing objects:  36% (106/293)        \rremote: Compressing objects:  37% (109/293)        \rremote: Compressing objects:  38% (112/293)        \rremote: Compressing objects:  39% (115/293)        \rremote: Compressing objects:  40% (118/293)        \rremote: Compressing objects:  41% (121/293)        \rremote: Compressing objects:  42% (124/293)        \rremote: Compressing objects:  43% (126/293)        \rremote: Compressing objects:  44% (129/293)        \rremote: Compressing objects:  45% (132/293)        \rremote: Compressing objects:  46% (135/293)        \rremote: Compressing objects:  47% (138/293)        \rremote: Compressing objects:  48% (141/293)        \rremote: Compressing objects:  49% (144/293)        \rremote: Compressing objects:  50% (147/293)        \rremote: Compressing objects:  51% (150/293)        \rremote: Compressing objects:  52% (153/293)        \rremote: Compressing objects:  53% (156/293)        \rremote: Compressing objects:  54% (159/293)        \rremote: Compressing objects:  55% (162/293)        \rremote: Compressing objects:  56% (165/293)        \rremote: Compressing objects:  57% (168/293)        \rremote: Compressing objects:  58% (170/293)        \rremote: Compressing objects:  59% (173/293)        \rremote: Compressing objects:  60% (176/293)        \rremote: Compressing objects:  61% (179/293)        \rremote: Compressing objects:  62% (182/293)        \rremote: Compressing objects:  63% (185/293)        \rremote: Compressing objects:  64% (188/293)        \rremote: Compressing objects:  65% (191/293)        \rremote: Compressing objects:  66% (194/293)        \rremote: Compressing objects:  67% (197/293)        \rremote: Compressing objects:  68% (200/293)        \rremote: Compressing objects:  69% (203/293)        \rremote: Compressing objects:  70% (206/293)        \rremote: Compressing objects:  71% (209/293)        \rremote: Compressing objects:  72% (211/293)        \rremote: Compressing objects:  73% (214/293)        \rremote: Compressing objects:  74% (217/293)        \rremote: Compressing objects:  75% (220/293)        \rremote: Compressing objects:  76% (223/293)        \rremote: Compressing objects:  77% (226/293)        \rremote: Compressing objects:  78% (229/293)        \rremote: Compressing objects:  79% (232/293)        \rremote: Compressing objects:  80% (235/293)        \rremote: Compressing objects:  81% (238/293)        \rremote: Compressing objects:  82% (241/293)        \rremote: Compressing objects:  83% (244/293)        \rremote: Compressing objects:  84% (247/293)        \rremote: Compressing objects:  85% (250/293)        \rremote: Compressing objects:  86% (252/293)        \rremote: Compressing objects:  87% (255/293)        \rremote: Compressing objects:  88% (258/293)        \rremote: Compressing objects:  89% (261/293)        \rremote: Compressing objects:  90% (264/293)        \rremote: Compressing objects:  91% (267/293)        \rremote: Compressing objects:  92% (270/293)        \rremote: Compressing objects:  93% (273/293)        \rremote: Compressing objects:  94% (276/293)        \rremote: Compressing objects:  95% (279/293)        \rremote: Compressing objects:  96% (282/293)        \rremote: Compressing objects:  97% (285/293)        \rremote: Compressing objects:  98% (288/293)        \rremote: Compressing objects:  99% (291/293)        \rremote: Compressing objects: 100% (293/293)        \rremote: Compressing objects: 100% (293/293), done.\ninmanta.env              DEBUG   Receiving objects:   0% (1/2450)\rReceiving objects:   1% (25/2450)\rReceiving objects:   2% (49/2450)\rReceiving objects:   3% (74/2450)\rReceiving objects:   4% (98/2450)\rReceiving objects:   5% (123/2450)\rReceiving objects:   6% (147/2450)\rReceiving objects:   7% (172/2450)\rReceiving objects:   8% (196/2450)\rReceiving objects:   9% (221/2450)\rReceiving objects:  10% (245/2450)\rReceiving objects:  11% (270/2450)\rReceiving objects:  12% (294/2450)\rReceiving objects:  13% (319/2450)\rReceiving objects:  14% (343/2450)\rReceiving objects:  15% (368/2450)\rReceiving objects:  16% (392/2450)\rReceiving objects:  17% (417/2450)\rReceiving objects:  18% (441/2450)\rReceiving objects:  19% (466/2450)\rReceiving objects:  20% (490/2450)\rReceiving objects:  21% (515/2450)\rReceiving objects:  22% (539/2450)\rReceiving objects:  23% (564/2450)\rReceiving objects:  24% (588/2450)\rReceiving objects:  25% (613/2450)\rReceiving objects:  26% (637/2450)\rReceiving objects:  27% (662/2450)\rReceiving objects:  28% (686/2450)\rReceiving objects:  29% (711/2450)\rReceiving objects:  30% (735/2450)\rReceiving objects:  31% (760/2450)\rReceiving objects:  32% (784/2450)\rReceiving objects:  33% (809/2450)\rReceiving objects:  34% (833/2450)\rReceiving objects:  35% (858/2450)\rReceiving objects:  36% (882/2450)\rReceiving objects:  37% (907/2450)\rReceiving objects:  38% (931/2450)\rReceiving objects:  39% (956/2450)\rReceiving objects:  40% (980/2450)\rReceiving objects:  41% (1005/2450)\rReceiving objects:  42% (1029/2450)\rReceiving objects:  43% (1054/2450)\rReceiving objects:  44% (1078/2450)\rReceiving objects:  45% (1103/2450)\rReceiving objects:  46% (1127/2450)\rReceiving objects:  47% (1152/2450)\rReceiving objects:  48% (1176/2450)\rReceiving objects:  49% (1201/2450)\rReceiving objects:  50% (1225/2450)\rReceiving objects:  51% (1250/2450)\rReceiving objects:  52% (1274/2450)\rReceiving objects:  53% (1299/2450)\rReceiving objects:  54% (1323/2450)\rReceiving objects:  55% (1348/2450)\rReceiving objects:  56% (1372/2450)\rReceiving objects:  57% (1397/2450)\rReceiving objects:  58% (1421/2450)\rReceiving objects:  59% (1446/2450)\rReceiving objects:  60% (1470/2450)\rReceiving objects:  61% (1495/2450)\rReceiving objects:  62% (1519/2450)\rReceiving objects:  63% (1544/2450)\rReceiving objects:  64% (1568/2450)\rReceiving objects:  65% (1593/2450)\rReceiving objects:  66% (1617/2450)\rReceiving objects:  67% (1642/2450)\rReceiving objects:  68% (1666/2450)\rReceiving objects:  69% (1691/2450)\rReceiving objects:  70% (1715/2450)\rReceiving objects:  71% (1740/2450)\rReceiving objects:  72% (1764/2450)\rReceiving objects:  73% (1789/2450)\rReceiving objects:  74% (1813/2450)\rReceiving objects:  75% (1838/2450)\rReceiving objects:  76% (1862/2450)\rReceiving objects:  77% (1887/2450)\rReceiving objects:  78% (1911/2450)\rReceiving objects:  79% (1936/2450)\rReceiving objects:  80% (1960/2450)\rReceiving objects:  81% (1985/2450)\rremote: Total 2450 (delta 325), reused 563 (delta 292), pack-reused 1821\ninmanta.env              DEBUG   Receiving objects:  82% (2009/2450)\rReceiving objects:  83% (2034/2450)\rReceiving objects:  84% (2058/2450)\rReceiving objects:  85% (2083/2450)\rReceiving objects:  86% (2107/2450)\rReceiving objects:  87% (2132/2450)\rReceiving objects:  88% (2156/2450)\rReceiving objects:  89% (2181/2450)\rReceiving objects:  90% (2205/2450)\rReceiving objects:  91% (2230/2450)\rReceiving objects:  92% (2254/2450)\rReceiving objects:  93% (2279/2450)\rReceiving objects:  94% (2303/2450)\rReceiving objects:  95% (2328/2450)\rReceiving objects:  96% (2352/2450)\rReceiving objects:  97% (2377/2450)\rReceiving objects:  98% (2401/2450)\rReceiving objects:  99% (2426/2450)\rReceiving objects: 100% (2450/2450)\rReceiving objects: 100% (2450/2450), 496.58 KiB | 8.28 MiB/s, done.\ninmanta.env              DEBUG   Resolving deltas:   0% (0/1293)\rResolving deltas:   1% (13/1293)\rResolving deltas:   2% (26/1293)\rResolving deltas:   3% (39/1293)\rResolving deltas:   4% (52/1293)\rResolving deltas:   5% (65/1293)\rResolving deltas:   6% (78/1293)\rResolving deltas:   7% (91/1293)\rResolving deltas:   8% (104/1293)\rResolving deltas:   9% (117/1293)\rResolving deltas:  10% (130/1293)\rResolving deltas:  11% (143/1293)\rResolving deltas:  12% (156/1293)\rResolving deltas:  13% (169/1293)\rResolving deltas:  14% (182/1293)\rResolving deltas:  15% (194/1293)\rResolving deltas:  16% (207/1293)\rResolving deltas:  17% (220/1293)\rResolving deltas:  18% (233/1293)\rResolving deltas:  19% (246/1293)\rResolving deltas:  20% (259/1293)\rResolving deltas:  21% (272/1293)\rResolving deltas:  22% (285/1293)\rResolving deltas:  23% (298/1293)\rResolving deltas:  24% (311/1293)\rResolving deltas:  25% (324/1293)\rResolving deltas:  26% (337/1293)\rResolving deltas:  27% (350/1293)\rResolving deltas:  28% (363/1293)\rResolving deltas:  29% (375/1293)\rResolving deltas:  30% (388/1293)\rResolving deltas:  31% (401/1293)\rResolving deltas:  32% (414/1293)\rResolving deltas:  33% (427/1293)\rResolving deltas:  34% (440/1293)\rResolving deltas:  35% (453/1293)\rResolving deltas:  36% (466/1293)\rResolving deltas:  37% (479/1293)\rResolving deltas:  38% (492/1293)\rResolving deltas:  39% (505/1293)\rResolving deltas:  40% (518/1293)\rResolving deltas:  41% (531/1293)\rResolving deltas:  42% (544/1293)\rResolving deltas:  43% (556/1293)\rResolving deltas:  44% (569/1293)\rResolving deltas:  45% (582/1293)\rResolving deltas:  46% (595/1293)\rResolving deltas:  47% (608/1293)\rResolving deltas:  48% (621/1293)\rResolving deltas:  49% (634/1293)\rResolving deltas:  50% (647/1293)\rResolving deltas:  51% (660/1293)\rResolving deltas:  52% (673/1293)\rResolving deltas:  53% (686/1293)\rResolving deltas:  54% (699/1293)\rResolving deltas:  55% (712/1293)\rResolving deltas:  56% (725/1293)\rResolving deltas:  57% (738/1293)\rResolving deltas:  58% (751/1293)\rResolving deltas:  59% (763/1293)\rResolving deltas:  60% (776/1293)\rResolving deltas:  61% (789/1293)\rResolving deltas:  62% (802/1293)\rResolving deltas:  63% (815/1293)\rResolving deltas:  64% (828/1293)\rResolving deltas:  65% (841/1293)\rResolving deltas:  66% (854/1293)\rResolving deltas:  67% (867/1293)\rResolving deltas:  68% (880/1293)\rResolving deltas:  69% (893/1293)\rResolving deltas:  70% (906/1293)\rResolving deltas:  71% (919/1293)\rResolving deltas:  72% (931/1293)\rResolving deltas:  73% (944/1293)\rResolving deltas:  74% (957/1293)\rResolving deltas:  75% (970/1293)\rResolving deltas:  76% (983/1293)\rResolving deltas:  77% (996/1293)\rResolving deltas:  78% (1009/1293)\rResolving deltas:  79% (1023/1293)\rResolving deltas:  80% (1035/1293)\rResolving deltas:  81% (1048/1293)\rResolving deltas:  82% (1061/1293)\rResolving deltas:  83% (1074/1293)\rResolving deltas:  84% (1087/1293)\rResolving deltas:  85% (1100/1293)\rResolving deltas:  86% (1113/1293)\rResolving deltas:  87% (1125/1293)\rResolving deltas:  88% (1139/1293)\rResolving deltas:  89% (1151/1293)\rResolving deltas:  90% (1164/1293)\rResolving deltas:  91% (1177/1293)\rResolving deltas:  92% (1190/1293)\rResolving deltas:  93% (1203/1293)\rResolving deltas:  94% (1216/1293)\rResolving deltas:  95% (1229/1293)\rResolving deltas:  96% (1242/1293)\rResolving deltas:  97% (1255/1293)\rResolving deltas:  98% (1268/1293)\rResolving deltas:  99% (1282/1293)\rResolving deltas: 100% (1293/1293)\rResolving deltas: 100% (1293/1293), done.\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 3.1.4 in /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std from https://github.com/inmanta/std.\ninmanta.module           DEBUG   Parsing took 0.000132 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.9.1)\ninmanta.env              DEBUG   Collecting pydantic~=1.9\ninmanta.env              DEBUG   Using cached pydantic-1.9.2-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (12.4 MB)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta==2020.5.1rc0 in /home/sander/documents/projects/inmanta/inmanta-core/src (2020.5.1rc0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.7.1)\ninmanta.env              DEBUG   Collecting typing-inspect~=0.7\ninmanta.env              DEBUG   Using cached typing_inspect-0.8.0-py3-none-any.whl (8.7 kB)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.6.0)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=3.7.4.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.env              DEBUG   Installing collected packages: typing-inspect, pydantic\ninmanta.env              DEBUG   Attempting uninstall: typing-inspect\ninmanta.env              DEBUG   Found existing installation: typing-inspect 0.7.1\ninmanta.env              DEBUG   Not uninstalling typing-inspect at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/.env\ninmanta.env              DEBUG   Can't uninstall 'typing-inspect'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: pydantic\ninmanta.env              DEBUG   Found existing installation: pydantic 1.9.1\ninmanta.env              DEBUG   Not uninstalling pydantic at /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages, outside environment /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/.env\ninmanta.env              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.env              DEBUG   Successfully installed pydantic-1.9.2 typing-inspect-0.8.0\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000082 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.9.2)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta==2020.5.1rc0 in /home/sander/documents/projects/inmanta/inmanta-core/src (2020.5.1rc0)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.6.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=3.7.4.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.module           INFO    verifying project\n	0	0658c339-41e1-4d40-aa5e-78ad9801f3e6
b5a95bbf-6ca2-4ded-a8bc-3f57ee43e288	2022-08-19 11:18:36.580798+02	2022-08-19 11:18:41.091696+02	/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/.env/bin/python -m inmanta.app -vvv export -X -e f0a8a1e8-59a8-4f86-861a-67dedcc3f511 --server_address localhost --server_port 38417 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp1kfulvrq	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.005754 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000116 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002979)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002143)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000087)\ninmanta.execute.schedulerINFO    Total compilation time 0.005310\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:38417/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:38417/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:38417/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:38417/api/v1/file/63ae135b9a2eb874b3aa81fe5bd84283ef3617c9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:38417/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:38417/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:38417/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:38417/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	0658c339-41e1-4d40-aa5e-78ad9801f3e6
44a9bcef-3ce7-4fd2-894a-3bc1f1daa27c	2022-08-19 11:18:44.452586+02	2022-08-19 11:18:44.454762+02		Init		Using extra environment variables during compile \n	0	2c07c873-07b0-48ca-8931-53036a653ba3
e273d60d-1d77-40b5-9648-aeafa4316fa2	2022-08-19 11:18:54.447996+02	2022-08-19 11:18:55.82981+02	/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/.env/bin/python -m inmanta.app -vvv export -X -e f0a8a1e8-59a8-4f86-861a-67dedcc3f511 --server_address localhost --server_port 38417 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpxskag_0k	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.005849 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000123 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003159)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002126)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000070)\ninmanta.execute.schedulerINFO    Total compilation time 0.005466\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:38417/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:38417/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:38417/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:38417/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:38417/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	2c07c873-07b0-48ca-8931-53036a653ba3
78d45d84-096a-4a08-a3c1-7f7f0cc7254b	2022-08-19 11:18:44.460411+02	2022-08-19 11:18:54.446828+02	/tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000129 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.9.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta==2020.5.1rc0 in /home/sander/documents/projects/inmanta/inmanta-core/src (2020.5.1rc0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.6.0)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=3.7.4.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000081 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpwxtigdct/server/environments/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/libs/std\ninmanta.module           INFO    verifying project\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.9.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta==2020.5.1rc0 in /home/sander/documents/projects/inmanta/inmanta-core/src (2020.5.1rc0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.6.0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=3.7.4.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/sander/.virtualenvs/inmanta-core-39/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.module           INFO    verifying project\n	0	2c07c873-07b0-48ca-8931-53036a653ba3
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-08-19 11:18:44.383122+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-08-19 11:18:44.649572+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-08-19 11:18:55.729401+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-08-19 11:18:55.759796+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
c774fa44-0f5a-49aa-bd09-63ff1234d3c6	store	2022-08-19 11:18:37.837209+02	2022-08-19 11:18:39.419647+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-08-19T11:18:39.419691+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
48f4ce55-4679-4dae-ac26-021424ea4dd1	pull	2022-08-19 11:18:40.975188+02	2022-08-19 11:18:40.977724+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-08-19T11:18:40.978709+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
5e6966cb-d74b-4d43-99a6-71f7097f9f7b	pull	2022-08-19 11:18:41.887324+02	2022-08-19 11:18:41.891056+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-08-19T11:18:41.891071+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::File[localhost,path=/tmp/test],v=1"}
c987225d-2338-4773-a240-756a49f20df1	deploy	2022-08-19 11:18:41.009914+02	2022-08-19 11:18:41.029316+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"a0e6abbe-a22a-4c6e-a695-474455ce5033\\"}, \\"timestamp\\": \\"2022-08-19T11:18:41.005843+02:00\\"}","{\\"msg\\": \\"Start deploy a0e6abbe-a22a-4c6e-a695-474455ce5033 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"a0e6abbe-a22a-4c6e-a695-474455ce5033\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-08-19T11:18:41.012449+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-19T11:18:41.013161+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-19T11:18:41.017489+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy a0e6abbe-a22a-4c6e-a695-474455ce5033\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"a0e6abbe-a22a-4c6e-a695-474455ce5033\\"}, \\"timestamp\\": \\"2022-08-19T11:18:41.021752+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
d1e2c674-0ec5-4b8d-8f36-bba3e0ccc3e4	pull	2022-08-19 11:18:41.96783+02	2022-08-19 11:18:41.969611+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-08-19T11:18:41.969621+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::File[localhost,path=/tmp/test],v=1"}
ca3214b1-402e-4c29-b3bc-14f0cde67ce7	deploy	2022-08-19 11:18:42.749286+02	2022-08-19 11:18:43.548963+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-08-19 11:18:41+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-08-19 11:18:41+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"37ad2811-e469-4247-a5ab-8cf2783bb80a\\"}, \\"timestamp\\": \\"2022-08-19T11:18:41.918812+02:00\\"}","{\\"msg\\": \\"Start deploy 37ad2811-e469-4247-a5ab-8cf2783bb80a of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"37ad2811-e469-4247-a5ab-8cf2783bb80a\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-19T11:18:43.538918+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-19T11:18:43.539654+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-08-19T11:18:43.543270+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpwxtigdct/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-19T11:18:43.543929+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 37ad2811-e469-4247-a5ab-8cf2783bb80a\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"37ad2811-e469-4247-a5ab-8cf2783bb80a\\"}, \\"timestamp\\": \\"2022-08-19T11:18:43.544356+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::File[localhost,path=/tmp/test],v=1"}
1e4f5cb7-f3b8-4f07-b042-9ebc8ea7b5fb	deploy	2022-08-19 11:18:44.374173+02	2022-08-19 11:18:44.383122+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"051889e5-2b59-4a3e-9746-2a0dab5e07d3\\"}, \\"timestamp\\": \\"2022-08-19T11:18:44.370514+02:00\\"}","{\\"msg\\": \\"Start deploy 051889e5-2b59-4a3e-9746-2a0dab5e07d3 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"051889e5-2b59-4a3e-9746-2a0dab5e07d3\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-19T11:18:44.376354+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-19T11:18:44.376785+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-08-19T11:18:44.379448+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpwxtigdct/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-19T11:18:44.379731+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 051889e5-2b59-4a3e-9746-2a0dab5e07d3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"051889e5-2b59-4a3e-9746-2a0dab5e07d3\\"}, \\"timestamp\\": \\"2022-08-19T11:18:44.380008+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::File[localhost,path=/tmp/test],v=1"}
c9a68032-b349-41a9-8260-70554d0b2a26	pull	2022-08-19 11:18:43.04329+02	2022-08-19 11:18:43.869691+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-08-19T11:18:43.869705+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
6afc3f6a-b009-447a-b17f-996efca9f068	deploy	2022-08-19 11:18:44.638897+02	2022-08-19 11:18:44.649572+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-08-19 11:18:43+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-08-19 11:18:43+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"ff466115-39cd-4ba5-8047-b110128ff85b\\"}, \\"timestamp\\": \\"2022-08-19T11:18:44.634583+02:00\\"}","{\\"msg\\": \\"Start deploy ff466115-39cd-4ba5-8047-b110128ff85b of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"ff466115-39cd-4ba5-8047-b110128ff85b\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-08-19T11:18:44.641240+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-19T11:18:44.642104+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy ff466115-39cd-4ba5-8047-b110128ff85b\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"ff466115-39cd-4ba5-8047-b110128ff85b\\"}, \\"timestamp\\": \\"2022-08-19T11:18:44.646788+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
884cb131-bd77-424d-a4c4-775e092845b8	store	2022-08-19 11:18:55.709449+02	2022-08-19 11:18:55.712602+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-08-19T11:18:55.712621+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
d6c23b77-8a6c-445d-8ebe-dc804b7e2bab	pull	2022-08-19 11:18:55.726143+02	2022-08-19 11:18:55.729272+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-08-19T11:18:55.730817+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2	{"std::File[localhost,path=/tmp/test],v=2"}
8cab31f2-d54d-4d02-90f3-a7fefb1e93d9	deploy	2022-08-19 11:18:55.729401+02	2022-08-19 11:18:55.729401+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-08-19T09:18:55.729401+00:00\\"}"}	deployed	\N	nochange	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
774d3bbe-dc0b-401a-896d-6a0d7201014f	deploy	2022-08-19 11:18:55.750364+02	2022-08-19 11:18:55.759796+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"fe4b4024-a989-4c6a-aa44-525e6c027ec0\\"}, \\"timestamp\\": \\"2022-08-19T11:18:55.747015+02:00\\"}","{\\"msg\\": \\"Start deploy fe4b4024-a989-4c6a-aa44-525e6c027ec0 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"fe4b4024-a989-4c6a-aa44-525e6c027ec0\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-19T11:18:55.752482+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-08-19T11:18:55.752908+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"sander\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-08-19T11:18:55.755674+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpwxtigdct/f0a8a1e8-59a8-4f86-861a-67dedcc3f511/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/sander/documents/projects/inmanta/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-08-19T11:18:55.755919+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy fe4b4024-a989-4c6a-aa44-525e6c027ec0\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"fe4b4024-a989-4c6a-aa44-525e6c027ec0\\"}, \\"timestamp\\": \\"2022-08-19T11:18:55.756200+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2	{"std::File[localhost,path=/tmp/test],v=2"}
0160eed3-d671-4fa4-86b5-dca0892a7983	pull	2022-08-19 11:18:55.963+02	2022-08-19 11:18:55.965742+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-08-19T11:18:55.965753+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
463b97be-5a74-4c7e-9694-7f97d1786632	pull	2022-08-19 11:18:55.963179+02	2022-08-19 11:18:55.966454+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-08-19T11:18:55.966461+02:00\\"}"}	\N	\N	\N	f0a8a1e8-59a8-4f86-861a-67dedcc3f511	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180}
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

