"""
    Copyright 2019 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com
"""

import asyncpg

DISABLED = False


async def update(connection: asyncpg.Connection) -> None:
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

CREATE UNIQUE INDEX environment_name_project_index ON environment (project, name);

-- Table: public.configurationmodels
CREATE TABLE IF NOT EXISTS public.configurationmodel (
    version integer NOT NULL,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    date timestamp,
    released boolean DEFAULT false,
    deployed boolean DEFAULT false,
    result versionstate DEFAULT 'pending',
    version_info JSONB,
    total integer DEFAULT 0,
    undeployable varchar[],
    skipped_for_undeployable varchar[],
    PRIMARY KEY(environment, version)
);

-- Used in:
--      * data.mark_done_if_done()
-- => This query is exected frequently
CREATE UNIQUE INDEX configurationmodel_env_version_total_index ON configurationmodel (environment, version DESC, total);
-- Used in:
--      * data.get_latest_version()
--      * data.get_version_nr_latest_version()
--      * data.get_increment()
-- => Prevent sort operation on column version
CREATE UNIQUE INDEX configurationmodel_env_released_version_index ON configurationmodel (environment, released, version DESC);

-- Table: public.resources
CREATE TABLE IF NOT EXISTS public.resource (
    environment uuid NOT NULL,
    model integer NOT NULL,
    resource_id varchar NOT NULL,
    resource_version_id varchar NOT NULL,
    agent varchar NOT NULL,
    last_deploy timestamp,
    attributes JSONB,
    attribute_hash varchar,
    status resourcestate DEFAULT 'available',
    provides varchar[] DEFAULT array[]::varchar[],
    PRIMARY KEY(environment, resource_version_id),
    FOREIGN KEY (environment, model) REFERENCES configurationmodel (environment, version) ON DELETE CASCADE
);

-- Used in:
--   * data. get_resources_for_attribute_hash()
CREATE INDEX resource_env_attr_hash_index ON resource (environment, attribute_hash);
-- Used in:
--      * data.get_resources_for_version()
--      * data.get_deleted_resources()
-- => Prevent sequential scan through all resources
CREATE INDEX resource_env_model_agent_index ON resource (environment, model, agent);
-- Used in:
--      * data.get_resources_report()
--      * data.get_latest_version()
--      * data.get_deleted_resources()
-- => Prevent sequential scan through all resources
-- => Prevent sort operation on column model
CREATE INDEX resource_env_resourceid_index ON resource (environment, resource_id, model DESC);
-- Used in:
--      * data.get_deleted_resources()
-- => Prevent costly search through jsonb structures
CREATE INDEX resource_attributes_index ON resource USING gin (attributes jsonb_path_ops);

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

-- Used in:
--      * data.get_log()
-- => Prevent sort operation on column started
CREATE UNIQUE INDEX resourceaction_action_id_started_index ON resourceaction (action_id, started DESC);
-- Used in:
--      * data.purge_logs()
-- => Prevent sequential scan through all resource actions
CREATE INDEX resourceaction_started_index ON resourceaction (started);

-- Table: public.resourceversionid
-- TODO: FK CONSTRAINT???
CREATE TABLE IF NOT EXISTS public.resourceversionid (
    environment uuid NOT NULL,
    action_id uuid NOT NULL REFERENCES resourceaction (action_id) ON DELETE CASCADE,
    resource_version_id varchar NOT NULL,
    PRIMARY KEY(environment, action_id, resource_version_id)
);

-- Used in:
--      * data.ResourceAction.get_log()
-- => Prevent sequential scan through all resourceversionids in a certain environment
CREATE INDEX resourceversionid_environment_resource_version_id_index ON resourceversionid (environment, resource_version_id);
-- Used in:
--      * data.ResourceAction.get_by_id()
--      * data.ResourceAction.get_list
--      * data.ResourceAction.get_log()
-- => Prevent sequential scan through all resourceversionids
CREATE INDEX resourceversionid_action_id_index ON resourceversionid (action_id);

-- Table: public.code
-- There is no foreign key constraint from code to configurationmodel, since the code is uploaded
-- to the server before the configuration model is created. Working the other was around results
-- in a configuration model which doesn't have the code required to deploy the model.
CREATE TABLE IF NOT EXISTS public.code (
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    resource varchar NOT NULL,
    version integer NOT NULL,
    source_refs JSONB,
    PRIMARY KEY(environment, version, resource)
);

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

-- Used in:
--      * server.get_version()
CREATE INDEX unknownparameter_env_version_index ON unknownparameter (environment, version);
-- Used in:
--      * server.renew_expired_facts()
CREATE INDEX unknownparameter_resolved_index ON unknownparameter (resolved);

-- Table: public.agentprocess
CREATE TABLE IF NOT EXISTS public.agentprocess (
    hostname varchar NOT NULL,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    first_seen timestamp,
    last_seen timestamp,
    expired timestamp,
    sid uuid NOT NULL PRIMARY KEY
);

-- Used in:
--      * data.get_live()
--      * data.get_live_by_env()
--      * data.get_by_env()
-- => Speed up search for records which have expired set to NULL
CREATE UNIQUE INDEX agentprocess_sid_expired_index ON agentprocess (sid, expired);
-- Used in:
--      * data.get_by_sid()
-- => Prevent sequential scan through all agentprocesses
CREATE INDEX agentprocess_env_expired_index ON agentprocess (environment, expired);

-- Table: public.agentinstance
CREATE TABLE IF NOT EXISTS public.agentinstance (
    id uuid PRIMARY KEY,
    process uuid NOT NULL REFERENCES agentprocess (sid) ON DELETE CASCADE,
    name varchar NOT NULL,
    expired timestamp,
    -- tid is an environment id
    tid uuid NOT NULL
);

-- Used in:
--      * data.active_for()
-- => Prevent sequential scan through all agentinstances
CREATE INDEX agentinstance_expired_tid_endpoint_index ON agentinstance (tid, name, expired);
-- Used in:
--      * expire_session()
-- => Prevent sequential scan through all agentinstances
CREATE INDEX agentinstance_process_index ON agentinstance (process);

-- Table: public.agent
CREATE TABLE IF NOT EXISTS public.agent (
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    name varchar NOT NULL,
    last_failover timestamp,
    paused boolean DEFAULT false,
-- primary is a reserved keyword in postgresql ==> change to id_primary
    id_primary uuid REFERENCES agentinstance(id) ON DELETE CASCADE,
    PRIMARY KEY(environment, name)
);

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

-- Used in:
--      * data.get_updated_before()
-- => Prevent sequential scan through all parameters
CREATE INDEX parameter_updated_index ON parameter (updated);
-- Used in:
--      * data.list_parameters()
--      * server.get_param()
--      * server.resource_action_update()
--      * server.set_param()
-- => Prevent sequential scan through all parameters
CREATE INDEX parameter_env_name_resource_id_index ON parameter (environment, name, resource_id);
-- Used in:
--      * data.list_parameters()
-- => Prevent costly search through jsonb structures
CREATE INDEX parameter_metadata_index ON parameter USING gin (metadata jsonb_path_ops);

-- Table: public.form
CREATE TABLE IF NOT EXISTS public.form (
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    form_type varchar NOT NULL UNIQUE,
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
    environment uuid NOT NULL,
    fields JSONB,
    changed timestamp,
    FOREIGN KEY (form) REFERENCES form(form_type) ON DELETE CASCADE
);

-- Used in:
--      * server.list_records()
-- => Prevent sequential scan through all formrecords
CREATE INDEX formrecord_form_index ON formrecord (form);

-- Table: public.compile
CREATE TABLE IF NOT EXISTS public.compile(
    id uuid PRIMARY KEY,
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    started timestamp,
    completed timestamp
);

-- Used in:
--      * data.get_reports()
-- => Prevent sort operation on started
CREATE INDEX compile_env_started_index ON compile (environment, started DESC);

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

-- Used in:
--      * data.get_report()
-- => Prevent sequential scan through all reports
CREATE INDEX report_compile_index ON report (compile);

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

-- Used in:
--      * server.dryrun_list()
-- => Prevent sequential scan through all dryruns
CREATE INDEX dryrun_env_model_index ON dryrun (environment, model);
"""
    async with connection.transaction():
        await connection.execute(schema)
