import asyncio
import asyncpg

import pytest


async def test_postgres_cascade(postgresql_pool) -> None:
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


# TODO: add tests for known deadlocks
