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
    -- Add the 'discovered_at' column
    ALTER TABLE public.unmanagedresource ADD COLUMN discovered_at TIMESTAMP NOT NULL;

    -- drop the old primary key
    ALTER TABLE public.unmanagedresource DROP CONSTRAINT unmanagedresource_pkey;

    -- Rename the 'unmanaged_resource_id' column
    ALTER TABLE public.unmanagedresource RENAME COLUMN unmanaged_resource_id TO discovered_resource_id;

    -- Rename the table
    ALTER TABLE public.unmanagedresource RENAME TO discoveredresource;

    -- add a new primary key constraint
    ALTER TABLE public.discoveredresource ADD CONSTRAINT
    discoveredresource_pkey PRIMARY KEY (environment, discovered_resource_id);
    """
    await connection.execute(schema)
