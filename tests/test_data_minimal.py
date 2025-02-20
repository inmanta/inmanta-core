from inmanta import data
import pytest

from inmanta.data import get_connection_ctx_mgr, ArgumentCollector


async def test_environment_no_environment_name(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    with pytest.raises(AttributeError):
        data.Environment(project=project.id, repo_url="", repo_branch="")


async def test_environment_no_project_id(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    with pytest.raises(AttributeError):
        data.Environment(name="dev", repo_url="", repo_branch="")


async def test_connect_default_parameters(sql_alchemy_engine):
    assert sql_alchemy_engine is not None
    async with sql_alchemy_engine.connect() as connection:
        assert connection is not None


async def test_postgres_client(sql_alchemy_engine):
    async with get_connection_ctx_mgr() as postgresql_client:
        await postgresql_client.execute("CREATE TABLE test(id serial PRIMARY KEY, name VARCHAR (25) NOT NULL)")
        await postgresql_client.execute("INSERT INTO test VALUES(5, 'jef')")
        records = await postgresql_client.fetch("SELECT * FROM test")
        assert len(records) == 1
        first_record = records[0]
        assert first_record["id"] == 5
        assert first_record["name"] == "jef"
        await postgresql_client.execute("DELETE FROM test WHERE test.id = " + str(first_record["id"]))
        records = await postgresql_client.fetch("SELECT * FROM test")
        assert len(records) == 0


def test_arg_collector():
    args = ArgumentCollector()
    assert args("a") == "$1"
    assert args("a") == "$2"
    assert args("b") == "$3"
    assert args.get_values() == ["a", "a", "b"]

    args = ArgumentCollector(offset=2)
    assert args("a") == "$3"
    assert args("a") == "$4"
    assert args("b") == "$5"
    assert args.get_values() == ["a", "a", "b"]

    args = ArgumentCollector(de_duplicate=True)
    assert args("a") == "$1"
    assert args("a") == "$1"
    assert args("b") == "$2"
    assert args.get_values() == ["a", "b"]

    args = ArgumentCollector(de_duplicate=True, offset=3)
    assert args("a") == "$4"
    assert args("a") == "$4"
    assert args("b") == "$5"
    assert args.get_values() == ["a", "b"]
