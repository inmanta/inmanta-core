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
    set_default_for_facts = """
    UPDATE public.parameter

    -- Facts (i.e. associated to a resource) expire by default:

    SET expires=true
    where resource_id != '' and expires is null;
    """

    set_default_for_parameters = """
    UPDATE public.parameter

    -- Parameters (i.e. not associated to a resource) never expire:

    SET expires=false
    where resource_id = '';
    """

    set_not_null = """
     -- change the type of the 'expires' column to disallow null values

     ALTER TABLE public.parameter
     ALTER COLUMN expires SET NOT NULL;
     """

    async with connection.transaction():
        await connection.execute(set_default_for_facts)
        await connection.execute(set_default_for_parameters)
        await connection.execute(set_not_null)

