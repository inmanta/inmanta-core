import pytest
import asyncpg


async def postgresql_client(postgresql_proc):
    connection = await asyncpg.connect('postgresql://%s@%s:%d/' % (postgresql_proc.user, postgresql_proc.host, postgresql_proc.port))
    return connection

@pytest.mark.gen_test
def test_postgres_client2(postgresql_proc):
    connection = yield postgresql_client(postgresql_proc)
    yield connection.execute("CREATE database testx")
    yield connection.close()
