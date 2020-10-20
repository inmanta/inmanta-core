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
import datetime
from functools import reduce
from typing import Iterator, List, Optional

from asyncpg import Connection, Record

DISABLED = False


async def update(connection: Connection) -> None:
    await connection.execute(
        """
        CREATE INDEX resourceaction_environment_version_started_index ON resourceaction(environment,version,started DESC);
        """
    )
    await enforce_unique_agent_instances(connection)


async def enforce_unique_agent_instances(connection: Connection) -> None:
    async with connection.transaction():
        await merge_agent_instances(connection)
        await connection.execute(
            """
            ALTER TABLE public.agentinstance ADD CONSTRAINT agentinstance_unique UNIQUE (tid, process, name);
            """
        )


async def merge_agent_instances(connection: Connection) -> None:
    """
    Merges AgentInstance records for the same agent instance to conform to the new AgentInstance table constraints.
    """
    async with connection.transaction():
        records: List[Record] = await connection.fetch(
            """
            SELECT DISTINCT tid, process, name
            FROM public.agentinstance
            ;
            """
        )
        for record in records:
            record["tid"]
            instances: List[Record] = await connection.fetch(
                """
                SELECT id, expired
                FROM public.agentinstance
                WHERE tid = $1 AND process = $2 AND name = $3
                ;
                """,
                record["tid"],
                record["process"],
                record["name"],
            )
            # Merged instance should be active iff at least one of the instances being merged is active.
            # Otherwise the most recent expiry timestamp will be used.
            expired: Optional[datetime.datetime] = reduce(
                lambda acc, current: None if (current is None or acc is None) else max(acc, current),
                (instance["expired"] for instance in instances),
            )
            iterator: Iterator[Record] = iter(instances)
            keep: Record
            discard: List[Record]
            keep, *discard = iterator

            if keep["expired"] is not expired:
                await connection.execute("UPDATE public.agentinstance SET expired = $1 WHERE id = $2", expired, keep["id"])
            if len(discard) > 0:
                await connection.execute(
                    "DELETE FROM public.agentinstance WHERE id IN (%s)" % ", ".join(f"${i + 1}" for i in range(len(discard))),
                    *(instance["id"] for instance in discard),
                )
