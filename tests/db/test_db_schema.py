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
from asyncio import Semaphore
from typing import Optional, Set

import asyncpg
import pytest
from asyncpg import PostgresSyntaxError

import inmanta.db.versions
from data.db import versions
from data.db_with_invalid_versions import invalid_versions
from inmanta import data
from inmanta.data import CORE_SCHEMA_NAME, schema
from inmanta.data.schema import TableNotFound, Version
from utils import log_contains


async def run_updates_and_verify(
    get_columns_in_db_table, schema_manager: schema.DBSchema, current: Optional[Set[int]] = None, prefix: str = ""
):
    async def update_function1(connection):
        await connection.execute(f"CREATE TABLE public.{prefix}tab(id integer primary key, val varchar NOT NULL);")

    async def update_function2(connection):
        await connection.execute(f"ALTER TABLE public.{prefix}tab ADD COLUMN mycolumn varchar;")

    async def update_function3(connection):
        await connection.execute(f"ALTER TABLE public.{prefix}tab DROP COLUMN val;")

    current_db_versions: Set[int] = await schema_manager.get_installed_versions()
    assert current is None or current_db_versions == current
    latest_version: int = max(current_db_versions) if len(current_db_versions) > 0 else 0
    update_function_map = [
        Version(f"v{latest_version + 1}", update_function1),
        Version(f"v{latest_version + 3}", update_function3),
    ]

    await schema_manager._update_db_schema(update_function_map)

    assert (await schema_manager.get_installed_versions()) == current_db_versions.union({latest_version + i for i in (1, 3)})
    assert set(await get_columns_in_db_table(f"{prefix}tab")) == {"id"}

    await schema_manager._update_db_schema([*update_function_map, Version(f"v{latest_version + 2}", update_function2)])
    assert (await schema_manager.get_installed_versions()) == current_db_versions.union({latest_version + i for i in (1, 2, 3)})
    assert set(await get_columns_in_db_table(f"{prefix}tab")) == {"id", "mycolumn"}


async def get_core_versions(postgresql_client) -> Set[int]:
    dbm = schema.DBSchema(CORE_SCHEMA_NAME, inmanta.db.versions, postgresql_client)
    try:
        return await dbm.get_installed_versions()
    except TableNotFound:
        return set()


async def assert_core_untouched(postgresql_client, corev: Optional[Set[int]] = None):
    """
    Verify abscence of side-effect leaks to other cases
    """
    if corev is None:
        corev = set()
    dbm = schema.DBSchema(CORE_SCHEMA_NAME, inmanta.db.versions, postgresql_client)
    current_db_versions = await dbm.get_installed_versions()
    assert current_db_versions == corev


@pytest.mark.asyncio
async def test_dbschema_clean(postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db, caplog):
    with caplog.at_level(logging.INFO):
        dbm = schema.DBSchema("test_dbschema_clean", inmanta.db.versions, postgresql_client)
        with pytest.raises(TableNotFound):
            await dbm.get_installed_versions()
        await dbm.ensure_self_update()
        await run_updates_and_verify(get_columns_in_db_table, dbm, set())
        await assert_core_untouched(postgresql_client)

        log_contains(caplog, "inmanta.data.schema.schema:test_dbschema_clean", logging.INFO, "Creating schema version table")


@pytest.mark.asyncio
async def test_dbschema_unclean(postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db):
    dbm = schema.DBSchema("test_dbschema_unclean", inmanta.db.versions, postgresql_client)
    await dbm.ensure_self_update()
    assert await dbm.get_installed_versions() == set()

    await dbm.set_installed_version(5)
    current_versions: Set[int] = await dbm.get_installed_versions()
    assert current_versions == {5}

    await run_updates_and_verify(get_columns_in_db_table, dbm, current_versions)
    await assert_core_untouched(postgresql_client)


@pytest.mark.asyncio
async def test_dbschema_update_legacy_1(
    postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db, hard_clean_db_post
):
    await postgresql_client.execute(
        """
-- Table: public.schemamanager
CREATE TABLE IF NOT EXISTS public.schemamanager(
    name varchar PRIMARY KEY,
    current_version integer NOT NULL
);
"""
    )
    dbm = schema.DBSchema("test_l1", inmanta.db.versions, postgresql_client)
    assert set(await get_columns_in_db_table("schemamanager")) == {"name", "current_version"}
    await dbm._legacy_migration_table()
    assert set(await get_columns_in_db_table("schemamanager")) == {"name", "legacy_version", "installed_versions"}
    current_db_version = await dbm.get_legacy_version()
    assert current_db_version == 0
    await dbm._legacy_migration_row({0, 1, 2})
    await run_updates_and_verify(get_columns_in_db_table, dbm, set())


@pytest.mark.asyncio
async def test_dbschema_update_legacy_2(
    postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db, hard_clean_db_post
):
    await postgresql_client.execute(
        """
-- Table: public.schemamanager
CREATE TABLE IF NOT EXISTS public.schemamanager(
    name varchar PRIMARY KEY,
    current_version integer NOT NULL
);
"""
    )
    await postgresql_client.execute("INSERT INTO public.schemamanager(name, current_version) VALUES ($1, $2);", "myslice", 1)

    dbm = schema.DBSchema("myslice", inmanta.db.versions, postgresql_client)
    await dbm._legacy_migration_table()
    current_db_version = await dbm.get_legacy_version()
    assert current_db_version == 1
    await dbm._legacy_migration_row({0, 1, 2, 3})
    await run_updates_and_verify(get_columns_in_db_table, dbm, {0, 1})


@pytest.mark.asyncio
async def test_dbschema_update_legacy_contained(
    postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db, hard_clean_db_post
):
    """
    Verify that the legacy row migration is contained to the instance it is called on.
    """
    await postgresql_client.execute(
        """
-- Table: public.schemamanager
CREATE TABLE IF NOT EXISTS public.schemamanager(
    name varchar PRIMARY KEY,
    current_version integer NOT NULL
);
"""
    )
    await postgresql_client.execute("INSERT INTO public.schemamanager(name, current_version) VALUES ($1, $2);", "myslice", 1)
    await postgresql_client.execute("INSERT INTO public.schemamanager(name, current_version) VALUES ($1, $2);", "otherslice", 3)
    dbm1 = schema.DBSchema("myslice", versions, postgresql_client)
    dbm2 = schema.DBSchema("otherslice", versions, postgresql_client)
    await dbm1.ensure_self_update()
    assert await dbm1.get_legacy_version() == 1
    assert await dbm1.get_installed_versions() == {1}
    assert await dbm2.get_legacy_version() == 3
    assert await dbm2.get_installed_versions() == set()
    await dbm2.ensure_self_update()
    assert await dbm1.get_legacy_version() == 1
    assert await dbm1.get_installed_versions() == {1}
    assert await dbm2.get_legacy_version() == 3
    assert await dbm2.get_installed_versions() == {1, 3}


@pytest.mark.asyncio
async def test_dbschema_update_legacy_table_concurrent(
    postgres_db, database_name, get_columns_in_db_table, hard_clean_db, hard_clean_db_post
):
    """
    Verify that no conflicts arise from multiple concurrent processes trying to migrate from the legacy table.
    """
    client1 = await asyncpg.connect(host=postgres_db.host, port=postgres_db.port, user=postgres_db.user, database=database_name)
    client2 = await asyncpg.connect(host=postgres_db.host, port=postgres_db.port, user=postgres_db.user, database=database_name)
    await client1.execute(
        """
-- Table: public.schemamanager
CREATE TABLE IF NOT EXISTS public.schemamanager(
    name varchar PRIMARY KEY,
    current_version integer NOT NULL
);
"""
    )
    dbm1 = schema.DBSchema("myslice", inmanta.db.versions, client1)
    dbm2 = schema.DBSchema("otherslice", inmanta.db.versions, client2)
    assert set(await get_columns_in_db_table("schemamanager")) == {"name", "current_version"}
    await asyncio.gather(
        dbm1._legacy_migration_table(),
        dbm2._legacy_migration_table(),
    )
    assert set(await get_columns_in_db_table("schemamanager")) == {"name", "legacy_version", "installed_versions"}
    assert await dbm1.get_installed_versions() == set()
    assert await dbm2.get_installed_versions() == set()


@pytest.mark.asyncio
async def test_dbschema_ensure_self_update(
    postgresql_client: asyncpg.Connection, get_columns_in_db_table, hard_clean_db, hard_clean_db_post
):
    await postgresql_client.execute(
        """
-- Table: public.schemamanager
CREATE TABLE IF NOT EXISTS public.schemamanager(
    name varchar PRIMARY KEY,
    current_version integer NOT NULL
);
"""
    )
    await postgresql_client.execute("INSERT INTO public.schemamanager(name, current_version) VALUES ($1, $2);", "myslice", 3)
    dbm = schema.DBSchema("myslice", versions, postgresql_client)
    await dbm.ensure_self_update()
    assert await dbm.get_installed_versions() == {1, 3}
    # make sure legacy update gets executed only once
    await postgresql_client.execute("UPDATE public.schemamanager SET legacy_version=$1 WHERE name=$2", 2, "myslice")
    dbm.ensure_self_update()
    assert await dbm.get_installed_versions() == {1, 3}


@pytest.mark.asyncio
async def test_dbschema_update_db_schema(postgresql_client, get_columns_in_db_table, hard_clean_db, hard_clean_db_post):

    db_schema = schema.DBSchema("test_dbschema_update_db_schema", inmanta.db.versions, postgresql_client)
    await db_schema.ensure_self_update()

    await run_updates_and_verify(get_columns_in_db_table, db_schema, set())

    db_schema = schema.DBSchema("test_dbschema_update_db_schema_1", inmanta.db.versions, postgresql_client)

    await run_updates_and_verify(get_columns_in_db_table, db_schema, set(), prefix="c")


@pytest.mark.asyncio
async def test_dbschema_update_db_schema_failure(postgresql_client, get_columns_in_db_table):
    corev: Set[int] = await get_core_versions(postgresql_client)
    db_schema = schema.DBSchema("test_dbschema_update_db_schema_failure", inmanta.db.versions, postgresql_client)
    await db_schema.ensure_self_update()

    async def update_function(connection):
        # Syntax error should trigger database rollback
        await connection.execute("CREATE TABE public.tab(id integer primary key, val varchar NOT NULL);")

    current_db_versions: Set[int] = await db_schema.get_installed_versions()
    assert len(current_db_versions) == 0
    new_db_version = 1
    update_function_map = [Version(f"v{new_db_version}", update_function)]

    with pytest.raises(PostgresSyntaxError):
        await db_schema._update_db_schema(update_function_map)

    # Assert rollback
    assert (await db_schema.get_installed_versions()) == current_db_versions
    assert (
        await postgresql_client.fetchval(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='tab'"
        )
    ) is None

    async def update_function2(connection):
        # Fix syntax issue
        await connection.execute("CREATE TABLE public.tab(id integer primary key, val varchar NOT NULL);")

    update_function_map = [Version(f"v{new_db_version}", update_function2)]
    await db_schema._update_db_schema(update_function_map)

    # Assert update
    assert (await db_schema.get_installed_versions()) == current_db_versions.union({new_db_version})
    assert sorted(["id", "val"]) == sorted(await get_columns_in_db_table("tab"))
    await assert_core_untouched(postgresql_client, corev)


def make_version(nr, fct):
    return Version(f"v{nr}", fct)


def make_versions(idx, *fcts):
    return [make_version(idx + i, fct) for i, fct in enumerate(fcts)]


@pytest.mark.asyncio
async def test_dbschema_partial_update_db_schema_failure(postgresql_client, get_columns_in_db_table):
    corev: Set[int] = await get_core_versions(postgresql_client)
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

    current_db_versions: Set[int] = await db_schema.get_installed_versions()
    assert len(current_db_versions) == 0

    update_function_map = make_versions(1, update_function_good, update_function_bad, update_function_good2)

    with pytest.raises(PostgresSyntaxError):
        await db_schema._update_db_schema(update_function_map)

    # Assert full rollback
    assert (await db_schema.get_installed_versions()) == set()
    assert (
        await postgresql_client.fetchval(
            "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name='taba'"
        )
    ) is None

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


def test_dbschema_get_dct_with_update_functions():
    module_names = [modname for _, modname, ispkg in pkgutil.iter_modules(data.PACKAGE_WITH_UPDATE_FILES.__path__) if not ispkg]
    for module_name in module_names:
        module = __import__(data.PACKAGE_WITH_UPDATE_FILES.__name__ + "." + module_name, fromlist=["update"])
        if module.DISABLED:
            module_names.remove(module_name)
    all_versions = [int(mod_name[1:]) for mod_name in module_names]

    db_schema = schema.DBSchema(CORE_SCHEMA_NAME, data.PACKAGE_WITH_UPDATE_FILES, None)
    update_function_map = db_schema._get_update_functions()
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
            corev: Set[int] = await get_core_versions(postgresql_client)

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

            current_db_versions: Set[int] = await db_schema.get_installed_versions()
            assert len(current_db_versions) == 0

            update_function_map = make_versions(1, update_function_a, update_function_b, update_function_c)

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
            assert (await db_schema.get_installed_versions()) == {1, 2, 3}
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
    update_function_map = db_schema._get_update_functions()
    assert {v.version for v in update_function_map} == {1, 3}
    for version in update_function_map:
        assert version.version >= 0
        assert isinstance(version.function, types.FunctionType)
        assert version.function.__name__ == "update"
        assert inspect.getfullargspec(version.function)[0] == ["connection"]


@pytest.mark.asyncio
async def test_dbschema_get_dct_filter_invalid_names(caplog):
    db_schema = schema.DBSchema(CORE_SCHEMA_NAME, invalid_versions, None)
    update_function_map = db_schema._get_update_functions()
    assert len(update_function_map) == 0
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "V2 doesn't match the expected pattern")
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "ver1 doesn't match the expected pattern")
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "ver1a doesn't match the expected pattern")
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "version3 doesn't match the expected pattern")
    log_contains(caplog, "inmanta.data.schema", logging.WARNING, "v1b doesn't match the expected pattern")
