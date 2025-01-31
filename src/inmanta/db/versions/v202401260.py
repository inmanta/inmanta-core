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
    schema = """
    UPDATE public.parameter
    SET expires=(
        CASE
            WHEN resource_id IS NOT NULL AND resource_id != '' AND expires IS NULL
            -- It's a fact and facts expire by default.
            THEN TRUE
            WHEN resource_id IS NULL OR resource_id = ''
            -- It's a parameter. Parameters never expire.
            THEN FALSE
            -- Keep current value
            ELSE expires
        END
    );

     -- change the type of the 'expires' column to disallow null values

     ALTER TABLE public.parameter
     ALTER COLUMN expires SET NOT NULL;
     """

    await connection.execute(schema)
