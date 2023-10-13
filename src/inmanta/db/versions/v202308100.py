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
    """
    Add the indexes to make the joins done by a cascading delete perform well.
    """
    schema = """
        -- Foreign key resourceaction_resource(resource_action_id) --> resource(action_id)
        CREATE INDEX IF NOT EXISTS resourceaction_resource_resource_action_id_index
            ON resourceaction_resource(resource_action_id);

        -- Required by query done in the ConfigurationModel.delete_cascade() method that deletes
        -- facts for resources that don't exist anymore.
        CREATE INDEX parameter_environment_resource_id_index ON parameter(environment, resource_id);
        CREATE INDEX resource_resource_id_index ON resource(resource_id);

        -- Foreign key Compile(substitute_compile_id) --> compile(id)
        CREATE INDEX compile_substitute_compile_id_index ON compile(substitute_compile_id);

        -- Drop partial index on agent(id_primary) and replace by a full index.
        -- Required for foreign key agent(id_primary) --> agentinstance(id)
        DROP INDEX agent_id_primary_index;
        CREATE INDEX agent_id_primary_index ON agent(id_primary);
    """
    await connection.execute(schema)
