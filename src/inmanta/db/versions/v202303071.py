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

from inmanta import data


async def update(connection: Connection) -> None:
    """
    * Create index on table to efficiently filter resources based on the resource set that they belong to.
    * Ensure that the configurationmodel table has the is_suitable_for_partial_compiles column and make sure
      it's correctly populated for all existing models in the table.
    """
    # Add index on resource table
    await connection.execute("CREATE INDEX ON public.resource (environment, model, resource_set)")

    # Create column
    await connection.execute("ALTER TABLE public.configurationmodel ADD COLUMN is_suitable_for_partial_compiles boolean")
    # Populate column
    await connection.execute(
        f"""
            UPDATE {data.ConfigurationModel.table_name()}
            SET is_suitable_for_partial_compiles=FALSE
        """
    )
    # Add non null constraint
    await connection.execute("ALTER TABLE public.configurationmodel ALTER COLUMN is_suitable_for_partial_compiles SET NOT NULL")

    # Remove the version field from the attributes of a resource
    await connection.execute(
        f"""
            UPDATE {data.Resource.table_name()}
            SET attributes = attributes - 'version'
            WHERE attributes ? 'version'
        """
    )
