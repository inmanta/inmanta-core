"""
    Copyright 2022 Inmanta

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
from asyncio import Event

"""
This module contains tests related to PostgreSQL and how we interact with it. Its purpose is to verify PostgreSQL internals,
especially those that are not explicitly documented anywhere. These tests act both as a confidence check for compatibility with
future PostgreSQL versions and as a knowledge collector to refer back to when we need it.
"""
import asyncio
from collections import abc

import asyncpg
import pytest


@pytest.mark.slowtest
async def test_postgres_cascade_locking_order(postgresql_pool, run_without_keeping_psql_logs) -> None:
    """
    Verifies that Postgres' cascade deletion acquires locks top-down. This is important because in order to avoid deadlocks
    we define a corresponding locking order for all transactions. See `TableLockMode`, `RowLockMode` and `ConfigurationModel`
    docstrings in `inmanta.data`.
    """
    async with postgresql_pool.acquire() as connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS root (name varchar PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS leaf (
                name varchar PRIMARY KEY,
                myroot varchar REFERENCES root(name) ON DELETE CASCADE
            );
            """
        )

    async def insert():
        async with postgresql_pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO root VALUES
                    ('root1');

                INSERT INTO leaf VALUES
                    ('leaf1', 'root1'),
                    ('leaf2', 'root1');
                """
            )

    async def lock_top_down():
        async with postgresql_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("LOCK TABLE root IN SHARE MODE")
                await asyncio.sleep(0.1)
                await connection.execute("LOCK TABLE leaf IN SHARE MODE")

    async def lock_bottom_up():
        async with postgresql_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("LOCK TABLE leaf IN SHARE MODE")
                await asyncio.sleep(0.1)
                await connection.execute("LOCK TABLE root IN SHARE MODE")

    async def delete():
        async with postgresql_pool.acquire() as connection:
            async with connection.transaction():
                await asyncio.sleep(0.05)
                await connection.execute("DELETE FROM root")

    await insert()
    await asyncio.gather(
        lock_top_down(),
        delete(),
    )

    await insert()
    with pytest.raises(asyncpg.DeadlockDetectedError):
        await asyncio.gather(
            lock_bottom_up(),
            delete(),
        )


@pytest.mark.slowtest
@pytest.mark.parametrize("definition_order_one_two", [True, False])
async def test_postgres_cascade_locking_order_siblings(
    postgresql_pool, definition_order_one_two: bool, run_without_keeping_psql_logs
) -> None:
    """
    Verifies locking order for siblings in the cascade tree. Locking order seems to be based on definition order of the
    referencing columns. Locking order may shift in case of updates to the definition of these columns.
    """
    leaf_definitions: tuple[str] = tuple(
        f"CREATE TABLE IF NOT EXISTS {name} (name varchar PRIMARY KEY, myroot varchar REFERENCES root(name) ON DELETE CASCADE);"
        for name in ("leafone", "leaftwo")
    )
    async with postgresql_pool.acquire() as connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS root (name varchar PRIMARY KEY);
            %s
            %s
            """
            % (leaf_definitions if definition_order_one_two else tuple(reversed(leaf_definitions)))
        )

    async def insert():
        async with postgresql_pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO root VALUES
                    ('root1');

                INSERT INTO leafone VALUES
                    ('leafone1', 'root1'),
                    ('leafone2', 'root1');

                INSERT INTO leaftwo VALUES
                    ('leaftwo1', 'root1'),
                    ('leaftwo2', 'root1');
                """
            )

    async def lock_one_two():
        async with postgresql_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("LOCK TABLE leafone IN SHARE MODE")
                await asyncio.sleep(0.1)
                await connection.execute("LOCK TABLE leaftwo IN SHARE MODE")

    async def lock_two_one():
        async with postgresql_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("LOCK TABLE leaftwo IN SHARE MODE")
                await asyncio.sleep(0.1)
                await connection.execute("LOCK TABLE leafone IN SHARE MODE")

    async def delete():
        async with postgresql_pool.acquire() as connection:
            async with connection.transaction():
                await asyncio.sleep(0.05)
                await connection.execute("DELETE FROM root")

    success: abc.Awaitable[None] = lock_one_two() if definition_order_one_two else lock_two_one()
    deadlock: abc.Awaitable[None] = lock_two_one() if definition_order_one_two else lock_one_two()

    # always do successful first so we don't need to deal with cleanup after deadlock
    await insert()
    await asyncio.gather(
        success,
        delete(),
    )

    await insert()
    with pytest.raises(asyncpg.DeadlockDetectedError):
        await asyncio.gather(
            deadlock,
            delete(),
        )


@pytest.mark.slowtest
async def test_postgres_transaction_re_entry(postgresql_pool) -> None:
    """
    When do transaction lock each other out?

    More specifically, how to make the release_version method lock itself out.
    """

    # Make a table
    async with postgresql_pool.acquire() as connection:
        await connection.execute("CREATE TABLE IF NOT EXISTS root (name varchar PRIMARY KEY, released BOOL);")
        await connection.execute(
            """
            INSERT INTO root VALUES
                ('root1', False),
                ('root2', False);
            """
        )

    async def update_root(name: str, lock: Event):
        # Main routine: lock table and update if required
        # there is lock given as an argument to make sure we can make one wait for the other
        async with postgresql_pool.acquire() as connection:
            async with connection.transaction():
                print(f"{name}: ENTER")
                # for update is the key here!!!
                record = await connection.fetchrow("select released from root where name=$1 for update", "root1")
                print(f"{name}: WAIT")
                await lock.wait()
                assert len(record) == 1
                if record[0] is True:
                    return False
                print(f"{name}: UPDATE")
                await connection.execute("UPDATE root SET released=true where name=$1", "root1")
                return True
        print(f"{name}: COMMITTED")

    # Two locks
    l1 = Event()
    l2 = Event()

    # Two task running
    f1 = asyncio.create_task(update_root("1", l1))
    f2 = asyncio.create_task(update_root("2", l2))

    # Sleep a bit to get them to lock up
    await asyncio.sleep(0.1)
    # Unlock
    l2.set()
    l1.set()

    # get results
    r1 = await f1
    r2 = await f2

    # One should return true, the other false
    print(r1, r2)
    assert r1 + r2 == 1
