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
    Split resource id into its composite value columns on the discovered resources table.
    """
    schema = r"""
    ALTER TABLE public.discoveredresource
        ADD COLUMN resource_type varchar,
        ADD COLUMN resource_id_value varchar,
        ADD COLUMN agent varchar
    ;
    UPDATE public.discoveredresource AS r
    SET (resource_type, agent, resource_id_value) = (
        SELECT rid.match[1], rid.match[3], rid.match[4]
        FROM (
            SELECT regexp_match(
                r.discovered_resource_id,
                '^(\w+(::\w+)*::[\w-]+)\[([^,]+),[^=]+=([^\]]*)]$'
            )
        ) AS rid(match)
    )
    ;
    ALTER TABLE public.discoveredresource
        ALTER COLUMN resource_type SET NOT NULL,
        ALTER COLUMN resource_id_value SET NOT NULL,
        ALTER COLUMN agent SET NOT NULL
    ;
    """
    await connection.execute(schema)
