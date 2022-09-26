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

"""
This module contains tests related to PostgreSQL and how we interact with it. Its purpose is to verify PostgreSQL internals,
especially those that are not explicitly documented anywhere. These tests act both as a confidence check for compatibility with
future PostgreSQL versions and as a knowledge collector to refer back to when we need it.
"""
import asyncio

import asyncpg
import pytest


async def test_postgres_cascade_locking_order(postgresql_pool) -> None:
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
