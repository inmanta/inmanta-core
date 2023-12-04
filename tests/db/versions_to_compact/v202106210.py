"""
    Copyright 2021 Inmanta

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
    schema = """

ALTER TABLE public.resource
    ADD COLUMN resource_id_value varchar;

UPDATE public.resource
SET resource_id_value=substring(resource_id from '\\[(?:.*),(?:.*)=(.*)\\]');

-- Set NOT NULL constraint after column is populated
ALTER TABLE public.resource
    ALTER COLUMN resource_id_value SET NOT NULL;

CREATE INDEX resource_environment_resource_id_value_index ON public.resource (environment, resource_id_value);
"""
    async with connection.transaction():
        await connection.execute(schema)
