CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE versionstate AS ENUM('success', 'failed', 'deploying', 'pending');
CREATE TYPE resourcestate AS ENUM('unavailable', 'skipped', 'dry', 'deployed', 'failed', 'queued', 'available',
                                  'cancelled', 'undefined', 'skipped_for_undefined');
CREATE TYPE resourceaction_type AS ENUM('store', 'push', 'pull', 'deploy', 'dryrun', 'snapshot', 'restore', 'other');
CREATE type change AS ENUM('nochange', 'created', 'purged', 'updated');


-- Table: public.projects
CREATE TABLE public.project (
    name varchar PRIMARY KEY
);

-- Table: public.environments
CREATE TABLE public.environment (
    name varchar,
    project varchar NOT NULL,
    repo_url varchar DEFAULT '',
    repo_branch varchar DEFAULT '',
    settings JSONB DEFAULT '{}',
    PRIMARY KEY (name, project),
    FOREIGN KEY (project) REFERENCES project (name) ON DELETE CASCADE
);

-- Table: public.configurationmodels
CREATE TABLE public.configurationmodel (
    version integer,
    environment varchar NOT NULL,
    project varchar NOT NULL,
    date timestamp,
    released boolean DEFAULT false,
    deployed boolean DEFAULT false,
    result versionstate DEFAULT 'pending',
    status JSONB DEFAULT '{}',
    version_info JSONB,
    total integer DEFAULT 0,
    undeployable varchar[],
    skipped_for_undeployable varchar[],
    PRIMARY KEY (environment, version),
    FOREIGN KEY (environment, project) REFERENCES environment (name, project) ON DELETE CASCADE
);

-- Table: public.resources
CREATE TABLE public.resource (
    environment varchar NOT NULL,
    project varchar NOT NULL,
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
    PRIMARY KEY (environment, resource_version_id),
    FOREIGN KEY (environment, project) REFERENCES environment (name, project) ON DELETE CASCADE
);

CREATE INDEX resource_env_model_agent_index ON resource (environment, model, agent);
CREATE INDEX resource_env_resourceid_index ON resource (environment, resource_id);

-- Table: public.resourceaction
CREATE TABLE public.resourceaction (
    resource_version_ids varchar[] NOT NULL,
    environment varchar NOT NULL,
    project varchar NOT NULL,
    action_id uuid NOT NULL,
    action resourceaction_type NOT NULL,
    started timestamp NOT NULL,
    finished timestamp,
    messages JSONB[],
    status resourcestate,
    changes JSONB[],
    change change,
    send_event boolean,
    PRIMARY KEY (environment, action_id),
    FOREIGN KEY (environment, project) REFERENCES environment (name, project) ON DELETE CASCADE
);

CREATE INDEX resourceaction_env_resourceversionid__started_index ON resourceaction (environment, resource_version_ids, started DESC);

-- Table: public.code
CREATE TABLE public.code (
    id uuid PRIMARY KEY,
    environment varchar NOT NULL,
    project varchar NOT NULL,
    resource varchar NOT NULL,
    version integer NOT NULL,
    sources JSONB,
    source_refs JSONB,
    FOREIGN KEY (environment, project) REFERENCES environment (name, project) ON DELETE CASCADE
);

CREATE INDEX code_env_version_resource_index ON code (environment, version, resource);

-- Table: public.unknownparameter
CREATE TABLE public.unknownparameter (
    id uuid PRIMARY KEY,
    name varchar NOT NULL,
    environment varchar NOT NULL,
    project varchar NOT NULL,
    source varchar NOT NULL,
    resource_id varchar DEFAULT '',
    version integer NOT NULL,
    metadata JSONB,
    resolved boolean DEFAULT false,
    FOREIGN KEY (environment, project) REFERENCES environment (name, project) ON DELETE CASCADE
);

CREATE INDEX unknownparameter_env_version_index ON unknownparameter (environment, version);

-- Table: public.agentprocess
CREATE TABLE public.agentprocess (
    id uuid PRIMARY KEY,
    hostname varchar NOT NULL,
    environment varchar NOT NULL,
    project varchar NOT NULL,
    first_seen timestamp,
    last_seen timestamp,
    expired timestamp,
    sid uuid NOT NULL,
    FOREIGN KEY (environment, project) REFERENCES environment (name, project) ON DELETE CASCADE
);

-- Table: public.agentinstance
CREATE TABLE public.agentinstance (
    id uuid PRIMARY KEY,
    process uuid NOT NULL REFERENCES agentprocess (id),
    name varchar NOT NULL,
    expired timestamp,
    tid uuid NOT NULL
);

-- Table: public.agent
CREATE TABLE public.agent (
    environment varchar NOT NULL,
    project varchar NOT NULL,
    name varchar NOT NULL,
    last_failover timestamp,
    paused boolean DEFAULT false,
-- primary is a reserved keyword in postgresql ==> hange to id_primary
    id_primary uuid,
    PRIMARY KEY (environment, name),
    FOREIGN KEY (environment, project) REFERENCES environment (name, project) ON DELETE CASCADE,
    FOREIGN KEY (id_primary) REFERENCES agentinstance (id) ON DELETE CASCADE
);
