"""
Copyright 2026 Inmanta

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


async def update(connection: Connection) -> None:
    """
    Add the orphaned_after field to the rps table, populate it and drop is_orphan
    """
    schema = """
     ALTER TABLE public.resource_persistent_state ADD COLUMN orphaned_after integer;

     UPDATE public.resource_persistent_state AS rps
     SET orphaned_after=(
        -- Safeguard for orphaned resources that are not present on the rscm table
        SELECT COALESCE(MAX(rscm.model), 0)
        FROM public.resource AS r
        INNER JOIN public.resource_set_configuration_model AS rscm
            ON r.environment=rscm.environment AND r.resource_set=rscm.resource_set
        INNER JOIN public.configurationmodel AS m
            ON rscm.environment=m.environment AND rscm.model=m.version
        WHERE r.environment=rps.environment AND r.resource_id=rps.resource_id AND m.released
    ) WHERE rps.is_orphan;

    CREATE INDEX resource_persistent_state_environment_orphaned_after_index ON public.resource_persistent_state
        USING btree (environment) WHERE orphaned_after IS NULL;

    CREATE INDEX resource_persistent_state_environment_resource_id_orphaned_after_index ON public.resource_persistent_state
        USING btree (environment, resource_id, orphaned_after);

    DROP INDEX resource_persistent_state_environment_is_orphan_index;
    DROP INDEX resource_persistent_state_environment_resource_id_is_orphan;

    ALTER TABLE public.resource_persistent_state DROP COLUMN is_orphan;
    """
    await connection.execute(schema)
