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
    schema = f"""
    ALTER TABLE ONLY public.resource
        DROP CONSTRAINT resource_pkey;

    ALTER TABLE ONLY public.resource
        ADD PRIMARY KEY (environment, model, resource_id);

    ALTER TABLE public.resource
        DROP COLUMN resource_version_id;

    DROP INDEX resourceaction_resource_version_ids_index;

    CREATE TYPE resource_id_version_pair AS (resource_id character varying, version int);

    UPDATE public.resource SET
        provides = {query_part_convert_provides('provides')},
        attributes = {query_part_convert_requires('attributes')};

    """

    # Deep rewrite of the data
    # convert resource_version_id into resource_id
    await connection.execute(schema)


def query_part_convert_rvid_to_rid(from_value: str) -> str:
    return f"REGEXP_REPLACE({from_value}, ',v=[0-9]+$', '')"


def query_part_convert_requires(from_value: str) -> str:
    project = f"{from_value}->'requires'"
    convert = query_part_convert_rvid_to_rid("element")

    collect = f"""
     (select
         jsonb_agg(
            {convert}
         )
     from jsonb_array_elements_text({project}) element)"""

    return f"coalesce(jsonb_set({from_value}, '{{requires}}', {collect}), {from_value})"


def query_part_convert_provides(from_value: str) -> str:
    convert = query_part_convert_rvid_to_rid("element")

    collect = f"""
        (select
             array_agg(
               {convert}
            )
        from unnest({from_value}) element)"""

    return collect
