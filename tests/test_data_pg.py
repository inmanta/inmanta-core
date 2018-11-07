import pytest
import asyncpg


@pytest.fixture
async def postgresql_client(postgresql_proc):
    connection = await asyncpg.connect('postgresql://%s@%s:%d/' % (postgresql_proc.user, postgresql_proc.host, postgresql_proc.port))
    yield connection
    await connection.close()

@pytest.mark.asyncio
async def test_postgres_client2(postgresql_client):
    await postgresql_client.execute("CREATE database testx")
