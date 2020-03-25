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
import asyncio
import inspect
import logging
import pkgutil
import types
import uuid
from asyncio import Semaphore
from typing import Optional

import asyncpg
import pytest
from asyncpg import PostgresSyntaxError

import inmanta.db.versions
from data.db import versions
from data.db_with_invalid_versions import invalid_versions
from inmanta import data
from inmanta.data import CORE_SCHEMA_NAME, schema
from inmanta.data.schema import InvalidSchemaVersion, TableNotFound, Version, create_schemamanager
from utils import log_contains


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


async def get_core_version(postgresql_client):
    dbm = schema.DBSchema(CORE_SCHEMA_NAME, inmanta.db.versions, postgresql_client)
    try:
        return await dbm.get_current_version()
    except TableNotFound:
        return 0


async def assert_core_untouched(postgresql_client, corev=0):
    """
    Verify abscence of side-effect leaks to other cases
    """
    dbm = schema.DBSchema(CORE_SCHEMA_NAME, inmanta.db.versions, postgresql_client)
    current_db_version = await dbm.get_current_version()
    assert current_db_version == corev


@pytest.mark.asyncio
async def test_dbschema_clean(postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db, caplog):
    with caplog.at_level(logging.INFO):
        dbm = schema.DBSchema("test_dbschema_clean", inmanta.db.versions, postgresql_client)
        with pytest.raises(TableNotFound):
            await dbm.get_current_version()
        await dbm.ensure_self_update()
        await run_updates_and_verify(get_columns_in_db_table, dbm, 0)
        await assert_core_untouched(postgresql_client)

        log_contains(caplog, "inmanta.data.schema.schema:test_dbschema_clean", logging.INFO, "Creating schema version table")


@pytest.mark.asyncio
async def test_dbschema_unclean(postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db):
    dbm = schema.DBSchema("test_dbschema_unclean", inmanta.db.versions, postgresql_client)
    current_db_version = await dbm.ensure_self_update()
    assert current_db_version == 0

    await dbm.set_current_version(5)
    current_db_version = await dbm.get_current_version()
    assert current_db_version == 5

    await run_updates_and_verify(get_columns_in_db_table, dbm, current_db_version)
    await assert_core_untouched(postgresql_client)


@pytest.mark.asyncio
async def test_dbschema_update_legacy_1(
    postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db, hard_clean_db_post
):
    await postgresql_client.execute(
        """
-- Table: public.schemaversion
CREATE TABLE IF NOT EXISTS public.schemaversion(
    id uuid PRIMARY KEY,
    current_version integer NOT NULL UNIQUE
);
"""
    )
    dbm = schema.DBSchema("test_l1", inmanta.db.versions, postgresql_client)
    current_db_version = await dbm.get_legacy_version()
    assert current_db_version == 0
    await dbm.ensure_self_update()
    await run_updates_and_verify(get_columns_in_db_table, dbm, current_db_version)


@pytest.mark.asyncio
async def test_dbschema_update_legacy_2(
    postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db, hard_clean_db_post
):
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

    dbm = schema.DBSchema(CORE_SCHEMA_NAME, inmanta.db.versions, postgresql_client)
    current_db_version = await dbm.get_legacy_version()
    assert current_db_version == 1
    await dbm.ensure_self_update()
    await run_updates_and_verify(get_columns_in_db_table, dbm, current_db_version)


@pytest.mark.asyncio
async def test_dbschema_update_db_schema(postgresql_client, get_columns_in_db_table, hard_clean_db, hard_clean_db_post):

    db_schema = schema.DBSchema("test_dbschema_update_db_schema", inmanta.db.versions, postgresql_client)
    await db_schema.ensure_self_update()

    await run_updates_and_verify(get_columns_in_db_table, db_schema, 0)

    db_schema = schema.DBSchema("test_dbschema_update_db_schema_1", inmanta.db.versions, postgresql_client)

    await run_updates_and_verify(get_columns_in_db_table, db_schema, 0, prefix="C")


@pytest.mark.asyncio
async def test_dbschema_update_db_schema_failure(postgresql_client, get_columns_in_db_table):
    corev = await get_core_version(postgresql_client)
    db_schema = schema.DBSchema("test_dbschema_update_db_schema_failure", inmanta.db.versions, postgresql_client)
    await db_schema.ensure_self_update()

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
    await assert_core_untouched(postgresql_client, corev)


def make_version(nr, fct):
    return Version(f"v{nr}", fct)


def make_versions(idx, *fcts):
    return [make_version(idx + i, fct) for i, fct in enumerate(fcts)]


@pytest.mark.asyncio
async def test_dbschema_partial_update_db_schema_failure(postgresql_client, get_columns_in_db_table):
    corev = await get_core_version(postgresql_client)
    db_schema = schema.DBSchema("test_dbschema_partial_update_db_schema_failure", inmanta.db.versions, postgresql_client)
    await db_schema.ensure_self_update()

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
    if current_db_version is None:
        current_db_version = 0

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

    await assert_core_untouched(postgresql_client, corev)


@pytest.mark.asyncio
async def test_dbschema_get_dct_with_update_functions():
    module_names = [modname for _, modname, ispkg in pkgutil.iter_modules(data.PACKAGE_WITH_UPDATE_FILES.__path__) if not ispkg]
    for module_name in module_names:
        module = __import__(data.PACKAGE_WITH_UPDATE_FILES.__name__ + "." + module_name, fromlist=["update"])
        if module.DISABLED:
            module_names.remove(module_name)
    all_versions = [int(mod_name[1:]) for mod_name in module_names]

    db_schema = schema.DBSchema(CORE_SCHEMA_NAME, data.PACKAGE_WITH_UPDATE_FILES, None)
    update_function_map = await db_schema._get_update_functions()
    assert sorted(all_versions) == [v.version for v in update_function_map]
    for version in update_function_map:
        assert version.version >= 0
        assert isinstance(version.function, types.FunctionType)
        assert version.function.__name__ == "update"
        assert inspect.getfullargspec(version.function)[0] == ["connection"]


@pytest.mark.asyncio
async def test_multi_upgrade_lockout(postgresql_pool, get_columns_in_db_table, hard_clean_db):
    async with postgresql_pool.acquire() as postgresql_client:
        async with postgresql_pool.acquire() as postgresql_client2:

            # schedule 3 updates, hang on second, unblock one, verify, unblock other, verify
            corev = await get_core_version(postgresql_client)

            db_schema = schema.DBSchema("test_multi_upgrade_lockout", inmanta.db.versions, postgresql_client)
            db_schema2 = schema.DBSchema("test_multi_upgrade_lockout", inmanta.db.versions, postgresql_client2)
            await db_schema.ensure_self_update()

            lock = Semaphore(0)

            async def update_function_a(connection):
                # Fix syntax issue
                await connection.execute("CREATE TABLE public.taba(id integer primary key, val varchar NOT NULL);")

            async def update_function_b(connection):
                # Syntax error should trigger database rollback
                await lock.acquire()
                await connection.execute("CREATE TABLE public.tabb(id integer primary key, val varchar NOT NULL);")

            async def update_function_c(connection):
                # Fix syntax issue
                await connection.execute("CREATE TABLE public.tabc(id integer primary key, val varchar NOT NULL);")

            current_db_version = await db_schema.get_current_version()
            if current_db_version is None:
                current_db_version = 0

            update_function_map = make_versions(current_db_version + 1, update_function_a, update_function_b, update_function_c)

            r1 = asyncio.ensure_future(db_schema._update_db_schema(update_function_map))
            r2 = asyncio.ensure_future(db_schema2._update_db_schema(update_function_map))

            both = asyncio.as_completed([r1, r2]).__iter__()

            await asyncio.sleep(0.1)
            first = next(both)
            lock.release()
            await first

            # second one doesn't even hit the lock, as it never sees schema version 0
            # lock.release()
            second = next(both)
            await second

            # Assert done
            assert (await db_schema.get_current_version()) == current_db_version + 3
            assert (
                await postgresql_client.fetchval(
                    "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name='taba'"
                )
            ) is not None

            assert (
                await postgresql_client.fetchval(
                    "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name='tabb'"
                )
            ) is not None

            assert (
                await postgresql_client.fetchval(
                    "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name='tabc'"
                )
            ) is not None

            await assert_core_untouched(postgresql_client, corev)


@pytest.mark.asyncio
async def test_dbschema_get_dct_filter_disabled():
    db_schema = schema.DBSchema(CORE_SCHEMA_NAME, versions, None)
    update_function_map = await db_schema._get_update_functions()
    assert 2 not in [v.version for v in update_function_map]
    for version in update_function_map:
        assert version.version >= 0
        assert isinstance(version.function, types.FunctionType)
        assert version.function.__name__ == "update"
        assert inspect.getfullargspec(version.function)[0] == ["connection"]


@pytest.mark.asyncio
async def test_dbschema_update_db_downgrade(postgresql_client):
    schema_name = "test_dbschema_update_db_downgrade"
    SCHEMA_VERSION_TABLE = "schemamanager"
    await postgresql_client.execute(create_schemamanager)

    db_schema = schema.DBSchema(schema_name, inmanta.db.versions, postgresql_client)
    update_function_map = await db_schema._get_update_functions()
    original_version = len(update_function_map) + 1
    await postgresql_client.execute(
        f"INSERT INTO {SCHEMA_VERSION_TABLE} (name, current_version) VALUES ($1, $2)", schema_name, original_version
    )
    with pytest.raises(InvalidSchemaVersion):
        await db_schema.ensure_db_schema()
    current_db_version = await db_schema.get_current_version()
    assert original_version == current_db_version


@pytest.mark.asyncio
async def test_dbschema_get_dct_filter_invalid_names(caplog):
    db_schema = schema.DBSchema(CORE_SCHEMA_NAME, invalid_versions, None)
    update_function_map = await db_schema._get_update_functions()
    assert len(update_function_map) == 0
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "V2 doesn't match the expected pattern")
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "ver1 doesn't match the expected pattern")
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "ver1a doesn't match the expected pattern")
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "version3 doesn't match the expected pattern")
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "v1b doesn't match the expected pattern")
