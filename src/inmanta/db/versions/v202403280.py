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
    # TODO: better still might be to have a resource identity table, then reference that one from both resource and
    #   resource_persistent_state. Consider or follow-up ticket?
    # TODO: migration test

    await connection.execute(
        """
        ALTER TABLE public.resource_persistent_state
            ADD COLUMN resource_type varchar,
            ADD COLUMN agent varchar,
            ADD COLUMN resource_id_value varchar
            ;
        UPDATE public.resource_persistent_state AS rps
            SET (resource_type, resource_id_value, agent) = (
                SELECT r.resource_type, resource_id_value, agent
                FROM public.resource AS r
                WHERE rps.resource_id = r.resource_id AND rps.environment = r.environment
            )
            ;
        ALTER TABLE public.resource_persistent_state
            ALTER COLUMN resource_type SET NOT NULL,
            ALTER COLUMN agent SET NOT NULL,
            ALTER COLUMN resource_id_value SET NOT NULL,
            ADD CONSTRAINT derived_id UNIQUE (resource_type, agent, resource_id)
            ;
        """
    )

    # TODO: these seem to not be required. Probably because scale is still relatively small when it comes to distinct resources (5000)
    #await connection.execute("CREATE INDEX ON public.resource_persistent_state (environment, resource_type, resource_id)")
    #await connection.execute("CREATE INDEX ON public.resource_persistent_state (environment, resource_id_value, resource_id)")
    #await connection.execute("CREATE INDEX ON public.resource_persistent_state (environment, agent, resource_id)")
