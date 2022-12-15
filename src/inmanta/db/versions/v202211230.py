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
    """
    Query part to actually convert a resource version id to a resource id

    split off for easier testing
    """
    return f"REGEXP_REPLACE({from_value}, ',v=[0-9]+$', '')"


def query_part_convert_requires(from_value: str) -> str:
    """
    Query part to convert requires, which is in a jsonb dict

    split off for easier testing
    """
    # get the value out of the dict
    project = f"{from_value}->'requires'"

    # make conversion on one element
    convert = query_part_convert_rvid_to_rid("element")

    # loop over the array and convert
    collect = f"""
     (select
         jsonb_agg(
            {convert}
         )
     from jsonb_array_elements_text({project}) element)"""

    # set the value and handle the case where the requires key doesn't exist
    return f"coalesce(jsonb_set({from_value}, '{{requires}}', {collect}), {from_value})"


def query_part_convert_provides(from_value: str) -> str:
    """
    Query part to convert provides, which is a varchar array

    split off for easier testing
    """
    # make conversion on one element
    convert = query_part_convert_rvid_to_rid("element")

    # loop over the array and convert
    collect = f"""
        coalesce(
            (select
                 array_agg(
                   {convert}
                )
            from unnest({from_value}) element),
            ARRAY[]::character varying[]
        )
        """

    return collect
