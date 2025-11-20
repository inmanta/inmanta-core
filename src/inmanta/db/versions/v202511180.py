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
    Make discovery_resource_id a mandatory column.
    """
    schema = """
    -- Add dummy discovery_resource_id for discovered resources that do not have
    -- a discovery_resource_id set.
    UPDATE public.discoveredresource
    SET discovery_resource_id='core::UnknownDiscoveryResource[internal,key=unknown]'
    WHERE discovery_resource_id IS NULL;

    -- Make discovery_resource_id column mandatory
    ALTER TABLE public.discoveredresource
        ALTER COLUMN discovery_resource_id SET NOT NULL;
    """
    await connection.execute(schema)
