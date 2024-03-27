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
    # TODO: verify which indexes/changes are required.
    # TODO: add UNIQUE to some indexes?
    # TODO: cleanup
    # TODO: document

    await connection.execute("CREATE INDEX ON public.resource (environment, resource_id, model)")
    await connection.execute("CREATE INDEX ON public.configurationmodel (environment, released, version)")
    await connection.execute(
        "CREATE INDEX ON public.resource (environment, resource_type NULLS FIRST, resource_id NULLS FIRST)"
    )

    await connection.execute("ALTER TABLE public.resource_persistent_state ADD COLUMN resource_type varchar")
    await connection.execute("ALTER TABLE public.resource_persistent_state ADD COLUMN resource_id_value varchar")
    await connection.execute("ALTER TABLE public.resource_persistent_state ADD COLUMN agent varchar")
    await connection.execute("CREATE INDEX ON public.resource_persistent_state (environment, resource_type, resource_id)")
    await connection.execute("CREATE INDEX ON public.resource_persistent_state (environment, resource_id_value, resource_id)")
    await connection.execute("CREATE INDEX ON public.resource_persistent_state (environment, agent, resource_id)")
    await connection.execute(
        """
        UPDATE public.resource_persistent_state AS rps
        SET (resource_type, resource_id_value, agent) = (
            SELECT r.resource_type, resource_id_value, agent
            FROM public.resource AS r
            WHERE rps.resource_id = r.resource_id AND rps.environment = r.environment
        )
        """
    )
