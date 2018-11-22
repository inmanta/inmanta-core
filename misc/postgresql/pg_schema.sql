CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS public.project CASCADE;
DROP TABLE IF EXISTS public.environment CASCADE;
DROP TABLE IF EXISTS public.configurationmodel;
DROP TABLE IF EXISTS public.resource;
DROP TABLE IF EXISTS public.resourceaction;
DROP TABLE IF EXISTS public.code;
DROP TABLE IF EXISTS public.unknownparameter;
DROP TABLE IF EXISTS public.agentprocess CASCADE;
DROP TABLE IF EXISTS public.agentinstance CASCADE;
DROP TABLE IF EXISTS public.agent;
DROP TYPE IF EXISTS versionstate;
DROP TYPE IF EXISTS resourcestate;
DROP TYPE IF EXISTS resourceaction_type;
DROP TYPE IF EXISTS change;

CREATE TYPE versionstate AS ENUM('success', 'failed', 'deploying', 'pending');
CREATE TYPE resourcestate AS ENUM('unavailable', 'skipped', 'dry', 'deployed', 'failed', 'queued', 'available',
                                  'cancelled', 'undefined', 'skipped_for_undefined');
CREATE TYPE resourceaction_type AS ENUM('store', 'push', 'pull', 'deploy', 'dryrun', 'snapshot', 'restore', 'other');
CREATE type change AS ENUM('nochange', 'created', 'purged', 'updated');


-- Table: public.projects
CREATE TABLE IF NOT EXISTS public.project (
    id uuid PRIMARY KEY,
    name varchar NOT NULL UNIQUE
);

-- Table: public.environments
CREATE TABLE IF NOT EXISTS public.environment (
    id uuid PRIMARY KEY,
    name varchar NOT NULL,
    project uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    repo_url varchar DEFAULT '',
    repo_branch varchar DEFAULT '',
    settings JSONB DEFAULT '{}'
);

CREATE UNIQUE INDEX environment_name_project_index ON environment (name, project);

-- Table: public.configurationmodels
CREATE TABLE IF NOT EXISTS public.configurationmodel (
    id uuid PRIMARY KEY,
    version integer NOT NULL,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    date timestamp,
    released boolean DEFAULT false,
    deployed boolean DEFAULT false,
    result versionstate DEFAULT 'pending',
    status JSONB DEFAULT '{}',
    version_info JSONB,
    total integer DEFAULT 0,
    undeployable varchar[],
    skipped_for_undeployable varchar[]
);

CREATE UNIQUE INDEX configurationmodel_env_version_index ON configurationmodel (environment, version);

-- Table: public.resources
CREATE TABLE IF NOT EXISTS public.resource (
    id uuid PRIMARY KEY,
    environment uuid NOT NULL,
    model integer NOT NULL,
    resource_id varchar NOT NULL,
    resource_version_id varchar NOT NULL,
    resource_type varchar NOT NULL,
    agent varchar NOT NULL,
    id_attribute_name varchar NOT NULL,
    id_attribute_value varchar NOT NULL,
    last_deploy timestamp,
    attributes JSONB,
    status resourcestate DEFAULT 'available',
    provides varchar[] DEFAULT array[]::varchar[],
    FOREIGN KEY (environment, model) REFERENCES configurationmodel (environment, version) ON DELETE CASCADE
);

CREATE INDEX resource_env_model_agent_index ON resource (environment, model, agent);
CREATE INDEX resource_env_resourceid_index ON resource (environment, resource_id);
CREATE UNIQUE INDEX resource_env_resourceversionid_index ON resource (environment, resource_version_id);

-- Table: public.resourceaction
CREATE TABLE IF NOT EXISTS public.resourceaction (
    id uuid PRIMARY KEY,
    resource_version_ids varchar[] NOT NULL,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    action_id uuid NOT NULL,
    action resourceaction_type NOT NULL,
    started timestamp NOT NULL,
    finished timestamp,
    messages JSONB[],
    status resourcestate,
    changes JSONB DEFAULT '{}'::jsonb,
    change change,
    send_event boolean
);

CREATE UNIQUE INDEX resourceaction_env_resourceversionid_index ON resourceaction (environment, action_id);
CREATE INDEX resourceaction_env_resourceversionid__started_index ON resourceaction (environment, resource_version_ids, started DESC);

-- Table: public.code
CREATE TABLE IF NOT EXISTS public.code (
    id uuid PRIMARY KEY,
    environment uuid NOT NULL,
    resource varchar NOT NULL,
    version integer NOT NULL,
    sources JSONB,
    source_refs JSONB,
    FOREIGN KEY (environment, version) REFERENCES configurationmodel (environment, version) ON DELETE CASCADE
);

CREATE INDEX code_env_version_resource_index ON code (environment, version, resource);

-- Table: public.unknownparameter
CREATE TABLE IF NOT EXISTS public.unknownparameter (
    id uuid PRIMARY KEY,
    name varchar NOT NULL,
    environment uuid NOT NULL,
    source varchar NOT NULL,
    resource_id varchar DEFAULT '',
    version integer NOT NULL,
    metadata JSONB,
    resolved boolean DEFAULT false,
    FOREIGN KEY (environment, version) REFERENCES configurationmodel (environment, version) ON DELETE CASCADE
);

CREATE INDEX unknownparameter_env_version_index ON code (environment, version);

-- Table: public.agentprocess
CREATE TABLE IF NOT EXISTS public.agentprocess (
    id uuid PRIMARY KEY,
    hostname varchar NOT NULL,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    first_seen timestamp,
    last_seen timestamp,
    expired timestamp,
    sid uuid NOT NULL
);


-- Table: public.agentinstance
CREATE TABLE IF NOT EXISTS public.agentinstance (
    id uuid PRIMARY KEY,
    process uuid NOT NULL REFERENCES agentprocess (id) ON DELETE CASCADE,
    name varchar NOT NULL,
    expired timestamp,
    tid uuid NOT NULL
);

-- Table: public.agent
CREATE TABLE IF NOT EXISTS public.agent (
    id uuid PRIMARY KEY,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    name varchar NOT NULL,
    last_failover timestamp,
    paused boolean DEFAULT false,
-- primary is a reserved keyword in postgresql ==> hange to id_primary
    id_primary uuid REFERENCES agentinstance(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX agent_env_name_index ON agent (environment, name);
