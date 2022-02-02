"""
    Copyright 2021 Inmanta

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
import json
from datetime import datetime
from typing import Dict, List

from asyncpg import Connection, Record

from inmanta import const

DISABLED = False


TIMESTAMP_COLUMNS: Dict[str, List[str]] = {
    "agent": ["last_failover"],
    "agentinstance": ["expired"],
    "agentprocess": ["first_seen", "last_seen", "expired"],
    "compile": ["started", "completed", "requested"],
    "configurationmodel": ["date"],
    "dryrun": ["date"],
    "parameter": ["updated"],
    "report": ["started", "completed"],
    "resourceaction": ["started", "finished"],
    "resource": ["last_deploy"],
}


async def update(connection: Connection) -> None:
    # update all timestamp types
    await connection.execute(
        "\n".join(
            f"ALTER TABLE public.{table} %s;"
            % ", ".join(f"ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE" for column in columns)
            for table, columns in TIMESTAMP_COLUMNS.items()
        )
    )

    # update timestamps embedded in jsonb types
    def transform_message(message: str) -> str:
        obj: Dict = json.loads(message)
        if "timestamp" in obj:
            obj["timestamp"] = (
                datetime.strptime(obj["timestamp"], const.TIME_ISOFMT).astimezone().isoformat(timespec="microseconds")
            )
        return json.dumps(obj)

    records: List[Record] = await connection.fetch("SELECT action_id, messages FROM public.resourceaction")
    await connection.executemany(
        """
        UPDATE public.resourceaction
        SET messages = $1
        WHERE action_id = $2
        """,
        [
            (
                None if record["messages"] is None else [transform_message(msg) for msg in record["messages"]],
                record["action_id"],
            )
            for record in records
        ],
    )
