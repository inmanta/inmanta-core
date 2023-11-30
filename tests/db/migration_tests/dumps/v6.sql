--
-- PostgreSQL database dump
--

-- Dumped from database version 10.14
-- Dumped by pg_dump version 10.14

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
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


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

SET default_with_oids = false;

--
-- Name: agent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent (
    environment uuid NOT NULL,
    name character varying NOT NULL,
    last_failover timestamp without time zone,
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
    expired timestamp without time zone,
    tid uuid NOT NULL
);


--
-- Name: agentprocess; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agentprocess (
    hostname character varying NOT NULL,
    environment uuid NOT NULL,
    first_seen timestamp without time zone,
    last_seen timestamp without time zone,
    expired timestamp without time zone,
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
    started timestamp without time zone,
    completed timestamp without time zone,
    requested timestamp without time zone,
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
    date timestamp without time zone,
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
    date timestamp without time zone,
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
    halted boolean DEFAULT false NOT NULL
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
    updated timestamp without time zone,
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
    started timestamp without time zone NOT NULL,
    completed timestamp without time zone,
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
    last_deploy timestamp without time zone,
    attributes jsonb,
    attribute_hash character varying,
    status public.resourcestate DEFAULT 'available'::public.resourcestate,
    provides character varying[] DEFAULT ARRAY[]::character varying[],
    resource_type character varying NOT NULL
);


--
-- Name: resourceaction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resourceaction (
    action_id uuid NOT NULL,
    action public.resourceaction_type NOT NULL,
    started timestamp without time zone NOT NULL,
    finished timestamp without time zone,
    messages jsonb[],
    status public.resourcestate,
    changes jsonb DEFAULT '{}'::jsonb,
    change public.change,
    send_event boolean,
    environment uuid NOT NULL,
    version integer NOT NULL,
    resource_version_ids character varying[] NOT NULL
);


--
-- Name: schemamanager; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schemamanager (
    name character varying NOT NULL,
    current_version integer NOT NULL
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
be485486-4917-4935-ac11-ecdd4a5b9f25	internal	2020-09-15 15:20:22.78929	f	45292a97-75b0-4498-9075-e0e8891b2929	\N
be485486-4917-4935-ac11-ecdd4a5b9f25	localhost	2020-09-15 15:20:25.813049	f	06e6ebbf-4694-45fc-9be7-e3bd58822326	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
45292a97-75b0-4498-9075-e0e8891b2929	34c974b2-f756-11ea-827d-106530e9353d	internal	\N	be485486-4917-4935-ac11-ecdd4a5b9f25
06e6ebbf-4694-45fc-9be7-e3bd58822326	34c974b2-f756-11ea-827d-106530e9353d	localhost	\N	be485486-4917-4935-ac11-ecdd4a5b9f25
c7c42e39-d41f-416b-b3f8-79e3bde8fef8	34c974b2-f756-11ea-827d-106530e9353d	agent_instance_1	\N	be485486-4917-4935-ac11-ecdd4a5b9f25
987b0312-21a9-4311-9c8f-9eb7bf69fbb4	34c974b2-f756-11ea-827d-106530e9353d	agent_instance_2	2020-10-21 13:36:36.828691	be485486-4917-4935-ac11-ecdd4a5b9f25
1e273c86-a013-46d6-859a-4e448927aabd	34c974b2-f756-11ea-827d-106530e9353d	agent_instance_2	\N	be485486-4917-4935-ac11-ecdd4a5b9f25
32a6ce2d-49fa-4e74-b462-44640526bf81	34c974b2-f756-11ea-827d-106530e9353d	agent_instance_3	2020-10-21 13:36:36.831779	be485486-4917-4935-ac11-ecdd4a5b9f25
58c38394-028b-4065-8ab4-ac9068244e69	34c974b2-f756-11ea-827d-106530e9353d	agent_instance_3	2020-10-21 13:36:36.833183	be485486-4917-4935-ac11-ecdd4a5b9f25
d9b3fabc-7b54-4ef8-88b5-92145c1604ee	34c974b2-f756-11ea-827d-106530e9353d	agent_instance_3	\N	be485486-4917-4935-ac11-ecdd4a5b9f25
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-laptop	be485486-4917-4935-ac11-ecdd4a5b9f25	2020-09-15 15:20:22.78929	2020-09-15 15:20:27.007936	\N	34c974b2-f756-11ea-827d-106530e9353d
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
be485486-4917-4935-ac11-ecdd4a5b9f25	std::Service	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::File	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::Directory	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::Package	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::Symlink	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::AgentConfig	1	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::Service	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::File	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::Directory	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::Package	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::Symlink	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
be485486-4917-4935-ac11-ecdd4a5b9f25	std::AgentConfig	2	{"82ed41381f2512462ae3bb9e514f84d8cd2d0772": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]], "967cda255497c4742364e7a35dc381dd70d6fa13": ["/tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=2.11", "email_validator~=1.1", "pydantic~=1.6", "dataclasses~=0.7;python_version<'3.7'", "dnspython~=2.0", "idna~=2.10", "MarkupSafe~=1.1"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data) FROM stdin;
03ce6b65-3101-4fc2-8c97-47dc383bb712	be485486-4917-4935-ac11-ecdd4a5b9f25	2020-09-15 15:20:16.588305	2020-09-15 15:20:22.966172	2020-09-15 15:20:16.577839	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	a3eff5fc-e6a2-444a-a95b-b692c83ce306	t	\N	{"errors": []}
25890b2a-238d-4caf-b964-077e5b6b8d40	be485486-4917-4935-ac11-ecdd4a5b9f25	2020-09-15 15:20:25.986888	2020-09-15 15:20:26.810324	2020-09-15 15:20:25.972017	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	51a7308d-fc65-44c9-b68f-918b08c0b933	t	\N	{"errors": []}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable) FROM stdin;
1	be485486-4917-4935-ac11-ecdd4a5b9f25	2020-09-15 15:20:20.639712	t	t	failed	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
2	be485486-4917-4935-ac11-ecdd4a5b9f25	2020-09-15 15:20:26.731691	t	t	deploying	{"model": null, "export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-laptop", "inmanta:compile:state": "success"}}	2	{}	{}
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted) FROM stdin;
e7f03e84-ba88-4d44-8389-e9e4af044622	dev-2	ff546078-c700-413d-bf1e-c581166304e3			{}	0	f
be485486-4917-4935-ac11-ecdd4a5b9f25	dev-1	ff546078-c700-413d-bf1e-c581166304e3			{"auto_deploy": true, "server_compile": true, "purge_on_delete": true, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f
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
ff546078-c700-413d-bf1e-c581166304e3	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
9503c5cd-ce80-45d1-a26f-0f7e74dfe7dc	2020-09-15 15:20:16.589077	2020-09-15 15:20:16.592452		Init		Using extra environment variables during compile \n	0	03ce6b65-3101-4fc2-8c97-47dc383bb712
643f6e9f-1fcf-4860-84e2-1a95cba1b621	2020-09-15 15:20:16.593594	2020-09-15 15:20:22.96477	/home/arnaud/.virtualenvs/inmanta/bin/python -m inmanta.app -vvv export -X -e be485486-4917-4935-ac11-ecdd4a5b9f25 --server_address localhost --server_port 59961 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpy1gx5ff_	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    Checking out 2.0.6 on /tmp/tmpgpmcbn4s/server/environments/be485486-4917-4935-ac11-ecdd4a5b9f25/libs/std\ninmanta.env              DEBUG   Created a new virtualenv at ./.env\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003548)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002001)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000066)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:59961/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:59961/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:59961/api/v1/file/967cda255497c4742364e7a35dc381dd70d6fa13\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:59961/api/v1/file/82ed41381f2512462ae3bb9e514f84d8cd2d0772\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:59961/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:59961/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:59961/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:59961/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	03ce6b65-3101-4fc2-8c97-47dc383bb712
80bea0d9-141e-4de9-8c58-a3f6f0e36363	2020-09-15 15:20:25.988232	2020-09-15 15:20:25.992229		Init		Using extra environment variables during compile \n	0	25890b2a-238d-4caf-b964-077e5b6b8d40
2ab71b9e-67a5-4bb0-b26f-54e4cdb9ef11	2020-09-15 15:20:25.993972	2020-09-15 15:20:26.809376	/home/arnaud/.virtualenvs/inmanta/bin/python -m inmanta.app -vvv export -X -e be485486-4917-4935-ac11-ecdd4a5b9f25 --server_address localhost --server_port 59961 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpo_wdjb2c	Recompiling configuration model		inmanta.env              INFO    Creating new virtual environment in ./.env\ninmanta.compiler         DEBUG   Starting compile\ninmanta.module           INFO    verifying project\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std.resources\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.003199)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 71, time: 0.002250)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerINFO    Iteration 2 (e: 0, w: 0, p: 0, done: 73, time: 0.000065)\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:59961/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:59961/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:59961/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:59961/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:59961/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	25890b2a-238d-4caf-b964-077e5b6b8d40
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, resource_version_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type) FROM stdin;
be485486-4917-4935-ac11-ecdd4a5b9f25	1	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=1	internal	2020-09-15 15:20:24.842472	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
be485486-4917-4935-ac11-ecdd4a5b9f25	1	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=1	localhost	2020-09-15 15:20:25.871084	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
be485486-4917-4935-ac11-ecdd4a5b9f25	2	std::AgentConfig[internal,agentname=localhost]	std::AgentConfig[internal,agentname=localhost],v=2	internal	2020-09-15 15:20:26.756144	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": true}	98f966a450a4745167a44a7e39d0dc61	deployed	{}	std::AgentConfig
be485486-4917-4935-ac11-ecdd4a5b9f25	2	std::File[localhost,path=/tmp/test]	std::File[localhost,path=/tmp/test],v=2	localhost	2020-09-15 15:20:26.785661	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": [], "send_event": false, "permissions": 644, "purge_on_delete": false}	43bc32acc108f82c584f651da52e51a3	failed	{}	std::File
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, send_event, environment, version, resource_version_ids) FROM stdin;
6bb27535-0395-4c17-ad80-7a9efd8395bd	store	2020-09-15 15:20:20.636953	2020-09-15 15:20:20.654863	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2020-09-15T15:20:20.654871\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
1f999175-985f-4be1-a91e-9d5403429d5d	pull	2020-09-15 15:20:22.801291	2020-09-15 15:20:22.80842	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-09-15T15:20:22.808425\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
647a4379-c532-4264-9fb6-eb9e643b4eb1	pull	2020-09-15 15:20:24.755063	2020-09-15 15:20:24.756666	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-09-15T15:20:24.756671\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
9320c113-5069-4360-9995-66b944891cf0	deploy	2020-09-15 15:20:24.750819	2020-09-15 15:20:24.781449	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2020-09-15 15:20:22\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2020-09-15 15:20:22\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"37bad087-72e8-49bc-8f04-327f93851772\\"}, \\"timestamp\\": \\"2020-09-15T15:20:24.750880\\"}","{\\"msg\\": \\"Start deploy 37bad087-72e8-49bc-8f04-327f93851772 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"37bad087-72e8-49bc-8f04-327f93851772\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-09-15T15:20:24.750931\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-15T15:20:24.771288\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-15T15:20:24.776913\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 37bad087-72e8-49bc-8f04-327f93851772\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"37bad087-72e8-49bc-8f04-327f93851772\\"}, \\"timestamp\\": \\"2020-09-15T15:20:24.781404\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
00c3acd3-bbbc-4652-a8c1-96da71196209	deploy	2020-09-15 15:20:24.798933	2020-09-15 15:20:24.809096	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"bd28da53-8a4e-4c89-b17b-2c867eb63095\\"}, \\"timestamp\\": \\"2020-09-15T15:20:24.798969\\"}","{\\"msg\\": \\"Start deploy bd28da53-8a4e-4c89-b17b-2c867eb63095 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"bd28da53-8a4e-4c89-b17b-2c867eb63095\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-09-15T15:20:24.799028\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-15T15:20:24.804818\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy bd28da53-8a4e-4c89-b17b-2c867eb63095\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"bd28da53-8a4e-4c89-b17b-2c867eb63095\\"}, \\"timestamp\\": \\"2020-09-15T15:20:24.809045\\"}"}	deployed	\N	nochange	f	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
22fcb908-63f2-4502-b143-edf5ff0b083c	pull	2020-09-15 15:20:24.818172	2020-09-15 15:20:24.819588	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-09-15T15:20:24.819592\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
6c8df61b-3a53-4733-9250-60f860396a11	deploy	2020-09-15 15:20:24.832703	2020-09-15 15:20:24.842472	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Restarting run 'Repair run started at 2020-09-15 15:20:22', interrupted for 'call to trigger_update'\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Restarting run 'Repair run started at 2020-09-15 15:20:22', interrupted for 'call to trigger_update'\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"6a49c527-f646-445f-965d-92f960c215cc\\"}, \\"timestamp\\": \\"2020-09-15T15:20:24.832727\\"}","{\\"msg\\": \\"Start deploy 6a49c527-f646-445f-965d-92f960c215cc of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"6a49c527-f646-445f-965d-92f960c215cc\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2020-09-15T15:20:24.832762\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-15T15:20:24.838563\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy 6a49c527-f646-445f-965d-92f960c215cc\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"6a49c527-f646-445f-965d-92f960c215cc\\"}, \\"timestamp\\": \\"2020-09-15T15:20:24.842431\\"}"}	deployed	\N	nochange	f	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
81dd4b90-9f80-460e-91e3-7bea44e7fb0d	pull	2020-09-15 15:20:25.837215	2020-09-15 15:20:25.840951	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-09-15T15:20:25.840957\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::File[localhost,path=/tmp/test],v=1"}
1fcd5cf5-16c5-4465-b6fb-e5dc5d1a6c8f	deploy	2020-09-15 15:20:25.858776	2020-09-15 15:20:25.871084	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2020-09-15 15:20:25\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2020-09-15 15:20:25\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"3b40b94b-498d-42c3-91c0-2fbe4914ee05\\"}, \\"timestamp\\": \\"2020-09-15T15:20:25.858806\\"}","{\\"msg\\": \\"Start deploy 3b40b94b-498d-42c3-91c0-2fbe4914ee05 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"3b40b94b-498d-42c3-91c0-2fbe4914ee05\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-09-15T15:20:25.858848\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-15T15:20:25.866797\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-15T15:20:25.866968\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 881, in execute\\\\n    self.create_resource(ctx, desired)\\\\n  File \\\\\\"/tmp/tmpgpmcbn4s/be485486-4917-4935-ac11-ecdd4a5b9f25/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 193, in create_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 594, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-09-15T15:20:25.870732\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 3b40b94b-498d-42c3-91c0-2fbe4914ee05\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"3b40b94b-498d-42c3-91c0-2fbe4914ee05\\"}, \\"timestamp\\": \\"2020-09-15T15:20:25.871040\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"purged": {"current": true, "desired": false}}}	nochange	f	be485486-4917-4935-ac11-ecdd4a5b9f25	1	{"std::File[localhost,path=/tmp/test],v=1"}
efc68f5b-fe50-4875-86f4-83d91fde1c54	store	2020-09-15 15:20:26.730063	2020-09-15 15:20:26.734769	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2020-09-15T15:20:26.734775\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
9ece2aec-023c-491c-b71a-1c19428f1cfa	pull	2020-09-15 15:20:26.752272	2020-09-15 15:20:26.756004	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-09-15T15:20:26.757519\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	2	{"std::File[localhost,path=/tmp/test],v=2"}
b6412506-2045-4342-b393-ecd7a889faac	deploy	2020-09-15 15:20:26.756144	2020-09-15 15:20:26.756144	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2020-09-15T15:20:26.756144\\"}"}	deployed	\N	nochange	f	be485486-4917-4935-ac11-ecdd4a5b9f25	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
1d918f84-17c0-45a5-9a02-04188546f2c2	deploy	2020-09-15 15:20:26.775125	2020-09-15 15:20:26.785661	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"02a7566e-ff69-4a46-a301-7c1638075467\\"}, \\"timestamp\\": \\"2020-09-15T15:20:26.775158\\"}","{\\"msg\\": \\"Start deploy 02a7566e-ff69-4a46-a301-7c1638075467 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"02a7566e-ff69-4a46-a301-7c1638075467\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-09-15T15:20:26.775242\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2020-09-15T15:20:26.781825\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2020-09-15T15:20:26.785057\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError(1, 'Operation not permitted'))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError(1, 'Operation not permitted')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/handler.py\\\\\\", line 888, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmpgpmcbn4s/be485486-4917-4935-ac11-ecdd4a5b9f25/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta/src/inmanta/agent/io/local.py\\\\\\", line 594, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2020-09-15T15:20:26.785358\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 02a7566e-ff69-4a46-a301-7c1638075467\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"02a7566e-ff69-4a46-a301-7c1638075467\\"}, \\"timestamp\\": \\"2020-09-15T15:20:26.785624\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"group": {"current": "arnaud", "desired": "root"}, "owner": {"current": "arnaud", "desired": "root"}}}	nochange	f	be485486-4917-4935-ac11-ecdd4a5b9f25	2	{"std::File[localhost,path=/tmp/test],v=2"}
d8290aad-46f7-4125-8457-9ad64e731fb0	pull	2020-09-15 15:20:27.008479	2020-09-15 15:20:27.011087	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2020-09-15T15:20:27.011090\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	2	{"std::File[localhost,path=/tmp/test],v=2"}
62e51973-64e3-4ace-b6b7-c81243bae0e1	pull	2020-09-15 15:20:27.008347	2020-09-15 15:20:27.010564	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2020-09-15T15:20:27.010568\\"}"}	\N	\N	\N	\N	be485486-4917-4935-ac11-ecdd4a5b9f25	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, current_version) FROM stdin;
core	6
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
-- Name: resource_environment_resource_type_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_type_index ON public.resource USING btree (environment, resource_type);


--
-- Name: resourceaction_environment_action_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_environment_action_started_index ON public.resourceaction USING btree (environment, action, started DESC);


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
    ADD CONSTRAINT agent_id_primary_fkey FOREIGN KEY (id_primary) REFERENCES public.agentinstance(id) ON DELETE CASCADE;


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
-- Name: dryrun dryrun_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun
    ADD CONSTRAINT dryrun_environment_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: environment environment_project_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment
    ADD CONSTRAINT environment_project_fkey FOREIGN KEY (project) REFERENCES public.project(id) ON DELETE CASCADE;


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
-- Name: resource resource_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_environment_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: resourceaction resourceaction_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction
    ADD CONSTRAINT resourceaction_environment_fkey FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_fkey1 FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

