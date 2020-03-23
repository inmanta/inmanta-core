"""
    Copyright 2020 Inmanta

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
from asyncpg import Connection

DISABLED = False


async def update(connection: Connection) -> None:
    await connection.execute(
        """
--------------------------------
-- Remove forms functionality --
--------------------------------

DROP TABLE IF EXISTS public.formrecord;
DROP TABLE IF EXISTS public.form;

--------------------------------------------------------------------------------
-- Remove join table resourceversionid and put fields in resourceaction table --
--------------------------------------------------------------------------------

-- Add new columns to resourceaction table
ALTER TABLE public.resourceaction
    ADD COLUMN environment uuid,
    ADD COLUMN version integer,
    ADD COLUMN resource_version_ids varchar[];

-- Populate the environment and resource_version_ids columns
UPDATE public.resourceaction AS r
SET environment=(SELECT DISTINCT rvi.environment
                 FROM public.resourceversionid rvi
                 WHERE rvi.action_id=r.action_id),
    resource_version_ids=ARRAY(SELECT rvi.resource_version_id
                               FROM public.resourceversionid rvi
                               WHERE rvi.action_id=r.action_id);

-- Remove dangling resource actions. Due to a bug, the environment is
-- unknown when no resources are associated with a resource action.
DELETE FROM public.resourceaction WHERE environment IS NULL;

-- Populate the version column
UPDATE public.resourceaction AS ra
SET version=(SELECT model
             FROM public.resource AS rs
             WHERE rs.environment=ra.environment AND rs.resource_version_id=ra.resource_version_ids[1]);

-- Delete resource actions from the database for which the configuration model doesn't exist anymore.
-- This is caused by a cascading delete issue.
DELETE FROM public.resourceaction AS ra WHERE NOT EXISTS(SELECT 1
                                                         FROM public.resource AS r
                                                         WHERE r.environment=ra.environment AND r.model=ra.version);

-- Set constraints on the new columns in the resourceaction table
ALTER TABLE public.resourceaction
    ALTER COLUMN environment SET NOT NULL,
    ALTER COLUMN version SET NOT NULL,
    ALTER COLUMN resource_version_ids SET NOT NULL,
    ADD FOREIGN KEY (environment, version) REFERENCES configurationmodel (environment, version) ON DELETE CASCADE;

-- Drop resourceversionid table and its indexes
DROP INDEX IF EXISTS resourceversionid_environment_resource_version_id_index;
DROP INDEX IF EXISTS resourceversionid_action_id_index;
DROP TABLE IF EXISTS public.resourceversionid;

-- Setup/Remove indexes
CREATE INDEX resourceaction_resource_version_ids_index ON resourceaction USING gin(resource_version_ids);
DROP INDEX resourceaction_action_id_started_index;
CREATE INDEX resourceaction_environment_action_started_index ON resourceaction(environment,action,started DESC);
"""
    )
