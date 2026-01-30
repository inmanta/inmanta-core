"""
Copyright 2024 Inmanta

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
    Add all resource identifying columns to the resource persistent state table to improve efficiency of resource filtering and
    sorting. These tables are derived from the resource id and are therefore part of the identity of a resource. They will not
    change for the lifetime of a resource (with a given resource id).
    """

    await connection.execute("""
        ALTER TABLE public.resource_persistent_state
            ADD COLUMN resource_type varchar,
            ADD COLUMN agent varchar,
            ADD COLUMN resource_id_value varchar
            ;
        UPDATE public.resource_persistent_state AS rps
            SET (resource_type, agent, resource_id_value) = (
                SELECT r.resource_type, r.agent, r.resource_id_value
                FROM public.resource AS r
                WHERE rps.environment = r.environment AND rps.resource_id = r.resource_id
                LIMIT 1
            )
            ;
        -- Delete long-orphaned resources that don't exist in the resource column anymore but still linger in the persistent
        -- state one. Required for the `NOT NULL` constraint.
        DELETE
            FROM public.resource_persistent_state
            WHERE resource_type IS NULL
            ;
        ALTER TABLE public.resource_persistent_state
            ALTER COLUMN resource_type SET NOT NULL,
            ALTER COLUMN agent SET NOT NULL,
            ALTER COLUMN resource_id_value SET NOT NULL
            -- do not add UNIQUE constraint on (environment, resource_type, agent, resource_id_value) because resource_id_name
            -- might change, which could result in a different resource_id, while still having the same value for all derived
            -- fields
            ;

        CREATE INDEX ON public.resource_persistent_state (environment, resource_type, resource_id);
        CREATE INDEX ON public.resource_persistent_state (environment, resource_id_value, resource_id);
        CREATE INDEX ON public.resource_persistent_state (environment, agent, resource_id);

        -- force Postgres to analyze resource table to allow it to pick efficient query plans
        ANALYZE public.resource;
        """)
