"""
Copyright 2025 Inmanta

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
    Add 'created' column to ResourcePersistentState
    """
    schema = """
    -- Remove dangling resource_sets (resources are deleted with cascade)
    DELETE FROM resource_set AS rs
    WHERE NOT EXISTS (
        SELECT 1
        FROM resource_set_configuration_model AS rscm
        WHERE rscm.environment=rs.environment
        AND rscm.resource_set_id=rs.id
    );

    -- Remove rps entries that no longer have a matching resource in the database
    DELETE FROM public.resource_persistent_state AS rps
    WHERE NOT EXISTS (
        SELECT 1
        FROM resource AS r
        WHERE rps.environment=r.environment
        AND rps.resource_id=r.resource_id
    );

    ALTER TABLE public.resource_persistent_state
        ADD COLUMN created TIMESTAMP WITH TIME ZONE;

    UPDATE public.resource_persistent_state AS rps
    SET created=(
        SELECT DISTINCT ON (r.resource_id)
            cm.date
        FROM public.resource AS r
        INNER JOIN public.resource_set_configuration_model AS rscm
            ON r.environment=rscm.environment
            AND r.resource_set_id=rscm.resource_set_id
        INNER JOIN public.configurationmodel AS cm
            ON rscm.environment=cm.environment
            AND rscm.model=cm.version
        WHERE r.environment=rps.environment
            AND r.resource_id=rps.resource_id
        ORDER BY r.resource_id, rscm.model asc
    );
    ALTER TABLE public.resource_persistent_state
         ALTER COLUMN created SET NOT NULL;
    """
    await connection.execute(schema)
