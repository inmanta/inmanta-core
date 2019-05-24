"""
    Copyright 2019 Inmanta

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
import inspect
import pkgutil
import types
import uuid
from typing import Optional

import asyncpg
import pytest
from asyncpg import PostgresSyntaxError

import inmanta.db.versions
from inmanta import data
from inmanta.data import schema
from inmanta.data.schema import CORE_NAME, Version


async def run_updates_and_verify(
    get_columns_in_db_table, schema_manager: schema.DBSchema, current: Optional[int] = None, prefix: str = ""
):
    async def update_function1(connection):
        await connection.execute(f"CREATE TABLE public.{prefix}tab(id integer primary key, val varchar NOT NULL);")

    async def update_function2(connection):
        await connection.execute(f"ALTER TABLE public.{prefix}tab DROP COLUMN val;")

    current_db_version = await schema_manager.get_current_version()
    assert current is None or current_db_version == current
    if current_db_version is None:
        current_db_version = 0
    version_update1 = current_db_version + 1
    version_update2 = current_db_version + 2
    update_function_map = [Version(f"v{version_update1}", update_function1), Version(f"v{version_update2}", update_function2)]

    await schema_manager._update_db_schema(update_function_map)

    assert (await schema_manager.get_current_version()) == version_update2
    assert sorted(["id"]) == sorted(await get_columns_in_db_table("tab"))


@pytest.mark.asyncio
async def test_dbschema_clean(postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db):
    dbm = schema.DBSchema("test", inmanta.db.versions, postgresql_client)
    current_db_version = await dbm.get_current_version()
    assert current_db_version == schema.VERSION_NONE
    await dbm.ensure_self_update()
    await run_updates_and_verify(get_columns_in_db_table, dbm, 0)


@pytest.mark.asyncio
async def test_dbschema_unclean(postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db):
    dbm = schema.DBSchema("test", inmanta.db.versions, postgresql_client)
    current_db_version = await dbm.ensure_self_update()
    assert current_db_version == 0

    await dbm.set_current_version(5)
    current_db_version = await dbm.get_current_version()
    assert current_db_version == 5

    assert current_db_version == 5
    await run_updates_and_verify(get_columns_in_db_table, dbm, 5)


@pytest.mark.asyncio
async def test_dbschema_update_legacy_1(postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db):
    await postgresql_client.execute(
        """
-- Table: public.schemaversion
CREATE TABLE IF NOT EXISTS public.schemaversion(
    id uuid PRIMARY KEY,
    current_version integer NOT NULL UNIQUE
);
"""
    )
    dbm = schema.DBSchema("test", inmanta.db.versions, postgresql_client)
    current_db_version = await dbm.get_legacy_version()
    assert current_db_version == schema.VERSION_LEGACY
    await dbm.ensure_self_update()
    await run_updates_and_verify(get_columns_in_db_table, dbm, 0)


@pytest.mark.asyncio
async def test_dbschema_update_legacy_2(postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db):
    await postgresql_client.execute(
        """
-- Table: public.schemaversion
CREATE TABLE IF NOT EXISTS public.schemaversion(
    id uuid PRIMARY KEY,
    current_version integer NOT NULL UNIQUE
);
"""
    )
    await postgresql_client.execute("INSERT INTO public.schemaversion(id, current_version) VALUES ($1, $2);", uuid.uuid4(), 1)

    dbm = schema.DBSchema(CORE_NAME, inmanta.db.versions, postgresql_client)
    current_db_version = await dbm.get_legacy_version()
    assert current_db_version == 1
    await dbm.ensure_self_update()
    await run_updates_and_verify(get_columns_in_db_table, dbm, 1)


@pytest.mark.asyncio
async def test_dbschema_update_db_schema(postgresql_client, init_dataclasses_and_load_schema, get_columns_in_db_table):
    db_schema = schema.DBSchema("tes1t", inmanta.db.versions, postgresql_client)

    await run_updates_and_verify(get_columns_in_db_table, db_schema, 0)

    db_schema = schema.DBSchema(CORE_NAME, inmanta.db.versions, postgresql_client)

    await run_updates_and_verify(get_columns_in_db_table, db_schema, prefix="C")


@pytest.mark.asyncio
async def test_dbschema_update_db_schema_failure(postgresql_client, init_dataclasses_and_load_schema, get_columns_in_db_table):
    db_schema = schema.DBSchema("test2", inmanta.db.versions, postgresql_client)

    async def update_function(connection):
        # Syntax error should trigger database rollback
        await connection.execute("CREATE TABE public.tab(id integer primary key, val varchar NOT NULL);")

    current_db_version = await db_schema.get_current_version()
    new_db_version = current_db_version + 1
    update_function_map = [Version(f"v{new_db_version}", update_function)]

    with pytest.raises(PostgresSyntaxError):
        await db_schema._update_db_schema(update_function_map)

    # Assert rollback
    assert (await db_schema.get_current_version()) == current_db_version
    assert (
        await postgresql_client.fetchval(
            "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name='tab'"
        )
    ) is None

    async def update_function2(connection):
        # Fix syntax issue
        await connection.execute("CREATE TABLE public.tab(id integer primary key, val varchar NOT NULL);")

    update_function_map = [Version(f"v{new_db_version}", update_function2)]
    await db_schema._update_db_schema(update_function_map)

    # Assert update
    assert (await db_schema.get_current_version()) == new_db_version
    assert sorted(["id", "val"]) == sorted(await get_columns_in_db_table("tab"))


def make_version(nr, fct):
    return Version(f"v{nr}", fct)


def make_versions(idx, *fcts):
    return [make_version(idx + i, fct) for i, fct in enumerate(fcts)]


@pytest.mark.asyncio
async def test_dbschema_partial_update_db_schema_failure(
    postgresql_client, init_dataclasses_and_load_schema, get_columns_in_db_table
):
    db_schema = schema.DBSchema("test3", inmanta.db.versions, postgresql_client)

    async def update_function_good(connection):
        # Fix syntax issue
        await connection.execute("CREATE TABLE public.taba(id integer primary key, val varchar NOT NULL);")

    async def update_function_bad(connection):
        # Syntax error should trigger database rollback
        await connection.execute("CREATE TABLE public.tabb(id integer primary key, val varchar NOT NULL);")
        await connection.execute("CREATE TABE public.tab(id integer primary key, val varchar NOT NULL);")

    async def update_function_good2(connection):
        # Fix syntax issue
        await connection.execute("CREATE TABLE public.tabc(id integer primary key, val varchar NOT NULL);")

    current_db_version = await db_schema.get_current_version()

    update_function_map = make_versions(
        current_db_version + 1, update_function_good, update_function_bad, update_function_good2
    )

    with pytest.raises(PostgresSyntaxError):
        await db_schema._update_db_schema(update_function_map)

    # Assert rollback
    assert (await db_schema.get_current_version()) == current_db_version + 1
    assert (
        await postgresql_client.fetchval(
            "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name='taba'"
        )
    ) is not None

    assert (
        await postgresql_client.fetchval(
            "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name='tabb'"
        )
    ) is None

    assert (
        await postgresql_client.fetchval(
            "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name='tabc'"
        )
    ) is None


@pytest.mark.asyncio
async def test_dbschema_get_dct_with_update_functions():
    module_names = [modname for _, modname, ispkg in pkgutil.iter_modules(data.PACKAGE_WITH_UPDATE_FILES.__path__) if not ispkg]
    all_versions = [int(mod_name[1:]) for mod_name in module_names]

    db_schema = schema.DBSchema(CORE_NAME, data.PACKAGE_WITH_UPDATE_FILES, None)
    update_function_map = await db_schema._get_update_functions()
    assert sorted(all_versions) == [v.version for v in update_function_map]
    for version in update_function_map:
        assert version.version >= 0
        assert isinstance(version.function, types.FunctionType)
        assert version.function.__name__ == "update"
        assert inspect.getfullargspec(version.function)[0] == ["connection"]
