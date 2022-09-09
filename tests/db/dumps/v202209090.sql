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
0468b7d3-3847-40d8-887c-e458f9c8e58a	internal	2022-09-09 15:15:18.461851+02	f	9ba0e3c0-a871-4f25-9885-bc83822c4567	\N
0468b7d3-3847-40d8-887c-e458f9c8e58a	localhost	2022-09-09 15:15:20.607641+02	f	9dd6d56b-0ac2-4237-8d8f-88ddf66bfc4d	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
9ba0e3c0-a871-4f25-9885-bc83822c4567	73568b22-3041-11ed-a828-e9dfe4aa0a13	internal	\N	0468b7d3-3847-40d8-887c-e458f9c8e58a
9dd6d56b-0ac2-4237-8d8f-88ddf66bfc4d	73568b22-3041-11ed-a828-e9dfe4aa0a13	localhost	\N	0468b7d3-3847-40d8-887c-e458f9c8e58a
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
florent-Latitude-5421	0468b7d3-3847-40d8-887c-e458f9c8e58a	2022-09-09 15:15:18.461851+02	2022-09-09 15:15:32.133974+02	\N	73568b22-3041-11ed-a828-e9dfe4aa0a13
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::Service	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::File	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::Directory	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::Package	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::Symlink	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::AgentConfig	1	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::Service	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::File	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::Directory	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::Package	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::Symlink	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
0468b7d3-3847-40d8-887c-e458f9c8e58a	std::AgentConfig	2	{"63ae135b9a2eb874b3aa81fe5bd84283ef3617c9": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]], "9d0d5cd7c8331a5e3a20ae9c68979cafde658d21": ["/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.1", "pydantic~=1.9", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets) FROM stdin;
68c2d132-27a0-4843-ad95-10e04cf7e58b	0468b7d3-3847-40d8-887c-e458f9c8e58a	2022-09-09 15:14:58.381303+02	2022-09-09 15:15:18.638279+02	2022-09-09 15:14:58.325986+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	6d35b0d9-dfb9-495a-8dea-d8c3c59e094a	t	\N	{"errors": []}	f	{}
82a4e87f-1f29-4bef-884a-725e0f5e7a46	0468b7d3-3847-40d8-887c-e458f9c8e58a	2022-09-09 15:15:20.682238+02	2022-09-09 15:15:31.051498+02	2022-09-09 15:15:20.679047+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	5a65f72f-ea83-4eca-adc5-c8db2c977fba	t	\N	{"errors": []}	f	{}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	0468b7d3-3847-40d8-887c-e458f9c8e58a	2022-09-09 15:15:16.418993+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	0468b7d3-3847-40d8-887c-e458f9c8e58a	2022-09-09 15:15:30.955264+02	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "florent", "hostname": "florent-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N
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
d46618b0-4426-4ba0-921d-3d91f4953295	dev-2	11e1dbe9-9ba1-498d-a74d-973a533ab286			{"auto_full_compile": ""}	0	f		
0468b7d3-3847-40d8-887c-e458f9c8e58a	dev-1	11e1dbe9-9ba1-498d-a74d-973a533ab286			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
11e1dbe9-9ba1-498d-a74d-973a533ab286	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
c4ff5039-7c0e-49d3-80f1-755f5483f4e6	2022-09-09 15:14:58.381654+02	2022-09-09 15:14:58.382728+02		Init		Using extra environment variables during compile \n	0	68c2d132-27a0-4843-ad95-10e04cf7e58b
77879e5c-ba3d-4269-96ab-d7c752041acf	2022-09-09 15:14:58.383003+02	2022-09-09 15:14:58.389246+02		Creating venv			0	68c2d132-27a0-4843-ad95-10e04cf7e58b
96a3fa27-163a-4730-959d-1438f15d8dd3	2022-09-09 15:14:58.393421+02	2022-09-09 15:14:58.666354+02	/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	68c2d132-27a0-4843-ad95-10e04cf7e58b
eb9094e1-5a91-4983-90b3-81b2c8aa9a32	2022-09-09 15:14:58.667325+02	2022-09-09 15:15:15.720823+02	/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.env              DEBUG   Cloning into '/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std'...\ninmanta.env              DEBUG   remote: Enumerating objects: 2459, done.\ninmanta.env              DEBUG   remote: Counting objects:   0% (1/638)        \rremote: Counting objects:   1% (7/638)        \rremote: Counting objects:   2% (13/638)        \rremote: Counting objects:   3% (20/638)        \rremote: Counting objects:   4% (26/638)        \rremote: Counting objects:   5% (32/638)        \rremote: Counting objects:   6% (39/638)        \rremote: Counting objects:   7% (45/638)        \rremote: Counting objects:   8% (52/638)        \rremote: Counting objects:   9% (58/638)        \rremote: Counting objects:  10% (64/638)        \rremote: Counting objects:  11% (71/638)        \rremote: Counting objects:  12% (77/638)        \rremote: Counting objects:  13% (83/638)        \rremote: Counting objects:  14% (90/638)        \rremote: Counting objects:  15% (96/638)        \rremote: Counting objects:  16% (103/638)        \rremote: Counting objects:  17% (109/638)        \rremote: Counting objects:  18% (115/638)        \rremote: Counting objects:  19% (122/638)        \rremote: Counting objects:  20% (128/638)        \rremote: Counting objects:  21% (134/638)        \rremote: Counting objects:  22% (141/638)        \rremote: Counting objects:  23% (147/638)        \rremote: Counting objects:  24% (154/638)        \rremote: Counting objects:  25% (160/638)        \rremote: Counting objects:  26% (166/638)        \rremote: Counting objects:  27% (173/638)        \rremote: Counting objects:  28% (179/638)        \rremote: Counting objects:  29% (186/638)        \rremote: Counting objects:  30% (192/638)        \rremote: Counting objects:  31% (198/638)        \rremote: Counting objects:  32% (205/638)        \rremote: Counting objects:  33% (211/638)        \rremote: Counting objects:  34% (217/638)        \rremote: Counting objects:  35% (224/638)        \rremote: Counting objects:  36% (230/638)        \rremote: Counting objects:  37% (237/638)        \rremote: Counting objects:  38% (243/638)        \rremote: Counting objects:  39% (249/638)        \rremote: Counting objects:  40% (256/638)        \rremote: Counting objects:  41% (262/638)        \rremote: Counting objects:  42% (268/638)        \rremote: Counting objects:  43% (275/638)        \rremote: Counting objects:  44% (281/638)        \rremote: Counting objects:  45% (288/638)        \rremote: Counting objects:  46% (294/638)        \rremote: Counting objects:  47% (300/638)        \rremote: Counting objects:  48% (307/638)        \rremote: Counting objects:  49% (313/638)        \rremote: Counting objects:  50% (319/638)        \rremote: Counting objects:  51% (326/638)        \rremote: Counting objects:  52% (332/638)        \rremote: Counting objects:  53% (339/638)        \rremote: Counting objects:  54% (345/638)        \rremote: Counting objects:  55% (351/638)        \rremote: Counting objects:  56% (358/638)        \rremote: Counting objects:  57% (364/638)        \rremote: Counting objects:  58% (371/638)        \rremote: Counting objects:  59% (377/638)        \rremote: Counting objects:  60% (383/638)        \rremote: Counting objects:  61% (390/638)        \rremote: Counting objects:  62% (396/638)        \rremote: Counting objects:  63% (402/638)        \rremote: Counting objects:  64% (409/638)        \rremote: Counting objects:  65% (415/638)        \rremote: Counting objects:  66% (422/638)        \rremote: Counting objects:  67% (428/638)        \rremote: Counting objects:  68% (434/638)        \rremote: Counting objects:  69% (441/638)        \rremote: Counting objects:  70% (447/638)        \rremote: Counting objects:  71% (453/638)        \rremote: Counting objects:  72% (460/638)        \rremote: Counting objects:  73% (466/638)        \rremote: Counting objects:  74% (473/638)        \rremote: Counting objects:  75% (479/638)        \rremote: Counting objects:  76% (485/638)        \rremote: Counting objects:  77% (492/638)        \rremote: Counting objects:  78% (498/638)        \rremote: Counting objects:  79% (505/638)        \rremote: Counting objects:  80% (511/638)        \rremote: Counting objects:  81% (517/638)        \rremote: Counting objects:  82% (524/638)        \rremote: Counting objects:  83% (530/638)        \rremote: Counting objects:  84% (536/638)        \rremote: Counting objects:  85% (543/638)        \rremote: Counting objects:  86% (549/638)        \rremote: Counting objects:  87% (556/638)        \rremote: Counting objects:  88% (562/638)        \rremote: Counting objects:  89% (568/638)        \rremote: Counting objects:  90% (575/638)        \rremote: Counting objects:  91% (581/638)        \rremote: Counting objects:  92% (587/638)        \rremote: Counting objects:  93% (594/638)        \rremote: Counting objects:  94% (600/638)        \rremote: Counting objects:  95% (607/638)        \rremote: Counting objects:  96% (613/638)        \rremote: Counting objects:  97% (619/638)        \rremote: Counting objects:  98% (626/638)        \rremote: Counting objects:  99% (632/638)        \rremote: Counting objects: 100% (638/638)        \rremote: Counting objects: 100% (638/638), done.\ninmanta.env              DEBUG   remote: Compressing objects:   0% (1/302)        \rremote: Compressing objects:   1% (4/302)        \rremote: Compressing objects:   2% (7/302)        \rremote: Compressing objects:   3% (10/302)        \rremote: Compressing objects:   4% (13/302)        \rremote: Compressing objects:   5% (16/302)        \rremote: Compressing objects:   6% (19/302)        \rremote: Compressing objects:   7% (22/302)        \rremote: Compressing objects:   8% (25/302)        \rremote: Compressing objects:   9% (28/302)        \rremote: Compressing objects:  10% (31/302)        \rremote: Compressing objects:  11% (34/302)        \rremote: Compressing objects:  12% (37/302)        \rremote: Compressing objects:  13% (40/302)        \rremote: Compressing objects:  14% (43/302)        \rremote: Compressing objects:  15% (46/302)        \rremote: Compressing objects:  16% (49/302)        \rremote: Compressing objects:  17% (52/302)        \rremote: Compressing objects:  18% (55/302)        \rremote: Compressing objects:  19% (58/302)        \rremote: Compressing objects:  20% (61/302)        \rremote: Compressing objects:  21% (64/302)        \rremote: Compressing objects:  22% (67/302)        \rremote: Compressing objects:  23% (70/302)        \rremote: Compressing objects:  24% (73/302)        \rremote: Compressing objects:  25% (76/302)        \rremote: Compressing objects:  26% (79/302)        \rremote: Compressing objects:  27% (82/302)        \rremote: Compressing objects:  28% (85/302)        \rremote: Compressing objects:  29% (88/302)        \rremote: Compressing objects:  30% (91/302)        \rremote: Compressing objects:  31% (94/302)        \rremote: Compressing objects:  32% (97/302)        \rremote: Compressing objects:  33% (100/302)        \rremote: Compressing objects:  34% (103/302)        \rremote: Compressing objects:  35% (106/302)        \rremote: Compressing objects:  36% (109/302)        \rremote: Compressing objects:  37% (112/302)        \rremote: Compressing objects:  38% (115/302)        \rremote: Compressing objects:  39% (118/302)        \rremote: Compressing objects:  40% (121/302)        \rremote: Compressing objects:  41% (124/302)        \rremote: Compressing objects:  42% (127/302)        \rremote: Compressing objects:  43% (130/302)        \rremote: Compressing objects:  44% (133/302)        \rremote: Compressing objects:  45% (136/302)        \rremote: Compressing objects:  46% (139/302)        \rremote: Compressing objects:  47% (142/302)        \rremote: Compressing objects:  48% (145/302)        \rremote: Compressing objects:  49% (148/302)        \rremote: Compressing objects:  50% (151/302)        \rremote: Compressing objects:  51% (155/302)        \rremote: Compressing objects:  52% (158/302)        \rremote: Compressing objects:  53% (161/302)        \rremote: Compressing objects:  54% (164/302)        \rremote: Compressing objects:  55% (167/302)        \rremote: Compressing objects:  56% (170/302)        \rremote: Compressing objects:  57% (173/302)        \rremote: Compressing objects:  58% (176/302)        \rremote: Compressing objects:  59% (179/302)        \rremote: Compressing objects:  60% (182/302)        \rremote: Compressing objects:  61% (185/302)        \rremote: Compressing objects:  62% (188/302)        \rremote: Compressing objects:  63% (191/302)        \rremote: Compressing objects:  64% (194/302)        \rremote: Compressing objects:  65% (197/302)        \rremote: Compressing objects:  66% (200/302)        \rremote: Compressing objects:  67% (203/302)        \rremote: Compressing objects:  68% (206/302)        \rremote: Compressing objects:  69% (209/302)        \rremote: Compressing objects:  70% (212/302)        \rremote: Compressing objects:  71% (215/302)        \rremote: Compressing objects:  72% (218/302)        \rremote: Compressing objects:  73% (221/302)        \rremote: Compressing objects:  74% (224/302)        \rremote: Compressing objects:  75% (227/302)        \rremote: Compressing objects:  76% (230/302)        \rremote: Compressing objects:  77% (233/302)        \rremote: Compressing objects:  78% (236/302)        \rremote: Compressing objects:  79% (239/302)        \rremote: Compressing objects:  80% (242/302)        \rremote: Compressing objects:  81% (245/302)        \rremote: Compressing objects:  82% (248/302)        \rremote: Compressing objects:  83% (251/302)        \rremote: Compressing objects:  84% (254/302)        \rremote: Compressing objects:  85% (257/302)        \rremote: Compressing objects:  86% (260/302)        \rremote: Compressing objects:  87% (263/302)        \rremote: Compressing objects:  88% (266/302)        \rremote: Compressing objects:  89% (269/302)        \rremote: Compressing objects:  90% (272/302)        \rremote: Compressing objects:  91% (275/302)        \rremote: Compressing objects:  92% (278/302)        \rremote: Compressing objects:  93% (281/302)        \rremote: Compressing objects:  94% (284/302)        \rremote: Compressing objects:  95% (287/302)        \rremote: Compressing objects:  96% (290/302)        \rremote: Compressing objects:  97% (293/302)        \rremote: Compressing objects:  98% (296/302)        \rremote: Compressing objects:  99% (299/302)        \rremote: Compressing objects: 100% (302/302)        \rremote: Compressing objects: 100% (302/302), done.\ninmanta.env              DEBUG   Receiving objects:   0% (1/2459)\rReceiving objects:   1% (25/2459)\rReceiving objects:   2% (50/2459)\rReceiving objects:   3% (74/2459)\rReceiving objects:   4% (99/2459)\rReceiving objects:   5% (123/2459)\rReceiving objects:   6% (148/2459)\rReceiving objects:   7% (173/2459)\rReceiving objects:   8% (197/2459)\rReceiving objects:   9% (222/2459)\rReceiving objects:  10% (246/2459)\rReceiving objects:  11% (271/2459)\rReceiving objects:  12% (296/2459)\rReceiving objects:  13% (320/2459)\rReceiving objects:  14% (345/2459)\rReceiving objects:  15% (369/2459)\rReceiving objects:  16% (394/2459)\rReceiving objects:  17% (419/2459)\rReceiving objects:  18% (443/2459)\rReceiving objects:  19% (468/2459)\rReceiving objects:  20% (492/2459)\rReceiving objects:  21% (517/2459)\rReceiving objects:  22% (541/2459)\rReceiving objects:  23% (566/2459)\rReceiving objects:  24% (591/2459)\rReceiving objects:  25% (615/2459)\rReceiving objects:  26% (640/2459)\rReceiving objects:  27% (664/2459)\rReceiving objects:  28% (689/2459)\rReceiving objects:  29% (714/2459)\rReceiving objects:  30% (738/2459)\rReceiving objects:  31% (763/2459)\rReceiving objects:  32% (787/2459)\rReceiving objects:  33% (812/2459)\rReceiving objects:  34% (837/2459)\rReceiving objects:  35% (861/2459)\rReceiving objects:  36% (886/2459)\rReceiving objects:  37% (910/2459)\rReceiving objects:  38% (935/2459)\rReceiving objects:  39% (960/2459)\rReceiving objects:  40% (984/2459)\rReceiving objects:  41% (1009/2459)\rReceiving objects:  42% (1033/2459)\rReceiving objects:  43% (1058/2459)\rReceiving objects:  44% (1082/2459)\rReceiving objects:  45% (1107/2459)\rReceiving objects:  46% (1132/2459)\rReceiving objects:  47% (1156/2459)\rReceiving objects:  48% (1181/2459)\rReceiving objects:  49% (1205/2459)\rReceiving objects:  50% (1230/2459)\rReceiving objects:  51% (1255/2459)\rReceiving objects:  52% (1279/2459)\rReceiving objects:  53% (1304/2459)\rReceiving objects:  54% (1328/2459)\rReceiving objects:  55% (1353/2459)\rReceiving objects:  56% (1378/2459)\rReceiving objects:  57% (1402/2459)\rReceiving objects:  58% (1427/2459)\rReceiving objects:  59% (1451/2459)\rReceiving objects:  60% (1476/2459)\rReceiving objects:  61% (1500/2459)\rReceiving objects:  62% (1525/2459)\rReceiving objects:  63% (1550/2459)\rReceiving objects:  64% (1574/2459)\rReceiving objects:  65% (1599/2459)\rReceiving objects:  66% (1623/2459)\rReceiving objects:  67% (1648/2459)\rReceiving objects:  68% (1673/2459)\rReceiving objects:  69% (1697/2459)\rReceiving objects:  70% (1722/2459)\rReceiving objects:  71% (1746/2459)\rReceiving objects:  72% (1771/2459)\rReceiving objects:  73% (1796/2459)\rReceiving objects:  74% (1820/2459)\rReceiving objects:  75% (1845/2459)\rReceiving objects:  76% (1869/2459)\rReceiving objects:  77% (1894/2459)\rReceiving objects:  78% (1919/2459)\rReceiving objects:  79% (1943/2459)\rReceiving objects:  80% (1968/2459)\rReceiving objects:  81% (1992/2459)\rReceiving objects:  82% (2017/2459)\rReceiving objects:  83% (2041/2459)\rReceiving objects:  84% (2066/2459)\rReceiving objects:  85% (2091/2459)\rReceiving objects:  86% (2115/2459)\rReceiving objects:  87% (2140/2459)\rReceiving objects:  88% (2164/2459)\rReceiving objects:  89% (2189/2459)\rReceiving objects:  90% (2214/2459)\rReceiving objects:  91% (2238/2459)\rReceiving objects:  92% (2263/2459)\rReceiving objects:  93% (2287/2459)\rReceiving objects:  94% (2312/2459)\rReceiving objects:  95% (2337/2459)\rReceiving objects:  96% (2361/2459)\rReceiving objects:  97% (2386/2459)\rremote: Total 2459 (delta 331), reused 563 (delta 292), pack-reused 1821\ninmanta.env              DEBUG   Receiving objects:  98% (2410/2459)\rReceiving objects:  99% (2435/2459)\rReceiving objects: 100% (2459/2459)\rReceiving objects: 100% (2459/2459), 498.85 KiB | 2.39 MiB/s, done.\ninmanta.env              DEBUG   Resolving deltas:   0% (0/1299)\rResolving deltas:   1% (13/1299)\rResolving deltas:   2% (26/1299)\rResolving deltas:   3% (39/1299)\rResolving deltas:   4% (52/1299)\rResolving deltas:   5% (65/1299)\rResolving deltas:   6% (78/1299)\rResolving deltas:   7% (91/1299)\rResolving deltas:   8% (104/1299)\rResolving deltas:   9% (117/1299)\rResolving deltas:  10% (130/1299)\rResolving deltas:  11% (145/1299)\rResolving deltas:  12% (156/1299)\rResolving deltas:  13% (169/1299)\rResolving deltas:  14% (182/1299)\rResolving deltas:  15% (195/1299)\rResolving deltas:  16% (208/1299)\rResolving deltas:  17% (221/1299)\rResolving deltas:  18% (234/1299)\rResolving deltas:  19% (247/1299)\rResolving deltas:  20% (260/1299)\rResolving deltas:  21% (273/1299)\rResolving deltas:  22% (286/1299)\rResolving deltas:  23% (299/1299)\rResolving deltas:  24% (312/1299)\rResolving deltas:  25% (325/1299)\rResolving deltas:  26% (338/1299)\rResolving deltas:  27% (352/1299)\rResolving deltas:  28% (364/1299)\rResolving deltas:  29% (377/1299)\rResolving deltas:  30% (390/1299)\rResolving deltas:  31% (403/1299)\rResolving deltas:  32% (416/1299)\rResolving deltas:  33% (429/1299)\rResolving deltas:  34% (442/1299)\rResolving deltas:  35% (455/1299)\rResolving deltas:  36% (468/1299)\rResolving deltas:  37% (481/1299)\rResolving deltas:  38% (494/1299)\rResolving deltas:  39% (507/1299)\rResolving deltas:  40% (520/1299)\rResolving deltas:  41% (533/1299)\rResolving deltas:  42% (546/1299)\rResolving deltas:  43% (559/1299)\rResolving deltas:  44% (572/1299)\rResolving deltas:  45% (585/1299)\rResolving deltas:  46% (598/1299)\rResolving deltas:  47% (611/1299)\rResolving deltas:  48% (624/1299)\rResolving deltas:  49% (637/1299)\rResolving deltas:  50% (650/1299)\rResolving deltas:  51% (666/1299)\rResolving deltas:  52% (676/1299)\rResolving deltas:  53% (689/1299)\rResolving deltas:  54% (702/1299)\rResolving deltas:  55% (715/1299)\rResolving deltas:  56% (728/1299)\rResolving deltas:  57% (741/1299)\rResolving deltas:  58% (754/1299)\rResolving deltas:  59% (767/1299)\rResolving deltas:  60% (780/1299)\rResolving deltas:  61% (793/1299)\rResolving deltas:  62% (806/1299)\rResolving deltas:  63% (819/1299)\rResolving deltas:  64% (832/1299)\rResolving deltas:  65% (845/1299)\rResolving deltas:  66% (858/1299)\rResolving deltas:  67% (871/1299)\rResolving deltas:  68% (884/1299)\rResolving deltas:  69% (897/1299)\rResolving deltas:  70% (910/1299)\rResolving deltas:  71% (923/1299)\rResolving deltas:  72% (936/1299)\rResolving deltas:  73% (949/1299)\rResolving deltas:  74% (962/1299)\rResolving deltas:  75% (975/1299)\rResolving deltas:  76% (988/1299)\rResolving deltas:  77% (1001/1299)\rResolving deltas:  78% (1014/1299)\rResolving deltas:  79% (1027/1299)\rResolving deltas:  80% (1040/1299)\rResolving deltas:  81% (1053/1299)\rResolving deltas:  82% (1066/1299)\rResolving deltas:  83% (1079/1299)\rResolving deltas:  84% (1095/1299)\rResolving deltas:  85% (1105/1299)\rResolving deltas:  86% (1118/1299)\rResolving deltas:  87% (1131/1299)\rResolving deltas:  88% (1144/1299)\rResolving deltas:  89% (1157/1299)\rResolving deltas:  90% (1170/1299)\rResolving deltas:  91% (1183/1299)\rResolving deltas:  92% (1197/1299)\rResolving deltas:  93% (1209/1299)\rResolving deltas:  94% (1222/1299)\rResolving deltas:  95% (1235/1299)\rResolving deltas:  96% (1248/1299)\rResolving deltas:  97% (1262/1299)\rResolving deltas:  98% (1274/1299)\rResolving deltas:  99% (1287/1299)\rResolving deltas: 100% (1299/1299)\rResolving deltas: 100% (1299/1299), done.\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 3.1.4 in /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std from https://github.com/inmanta/std.\ninmanta.module           DEBUG   Parsing took 0.000075 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.9.1)\ninmanta.env              DEBUG   Collecting pydantic~=1.9\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/6eb/843dcc411b6a2/pydantic-1.10.2-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (13.2 MB)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.6.0)\ninmanta.env              DEBUG   Collecting colorlog~=6.0\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/0d3/3ca236784a1ba/colorlog-6.7.0-py2.py3-none-any.whl (11 kB)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.2)\ninmanta.env              DEBUG   Collecting arrow\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/5a4/9ab92e3b7b71d/arrow-1.2.3-py3-none-any.whl (66 kB)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15)\ninmanta.env              DEBUG   Collecting certifi>=2017.4.17\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/43d/adad18a7f1687/certifi-2022.6.15.1-py3-none-any.whl (160 kB)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.0)\ninmanta.env              DEBUG   Collecting charset-normalizer<3,>=2\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/83e/9a75d1911279a/charset_normalizer-2.1.1-py3-none-any.whl (39 kB)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.11)\ninmanta.env              DEBUG   Collecting urllib3<1.27,>=1.21.1\ninmanta.env              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b93/0dd878d5a8afb/urllib3-1.26.12-py2.py3-none-any.whl (140 kB)\ninmanta.env              DEBUG   Installing collected packages: urllib3, pydantic, colorlog, charset-normalizer, certifi, arrow\ninmanta.env              DEBUG   Attempting uninstall: urllib3\ninmanta.env              DEBUG   Found existing installation: urllib3 1.26.11\ninmanta.env              DEBUG   Not uninstalling urllib3 at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env\ninmanta.env              DEBUG   Can't uninstall 'urllib3'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: pydantic\ninmanta.env              DEBUG   Found existing installation: pydantic 1.9.1\ninmanta.env              DEBUG   Not uninstalling pydantic at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env\ninmanta.env              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: colorlog\ninmanta.env              DEBUG   Found existing installation: colorlog 6.6.0\ninmanta.env              DEBUG   Not uninstalling colorlog at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env\ninmanta.env              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: charset-normalizer\ninmanta.env              DEBUG   Found existing installation: charset-normalizer 2.1.0\ninmanta.env              DEBUG   Not uninstalling charset-normalizer at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env\ninmanta.env              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: certifi\ninmanta.env              DEBUG   Found existing installation: certifi 2022.6.15\ninmanta.env              DEBUG   Not uninstalling certifi at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env\ninmanta.env              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.env              DEBUG   Attempting uninstall: arrow\ninmanta.env              DEBUG   Found existing installation: arrow 1.2.2\ninmanta.env              DEBUG   Not uninstalling arrow at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env\ninmanta.env              DEBUG   Can't uninstall 'arrow'. No files were found to uninstall.\ninmanta.env              DEBUG   Successfully installed arrow-1.2.3 certifi-2022.6.15.1 charset-normalizer-2.1.1 colorlog-6.7.0 pydantic-1.10.2 urllib3-1.26.12\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000039 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\n	0	68c2d132-27a0-4843-ad95-10e04cf7e58b
ee3fa058-e3a6-42ce-852e-771e56214eba	2022-09-09 15:15:15.721714+02	2022-09-09 15:15:18.636828+02	/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env/bin/python -m inmanta.app -vvv export -X -e 0468b7d3-3847-40d8-887c-e458f9c8e58a --server_address localhost --server_port 48315 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpirn_eb7r	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003606 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000088 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001841)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001211)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000040)\ninmanta.execute.schedulerINFO    Total compilation time 0.003142\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48315/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48315/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48315/api/v1/file/63ae135b9a2eb874b3aa81fe5bd84283ef3617c9\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48315/api/v1/file/9d0d5cd7c8331a5e3a20ae9c68979cafde658d21\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48315/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48315/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48315/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48315/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	68c2d132-27a0-4843-ad95-10e04cf7e58b
692e6e4e-072a-4187-9ef7-70ed49e4bec4	2022-09-09 15:15:20.68257+02	2022-09-09 15:15:20.683525+02		Init		Using extra environment variables during compile \n	0	82a4e87f-1f29-4bef-884a-725e0f5e7a46
c07a9c1a-29db-4161-a201-bd86b8abb9da	2022-09-09 15:15:20.687174+02	2022-09-09 15:15:20.95092+02	/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 7.0.1.dev0\nNot uninstalling inmanta-core at /home/florent/.virtualenvs/core/lib/python3.9/site-packages, outside environment /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	82a4e87f-1f29-4bef-884a-725e0f5e7a46
3964ee29-95b4-42a7-9d0c-c2a168430bb6	2022-09-09 15:15:20.951957+02	2022-09-09 15:15:30.272948+02	/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Parsing took 0.000064 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.1)\ninmanta.module           INFO    verifying project\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000041 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.module           INFO    Checking out 3.1.4 on /tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/libs/std\ninmanta.env              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.env              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.env              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (3.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: pydantic~=1.9 in ./.env/lib/python3.9/site-packages (1.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: email_validator~=1.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (1.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: inmanta-core==7.0.1.dev0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (7.0.1.dev0)\ninmanta.env              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.11.0)\ninmanta.env              DEBUG   Requirement already satisfied: more-itertools~=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.14.0)\ninmanta.env              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: ply~=3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (3.11)\ninmanta.env              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.4)\ninmanta.env              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.6.4)\ninmanta.env              DEBUG   Requirement already satisfied: colorlog~=6.0 in ./.env/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.7.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.17.21)\ninmanta.env              DEBUG   Requirement already satisfied: docstring-parser<0.15,>=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.14.1)\ninmanta.env              DEBUG   Requirement already satisfied: build~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: crontab~=0.23 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.23.0)\ninmanta.env              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.26.0)\ninmanta.env              DEBUG   Requirement already satisfied: importlib-metadata~=4.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (4.12.0)\ninmanta.env              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (1.9.0)\ninmanta.env              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.8.2)\ninmanta.env              DEBUG   Requirement already satisfied: toml~=0.10 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.10.2)\ninmanta.env              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.2)\ninmanta.env              DEBUG   Requirement already satisfied: packaging~=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (21.3)\ninmanta.env              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (6.0)\ninmanta.env              DEBUG   Requirement already satisfied: pip>=21.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (22.2.2)\ninmanta.env              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (2.4.0)\ninmanta.env              DEBUG   Requirement already satisfied: typing-inspect~=0.7 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (0.8.0)\ninmanta.env              DEBUG   Requirement already satisfied: cryptography<38,>=36 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (37.0.4)\ninmanta.env              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from inmanta-core==7.0.1.dev0) (8.1.3)\ninmanta.env              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from Jinja2~=3.1) (2.1.1)\ninmanta.env              DEBUG   Requirement already satisfied: typing-extensions>=4.1.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pydantic~=1.9) (4.3.0)\ninmanta.env              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (2.2.1)\ninmanta.env              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from email_validator~=1.1) (3.3)\ninmanta.env              DEBUG   Requirement already satisfied: pep517>=0.9.1 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (0.13.0)\ninmanta.env              DEBUG   Requirement already satisfied: tomli>=1.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==7.0.1.dev0) (2.0.1)\ninmanta.env              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (6.1.2)\ninmanta.env              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.28.1)\ninmanta.env              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.4.4)\ninmanta.env              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (0.2.0)\ninmanta.env              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cryptography<38,>=36->inmanta-core==7.0.1.dev0) (1.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from importlib-metadata~=4.0->inmanta-core==7.0.1.dev0) (3.8.1)\ninmanta.env              DEBUG   Requirement already satisfied: pyparsing!=3.0.5,>=2.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from packaging~=21.3->inmanta-core==7.0.1.dev0) (3.0.9)\ninmanta.env              DEBUG   Requirement already satisfied: six in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==7.0.1.dev0) (1.16.0)\ninmanta.env              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==7.0.1.dev0) (0.2.6)\ninmanta.env              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from typing-inspect~=0.7->inmanta-core==7.0.1.dev0) (0.4.3)\ninmanta.env              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (5.0.0)\ninmanta.env              DEBUG   Requirement already satisfied: pycparser in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<38,>=36->inmanta-core==7.0.1.dev0) (2.21)\ninmanta.env              DEBUG   Requirement already satisfied: arrow in ./.env/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.2.3)\ninmanta.env              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/florent/.virtualenvs/core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.3)\ninmanta.env              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2022.6.15.1)\ninmanta.env              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (1.26.12)\ninmanta.env              DEBUG   Requirement already satisfied: charset-normalizer<3,>=2 in ./.env/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.1.dev0) (2.1.1)\ninmanta.module           INFO    verifying project\n	0	82a4e87f-1f29-4bef-884a-725e0f5e7a46
d234a7c6-ebac-4c9f-8f2a-14222d4fc0f5	2022-09-09 15:15:30.273909+02	2022-09-09 15:15:31.050579+02	/tmp/tmpfqyp2ghe/server/environments/0468b7d3-3847-40d8-887c-e458f9c8e58a/.env/bin/python -m inmanta.app -vvv export -X -e 0468b7d3-3847-40d8-887c-e458f9c8e58a --server_address localhost --server_port 48315 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmppdotdkk2	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.module           DEBUG   Parsing took 0.003513 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.module           DEBUG   Parsing took 0.000076 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 3.1.4\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.001792)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.001194)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 72, time: 0.000037)\ninmanta.execute.schedulerINFO    Total compilation time 0.003073\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48315/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48315/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48315/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:48315/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:48315/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	82a4e87f-1f29-4bef-884a-725e0f5e7a46
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
0468b7d3-3847-40d8-887c-e458f9c8e58a	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2022-09-09 15:15:19.602408+02	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
0468b7d3-3847-40d8-887c-e458f9c8e58a	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2022-09-09 15:15:20.624375+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
0468b7d3-3847-40d8-887c-e458f9c8e58a	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2022-09-09 15:15:31.548756+02	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File	/tmp/test	failed	\N
0468b7d3-3847-40d8-887c-e458f9c8e58a	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2022-09-09 15:15:30.966942+02	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	9050a27d4178ddd3ed1111d206e9d84e	deployed	{}	std::AgentConfig	localhost	deployed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
5d089563-bc2c-4252-812e-b30c1655b4a6	store	2022-09-09 15:15:16.418504+02	2022-09-09 15:15:17.494211+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2022-09-09T15:15:17.494231+02:00\\"}"}	\N	\N	\N	0468b7d3-3847-40d8-887c-e458f9c8e58a	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
e97f6d78-6276-4eca-adc3-f96287fc1b8a	pull	2022-09-09 15:15:18.501397+02	2022-09-09 15:15:19.033428+02	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2022-09-09T15:15:19.033444+02:00\\"}"}	\N	\N	\N	0468b7d3-3847-40d8-887c-e458f9c8e58a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
e2ca82bf-ff30-44d0-abe2-fb6b9ba320fd	deploy	2022-09-09 15:15:19.591604+02	2022-09-09 15:15:19.602408+02	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2022-09-09 15:15:18+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2022-09-09 15:15:18+0200\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"c72b3b51-e687-4e65-b695-ecce87c1fe96\\"}, \\"timestamp\\": \\"2022-09-09T15:15:19.589677+02:00\\"}","{\\"msg\\": \\"Start deploy c72b3b51-e687-4e65-b695-ecce87c1fe96 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"c72b3b51-e687-4e65-b695-ecce87c1fe96\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2022-09-09T15:15:19.593514+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-09T15:15:19.594301+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-09T15:15:19.596655+02:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy c72b3b51-e687-4e65-b695-ecce87c1fe96\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"c72b3b51-e687-4e65-b695-ecce87c1fe96\\"}, \\"timestamp\\": \\"2022-09-09T15:15:19.598772+02:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	0468b7d3-3847-40d8-887c-e458f9c8e58a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
4136b75a-65aa-423e-af7f-a020f7d2e693	pull	2022-09-09 15:15:20.611672+02	2022-09-09 15:15:20.612513+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-09T15:15:20.612520+02:00\\"}"}	\N	\N	\N	0468b7d3-3847-40d8-887c-e458f9c8e58a	1	{"std::File[localhost,path=/tmp/test],v=1"}
5a709d1c-8379-4466-bd39-f3979a52d0fb	deploy	2022-09-09 15:15:20.618935+02	2022-09-09 15:15:20.624375+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2022-09-09 15:15:20+0200\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2022-09-09 15:15:20+0200\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"c1355cb5-7201-4b4d-987a-395f7aec3640\\"}, \\"timestamp\\": \\"2022-09-09T15:15:20.617495+02:00\\"}","{\\"msg\\": \\"Start deploy c1355cb5-7201-4b4d-987a-395f7aec3640 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"c1355cb5-7201-4b4d-987a-395f7aec3640\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-09T15:15:20.619910+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-09T15:15:20.620516+02:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-09T15:15:20.620594+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 929, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpfqyp2ghe/0468b7d3-3847-40d8-887c-e458f9c8e58a/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-09T15:15:20.622417+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy c1355cb5-7201-4b4d-987a-395f7aec3640\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"c1355cb5-7201-4b4d-987a-395f7aec3640\\"}, \\"timestamp\\": \\"2022-09-09T15:15:20.622599+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	0468b7d3-3847-40d8-887c-e458f9c8e58a	1	{"std::File[localhost,path=/tmp/test],v=1"}
b26b7063-cd3d-41ce-9495-55d36061df66	store	2022-09-09 15:15:30.955095+02	2022-09-09 15:15:30.956451+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2022-09-09T15:15:30.956460+02:00\\"}"}	\N	\N	\N	0468b7d3-3847-40d8-887c-e458f9c8e58a	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
1bd62c46-3115-46dc-9256-01c43d355a17	pull	2022-09-09 15:15:30.965346+02	2022-09-09 15:15:30.966872+02	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2022-09-09T15:15:30.967715+02:00\\"}"}	\N	\N	\N	0468b7d3-3847-40d8-887c-e458f9c8e58a	2	{"std::File[localhost,path=/tmp/test],v=2"}
4382ef91-b71a-4ccb-bffc-836805f37ffc	deploy	2022-09-09 15:15:31.543562+02	2022-09-09 15:15:31.548756+02	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"aac25b8d-6b4d-41eb-a2a4-9ff77a16f162\\"}, \\"timestamp\\": \\"2022-09-09T15:15:31.541636+02:00\\"}","{\\"msg\\": \\"Start deploy aac25b8d-6b4d-41eb-a2a4-9ff77a16f162 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"aac25b8d-6b4d-41eb-a2a4-9ff77a16f162\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-09T15:15:31.544920+02:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2022-09-09T15:15:31.545186+02:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"florent\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2022-09-09T15:15:31.546418+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpfqyp2ghe/0468b7d3-3847-40d8-887c-e458f9c8e58a/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/florent/Desktop/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2022-09-09T15:15:31.546568+02:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy aac25b8d-6b4d-41eb-a2a4-9ff77a16f162\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"aac25b8d-6b4d-41eb-a2a4-9ff77a16f162\\"}, \\"timestamp\\": \\"2022-09-09T15:15:31.546720+02:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	0468b7d3-3847-40d8-887c-e458f9c8e58a	2	{"std::File[localhost,path=/tmp/test],v=2"}
d055b827-737b-4da0-99b7-2694f9b2c498	deploy	2022-09-09 15:15:30.966942+02	2022-09-09 15:15:30.966942+02	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2022-09-09T13:15:30.966942+00:00\\"}"}	deployed	\N	nochange	0468b7d3-3847-40d8-887c-e458f9c8e58a	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
0468b7d3-3847-40d8-887c-e458f9c8e58a	5d089563-bc2c-4252-812e-b30c1655b4a6	std::File[localhost,path=/tmp/test]	1
0468b7d3-3847-40d8-887c-e458f9c8e58a	5d089563-bc2c-4252-812e-b30c1655b4a6	std::AgentConfig[internal,agentname=localhost]	1
0468b7d3-3847-40d8-887c-e458f9c8e58a	e97f6d78-6276-4eca-adc3-f96287fc1b8a	std::AgentConfig[internal,agentname=localhost]	1
0468b7d3-3847-40d8-887c-e458f9c8e58a	e2ca82bf-ff30-44d0-abe2-fb6b9ba320fd	std::AgentConfig[internal,agentname=localhost]	1
0468b7d3-3847-40d8-887c-e458f9c8e58a	4136b75a-65aa-423e-af7f-a020f7d2e693	std::File[localhost,path=/tmp/test]	1
0468b7d3-3847-40d8-887c-e458f9c8e58a	5a709d1c-8379-4466-bd39-f3979a52d0fb	std::File[localhost,path=/tmp/test]	1
0468b7d3-3847-40d8-887c-e458f9c8e58a	b26b7063-cd3d-41ce-9495-55d36061df66	std::File[localhost,path=/tmp/test]	2
0468b7d3-3847-40d8-887c-e458f9c8e58a	b26b7063-cd3d-41ce-9495-55d36061df66	std::AgentConfig[internal,agentname=localhost]	2
0468b7d3-3847-40d8-887c-e458f9c8e58a	1bd62c46-3115-46dc-9256-01c43d355a17	std::File[localhost,path=/tmp/test]	2
0468b7d3-3847-40d8-887c-e458f9c8e58a	4382ef91-b71a-4ccb-bffc-836805f37ffc	std::File[localhost,path=/tmp/test]	2
0468b7d3-3847-40d8-887c-e458f9c8e58a	d055b827-737b-4da0-99b7-2694f9b2c498	std::AgentConfig[internal,agentname=localhost]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190}
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

