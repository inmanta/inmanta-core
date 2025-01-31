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
     UPDATE public.compile SET environment_variables = '{}' WHERE environment_variables is null;

     ALTER TABLE public.compile
        ADD COLUMN mergeable_environment_variables jsonb DEFAULT '{}' NOT NULL,
        ADD COLUMN used_environment_variables jsonb,
        ALTER COLUMN environment_variables SET NOT NULL;

     ALTER TABLE public.compile RENAME COLUMN environment_variables TO requested_environment_variables;

     UPDATE public.compile SET used_environment_variables = requested_environment_variables WHERE completed is not null;
     """

    await connection.execute(schema)
