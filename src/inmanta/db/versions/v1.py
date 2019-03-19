async def update(connection):
    schema = """
CREATE TYPE versionstate AS ENUM('success', 'failed', 'deploying', 'pending');
CREATE TYPE resourcestate AS ENUM('unavailable', 'skipped', 'dry', 'deployed', 'failed', 'deploying', 'available',
                                  'cancelled', 'undefined', 'skipped_for_undefined', 'processing_events');
CREATE TYPE resourceaction_type AS ENUM('store', 'push', 'pull', 'deploy', 'dryrun', 'getfact', 'other');
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
    skipped_for_undeployable varchar[],
    PRIMARY KEY(version, environment)
);

CREATE UNIQUE INDEX configurationmodel_env_version_index ON configurationmodel (environment, version);

-- Table: public.resources
CREATE TABLE IF NOT EXISTS public.resource (
    environment uuid NOT NULL,
    model integer NOT NULL,
    resource_id varchar NOT NULL,
    resource_version_id varchar NOT NULL,
    resource_type varchar NOT NULL,
    agent varchar NOT NULL,
    last_deploy timestamp,
    attributes JSONB,
    attribute_hash varchar,
    status resourcestate DEFAULT 'available',
    provides varchar[] DEFAULT array[]::varchar[],
    PRIMARY KEY(environment, resource_version_id),
    FOREIGN KEY (environment, model) REFERENCES configurationmodel (environment, version) ON DELETE CASCADE
);

CREATE INDEX resource_env_model_agent_index ON resource (environment, model, agent);
CREATE INDEX resource_env_resourceid_index ON resource (environment, resource_id);
CREATE UNIQUE INDEX resource_env_resourceversionid_index ON resource (environment, resource_version_id);

-- Table: public.resourceaction
CREATE TABLE IF NOT EXISTS public.resourceaction (
    action_id uuid PRIMARY KEY NOT NULL,
    action resourceaction_type NOT NULL,
    started timestamp NOT NULL,
    finished timestamp,
    messages JSONB[],
    status resourcestate,
    changes JSONB DEFAULT '{}'::jsonb,
    change change,
    send_event boolean
);

CREATE INDEX resourceaction_action_id_started_index ON resourceaction (action_id, started DESC);

-- Table: public.resourceversionid
-- TODO: FK CONSTRAINT???
CREATE TABLE IF NOT EXISTS public.resourceversionid (
    environment uuid NOT NULL,
    action_id uuid NOT NULL REFERENCES resourceaction (action_id) ON DELETE CASCADE,
    resource_version_id varchar NOT NULL,
    PRIMARY KEY(environment, action_id, resource_version_id)
);

-- Table: public.code
-- There is no foreign key constraint from code to configurationmodel, since the code is uploaded
-- to the server before the configuration model is created. Working the other was around results
-- in a configuration model which doesn't have the code required to deploy the model. 
CREATE TABLE IF NOT EXISTS public.code (
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    resource varchar NOT NULL,
    version integer NOT NULL,
    source_refs JSONB,
    PRIMARY KEY(environment, resource, version)
);

CREATE INDEX code_env_version_resource_index ON code (environment, version, resource);

-- Table: public.unknownparameter
CREATE TABLE IF NOT EXISTS public.unknownparameter (
    id uuid PRIMARY KEY,
    name varchar NOT NULL,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    source varchar NOT NULL,
    resource_id varchar DEFAULT '',
    version integer NOT NULL,
    metadata JSONB,
    resolved boolean DEFAULT false,
    FOREIGN KEY (environment, version) REFERENCES configurationmodel (environment, version) ON DELETE CASCADE
);

CREATE INDEX unknownparameter_env_version_index ON unknownparameter (environment, version);

-- Table: public.agentprocess
CREATE TABLE IF NOT EXISTS public.agentprocess (
    hostname varchar NOT NULL,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    first_seen timestamp,
    last_seen timestamp,
    expired timestamp,
    sid uuid NOT NULL PRIMARY KEY
);


-- Table: public.agentinstance
CREATE TABLE IF NOT EXISTS public.agentinstance (
    id uuid PRIMARY KEY,
    process uuid NOT NULL REFERENCES agentprocess (sid) ON DELETE CASCADE,
    name varchar NOT NULL,
    expired timestamp,
    -- tid is an environment id
    tid uuid NOT NULL
);

-- Table: public.agent
CREATE TABLE IF NOT EXISTS public.agent (
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    name varchar NOT NULL,
    last_failover timestamp,
    paused boolean DEFAULT false,
-- primary is a reserved keyword in postgresql ==> hange to id_primary
    id_primary uuid REFERENCES agentinstance(id) ON DELETE CASCADE,
    PRIMARY KEY(environment, name)
);

CREATE UNIQUE INDEX agent_env_name_index ON agent (environment, name);

-- Table: public.parameter
CREATE TABLE IF NOT EXISTS public.parameter (
    id uuid PRIMARY KEY,
    name varchar NOT NULL,
    value varchar NOT NULL DEFAULT '',
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    resource_id varchar DEFAULT '', 
    source varchar NOT NULL,
    updated timestamp,
    metadata JSONB
);

-- Table: public.form
CREATE TABLE IF NOT EXISTS public.form (
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    form_type varchar NOT NULL,
    options JSONB,
    fields JSONB,
    defaults JSONB,
    field_options JSONB,
    PRIMARY KEY(environment, form_type)
);

-- Table: public.formrecord
CREATE TABLE IF NOT EXISTS public.formrecord(
    id uuid PRIMARY KEY,
    form varchar NOT NULL,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    fields JSONB,
    changed timestamp,
    FOREIGN KEY (environment, form) REFERENCES form(environment, form_type) ON DELETE CASCADE
);

-- Table: public.compile
CREATE TABLE IF NOT EXISTS public.compile(
    id uuid PRIMARY KEY,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    started timestamp,
    completed timestamp
);

CREATE INDEX compile_env_started ON compile (environment, started DESC);

-- Table: public.report
CREATE TABLE IF NOT EXISTS public.report(
    id uuid PRIMARY KEY,
    started timestamp NOT NULL,
    completed timestamp NOT NULL,
    command varchar NOT NULL,
    name varchar NOT NULL,
    errstream varchar DEFAULT '',
    outstream varchar DEFAULT '',
    returncode integer,
    compile uuid NOT NULL REFERENCES compile(id) ON DELETE CASCADE
);

CREATE INDEX report_compile ON report (compile);

-- Table: public.dryrun
CREATE TABLE IF NOT EXISTS public.dryrun(
    id uuid PRIMARY KEY,
    environment uuid NOT NULL,
    model integer NOT NULL,
    date timestamp,
    total integer DEFAULT 0,
    todo integer DEFAULT 0,
    resources JSONB DEFAULT '{}'::jsonb,
    FOREIGN KEY (environment, model) REFERENCES configurationmodel (environment, version) ON DELETE CASCADE
);

CREATE INDEX dryrun_env_model ON dryrun (environment, model DESC);

-- Table: public.schemaversion
CREATE TABLE IF NOT EXISTS public.schemaversion(
    id uuid PRIMARY KEY,
    current_version integer NOT NULL UNIQUE
);
"""
    async with connection.transaction():
        await connection.execute(schema)
