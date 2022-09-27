"""
    Copyright 2022 Inmanta

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
    schema = """
    DROP INDEX resource_env_resourceid_index;
    CREATE UNIQUE INDEX resource_env_resourceid_index ON resource (environment, resource_id, model DESC);

    CREATE TABLE IF NOT EXISTS public.resourceaction_resource (
        environment uuid NOT NULL,
        resource_action_id uuid NOT NULL REFERENCES public.resourceaction ON DELETE CASCADE,
        resource_id character varying NOT NULL,
        resource_version integer NOT NULL,
        FOREIGN KEY(environment, resource_id, resource_version) REFERENCES
            public.resource (environment, resource_id, model) ON DELETE CASCADE,
        PRIMARY KEY(environment, resource_id, resource_version, resource_action_id)
    );

    INSERT INTO public.resourceaction_resource (resource_action_id, environment, resource_id, resource_version)
        SELECT ra.action_id, r.environment, r.resource_id, r.model FROM public.resourceaction as ra
            INNER JOIN public.resource as r
                ON r.resource_version_id = ANY(ra.resource_version_ids)
                AND r.environment = ra.environment
    """
    async with connection.transaction():
        await connection.execute(schema)
