CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE versionstate AS ENUM('success', 'failed', 'deploying', 'pending');
CREATE TYPE resourcestate AS ENUM('unavailable', 'skipped', 'dry', 'deployed', 'failed', 'queued', 'available',
                                  'cancelled', 'undefined', 'skipped_for_undefined');
CREATE TYPE resourceaction_type AS ENUM('store', 'push', 'pull', 'deploy', 'dryrun', 'snapshot', 'restore', 'other');
CREATE type change AS ENUM('nochange', 'created', 'purged', 'updated');


-- Table: public.projects
CREATE TABLE public.project (
    _id uuid PRIMARY KEY,
    name varchar NOT NULL UNIQUE
);

-- Table: public.environments
CREATE TABLE public.environment (
    _id uuid PRIMARY KEY,
    name varchar NOT NULL,
    project uuid NOT NULL REFERENCES project(_id) ON DELETE RESTRICT,
    repo_url varchar DEFAULT '',
    repo_branch varchar DEFAULT '',
    settings JSONB DEFAULT '{}'
);

CREATE UNIQUE INDEX environment_name_project_index ON environment (name, project);

-- Table: public.configurationmodels
CREATE TABLE public.configurationmodel (
    _id uuid PRIMARY KEY,
    version integer NOT NULL,
    environment uuid NOT NULL REFERENCES environment(_id) ON DELETE RESTRICT,
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
CREATE TABLE public.resource (
    _id uuid PRIMARY KEY,
    environment uuid NOT NULL REFERENCES environment(_id) ON DELETE RESTRICT,
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
    provides varchar[] DEFAULT array[]::varchar[]
);

CREATE INDEX resource_env_model_agent_index ON resource (environment, model, agent);
CREATE INDEX resource_env_resourceid_index ON resource (environment, resource_id);
CREATE UNIQUE INDEX resource_env_resourceversionid_index ON resource (environment, resource_version_id);

-- Table: public.resourceaction
CREATE TABLE public.resourceaction (
    _id uuid PRIMARY KEY,
    resource_version_ids varchar[] NOT NULL,
    environment uuid NOT NULL REFERENCES environment(_id) ON DELETE RESTRICT,
    action_id uuid NOT NULL REFERENCES resource(_id) ON DELETE CASCADE,
    action resourceaction_type NOT NULL,
    started timestamp NOT NULL,
    finished timestamp,
    messages JSONB[],
    status resourcestate,
    changes JSONB[],
    change change,
    send_event boolean
);

CREATE UNIQUE INDEX resourceaction_env_resourceversionid_index ON resourceaction (environment, action_id);
CREATE INDEX resourceaction_env_resourceversionid__started_index ON resourceaction (environment, resource_version_ids, started DESC);

-- Table: public.code
CREATE TABLE public.code (
    _id uuid PRIMARY KEY,
    environment uuid NOT NULL REFERENCES environment(_id) ON DELETE RESTRICT,
    resource varchar NOT NULL,
    version integer NOT NULL,
    sources JSONB,
    source_refs JSONB
);

CREATE INDEX code_env_version_resource_index ON code (environment, version, resource);

-- Table: public.unknownparameter
CREATE TABLE public.unknownparameter (
    _id uuid PRIMARY KEY,
    name varchar NOT NULL,
    environment uuid NOT NULL REFERENCES environment(_id) ON DELETE RESTRICT,
    source varchar NOT NULL,
    resource_id varchar DEFAULT '',
    version integer NOT NULL,
    metadata JSONB,
    resolved boolean DEFAULT false
);

CREATE INDEX unknownparameter_env_version_index ON code (environment, version);

-- Table: public.agentinstance
CREATE TABLE public.agentinstance (
    _id uuid PRIMARY KEY,
    process uuid NOT NULL,
    name varchar NOT NULL,
    expired timestamp,
    tid uuid NOT NULL
);

-- Table: public.agent
CREATE TABLE public.agent (
    _id uuid PRIMARY KEY,
    environment uuid NOT NULL REFERENCES environment(_id) ON DELETE RESTRICT,
    name varchar NOT NULL,
    last_failover timestamp,
    paused boolean DEFAULT false,
-- primary is a reserved keyword in postgresql ==> hange to id_primary
    id_primary uuid REFERENCES agentinstance(_id)
);

CREATE UNIQUE INDEX agent_env_name_index ON agent (environment, name);

-- Table: public.agentprocess
CREATE TABLE public.agentprocess (
    _id uuid PRIMARY KEY,
    hostname varchar NOT NULL,
    environment uuid NOT NULL REFERENCES environment(_id) ON DELETE RESTRICT,
    first_seen timestamp,
    last_seen timestamp,
    expired timestamp,
    sid uuid NOT NULL
);
