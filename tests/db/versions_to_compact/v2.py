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
from asyncpg import Connection

DISABLED = False


async def update(connection: Connection) -> None:
    schema = """
ALTER TABLE public.compile
    ADD COLUMN requested timestamp,
    ADD COLUMN metadata JSONB,
    ADD COLUMN environment_variables JSONB,
    ADD COLUMN do_export boolean,
    ADD COLUMN force_update boolean,
    ADD COLUMN success boolean,
    ADD COLUMN version integer,
    ADD COLUMN remote_id uuid,
    ADD COLUMN handled boolean;

ALTER TABLE public.report ALTER COLUMN completed DROP NOT NULL;

CREATE INDEX compile_env_requested_index ON compile (environment, requested ASC);
CREATE INDEX compile_env_remote_id_index ON compile (environment, remote_id);
"""
    async with connection.transaction():
        await connection.execute(schema)
