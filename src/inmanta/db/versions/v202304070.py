"""
Copyright 2023 Inmanta
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
CREATE TABLE IF NOT EXISTS public.unmanagedresource (
    environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
    unmanaged_resource_id VARCHAR NOT NULL,
    values jsonb NOT NULL,
    PRIMARY KEY (environment, unmanaged_resource_id)
);
    """

    await connection.execute(schema)
