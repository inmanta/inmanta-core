import pytest
import asyncpg

SCHEMA_FILE="pg_schema.sql"


@pytest.fixture
async def postgresql_client(postgresql_proc):
    connection = await asyncpg.connect('postgresql://%s@%s:%d/' % (postgresql_proc.user, postgresql_proc.host, postgresql_proc.port))
    yield connection
    await connection.close()

@pytest.fixture(scope="function", autouse=True)
async def reset(postgresql_client):
    await _drop_all_tables(postgresql_client)
    yield
    await _drop_all_tables(postgresql_client)

async def _drop_all_tables(postgresql_client):
    await postgresql_client.execute("DROP SCHEMA public CASCADE")
    await postgresql_client.execute("CREATE SCHEMA public")

@pytest.mark.asyncio
async def test_postgres_client(postgresql_client):
    await postgresql_client.execute("CREATE TABLE test(id serial PRIMARY KEY, name VARCHAR (25) NOT NULL)")
    await postgresql_client.execute("INSERT INTO test VALUES(5, 'jef')")
    records = await postgresql_client.fetch("SELECT * FROM test")
    assert len(records) == 1
    first_record = records[0]
    assert first_record['id'] == 5
    assert first_record['name'] == "jef"
    await postgresql_client.execute("DELETE FROM test WHERE test.id = " + str(first_record['id']))
    records = await postgresql_client.fetch("SELECT * FROM test")
    assert len(records) == 0

@pytest.mark.asyncio
async def test_load_schema(postgresql_client):
    import re
    prog = re.compile('.*; *')
    with open(SCHEMA_FILE, 'r') as f:
        query = ""
        for line in f:
            if line and not line.startswith("--"):
                line = line.strip('\n ')
                query += line
            if re.match(prog, query):
                print(query)
                await postgresql_client.execute(query)
                query = ""

