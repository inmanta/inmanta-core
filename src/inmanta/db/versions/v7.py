"""
    Copyright 2020 Inmanta

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

DISABLED = False


async def update(connection: Connection) -> None:
    await connection.execute(
        """
        CREATE INDEX resourceaction_environment_version_started_index ON resourceaction(environment,version,started DESC);
        """
    )
    await enforce_unique_agent_instances(connection)


async def enforce_unique_agent_instances(connection: Connection) -> None:
    """
    Deletes duplicate AgentInstance records and adds a uniqueness constraint.
    """
    async with connection.transaction():
        await connection.execute(
            """
            DELETE FROM public.agentinstance a
            USING public.agentinstance b
            WHERE a.id < b.id AND a.tid = b.tid AND a.process = b.process AND a.name = b.name
            ;

            ALTER TABLE public.agentinstance ADD CONSTRAINT agentinstance_unique UNIQUE (tid, process, name);
            """
        )
