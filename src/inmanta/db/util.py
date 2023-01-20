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
import collections.abc
import logging
from typing import List, Optional

from asyncpg import Connection

from inmanta.stable_api import stable_api

logger = logging.getLogger(__name__)

MODE_READ_COMMAND = 0
MODE_READ_INPUT = 1


class AsyncSingleton(collections.abc.AsyncIterable[bytes]):
    """AsyncPG wants an async iterable"""

    def __init__(self, item: bytes):
        self.item: Optional[bytes] = item

    def __aiter__(self) -> "AsyncSingleton":
        return self

    async def __anext__(self) -> bytes:
        if self.item is None:
            raise StopAsyncIteration
        item = self.item
        self.item = None
        return item


@stable_api
class PGRestore:
    """
    Class that offers support to restore a database dump.
    """

    # asyncpg execute method can not read in COPY IN

    def __init__(self, script: List[str], postgresql_client: Connection) -> None:
        self.commandbuffer = ""
        self.extbuffer = ""
        self.mode = MODE_READ_COMMAND
        self.script = script
        self.client = postgresql_client

    async def run(self) -> None:
        for line in self.script:
            if self.mode == MODE_READ_COMMAND:
                if line.startswith("COPY"):
                    await self.execute_buffer()
                    self.extbuffer = line
                    self.mode = MODE_READ_INPUT
                else:
                    self.buffer(line)
            else:
                if line == "\\.\n":
                    await self.execute_input()
                    self.mode = MODE_READ_COMMAND
                else:
                    self.buffer(line)
        assert self.mode == MODE_READ_COMMAND
        await self.execute_buffer()

    def buffer(self, cmd: str) -> None:
        if cmd.startswith("--"):
            return
        if not cmd.strip():
            return
        self.commandbuffer += cmd

    async def execute_buffer(self) -> None:
        if not self.commandbuffer.strip():
            return
        await self.client.execute(self.commandbuffer)
        self.commandbuffer = ""

    async def execute_input(self) -> None:
        await self.client._copy_in(self.extbuffer, AsyncSingleton(self.commandbuffer.encode()), 10)
        self.commandbuffer = ""


async def postgres_get_custom_types(postgresql_client: Connection) -> List[str]:
    """
    Returns all custom types defined in the database.
    """
    # Query extracted from CLI
    # psql -E
    # \dT

    get_custom_types = """
    SELECT n.nspname as "Schema",
      pg_catalog.format_type(t.oid, NULL) AS "Name",
      pg_catalog.obj_description(t.oid, 'pg_type') as "Description"
    FROM pg_catalog.pg_type t
         LEFT JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
    WHERE (t.typrelid = 0 OR (SELECT c.relkind = 'c' FROM pg_catalog.pg_class c WHERE c.oid = t.typrelid))
      AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_type el WHERE el.oid = t.typelem AND el.typarray = t.oid)
           AND n.nspname <> 'pg_catalog'
          AND n.nspname <> 'information_schema'
      AND pg_catalog.pg_type_is_visible(t.oid)
    ORDER BY 1, 2;
    """

    types_in_db = await postgresql_client.fetch(get_custom_types)
    type_names: List[str] = [str(x["Name"]) for x in types_in_db]

    return type_names


@stable_api
async def clear_database(postgresql_client: Connection) -> None:
    """
    Remove all content from the database. Removes functions, tables and data types.
    """
    assert not postgresql_client.is_in_transaction()
    await postgresql_client.reload_schema_state()
    # query taken from : https://database.guide/3-ways-to-list-all-functions-in-postgresql/
    functions_query = """
SELECT routine_name
FROM  information_schema.routines
WHERE routine_type = 'FUNCTION'
AND routine_schema = 'public';
    """
    functions_in_db = await postgresql_client.fetch(functions_query)
    function_names = [str(x["routine_name"]) for x in functions_in_db]
    if function_names:
        drop_query = "DROP FUNCTION if exists %s " % ", ".join(function_names)
        await postgresql_client.execute(drop_query)

    tables_in_db = await postgresql_client.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    table_names = [f"public.{x['table_name']}" for x in tables_in_db]
    if table_names:
        drop_query = "DROP TABLE %s CASCADE" % ", ".join(table_names)
        await postgresql_client.execute(drop_query)

    type_names = await postgres_get_custom_types(postgresql_client)
    if type_names:
        drop_query = "DROP TYPE %s" % ", ".join(type_names)
        await postgresql_client.execute(drop_query)
    logger.info(
        "Performed Hard Clean with tables: %s  types: %s  functions: %s",
        ",".join(table_names),
        ",".join(type_names),
        ",".join(function_names),
    )
