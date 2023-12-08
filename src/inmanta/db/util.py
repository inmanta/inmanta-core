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
import re
from collections import abc
from dataclasses import dataclass
from typing import NamedTuple, Optional

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

    This class assumes that the names of schemas, tables and columns in the dump don't contain a dot, double quote or
    whitespace character.
    """

    PARSE_EXT_BUFFER_REGEX = re.compile(r"COPY (?P<fq_table_name>[^ ]+)[ ]+\((?P<columns>[^)]+)\)[ ]+FROM stdin")

    # asyncpg execute method can not read in COPY IN

    def __init__(self, script: list[str], postgresql_client: Connection) -> None:
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

    async def _parse_fq_table_name(self, fq_table_name: str) -> tuple[Optional[str], str]:
        """
        Parse a fully qualified PostgreSQL table name into its schema and table components.

        :return: A tuple where the first element is the schema name and the second the table name.
                 If the provided fq_table_name doesn't contain a schema, the first element in the tuple
                 will be None.
        """
        if "." in fq_table_name:
            schema, table_name = fq_table_name.split(".", maxsplit=1)
        else:
            schema = None
            table_name = fq_table_name

        # The schema or table name might be surrounded in quotes when the name conflicts with a keyword.
        if schema:
            schema = schema.strip(' "')
        table_name = table_name.strip(' "')

        return schema, table_name

    async def _parse_copy_command_in_ext_buffer(self) -> tuple[Optional[str], str, list[str]]:
        assert self.extbuffer
        match = self.PARSE_EXT_BUFFER_REGEX.match(self.extbuffer)
        if match is None:
            raise Exception(f"Invalid COPY command: {self.extbuffer}")
        schema, table_name = await self._parse_fq_table_name(match.group("fq_table_name"))
        # A column name might be surrounded in quotes when the name conflicts with a keyword.
        columns = [elem.strip(' "') for elem in match.group("columns").split(",")]
        return schema, table_name, columns

    async def execute_input(self) -> None:
        schema_name, table_name, column_names = await self._parse_copy_command_in_ext_buffer()
        await self.client.copy_to_table(
            schema_name=schema_name,
            table_name=table_name,
            source=AsyncSingleton(self.commandbuffer.encode()),
            columns=column_names,
            timeout=10,
        )
        self.commandbuffer = ""


async def postgres_get_custom_types(postgresql_client: Connection) -> list[str]:
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
    type_names: list[str] = [str(x["Name"]) for x in types_in_db]

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


class ColumnDefinition(NamedTuple):
    """
    :param name: The name of the column.
    :param is_list: A boolean that indicates whether this column has the type list.
    :param default: The default value of this column. Or None, when this column doesn't have a default value.
    """

    name: str
    is_list: bool = False
    default: Optional[str] = None


@dataclass(frozen=True)
class EnumUpdateDefinition:
    """
    A definition on how an existing enum in the database has to be updated.

    :param name: The name of the enumeration.
    :param values: The values the enum should have after the update.
    :param deleted_values: A dictionary that indicates which elements are deleted from the existing enum and how
                           they should be migrated. The key of the dictionary is the name of the removed enum value
                           and the value of the dictionary is the value it should be replaced with or None if the new value
                           should be NULL.
    :param columns: A dictionary that indicates which columns of which tables are using the enum.
                    The key of the dictionary contains the name of the table.
    """

    name: str
    values: abc.Sequence[str]
    deleted_values: abc.Mapping[str, Optional[str]]
    columns: abc.Mapping[str, abc.Sequence[ColumnDefinition]]


async def replace_enum_type(new_type: EnumUpdateDefinition, *, connection: Connection) -> None:
    """
    Completely replaces an enum type with a new definition with the same name.

    :param new_type: The definition of the new type. Assumed to be an internal construct, this method is not safe against
                     injections via this object's attributes.
    """
    temp_name: str = f"_old_{new_type.name}"
    await connection.execute(
        f"""
        ALTER TYPE {new_type.name} RENAME TO {temp_name};
        CREATE TYPE {new_type.name} AS ENUM(%s);
        """
        % (", ".join(f"'{v}'" for v in new_type.values))
    )
    for table, columns in new_type.columns.items():
        for column, is_list, default in columns:
            for old_value, new_value in new_type.deleted_values.items():
                await connection.execute(f"UPDATE {table} SET {column}=$1 WHERE {column}=$2", new_value, old_value)
            await connection.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT")
            if is_list:
                # can't cast directly between enums -> go via varchar
                await connection.execute(
                    f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type.name}[]"
                    f"USING {column}::varchar[]::{new_type.name}[]"
                )
            else:
                # can't cast directly between enums -> go via varchar
                await connection.execute(
                    f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type.name} USING {column}::varchar::{new_type.name}"
                )
            if default:
                await connection.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT '{default}'")
    await connection.execute(f"DROP TYPE {temp_name}")
