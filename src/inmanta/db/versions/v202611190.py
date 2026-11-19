"""
Copyright 2026 Inmanta

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
    Make the columns that identify an inmanta module or one of its files use the C collation, which compares bytewise.

    An index on a text column is sorted by the collation of the column. The default collation of the database follows
    the sort rules of the operating system's C library, and those rules can change when the operating system of the
    database server is upgraded. An index built with the old rules then fails to find some of its rows. For these tables,
    that would let the cleanup of unused modules delete the code of a module that a model version still uses. The C
    collation never changes its order.

    Changing the collation of a column doesn't rewrite the table, it only rebuilds the indexes on that column.
    """
    schema = """
        ALTER TABLE public.inmanta_module
            ALTER COLUMN name TYPE varchar COLLATE "C",
            ALTER COLUMN version TYPE varchar COLLATE "C";

        ALTER TABLE public.module_files
            ALTER COLUMN inmanta_module_name TYPE varchar COLLATE "C",
            ALTER COLUMN inmanta_module_version TYPE varchar COLLATE "C",
            ALTER COLUMN path TYPE varchar COLLATE "C";

        ALTER TABLE public.configurationmodel_modules
            ALTER COLUMN inmanta_module_name TYPE varchar COLLATE "C",
            ALTER COLUMN inmanta_module_version TYPE varchar COLLATE "C";

        ALTER TABLE public.agent_modules
            ALTER COLUMN inmanta_module_name TYPE varchar COLLATE "C";
    """
    await connection.execute(schema)
