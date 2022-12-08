"""
    Copyright 2018 Inmanta

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
import datetime
import enum
import logging
import time
import uuid
from collections import abc
from typing import Dict, List, Optional, Type, cast

import asyncpg
import pytest
from asyncpg import Connection, ForeignKeyViolationError
from asyncpg.pool import Pool

import utils
from inmanta import const, data
from inmanta.const import AgentStatus, LogLevel
from inmanta.data import ArgumentCollector, QueryType
from inmanta.resources import Id, ResourceVersionIdStr


async def test_connect_too_small_connection_pool(postgres_db, database_name: str, create_db_schema: bool = False):
    pool: Pool = await data.connect(
        postgres_db.host,
        postgres_db.port,
        database_name,
        postgres_db.user,
        postgres_db.password,
        create_db_schema,
        connection_pool_min_size=1,
        connection_pool_max_size=1,
        connection_timeout=120,
    )
    assert pool is not None
    connection: Connection = await pool.acquire()
    try:
        with pytest.raises(asyncio.TimeoutError):
            await pool.acquire(timeout=1.0)
    finally:
        await connection.close()
        await data.disconnect()


async def test_connect_default_parameters(postgres_db, database_name: str, create_db_schema: bool = False):
    pool: Pool = await data.connect(
        postgres_db.host, postgres_db.port, database_name, postgres_db.user, postgres_db.password, create_db_schema
    )
    assert pool is not None
    try:
        async with pool.acquire() as connection:
            assert connection is not None
    finally:
        await data.disconnect()


@pytest.mark.parametrize("min_size, max_size", [(-1, 1), (2, 1), (-2, -2)])
async def test_connect_invalid_parameters(postgres_db, min_size, max_size, database_name: str, create_db_schema: bool = False):
    with pytest.raises(ValueError):
        await data.connect(
            postgres_db.host,
            postgres_db.port,
            database_name,
            postgres_db.user,
            postgres_db.password,
            create_db_schema,
            connection_pool_min_size=min_size,
            connection_pool_max_size=max_size,
        )


async def test_connection_failure(unused_tcp_port_factory, database_name, clean_reset):
    port = unused_tcp_port_factory()
    with pytest.raises(OSError):
        await data.connect("localhost", port, database_name, "testuser", None)


async def test_postgres_client(postgresql_client):
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


async def test_db_schema_enum_consistency(init_dataclasses_and_load_schema) -> None:
    """
    Verify that enumeration fields defined in data document objects match values defined in the db schema.
    """
    all_db_document_classes: abc.Set[Type[data.BaseDocument]] = utils.get_all_subclasses(data.BaseDocument) - {
        data.BaseDocument
    }
    for cls in all_db_document_classes:
        enums: abc.Mapping[str, data.Field] = {
            name: field for name, field in cls.get_field_metadata().items() if issubclass(field.field_type, enum.Enum)
        }
        for enum_column, field in enums.items():
            db_enum_values: abc.Sequence[asyncpg.Record] = await cls._fetch_query(
                """
                SELECT enumlabel
                FROM pg_enum
                INNER JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
                INNER JOIN information_schema.columns c ON pg_type.typname = c.udt_name
                WHERE table_schema='public' AND table_name=$1 AND column_name=$2
                """,
                cls._get_value(cls.table_name()),
                cls._get_value(enum_column),
            )
            # verify the db enum and the Python enum have the exact same values
            assert set(field.field_type) == {
                field._from_db_single(enum_column, record["enumlabel"]) for record in db_enum_values
            }


async def test_project(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    assert projects[0].id == project.id

    other = await data.Project.get_by_id(project.id)
    assert project != other
    assert project.id == other.id


async def test_project_unique(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    project = data.Project(name="test")
    with pytest.raises(asyncpg.UniqueViolationError):
        await project.insert()


def test_project_no_project_name(init_dataclasses_and_load_schema):
    with pytest.raises(AttributeError):
        data.Project()


async def test_project_cascade_delete(init_dataclasses_and_load_schema):
    async def create_full_environment(project_name, environment_name):
        project = data.Project(name=project_name)
        await project.insert()

        env = data.Environment(name=environment_name, project=project.id, repo_url="", repo_branch="")
        await env.insert()

        agent_proc = data.AgentProcess(
            hostname="testhost",
            environment=env.id,
            first_seen=datetime.datetime.now(),
            last_seen=datetime.datetime.now(),
            sid=uuid.uuid4(),
        )
        await agent_proc.insert()

        agi1 = data.AgentInstance(process=agent_proc.sid, name="agi1", tid=env.id)
        await agi1.insert()
        agi2 = data.AgentInstance(process=agent_proc.sid, name="agi2", tid=env.id)
        await agi2.insert()

        agent = data.Agent(
            environment=env.id, name="agi1", last_failover=datetime.datetime.now(), paused=False, id_primary=agi1.id
        )
        await agent.insert()

        version = int(time.time())
        cm = data.ConfigurationModel(version=version, environment=env.id)
        await cm.insert()

        resource_ids = []
        for i in range(5):
            path = "/etc/file" + str(i)
            key = "std::File[agent1,path=" + path + "]"
            res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
            await res1.insert()
            resource_ids.append((res1.environment, res1.resource_version_id))

        code = data.Code(version=version, resource="std::File", environment=env.id)
        await code.insert()

        unknown_parameter = data.UnknownParameter(name="test", environment=env.id, version=version, source="")
        await unknown_parameter.insert()

        return project, env, agent_proc, [agi1, agi2], agent, resource_ids, code, unknown_parameter

    async def assert_project_exists(
        project, env, agent_proc, agent_instances, agent, resource_ids, code, unknown_parameter, exists
    ):
        def func(x):
            if exists:
                return x is not None
            else:
                return x is None

        assert func(await data.Project.get_by_id(project.id))
        assert func(await data.Environment.get_by_id(env.id))
        assert func(await data.AgentProcess.get_one(sid=agent_proc.sid))
        assert func(await data.AgentInstance.get_by_id(agent_instances[0].id))
        assert func(await data.AgentInstance.get_by_id(agent_instances[1].id))
        assert func(await data.Agent.get_one(environment=agent.environment, name=agent.name))
        for (environment, resource_version_id) in resource_ids:
            id = Id.parse_id(resource_version_id)
            assert func(await data.Resource.get_one(environment=environment, resource_id=id.resource_str(), model=id.version))
        assert func(await data.Code.get_one(environment=code.environment, resource=code.resource, version=code.version))
        assert func(await data.UnknownParameter.get_by_id(unknown_parameter.id))

    # Setup two environments
    full_env_1 = await create_full_environment("proj1", "env1")
    full_env_2 = await create_full_environment("proj2", "env2")

    # Assert exists
    await assert_project_exists(*full_env_1, exists=True)
    await assert_project_exists(*full_env_2, exists=True)

    # Cascade delete project 1
    project_env1 = full_env_1[0]
    await project_env1.delete_cascade()

    # Assert outcome
    await assert_project_exists(*full_env_1, exists=False)
    await assert_project_exists(*full_env_2, exists=True)


async def test_environment(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()
    assert env.project == project.id

    await project.delete_cascade()

    projects = await data.Project.get_list()
    envs = await data.Environment.get_list()
    assert len(projects) == 0
    assert len(envs) == 0


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


async def test_environment_cascade_content_only(init_dataclasses_and_load_schema):
    project = data.Project(name="proj")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    agent_proc = data.AgentProcess(
        hostname="testhost",
        environment=env.id,
        first_seen=datetime.datetime.now(),
        last_seen=datetime.datetime.now(),
        sid=uuid.uuid4(),
    )
    await agent_proc.insert()

    agi1 = data.AgentInstance(process=agent_proc.sid, name="agi1", tid=env.id)
    await agi1.insert()
    agi2 = data.AgentInstance(process=agent_proc.sid, name="agi2", tid=env.id)
    await agi2.insert()

    agent = data.Agent(environment=env.id, name="agi1", last_failover=datetime.datetime.now(), paused=False, id_primary=agi1.id)
    await agent.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(version=version, environment=env.id)
    await cm.insert()

    resource_ids = []
    for i in range(5):
        path = "/etc/file" + str(i)
        key = "std::File[agent1,path=" + path + "]"
        res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
        await res1.insert()
        resource_ids.append((res1.environment, res1.resource_version_id))

    resource_version_ids = [f"std::File[agent1,path=/etc/file0],v={version}", f"std::File[agent1,path=/etc/file1],v={version}"]
    resource_action = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=resource_version_ids,
        action_id=uuid.uuid4(),
        action=const.ResourceAction.deploy,
        started=datetime.datetime.now(),
    )
    await resource_action.insert()

    code = data.Code(version=version, resource="std::File", environment=env.id)
    await code.insert()

    unknown_parameter = data.UnknownParameter(name="test", environment=env.id, version=version, source="")
    await unknown_parameter.insert()

    await env.set(data.AUTO_DEPLOY, True)

    assert (await data.Project.get_by_id(project.id)) is not None
    assert (await data.Environment.get_by_id(env.id)) is not None
    assert (await data.AgentProcess.get_one(sid=agent_proc.sid)) is not None
    assert (await data.AgentInstance.get_by_id(agi1.id)) is not None
    assert (await data.AgentInstance.get_by_id(agi2.id)) is not None
    assert (await data.Agent.get_one(environment=agent.environment, name=agent.name)) is not None
    for environment, resource_version_id in resource_ids:
        id = Id.parse_id(resource_version_id)
        assert (
            await data.Resource.get_one(environment=environment, resource_id=id.resource_str(), model=id.version)
        ) is not None
    assert await data.ResourceAction.get_by_id(resource_action.action_id) is not None
    assert (await data.Code.get_one(environment=code.environment, resource=code.resource, version=code.version)) is not None
    assert (await data.UnknownParameter.get_by_id(unknown_parameter.id)) is not None
    assert (await env.get(data.AUTO_DEPLOY)) is True

    await env.delete_cascade(only_content=True)

    assert (await data.Project.get_by_id(project.id)) is not None
    assert (await data.Environment.get_by_id(env.id)) is not None
    assert (await data.AgentProcess.get_one(sid=agent_proc.sid)) is None
    assert (await data.AgentInstance.get_by_id(agi1.id)) is None
    assert (await data.AgentInstance.get_by_id(agi2.id)) is None
    assert (await data.Agent.get_one(environment=agent.environment, name=agent.name)) is None
    for environment, resource_version_id in resource_ids:
        id = Id.parse_id(resource_version_id)
        assert (await data.Resource.get_one(environment=environment, resource_id=id.resource_str(), model=id.version)) is None
    assert await data.ResourceAction.get_by_id(resource_action.action_id) is None
    assert (await data.Code.get_one(environment=code.environment, version=code.version)) is None
    assert (await data.UnknownParameter.get_by_id(unknown_parameter.id)) is None
    assert (await env.get(data.AUTO_DEPLOY)) is True


async def test_environment_set_setting_parameter(init_dataclasses_and_load_schema):
    project = data.Project(name="proj")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    assert (await env.get(data.AUTO_DEPLOY)) is True
    await env.set(data.AUTO_DEPLOY, False)
    assert (await env.get(data.AUTO_DEPLOY)) is False
    await env.unset(data.AUTO_DEPLOY)
    assert (await env.get(data.AUTO_DEPLOY)) is True

    with pytest.raises(KeyError):
        await env.set("set_non_existing_parameter", 1)
    with pytest.raises(KeyError):
        await env.get("get_non_existing_parameter")
    with pytest.raises(AttributeError):
        await env.set(data.AUTO_DEPLOY, 5)


async def test_environment_deprecated_setting(init_dataclasses_and_load_schema, caplog):
    project = data.Project(name="proj")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for (deprecated_option, new_option) in [
        (data.AUTOSTART_AGENT_INTERVAL, data.AUTOSTART_AGENT_DEPLOY_INTERVAL),
        (data.AUTOSTART_SPLAY, data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME),
    ]:
        await env.set(deprecated_option, 22)
        caplog.clear()
        assert (await env.get(new_option)) == 22
        assert "Config option %s is deprecated. Use %s instead." % (deprecated_option, new_option) in caplog.text

        await env.set(new_option, 23)
        caplog.clear()
        assert (await env.get(new_option)) == 23
        assert "Config option %s is deprecated. Use %s instead." % (deprecated_option, new_option) not in caplog.text

        await env.unset(deprecated_option)
        caplog.clear()
        assert (await env.get(new_option)) == 23
        assert "Config option %s is deprecated. Use %s instead." % (deprecated_option, new_option) not in caplog.text


async def test_agent_process(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    sid = uuid.uuid4()
    agent_proc = data.AgentProcess(
        hostname="testhost", environment=env.id, first_seen=datetime.datetime.now(), last_seen=datetime.datetime.now(), sid=sid
    )
    await agent_proc.insert()

    agi1 = data.AgentInstance(process=agent_proc.sid, name="agi1", tid=env.id)
    await agi1.insert()
    agi2 = data.AgentInstance(process=agent_proc.sid, name="agi2", tid=env.id)
    await agi2.insert()

    agent_procs = await data.AgentProcess.get_list(environment=env.id, order_by_column="last_seen", order="ASC NULLS LAST")
    assert len(agent_procs) == 1
    assert agent_procs[0].sid == agent_proc.sid

    assert (await data.AgentProcess.get_by_sid(sid)).sid == agent_proc.sid
    assert (await data.AgentProcess.get_by_sid(uuid.UUID(int=1))) is None

    live_procs = await data.AgentProcess.get_live()
    assert len(live_procs) == 1
    assert live_procs[0].sid == agent_proc.sid

    live_by_env_procs = await data.AgentProcess.get_list(
        environment=env.id, expired=None, order_by_column="last_seen", order="ASC NULLS LAST"
    )
    assert len(live_by_env_procs) == 1
    assert live_by_env_procs[0].sid == agent_proc.sid

    await agent_proc.update_fields(expired=datetime.datetime.now())

    live_procs = await data.AgentProcess.get_live()
    assert len(live_procs) == 0

    live_by_env_procs = await data.AgentProcess.get_list(
        environment=env.id, expired=None, order_by_column="last_seen", order="ASC NULLS LAST"
    )
    assert len(live_by_env_procs) == 0

    await agent_proc.delete_cascade()

    assert (await data.AgentProcess.get_one(sid=agent_proc.sid)) is None
    assert (await data.AgentInstance.get_by_id(agi1.id)) is None
    assert (await data.AgentInstance.get_by_id(agi2.id)) is None


async def test_agentprocess_cleanup(init_dataclasses_and_load_schema, postgresql_client):
    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="env1", project=project.id, repo_url="", repo_branch="")
    await env1.insert()
    env2 = data.Environment(name="env2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    now = datetime.datetime.now()

    async def insert_agent_proc_and_instances(
        env_id: uuid.UUID, hostname: str, expired_proc: Optional[datetime.datetime], expired_instances: List[datetime.datetime]
    ) -> None:
        agent_proc = data.AgentProcess(hostname=hostname, environment=env_id, expired=expired_proc, sid=uuid.uuid4())
        await agent_proc.insert()
        for i in range(len(expired_instances)):
            agent_instance = data.AgentInstance(
                id=uuid.uuid4(), process=agent_proc.sid, name=f"agent_instance{i}", expired=expired_instances[i], tid=env_id
            )
            await agent_instance.insert()

    async def verify_nr_of_records(env: uuid.UUID, hostname: str, expected_nr_procs: int, expected_nr_instances: int):
        # Verify expected_nr_procs
        result = await data.AgentProcess.get_list(environment=env, hostname=hostname)
        assert len(result) == expected_nr_procs, result
        # Verify expected_nr_instances
        query = """
            SELECT count(*)
            FROM agentprocess AS proc INNER JOIN agentinstance AS instance ON proc.sid=instance.process
            WHERE environment=$1 AND hostname=$2
        """
        result = await postgresql_client.fetch(query, env, hostname)
        assert result[0]["count"] == expected_nr_instances, result

    # Setup env1
    await insert_agent_proc_and_instances(env1.id, "proc1", None, [None])
    await insert_agent_proc_and_instances(env1.id, "proc1", datetime.datetime(2020, 1, 1, 1, 0), [now])
    await insert_agent_proc_and_instances(env1.id, "proc2", None, [None])
    # Setup env2
    await insert_agent_proc_and_instances(env2.id, "proc2", None, [None, None])
    await insert_agent_proc_and_instances(env2.id, "proc2", datetime.datetime(2020, 1, 1, 1, 0), [now, now, now])
    await insert_agent_proc_and_instances(env2.id, "proc2", datetime.datetime(2020, 1, 1, 2, 0), [now, now])
    await insert_agent_proc_and_instances(env2.id, "proc2", datetime.datetime(2020, 1, 1, 3, 0), [now])

    # Run cleanup twice to verify stability
    for i in range(2):
        # Perform cleanup
        await data.AgentProcess.cleanup(nr_expired_records_to_keep=1)
        # Assert outcome
        await verify_nr_of_records(env1.id, hostname="proc1", expected_nr_procs=2, expected_nr_instances=2)
        await verify_nr_of_records(env1.id, hostname="proc2", expected_nr_procs=1, expected_nr_instances=1)
        await verify_nr_of_records(env2.id, hostname="proc2", expected_nr_procs=2, expected_nr_instances=3)
        # Assert records are deleted in the correct order
        query = """
            SELECT expired
            FROM agentprocess
            WHERE environment=$1 AND hostname=$2 AND expired IS NOT NULL
        """
        result = await postgresql_client.fetch(query, env2.id, "proc2")
        assert len(result) == 1
        assert result[0]["expired"] == datetime.datetime(2020, 1, 1, 3, 0).astimezone()


async def test_delete_agentinstance_which_is_primary(init_dataclasses_and_load_schema):
    """
    It should be impossible to delete an AgentInstance record which is references
    from the Agent stable.
    """
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="env1", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    agent_proc = data.AgentProcess(hostname="test", environment=env.id, expired=None, sid=uuid.uuid4())
    await agent_proc.insert()
    agent_instance = data.AgentInstance(
        id=uuid.uuid4(), process=agent_proc.sid, name="agent_instance", expired=None, tid=env.id
    )
    await agent_instance.insert()
    agent = data.Agent(environment=env.id, name="test", id_primary=agent_instance.id)
    await agent.insert()

    with pytest.raises(ForeignKeyViolationError):
        await agent_instance.delete()


async def test_agent_instance(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    sid = uuid.uuid4()
    agent_proc = data.AgentProcess(
        hostname="testhost", environment=env.id, first_seen=datetime.datetime.now(), last_seen=datetime.datetime.now(), sid=sid
    )
    await agent_proc.insert()

    agi1_name = "agi1"
    agi1 = data.AgentInstance(process=agent_proc.sid, name=agi1_name, tid=env.id)
    await agi1.insert()
    agi2_name = "agi2"
    agi2 = data.AgentInstance(process=agent_proc.sid, name=agi2_name, tid=env.id)
    await agi2.insert()

    active_instances = await data.AgentInstance.active()
    assert len(active_instances) == 2
    assert agi1.id in [x.id for x in active_instances]
    assert agi2.id in [x.id for x in active_instances]

    current_instances = await data.AgentInstance.active_for(env.id, agi1_name)
    assert len(current_instances) == 1
    assert current_instances[0].id == agi1.id
    current_instances = await data.AgentInstance.active_for(env.id, agi2_name)
    assert len(current_instances) == 1
    assert current_instances[0].id == agi2.id

    await data.AgentInstance.log_instance_expiry(sid=agent_proc.sid, endpoints={agi1_name}, now=datetime.datetime.now())

    active_instances = await data.AgentInstance.active()
    assert len(active_instances) == 1
    assert agi1.id not in [x.id for x in active_instances]
    assert agi2.id in [x.id for x in active_instances]

    current_instances = await data.AgentInstance.active_for(env.id, agi1_name)
    assert len(current_instances) == 0
    current_instances = await data.AgentInstance.active_for(env.id, agi2_name)
    assert len(current_instances) == 1
    assert current_instances[0].id == agi2.id

    await data.AgentInstance.log_instance_creation(process=agent_proc.sid, endpoints={agi1_name}, tid=env.id)
    current_instances = await data.AgentInstance.active_for(env.id, agi1_name)
    assert len(current_instances) == 1
    assert current_instances[0].id == agi1.id


async def test_agent(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    sid = uuid.uuid4()
    agent_proc = data.AgentProcess(
        hostname="testhost", environment=env.id, first_seen=datetime.datetime.now(), last_seen=datetime.datetime.now(), sid=sid
    )
    await agent_proc.insert()

    agi1_name = "agi1"
    agi1 = data.AgentInstance(process=agent_proc.sid, name=agi1_name, tid=env.id)
    await agi1.insert()

    agent1 = data.Agent(
        environment=env.id, name="agi1_agent1", last_failover=datetime.datetime.now(), paused=False, id_primary=agi1.id
    )
    await agent1.insert()
    agent2 = data.Agent(environment=env.id, name="agi1_agent2", paused=False)
    await agent2.insert()
    agent3 = data.Agent(environment=env.id, name="agi1_agent3", paused=True)
    await agent3.insert()

    agents = await data.Agent.get_list()
    assert len(agents) == 3
    for agent in agents:
        assert (agent.name, agent.environment) in [(a.name, a.environment) for a in [agent1, agent2, agent3]]

    for agent in [agent1, agent2, agent3]:
        retrieved_agent = await agent.get(agent.environment, agent.name)
        assert retrieved_agent is not None
        assert retrieved_agent.environment == agent.environment
        assert retrieved_agent.name == agent.name

    assert agent1.get_status() == AgentStatus.up
    assert agent2.get_status() == AgentStatus.down
    assert agent3.get_status() == AgentStatus.paused

    for agent in [agent1, agent2, agent3]:
        assert AgentStatus(agent.to_dict()["state"]) == agent.get_status()

    await agent1.update_fields(paused=True)
    assert agent1.get_status() == AgentStatus.paused

    await agent2.update_fields(primary=agi1.id)
    assert agent2.get_status() == AgentStatus.up

    await agent3.update_fields(paused=False)
    assert agent3.get_status() == AgentStatus.down

    primary_instance = await data.AgentInstance.get_by_id(agent1.primary)
    primary_process = await data.AgentProcess.get_one(sid=primary_instance.process)
    assert primary_process.sid == agent_proc.sid


async def test_pause_agent_endpoint_set(environment):
    """
    Test the pause() method in the Agent class
    """
    env_id = uuid.UUID(environment)
    agent_name = "test"
    agent = data.Agent(environment=env_id, name=agent_name, last_failover=datetime.datetime.now(), paused=False)
    await agent.insert()

    # Verify not paused
    agent = await data.Agent.get_one(environment=env_id, name=agent_name)
    assert not agent.paused

    # Pause
    paused_agents = await data.Agent.pause(env=env_id, endpoint=agent_name, paused=True)
    assert paused_agents == [agent_name]
    agent = await data.Agent.get_one(environment=env_id, name=agent_name)
    assert agent.paused

    # Unpause
    paused_agents = await data.Agent.pause(env=env_id, endpoint=agent_name, paused=False)
    assert paused_agents == [agent_name]
    agent = await data.Agent.get_one(environment=env_id, name=agent_name)
    assert not agent.paused


async def test_pause_all_agent_in_environment(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    env1 = data.Environment(name="env1", project=project.id)
    await env1.insert()
    env2 = data.Environment(name="env2", project=project.id)
    await env2.insert()

    await data.Agent(environment=env1.id, name="agent1", last_failover=datetime.datetime.now(), paused=False).insert()
    await data.Agent(environment=env1.id, name="agent2", last_failover=datetime.datetime.now(), paused=False).insert()
    await data.Agent(environment=env2.id, name="agent3", last_failover=datetime.datetime.now(), paused=False).insert()
    agents_in_env1 = ["agent1", "agent2"]

    async def assert_paused(env_paused_map: Dict[uuid.UUID, bool]) -> None:
        for env_id, paused in env_paused_map.items():
            agents = await data.Agent.get_list(environment=env_id)
            assert all([a.paused == paused for a in agents])

    # Test initial state
    await assert_paused(env_paused_map={env1.id: False, env2.id: False})
    # Pause env1 and pause again
    for _ in range(2):
        paused_agents = await data.Agent.pause(env1.id, endpoint=None, paused=True)
        assert sorted(paused_agents) == sorted(agents_in_env1)
        await assert_paused(env_paused_map={env1.id: True, env2.id: False})
    # Unpause env1 and pause again
    for _ in range(2):
        paused_agents = await data.Agent.pause(env1.id, endpoint=None, paused=False)
        assert sorted(paused_agents) == sorted(agents_in_env1)
        await assert_paused(env_paused_map={env1.id: False, env2.id: False})


async def test_config_model(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={})
    await cm.insert()

    # create resources
    key = "std::File[agent1,path=/etc/motd]"
    res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": "/etc/motd"})
    await res1.insert()

    agents = await data.ConfigurationModel.get_agents(env.id, version)
    assert len(agents) == 1
    assert "agent1" in agents


async def test_model_list(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for version in range(1, 20):
        cm = data.ConfigurationModel(
            environment=env.id, version=version, date=datetime.datetime.now(), total=0, version_info={}
        )
        await cm.insert()

    versions = await data.ConfigurationModel.get_versions(env.id, 0, 1)
    assert len(versions) == 1
    assert versions[0].version == 19

    versions = await data.ConfigurationModel.get_versions(env.id, 1, 1)
    assert len(versions) == 1
    assert versions[0].version == 18

    versions = await data.ConfigurationModel.get_versions(env.id)
    assert len(versions) == 19
    assert versions[0].version == 19
    assert versions[-1].version == 1

    versions = await data.ConfigurationModel.get_versions(env.id, 10)
    assert len(versions) == 9
    assert versions[0].version == 9
    assert versions[-1].version == 1


async def test_model_get_latest_version(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    cms = []
    for version in range(1, 5):
        cm = data.ConfigurationModel(
            environment=env.id, version=version, date=datetime.datetime.now(), total=0, version_info={}
        )
        await cm.insert()
        cms.append(cm)

    latest_version = await data.ConfigurationModel.get_latest_version(env.id)
    assert latest_version is None

    await cms[1].update_fields(released=True)
    latest_version = await data.ConfigurationModel.get_latest_version(env.id)
    assert latest_version.version == 2

    await cms[3].update_fields(released=True)
    latest_version = await data.ConfigurationModel.get_latest_version(env.id)
    assert latest_version.version == 4


async def test_model_set_ready(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={})
    await cm.insert()

    assert cm.done == 0

    path = "/etc/file"
    key = "std::File[agent1,path=" + path + "]"
    resource = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
    await resource.insert()

    assert cm.done == 0
    await resource.update_fields(status=const.ResourceState.deployed)
    cm = await data.ConfigurationModel.get_one(version=version, environment=env.id)
    assert cm.done == 1


@pytest.mark.parametrize(
    "resource_state, should_be_deployed",
    [
        (const.ResourceState.unavailable, True),
        (const.ResourceState.skipped, True),
        (const.ResourceState.deployed, True),
        (const.ResourceState.failed, True),
        (const.ResourceState.deploying, False),
        (const.ResourceState.available, False),
        (const.ResourceState.cancelled, True),
        (const.ResourceState.undefined, True),
        (const.ResourceState.skipped_for_undefined, True),
    ],
)
async def test_model_mark_done_if_done(init_dataclasses_and_load_schema, resource_state, should_be_deployed):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={})
    await cm.insert()

    assert cm.done == 0

    path = "/etc/file"
    key = "std::File[agent1,path=" + path + "]"
    resource = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
    await resource.insert()

    assert not cm.deployed
    await data.ConfigurationModel.mark_done_if_done(env.id, cm.version)
    cm = await data.ConfigurationModel.get_one(version=version, environment=env.id)
    assert not cm.deployed
    assert cm.done == 0

    await resource.update_fields(status=resource_state)
    await data.ConfigurationModel.mark_done_if_done(env.id, cm.version)
    cm = await data.ConfigurationModel.get_one(version=version, environment=env.id)
    assert cm.deployed == should_be_deployed
    assert cm.done == (1 if should_be_deployed else 0)

    # Make sure that a done resource stays in done even when a repair is running
    await resource.update_fields(status=const.ResourceState.deploying)
    cm = await data.ConfigurationModel.get_one(version=version, environment=env.id)
    assert cm.deployed == should_be_deployed
    assert cm.done == (1 if should_be_deployed else 0)


async def test_model_get_list(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env1.insert()
    env2 = data.Environment(name="prod", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    for env in [env1, env2]:
        for i in range(2):
            cm = data.ConfigurationModel(environment=env.id, version=i, date=datetime.datetime.now(), total=0, version_info={})
            await cm.insert()

            for r in range(3):
                if r % 2 == 0:
                    res = data.Resource.new(
                        environment=env.id,
                        status=const.ResourceState.deployed,
                        resource_version_id=f"std::File[agent1,path=/etc/file{r}],v={i}",
                        attributes={"purge_on_delete": False},
                        last_deploy=datetime.datetime.now(),
                    )
                else:
                    res = data.Resource.new(
                        environment=env.id,
                        status=const.ResourceState.deploying,
                        resource_version_id=f"std::File[agent1,path=/etc/file{r}],v={i}",
                        attributes={"purge_on_delete": False},
                    )
                await res.insert()

    for env in [env1, env2]:
        cms = await data.ConfigurationModel.get_list(environment=env.id)
        assert len(cms) == 2
        for c in cms:
            assert c.environment == env.id
            assert c.done == 2

    cms = await data.ConfigurationModel.get_list(environment=uuid.uuid4())
    assert not cms


async def test_model_serialization(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    now = datetime.datetime.now().astimezone()
    cm = data.ConfigurationModel(environment=env.id, version=version, date=now, total=1, version_info={})
    await cm.insert()

    assert cm.done == 0

    path = "/etc/file"
    key = "std::File[agent1,path=" + path + "]"
    resource = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"path": path},
        status=const.ResourceState.deployed,
    )
    await resource.insert()

    cm = await data.ConfigurationModel.get_one(environment=env.id, version=version)
    dct = cm.to_dict()
    assert dct["version"] == version
    assert dct["environment"] == env.id
    assert dct["date"] == now
    assert not dct["released"]
    assert not dct["deployed"]
    assert dct["result"] == const.VersionState.pending
    assert dct["version_info"] == {}
    assert dct["total"] == 1
    assert dct["done"] == 1
    assert dct["status"] == {str(uuid.uuid5(env.id, key)): {"id": key, "status": const.ResourceState.deployed.name}}


async def test_model_delete_cascade(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=0, version_info={})
    await cm.insert()

    path = "/etc/file"
    key = "std::File[agent1,path=" + path + "]"
    resource = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
    await resource.insert()

    code = data.Code(version=version, resource="std::File", environment=env.id)
    await code.insert()

    unknown_parameter = data.UnknownParameter(name="test", environment=env.id, version=version, source="")
    await unknown_parameter.insert()

    await cm.delete_cascade()

    assert (await data.ConfigurationModel.get_list()) == []
    id = Id.parse_resource_version_id(resource.resource_version_id)
    assert (
        await data.Resource.get_one(environment=resource.environment, resource_id=id.resource_str(), model=id.version)
    ) is None
    assert (await data.Code.get_one(environment=code.environment, resource=code.resource, version=code.version)) is None
    assert (await data.UnknownParameter.get_by_id(unknown_parameter.id)) is None


async def test_model_get_version_nr_latest_version(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env_dev = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env_dev.insert()
    env_prod = data.Environment(name="prod", project=project.id, repo_url="", repo_branch="")
    await env_prod.insert()

    now = datetime.datetime.now()
    await data.ConfigurationModel(environment=env_dev.id, version=4, total=0, date=now, released=True).insert()
    await data.ConfigurationModel(environment=env_dev.id, version=7, total=0, date=now, released=True).insert()
    await data.ConfigurationModel(environment=env_dev.id, version=9, total=0, date=now, released=False).insert()

    await data.ConfigurationModel(environment=env_prod.id, version=15, total=0, date=now, released=False).insert()
    await data.ConfigurationModel(environment=env_prod.id, version=11, total=0, date=now, released=False).insert()

    assert await data.ConfigurationModel.get_version_nr_latest_version(env_dev.id) == 7
    assert await data.ConfigurationModel.get_version_nr_latest_version(env_prod.id) is None
    assert await data.ConfigurationModel.get_version_nr_latest_version(uuid.uuid4()) is None


@pytest.mark.parametrize(
    "resource_state, version_state",
    [
        (const.ResourceState.deployed, const.VersionState.success),
        (const.ResourceState.failed, const.VersionState.failed),
        (const.ResourceState.undefined, const.VersionState.failed),
        (const.ResourceState.skipped_for_undefined, const.VersionState.failed),
        (const.ResourceState.cancelled, const.VersionState.failed),
        (const.ResourceState.skipped, const.VersionState.failed),
    ],
)
async def test_mark_done(init_dataclasses_and_load_schema, resource_state, version_state):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=2, version_info={})
    await cm.insert()

    assert cm.done == 0

    path1 = "/etc/file1"
    key1 = "std::File[agent1,path=" + path1 + "]"
    resource1 = data.Resource.new(
        environment=env.id, resource_version_id=key1 + ",v=%d" % version, attributes={"path": path1}, status=resource_state
    )
    await resource1.insert()

    path2 = "/etc/file2"
    key2 = "std::File[agent1,path=" + path2 + "]"
    resource2 = data.Resource.new(
        environment=env.id,
        resource_version_id=key2 + ",v=%d" % version,
        attributes={"path": path2},
        status=const.ResourceState.deployed,
    )
    await resource2.insert()

    assert cm.result == const.VersionState.pending
    await cm.mark_done()
    assert cm.result == version_state


async def populate_model(env_id, version):
    def get_path(n):
        return "/tmp/%d" % n

    def get_id(n):
        return "std::File[agent1,path=/tmp/%d],v=%s" % (n, version)

    def get_resource(n, depends, status=const.ResourceState.available):
        requires = [get_id(z) for z in depends]
        return data.Resource.new(
            environment=env_id,
            resource_version_id=get_id(n),
            status=status,
            attributes={"path": get_path(n), "purge_on_delete": False, "purged": False, "requires": requires},
        )

    res1 = get_resource(1, [])
    await res1.insert()

    res2 = get_resource(2, [1])
    await res2.insert()

    res3 = get_resource(3, [], const.ResourceState.undefined)
    await res3.insert()

    res4 = get_resource(4, [3])
    await res4.insert()

    res5 = get_resource(5, [4])
    await res5.insert()


async def test_resource_purge_on_delete(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # model 1
    version = 1
    cm1 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=2,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm1.insert()

    res11 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % version,
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
    )
    await res11.insert()

    res12 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent2,path=/etc/motd],v=%s" % version,
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True},
    )
    await res12.insert()

    # model 2 (multiple undeployed versions)
    while version < 10:
        version += 1
        cm2 = data.ConfigurationModel(
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=1,
            version_info={},
            released=False,
            deployed=False,
        )
        await cm2.insert()

        res21 = data.Resource.new(
            environment=env.id,
            resource_version_id="std::File[agent5,path=/etc/motd],v=%s" % version,
            status=const.ResourceState.available,
            attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
        )
        await res21.insert()

    # model 3
    version += 1
    cm3 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=0, version_info={})
    await cm3.insert()

    to_purge = await data.Resource.get_deleted_resources(env.id, version, set())

    assert len(to_purge) == 1
    assert to_purge[0].model == 1
    assert to_purge[0].resource_id == "std::File[agent1,path=/etc/motd]"


async def test_issue_422(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # model 1
    version = 1
    cm1 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm1.insert()

    res11 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % version,
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
    )
    await res11.insert()

    # model 2 (multiple undeployed versions)
    version += 1
    cm2 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=False,
        deployed=False,
    )
    await cm2.insert()

    res21 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % version,
        status=const.ResourceState.available,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
    )
    await res21.insert()

    # model 3
    version += 1
    cm3 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=0, version_info={})
    await cm3.insert()

    to_purge = await data.Resource.get_deleted_resources(env.id, version, set())

    assert len(to_purge) == 1
    assert to_purge[0].model == 1
    assert to_purge[0].resource_id == "std::File[agent1,path=/etc/motd]"


async def test_get_latest_resource(init_dataclasses_and_load_schema, postgresql_client):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    key = "std::File[agent1,path=/etc/motd]"
    assert (await data.Resource.get_latest_version(env.id, key)) is None

    version = 1
    cm2 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=False,
        deployed=False,
    )
    await cm2.insert()
    res11 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
    )
    await res11.insert()

    version = 2
    cm2 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=False,
        deployed=False,
    )
    await cm2.insert()
    res12 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True},
    )
    await res12.insert()

    res = await data.Resource.get_latest_version(env.id, key)
    assert res.model == 2


async def test_order_by_validation(init_dataclasses_and_load_schema):
    """Test the validation of the order by column names and the sort order value. This test case checks that wrong values
    are rejected. Other test cases validate that the parameters work.
    """
    with pytest.raises(RuntimeError):
        await data.Resource.get_list(order_by_column="; DROP DATABASE")

    with pytest.raises(RuntimeError):
        await data.Resource.get_list(order_by_column="resource_id", order="BAD")


async def test_get_resources(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm1 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm1.insert()

    resource_ids = []
    for i in range(1, 11):
        res = data.Resource.new(
            environment=env.id,
            resource_version_id="std::File[agent1,path=/tmp/file%d],v=%d" % (i, version),
            status=const.ResourceState.deployed,
            attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
        )
        await res.insert()
        resource_ids.append(res.resource_version_id)

    resources = await data.Resource.get_resources(env.id, resource_ids)
    assert len(resources) == len(resource_ids)
    assert sorted([x.resource_version_id for x in resources]) == sorted(resource_ids)

    resources = await data.Resource.get_resources(env.id, [resource_ids[0], "abcd"])
    assert len(resources) == 1

    resources = await data.Resource.get_resources(env.id, [])
    assert len(resources) == 0


async def test_model_get_resources_for_version(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    resource_ids_version_one = []
    version = 1
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm.insert()
    for i in range(1, 11):
        res = data.Resource.new(
            environment=env.id,
            resource_version_id="std::File[agent1,path=/tmp/file%d],v=%d" % (i, version),
            status=const.ResourceState.deployed,
            attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
        )
        await res.insert()
        resource_ids_version_one.append(res.resource_version_id)

    resource_ids_version_two = []
    version += 1
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm.insert()
    for i in range(11, 21):
        res = data.Resource.new(
            environment=env.id,
            resource_version_id="std::File[agent2,path=/tmp/file%d],v=%d" % (i, version),
            status=const.ResourceState.deployed,
            attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
        )
        await res.insert()
        resource_ids_version_two.append(res.resource_version_id)

    for version in range(3, 5):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=1,
            version_info={},
            released=True,
            deployed=True,
        )
        await cm.insert()

    async def make_with_status(i, status):
        res = data.Resource.new(
            environment=env.id,
            resource_version_id="std::File[agent3,path=/tmp/file%d],v=3" % i,
            status=status,
            attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
        )
        await res.insert()
        return res.resource_version_id

    d = await make_with_status(1, const.ResourceState.deployed)
    s = await make_with_status(2, const.ResourceState.skipped)
    su = await make_with_status(3, const.ResourceState.skipped_for_undefined)
    u = await make_with_status(4, const.ResourceState.undefined)

    resources = await data.Resource.get_resources_for_version(env.id, 1)
    assert len(resources) == 10
    assert sorted(resource_ids_version_one) == sorted([x.resource_version_id for x in resources])
    resources = await data.Resource.get_resources_for_version(env.id, 2)
    assert len(resources) == 10
    assert sorted(resource_ids_version_two) == sorted([x.resource_version_id for x in resources])
    resources = await data.Resource.get_resources_for_version(env.id, 4)
    assert resources == []

    resources = await data.Resource.get_resources_for_version(env.id, 3)
    assert len(resources) == 4
    assert sorted([x.resource_version_id for x in resources]) == sorted([d, s, u, su])


async def test_get_resources_in_latest_version(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for version in range(1, 3):
        status = const.ResourceState.deployed if version == 1 else const.ResourceState.available
        cm = data.ConfigurationModel(
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=2,
            version_info={},
            released=True,
            deployed=True,
        )
        await cm.insert()
        for i in range(1, 3):
            res = data.Resource.new(
                environment=env.id,
                resource_version_id="std::File[agent1,path=/tmp/file%d],v=%d" % (i, version),
                status=status,
                attributes={"path": f"/etc/motd{i}", "purge_on_delete": True, "purged": False},
            )
            await res.insert()

    resources = await data.Resource.get_resources_in_latest_version(
        env.id, "std::File", {"path": "/etc/motd1", "purge_on_delete": True}
    )
    assert len(resources) == 1
    resource = resources[0]
    expected_resource = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/tmp/file1],v=2",
        status=status,
        attributes={"path": "/etc/motd1", "purge_on_delete": True, "purged": False},
    )
    assert resource.to_dict() == expected_resource.to_dict()

    cm = data.ConfigurationModel(
        environment=env.id,
        version=3,
        date=datetime.datetime.now(),
        total=2,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm.insert()
    resources = await data.Resource.get_resources_in_latest_version(
        env.id, "std::File", {"path": "/etc/motd1", "purge_on_delete": True}
    )
    assert len(resources) == 0


async def test_model_get_resources_for_version_optional_args(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=3, version_info={})
    await cm.insert()

    async def insert_resource(env_id, version, agent_name, path, status):
        resource_version_id = f"std::File[{agent_name},path={path}],v={version}"
        resource = data.Resource.new(
            environment=env_id, resource_version_id=resource_version_id, attributes={"path": path}, status=status
        )
        await resource.insert()

    await insert_resource(env.id, version, "agent1", "path1", const.ResourceState.deployed)
    await insert_resource(env.id, version, "agent2", "path2", const.ResourceState.available)
    await insert_resource(env.id, version, "agent1", "path3", const.ResourceState.undefined)

    result = await data.Resource.get_resources_for_version(env.id, version)
    assert len(result) == 3
    assert sorted([r.agent for r in result]) == ["agent1", "agent1", "agent2"]
    for r in result:
        assert len(r.attributes) == 1

    result = await data.Resource.get_resources_for_version(env.id, version, agent="agent2")
    assert len(result) == 1
    assert result[0].agent == "agent2"

    result = await data.Resource.get_resources_for_version(env.id, version, no_obj=True)
    assert len(result) == 3
    assert sorted([r["agent"] for r in result]) == ["agent1", "agent1", "agent2"]
    for r in result:
        assert len(r["attributes"]) == 1


async def test_escaped_resources(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm1 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm1.insert()

    routes = {"8.0.0.0/8": "1.2.3.4", "0.0.0.0/0": "127.0.0.1"}
    res = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,name=router],v=%d" % version,
        status=const.ResourceState.deployed,
        attributes={"name": "router", "purge_on_delete": True, "purged": False, "routes": routes},
    )
    await res.insert()
    resource_id = res.resource_version_id

    resources = await data.Resource.get_resources(env.id, [resource_id])
    assert len(resources) == 1

    assert resources[0].attributes["routes"] == routes


async def test_resource_provides(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm1 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm1.insert()

    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=%d" % version,
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
    )
    res2 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file2],v=%d" % version,
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
    )
    res1.provides.append(res2.resource_version_id)

    assert len(res1.provides) == 1
    assert len(res2.provides) == 0
    assert res1.provides[0] == res2.resource_version_id
    assert res2.provides == []

    await res1.insert()
    await res2.insert()

    res1 = await data.Resource.get(env.id, res1.resource_version_id)
    res2 = await data.Resource.get(env.id, res2.resource_version_id)

    assert len(res1.provides) == 1
    assert len(res2.provides) == 0
    assert res1.provides[0] == res2.resource_version_id
    assert res2.provides == []


async def test_resource_hash(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for version in range(1, 4):
        cm1 = data.ConfigurationModel(
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=1,
            version_info={},
            released=True,
            deployed=True,
        )
        await cm1.insert()

    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=1",
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
    )
    res2 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=2",
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False},
    )
    res3 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=3",
        status=const.ResourceState.deployed,
        attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True},
    )
    await res1.insert()
    await res2.insert()
    await res3.insert()

    assert res1.attribute_hash is not None
    assert res1.attribute_hash == res2.attribute_hash
    assert res3.attribute_hash is not None
    assert res1.attribute_hash != res3.attribute_hash

    readres = await data.Resource.get_resources(
        env.id, [res1.resource_version_id, res2.resource_version_id, res3.resource_version_id]
    )

    resource_map = {r.resource_version_id: r for r in readres}
    res1 = resource_map[res1.resource_version_id]
    res2 = resource_map[res2.resource_version_id]
    res3 = resource_map[res3.resource_version_id]

    assert res1.attribute_hash is not None
    assert res1.attribute_hash == res2.attribute_hash
    assert res3.attribute_hash is not None
    assert res1.attribute_hash != res3.attribute_hash


async def test_resources_report(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # model 1
    version = 1
    cm1 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm1.insert()

    res11 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=%s" % version,
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 12, 30),
        attributes={"path": "/etc/file1"},
    )
    await res11.insert()
    res12 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file2],v=%s" % version,
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 12, 30),
        attributes={"path": "/etc/file2"},
    )
    await res12.insert()

    # model 2
    version += 1
    cm2 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=False,
        deployed=False,
    )
    await cm2.insert()
    res21 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=%s" % version,
        status=const.ResourceState.available,
        attributes={"path": "/etc/file1"},
    )
    await res21.insert()
    res22 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file3],v=%s" % version,
        status=const.ResourceState.available,
        attributes={"path": "/etc/file3"},
    )
    await res22.insert()

    # model 3
    version += 1
    cm3 = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm3.insert()

    res31 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file2],v=%s" % version,
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 14, 30),
        attributes={"path": "/etc/file2"},
    )
    await res31.insert()

    report = await data.Resource.get_resources_report(env.id)
    assert len(report) == 3
    report_as_map = {x["resource_id"]: x for x in report}
    for i in range(1, 4):
        assert f"std::File[agent1,path=/etc/file{i}]" in report_as_map

    assert report_as_map["std::File[agent1,path=/etc/file1]"]["resource_type"] == "std::File"
    assert report_as_map["std::File[agent1,path=/etc/file1]"]["deployed_version"] == 1
    assert report_as_map["std::File[agent1,path=/etc/file1]"]["latest_version"] == 2
    assert (
        report_as_map["std::File[agent1,path=/etc/file1]"]["last_deploy"] == datetime.datetime(2018, 7, 14, 12, 30).astimezone()
    )
    assert report_as_map["std::File[agent1,path=/etc/file1]"]["agent"] == "agent1"

    assert report_as_map["std::File[agent1,path=/etc/file2]"]["resource_type"] == "std::File"
    assert report_as_map["std::File[agent1,path=/etc/file2]"]["deployed_version"] == 3
    assert report_as_map["std::File[agent1,path=/etc/file2]"]["latest_version"] == 3
    assert (
        report_as_map["std::File[agent1,path=/etc/file2]"]["last_deploy"] == datetime.datetime(2018, 7, 14, 14, 30).astimezone()
    )
    assert report_as_map["std::File[agent1,path=/etc/file2]"]["agent"] == "agent1"

    assert report_as_map["std::File[agent1,path=/etc/file3]"]["resource_type"] == "std::File"
    assert report_as_map["std::File[agent1,path=/etc/file3]"]["deployed_version"] is None
    assert report_as_map["std::File[agent1,path=/etc/file3]"]["latest_version"] == 2
    assert report_as_map["std::File[agent1,path=/etc/file3]"]["last_deploy"] is None
    assert report_as_map["std::File[agent1,path=/etc/file3]"]["agent"] == "agent1"


async def test_resource_action(init_dataclasses_and_load_schema):
    """
    Test whether the save() method of a ResourceAction writes its changes, logs and fields
    correctly to the database.
    """
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm.insert()

    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=1",
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 14, 30),
        attributes={"path": "/etc/file2"},
    )
    await res1.insert()

    res2 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file2],v=1",
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 14, 30),
        attributes={"path": "/etc/file2"},
    )
    await res2.insert()

    now = datetime.datetime.now().astimezone()
    action_id = uuid.uuid4()
    resource_version_ids = ["std::File[agent1,path=/etc/file1],v=1", "std::File[agent1,path=/etc/file2],v=1"]
    resource_action = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=resource_version_ids,
        action_id=action_id,
        action=const.ResourceAction.deploy,
        started=now,
    )
    await resource_action.insert()

    resource_action.add_changes({"rid": {"field1": {"old": "a", "new": "b"}, "field2": {}, "field3": ["removed", "installed"]}})
    resource_action.add_logs([{}, {}])
    resource_action.set_field("status", const.ResourceState.failed)
    await resource_action.save()

    ra_via_get_one = await data.ResourceAction.get_one(action_id=resource_action.action_id)
    ra_via_get_by_id = await data.ResourceAction.get_by_id(resource_action.action_id)
    ra_list = await data.ResourceAction.get_list(action_id=resource_action.action_id)
    assert len(ra_list) == 1
    ra_via_get_list = ra_list[0]
    ra_via_get = await data.ResourceAction.get(action_id=resource_action.action_id)
    for ra in [ra_via_get_one, ra_via_get_by_id, ra_via_get_list, ra_via_get]:
        assert ra.environment == env.id
        assert ra.version == version
        assert ra.action_id == action_id
        assert ra.action == const.ResourceAction.deploy
        assert ra.started == now
        assert ra.finished is None

        assert len(ra.resource_version_ids) == 2
        assert sorted(ra.resource_version_ids) == sorted(resource_version_ids)

        assert len(ra.changes["rid"]) == 3
        assert ra.changes["rid"]["field1"]["old"] == "a"
        assert ra.changes["rid"]["field1"]["new"] == "b"
        assert ra.changes["rid"]["field2"] == {}
        assert ra.changes["rid"]["field3"] == ["removed", "installed"]
        assert ra.status == const.ResourceState.failed

        assert len(ra.messages) == 2
        for message in ra.messages:
            assert message == {}
        await utils.resource_action_consistency_check()


async def test_resource_action_get_logs(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(
        environment=env.id, version=version, date=datetime.datetime.now().astimezone(), total=1, version_info={}
    )
    await cm.insert()

    rv_id = f"std::File[agent1,path=/etc/motd],v={version}"
    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id=rv_id,
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 14, 30),
        attributes={"path": "/etc/file2"},
    )
    await res1.insert()

    for i in range(1, 11):
        action_id = uuid.uuid4()
        resource_action = data.ResourceAction(
            environment=env.id,
            version=version,
            resource_version_ids=[rv_id],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=datetime.datetime.now().astimezone(),
        )
        await resource_action.insert()
        resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=i)])
        await resource_action.save()

    action_id = uuid.uuid4()

    resource_action = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=[rv_id],
        action_id=action_id,
        action=const.ResourceAction.dryrun,
        started=datetime.datetime.now().astimezone(),
    )
    await resource_action.insert()
    times = datetime.datetime.now().astimezone()
    resource_action.add_logs([data.LogLine.log(logging.WARNING, "warning version %(version)d", version=100, timestamp=times)])
    await resource_action.save()

    resource_actions = await data.ResourceAction.get_log(env.id, rv_id)
    assert len(resource_actions) == 11
    for i in range(len(resource_actions)):
        action = resource_actions[i]
        if i == 0:
            assert action.action == const.ResourceAction.dryrun
        else:
            assert action.action == const.ResourceAction.deploy
    resource_actions = await data.ResourceAction.get_log(env.id, rv_id, const.ResourceAction.dryrun.name)
    assert len(resource_actions) == 1
    action = resource_actions[0]
    assert action.action == const.ResourceAction.dryrun
    assert action.messages[0]["level"] == LogLevel.WARNING.name
    assert action.messages[0]["timestamp"] == times

    resource_actions = await data.ResourceAction.get_log(env.id, rv_id, const.ResourceAction.deploy.name, limit=2)
    assert len(resource_actions) == 2
    for action in resource_actions:
        assert len(action.messages) == 1
        assert action.messages[0]["level"] == LogLevel.INFO.name

    # Get logs for non-existing resource_version_id
    resource_actions = await data.ResourceAction.get_log(env.id, "std::File[agent11,path=/etc/motd],v=1")
    assert len(resource_actions) == 0

    resource_actions = await data.ResourceAction.get_logs_for_version(env.id, version)
    assert len(resource_actions) == 11
    for i in range(len(resource_actions)):
        action = resource_actions[i]
        if i == 0:
            assert action.action == const.ResourceAction.dryrun
        else:
            assert action.action == const.ResourceAction.deploy

    await utils.resource_action_consistency_check()


async def test_data_document_recursion(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={})
    await cm.insert()

    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=1",
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 14, 30),
        attributes={"path": "/etc/file2"},
    )
    await res1.insert()

    now = datetime.datetime.now()
    ra = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=[res1.resource_version_id],
        action_id=uuid.uuid4(),
        action=const.ResourceAction.store,
        started=now,
        finished=now,
        messages=[data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=2)],
    )
    await ra.insert()


async def test_code(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={})
    await cm.insert()

    code1 = data.Code(environment=env.id, resource="std::File", version=version, source_refs={"ref": "ref"})
    await code1.insert()

    code2 = data.Code(environment=env.id, resource="std::Directory", version=version, source_refs={})
    await code2.insert()

    version2 = version + 1
    cm2 = data.ConfigurationModel(environment=env.id, version=version2, date=datetime.datetime.now(), total=1, version_info={})
    await cm2.insert()

    code3 = data.Code(environment=env.id, resource="std::Directory", version=version2, source_refs={})
    await code3.insert()

    # Test behavior of copy_versions. Create second environment to verify the method is restricted to the first one
    env2 = data.Environment(name="dev2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()
    await data.ConfigurationModel(environment=env2.id, version=code3.version).insert()
    await data.Code(environment=env2.id, resource="std::File", version=code3.version, source_refs={}).insert()
    await data.Code.copy_versions(env.id, code3.version, code3.version + 1)

    def assert_match_code(code1, code2):
        assert code1 is not None
        assert code2 is not None
        assert code1.environment == code1.environment
        assert code1.resource == code2.resource
        assert code1.version == code2.version
        shared_keys_source_refs = [
            k for k in code1.source_refs if k in code2.source_refs and code1.source_refs[k] == code2.source_refs[k]
        ]
        assert len(shared_keys_source_refs) == len(code1.source_refs.keys())

    code_file = await data.Code.get_version(env.id, version, "std::File")
    assert_match_code(code_file, code1)

    code_directory = await data.Code.get_version(env.id, version, "std::Directory")
    assert_match_code(code_directory, code2)

    code_test = await data.Code.get_version(env.id, version, "std::Test")
    assert code_test is None

    code_list = await data.Code.get_versions(env.id, version)
    ids_code_lost = [(c.environment, c.resource, c.version) for c in code_list]
    assert len(code_list) == 2
    assert (code1.environment, code1.resource, code1.version) in ids_code_lost
    assert (code2.environment, code2.resource, code2.version) in ids_code_lost
    code_list = await data.Code.get_versions(env.id, version + 1)
    assert len(code_list) == 1
    code = code_list[0]
    assert (code.environment, code.resource, code.version) == (code3.environment, code3.resource, code3.version)
    code_list = await data.Code.get_versions(env.id, version + 2)
    assert len(code_list) == 1
    assert (code_list[0].environment, code_list[0].resource, code_list[0].version, code_list[0].source_refs) == (
        code3.environment,
        code3.resource,
        code3.version + 1,
        code3.source_refs,
    )
    code_list = await data.Code.get_versions(env.id, version + 3)
    assert len(code_list) == 0

    # env2
    code_list = await data.Code.get_versions(env2.id, code3.version)
    assert len(code_list) == 1
    code_list = await data.Code.get_versions(env2.id, code3.version + 1)
    assert len(code_list) == 0

    # make sure deleting the base code does not delete the copied code
    await code3.delete()
    assert len(await data.Code.get_versions(env.id, code3.version)) == 0
    assert len(await data.Code.get_versions(env.id, code3.version + 1)) == 1


async def test_parameter(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    time1 = datetime.datetime(2018, 7, 14, 12, 30)
    time2 = datetime.datetime(2018, 7, 16, 12, 30)
    time3 = datetime.datetime(2018, 7, 12, 12, 30)

    parameters = []
    for current_time in [time1, time2, time3]:
        t = current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")
        parameter = data.Parameter(
            name="param_" + t, value="test_val_" + t, environment=env.id, source="test", updated=current_time
        )
        parameters.append(parameter)
        await parameter.insert()

    updated_before = await data.Parameter.get_updated_before(datetime.datetime(2018, 7, 12, 12, 30))
    assert len(updated_before) == 0
    updated_before = await data.Parameter.get_updated_before(datetime.datetime(2018, 7, 14, 12, 30))
    assert len(updated_before) == 1
    assert (updated_before[0].environment, updated_before[0].name) == (parameters[2].environment, parameters[2].name)
    updated_before = await data.Parameter.get_updated_before(datetime.datetime(2018, 7, 15, 12, 30))
    list_of_ids = [(x.environment, x.name) for x in updated_before]
    assert len(updated_before) == 2
    assert (parameters[0].environment, parameters[0].name) in list_of_ids
    assert (parameters[2].environment, parameters[2].name) in list_of_ids


async def test_parameter_list_parameters(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    metadata_param1 = {"test1": "testval1", "test2": "testval2"}
    parameter1 = data.Parameter(name="param1", value="val", environment=env.id, source="test", metadata=metadata_param1)
    await parameter1.insert()

    metadata_param2 = {"test3": "testval3"}
    parameter2 = data.Parameter(name="param2", value="val", environment=env.id, source="test", metadata=metadata_param2)
    await parameter2.insert()

    results = await data.Parameter.list_parameters(env.id, **{"test1": "testval1"})
    assert len(results) == 1
    assert (results[0].environment, results[0].name) == (parameter1.environment, parameter1.name)

    results = await data.Parameter.list_parameters(env.id, **{"test1": "testval1", "test2": "testval2"})
    assert len(results) == 1
    assert (results[0].environment, results[0].name) == (parameter1.environment, parameter1.name)

    results = await data.Parameter.list_parameters(env.id, **{})
    assert len(results) == 2


async def test_dryrun(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={})
    await cm.insert()

    dryrun = await data.DryRun.create(env.id, version, 10, 5)

    resource_version_id = "std::File[agent1,path=/etc/motd],v=%s" % version
    dryrun_data = {"id": resource_version_id, "changes": {}}
    await data.DryRun.update_resource(dryrun.id, resource_version_id, dryrun_data)

    dryrun_retrieved = await data.DryRun.get_by_id(dryrun.id)
    assert dryrun_retrieved.todo == 4
    key = str(uuid.uuid5(dryrun.id, resource_version_id))
    assert dryrun_retrieved.resources[key]["changes"] == {}
    assert dryrun_retrieved.resources[key]["id"] == resource_version_id


async def test_reports_append(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    started1 = datetime.datetime(2018, 7, 14, 12, 30)
    started2 = datetime.datetime(2018, 7, 16, 12, 30)
    started3 = datetime.datetime(2018, 7, 12, 12, 30)

    compiles = []
    for started in [started1, started2, started3]:
        completed = started + datetime.timedelta(minutes=30)
        compile = data.Compile(environment=env.id, started=started, completed=completed)
        await compile.insert()
        compiles.append(compile)


async def test_compile_get_reports(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # Compile 1
    started = datetime.datetime(2018, 7, 15, 12, 30)
    completed = datetime.datetime(2018, 7, 15, 13, 00)
    compile1 = data.Compile(environment=env.id, started=started, completed=completed)
    await compile1.insert()

    report1 = data.Report(started=datetime.datetime.now(), command="cmd", name="test", compile=compile1.id)
    await report1.insert()

    report2 = data.Report(started=datetime.datetime.now(), command="cmd", name="test", compile=compile1.id)
    await report2.insert()

    await report1.update_streams("aaaa")
    await report1.update_streams("aaaa", "eeee")

    report1 = await data.Report.get_by_id(report1.id)
    assert report1.outstream == "aaaaaaaa"
    assert report1.errstream == "eeee"


async def test_compile_get_latest(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    env2 = data.Environment(name="devx", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    # Compile 1
    started = datetime.datetime(2018, 7, 15, 12, 30)
    completed = datetime.datetime(2018, 7, 15, 13, 00)
    compile1 = data.Compile(environment=env.id, started=started, completed=completed, handled=True)
    await compile1.insert()

    # Compile 2 (later)
    started = datetime.datetime(2017, 7, 15, 12, 30)
    completed = datetime.datetime(2019, 7, 15, 13, 00)
    compile2 = data.Compile(environment=env.id, started=started, completed=completed, handled=False)
    await compile2.insert()

    # Compile 3 (later and other env)
    started = datetime.datetime(2022, 7, 15, 12, 30)
    completed = datetime.datetime(2022, 7, 15, 13, 00)
    compile3 = data.Compile(environment=env2.id, started=started, completed=completed)
    await compile3.insert()

    # Compile 3 (later and not complete)
    started = datetime.datetime(2024, 7, 15, 12, 30)
    completed = datetime.datetime(2024, 7, 15, 13, 00)
    compile4 = data.Compile(environment=env2.id, started=started)
    await compile4.insert()

    assert (await data.Compile.get_last_run(env.id)).id == compile2.id
    assert sorted([x.id for x in await data.Compile.get_unhandled_compiles()]) == sorted([compile2.id, compile3.id])


async def test_compile_get_next(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    env2 = data.Environment(name="dev2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    # Compile 1
    requested = datetime.datetime(2018, 7, 15, 12, 30)
    completed = datetime.datetime(2018, 7, 15, 13, 00)
    compile1 = data.Compile(environment=env.id, requested=requested, completed=completed)
    await compile1.insert()

    # Compile 2 (later)
    requested = datetime.datetime(2019, 7, 15, 12, 30)
    started = datetime.datetime(2019, 7, 15, 15, 00)
    compile2 = data.Compile(environment=env.id, requested=requested, started=started)
    await compile2.insert()

    # Compile 3 (later)
    requested = datetime.datetime(2020, 7, 15, 12, 30)
    started = datetime.datetime(2019, 7, 15, 13, 00)
    compile3 = data.Compile(environment=env.id, requested=requested, started=started)
    await compile3.insert()

    # Compile 4 (other env)
    compile4 = data.Compile(environment=env2.id, requested=requested, started=started)
    await compile4.insert()

    print(compile1.id, compile2.id, compile3.id)

    assert (await data.Compile.get_next_run(env.id)).id == compile2.id

    allenvs = await data.Compile.get_next_run_all()
    assert len(allenvs) == 2
    env_to_run = {c.environment: c.id for c in allenvs}
    assert env_to_run[env.id] == compile2.id
    assert env_to_run[env2.id] == compile4.id


async def test_compile_get_report(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # Compile 1
    started = datetime.datetime(2018, 7, 15, 12, 30).astimezone()
    completed = datetime.datetime(2018, 7, 15, 13, 00).astimezone()
    compile1 = data.Compile(environment=env.id, started=started, completed=completed)
    await compile1.insert()

    report_of_compile = await data.Compile.get_report(compile1.id)
    assert report_of_compile["reports"] == []

    report11 = data.Report(
        started=datetime.datetime.now(), completed=datetime.datetime.now(), command="cmd", name="test", compile=compile1.id
    )
    await report11.insert()
    report12 = data.Report(
        started=datetime.datetime.now(), completed=datetime.datetime.now(), command="cmd", name="test", compile=compile1.id
    )
    await report12.insert()

    # Compile 2
    compile2 = data.Compile(environment=env.id)
    await compile2.insert()
    report21 = data.Report(
        started=datetime.datetime.now(), completed=datetime.datetime.now(), command="cmd", name="test", compile=compile2.id
    )
    await report21.insert()

    report_of_compile = await data.Compile.get_report(compile1.id)
    assert report_of_compile["id"] == compile1.id
    assert report_of_compile["started"] == started
    assert report_of_compile["completed"] == completed
    reports = report_of_compile["reports"]
    report_ids = [r["id"] for r in reports]
    assert len(reports) == 2
    assert report11.id in report_ids
    assert report12.id in report_ids

    report_of_compile = await data.Compile.get_report(compile2.id)
    reports = report_of_compile["reports"]
    assert len(reports) == 1


async def test_match_tables_in_db_against_table_definitions_in_orm(
    postgres_db, database_name, postgresql_client, init_dataclasses_and_load_schema
):
    table_names = await postgresql_client.fetch(
        "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public'"
    )
    table_names_in_database = [x["table_name"] for x in table_names]
    table_names_in_classes_list = [x.__name__.lower() for x in data._classes]
    # Schema management table is not in classes list
    # Join tables on resource and resource action is not in the classes list
    assert len(table_names_in_classes_list) + 2 == len(table_names_in_database)
    for item in table_names_in_classes_list:
        assert item in table_names_in_database


async def test_purgelog_test(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm.insert()

    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=1",
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 14, 30),
        attributes={"path": "/etc/file2"},
    )
    await res1.insert()

    # ResourceAction 1
    timestamp_ra1 = datetime.datetime.now() - datetime.timedelta(days=8)
    log_line_ra1 = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=1)
    action_id = uuid.uuid4()
    ra1 = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=[res1.resource_version_id],
        action_id=action_id,
        action=const.ResourceAction.store,
        started=timestamp_ra1,
        finished=datetime.datetime.now(),
        messages=[log_line_ra1],
    )
    await ra1.insert()

    res2 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file2],v=1",
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime(2018, 7, 14, 14, 30),
        attributes={"path": "/etc/file2"},
    )
    await res2.insert()

    # ResourceAction 2
    timestamp_ra2 = datetime.datetime.now() - datetime.timedelta(days=6)
    log_line_ra2 = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=2)
    action_id = uuid.uuid4()
    ra2 = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=[res2.resource_version_id],
        action_id=action_id,
        action=const.ResourceAction.store,
        started=timestamp_ra2,
        finished=datetime.datetime.now(),
        messages=[log_line_ra2],
    )
    await ra2.insert()

    assert len(await data.ResourceAction.get_list()) == 2
    await data.ResourceAction.purge_logs()
    assert len(await data.ResourceAction.get_list()) == 1
    remaining_resource_action = (await data.ResourceAction.get_list())[0]
    assert remaining_resource_action.action_id == ra2.action_id


async def test_insert_many(init_dataclasses_and_load_schema, postgresql_client):
    project1 = data.Project(name="proj1")
    project2 = data.Project(name="proj2")
    projects = [project1, project2]
    await data.Project.insert_many(projects)

    result = await data.Project.get_list()
    project_names_in_result = [res.name for res in result]

    assert len(project_names_in_result) == 2
    assert sorted(["proj1", "proj2"]) == sorted(project_names_in_result)


async def test_resources_json(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        deployed=True,
    )
    await cm.insert()

    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::File[agent1,path=/etc/file1],v=%s" % version,
        status=const.ResourceState.deployed,
        last_deploy=datetime.datetime.now(),
        attributes={"attr": [{"a": 1, "b": "c"}]},
    )
    await res1.insert()

    id = Id.parse_resource_version_id(res1.resource_version_id)
    res = await data.Resource.get_one(environment=res1.environment, resource_id=id.resource_str(), model=id.version)

    assert res1.attributes == res.attributes


async def test_update_to_none_value(init_dataclasses_and_load_schema):
    """
    Verify that a field with a default value can be set to None if that field is nullable.
    """
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()

    # Default value is empty string
    assert env.repo_url is not None
    assert env.repo_url == ""
    # Set value to None
    await env.update(repo_url=None)
    # Assert None value
    assert env.repo_url is None

    env = await data.Environment.get_by_id(env.id)
    assert env.repo_url is None


async def test_query_resource_actions_simple(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={})
    await cm.insert()

    # Add multiple versions of model
    for i in range(1, 11):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.datetime.now() + datetime.timedelta(minutes=i),
            total=1,
            version_info={},
        )
        await cm.insert()

    # Add resource action for motd
    motd_first_start_time = datetime.datetime.now()

    async def make_file_resourceaction(version, offset=0, path="/etc/motd", log_level=logging.INFO):
        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id=f"std::File[agent1,path={path}],v={version}",
            status=const.ResourceState.deployed,
            last_deploy=motd_first_start_time + datetime.timedelta(minutes=offset),
            attributes={"attr": [{"a": 1, "b": "c"}], "path": "/etc/motd"},
        )
        await res1.insert()
        action_id = uuid.uuid4()
        resource_action = data.ResourceAction(
            environment=env.id,
            version=version,
            resource_version_ids=[res1.resource_version_id],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=motd_first_start_time + datetime.timedelta(minutes=offset),
        )
        await resource_action.insert()
        resource_action.add_logs([data.LogLine.log(log_level, "Successfully stored version %(version)d", version=i)])
        await resource_action.save()

    await make_file_resourceaction(version, log_level=LogLevel.WARNING)
    # Add resource for motd
    for i in range(1, 11):
        await make_file_resourceaction(i, i)

    # Add resource for file
    resource_ids = []
    for i in range(5):
        path = "/etc/file" + str(i)
        key = "std::File[agent1,path=" + path + "]"
        res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
        await res1.insert()
        resource_ids.append((res1.environment, res1.resource_version_id))

    # Add resource actions for file
    for i in range(5):
        resource_action = data.ResourceAction(
            environment=env.id,
            version=version,
            resource_version_ids=[f"std::File[agent1,path=/etc/file{str(i)}],v={version}"],
            action_id=uuid.uuid4(),
            action=const.ResourceAction.dryrun,
            started=datetime.datetime.now() + datetime.timedelta(minutes=i),
        )
        await resource_action.insert()

    # Add resource and resourceaction for host
    key = "std::Host[agent1,name=host1]"
    resource_version_id = key + ",v=%d" % version
    res1 = data.Resource.new(environment=env.id, resource_version_id=resource_version_id, attributes={"name": "host1"})
    await res1.insert()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=[resource_version_id],
        action_id=uuid.uuid4(),
        action=const.ResourceAction.deploy,
        started=datetime.datetime.now(),
    )
    await resource_action.insert()

    # Add resource and resourceaction for host with different agent
    key = "std::Host[agent2,name=host1]"
    resource_version_id = key + ",v=%d" % version
    res1 = data.Resource.new(environment=env.id, resource_version_id=resource_version_id, attributes={"name": "host1"})
    await res1.insert()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=[resource_version_id],
        action_id=uuid.uuid4(),
        action=const.ResourceAction.deploy,
        started=datetime.datetime.now(),
    )
    await resource_action.insert()

    # Get all versions of the "/etc/motd" file
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, attribute="path", attribute_value="/etc/motd")
    assert len(resource_actions) == 11

    # Get everything that starts with "/etc/file"
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, attribute="path", attribute_value="/etc/file")
    assert len(resource_actions) == 5

    # Get all files
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, resource_type="std::File")
    assert len(resource_actions) == 16

    # Get everything from agent 2
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, agent="agent2")
    assert len(resource_actions) == 1

    # Get everything of type host
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, resource_type="std::Host")
    assert len(resource_actions) == 2

    # Get only the last 5 file resource actions
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, resource_type="std::File", limit=5)
    assert len(resource_actions) == 5

    # Query actions older than the first
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=5,
        last_timestamp=motd_first_start_time,
    )
    assert len(resource_actions) == 0

    # Query the latest actions
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=5,
        last_timestamp=motd_first_start_time + datetime.timedelta(minutes=12),
    )
    assert len(resource_actions) == 5
    assert [resource_action.version for resource_action in resource_actions] == [10, 9, 8, 7, 6], resource_actions

    # Continue from the last one's timestamp
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=5,
        last_timestamp=resource_actions[-1].started,
    )
    assert len(resource_actions) == 5
    assert [resource_action.version for resource_action in resource_actions] == [5, 4, 3, 2, 1]

    # Query with first_timestamp
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=5,
        first_timestamp=motd_first_start_time - datetime.timedelta(milliseconds=1),
    )
    assert len(resource_actions) == 5
    assert [resource_action.version for resource_action in resource_actions] == [4, 3, 2, 1, version]

    # Query actions with WARNING level logs
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, log_severity="WARNING")
    assert len(resource_actions) == 1
    assert resource_actions[0].messages[0]["level"] == "WARNING"

    await utils.resource_action_consistency_check()


async def test_query_resource_actions_non_unique_timestamps(init_dataclasses_and_load_schema):
    """
    Test querying resource actions that have non unique timestamps, with pagination, using an explicit start and end time
    as well as limit.
    """
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={})
    await cm.insert()
    # Add multiple versions of model
    for i in range(1, 12):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.datetime.now(),
            total=1,
            version_info={},
        )
        await cm.insert()

    for i in range(1, 12):
        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % str(i),
            status=const.ResourceState.deployed,
            last_deploy=datetime.datetime.now() + datetime.timedelta(minutes=i),
            attributes={"attr": [{"a": 1, "b": "c"}], "path": "/etc/motd"},
        )
        await res1.insert()

    # Add resource actions for motd
    motd_first_start_time = datetime.datetime.now()
    earliest_action_id = uuid.uuid4()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=1,
        resource_version_ids=[f"std::File[agent1,path=/etc/motd],v={1}"],
        action_id=earliest_action_id,
        action=const.ResourceAction.deploy,
        started=motd_first_start_time - datetime.timedelta(minutes=1),
    )
    await resource_action.insert()
    resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=1)])
    await resource_action.save()

    action_ids_with_the_same_timestamp = []
    for i in range(2, 7):
        action_id = uuid.uuid4()
        action_ids_with_the_same_timestamp.append(action_id)
        resource_action = data.ResourceAction(
            environment=env.id,
            version=i,
            resource_version_ids=[f"std::File[agent1,path=/etc/motd],v={i}"],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=motd_first_start_time,
        )
        await resource_action.insert()
        resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=i)])
        await resource_action.save()
    action_ids_with_the_same_timestamp = sorted(action_ids_with_the_same_timestamp, reverse=True)
    action_ids_with_increasing_timestamps = []
    for i in range(7, 12):
        action_id = uuid.uuid4()
        action_ids_with_increasing_timestamps.append(action_id)
        resource_action = data.ResourceAction(
            environment=env.id,
            version=i,
            resource_version_ids=[f"std::File[agent1,path=/etc/motd],v={i}"],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=motd_first_start_time + datetime.timedelta(minutes=i),
        )
        await resource_action.insert()
        resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=i)])
        await resource_action.save()
    action_ids_with_increasing_timestamps = action_ids_with_increasing_timestamps[::-1]

    # Query actions with pagination, going backwards in time
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=2,
        last_timestamp=motd_first_start_time + datetime.timedelta(minutes=6),
    )
    assert len(resource_actions) == 2
    assert [resource_action.action_id for resource_action in resource_actions] == action_ids_with_the_same_timestamp[:2]
    # Querying pages based on last_timestamp and action_id from the previous query
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=2,
        action_id=resource_actions[1].action_id,
        last_timestamp=resource_actions[1].started,
    )
    assert len(resource_actions) == 2
    assert [resource_action.action_id for resource_action in resource_actions] == action_ids_with_the_same_timestamp[2:4]
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=2,
        action_id=resource_actions[1].action_id,
        last_timestamp=resource_actions[1].started,
    )
    assert len(resource_actions) == 2
    assert [resource_action.action_id for resource_action in resource_actions] == [
        action_ids_with_the_same_timestamp[-1],
        earliest_action_id,
    ]

    # Query actions going forward in time
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=4,
        first_timestamp=motd_first_start_time - datetime.timedelta(seconds=30),
    )
    assert len(resource_actions) == 4
    assert [resource_action.action_id for resource_action in resource_actions] == action_ids_with_the_same_timestamp[1:5]
    # Page forward in time
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        limit=4,
        action_id=resource_actions[0].action_id,
        first_timestamp=resource_actions[0].started,
    )
    assert len(resource_actions) == 4
    #  First three of the increasing ones and the first of the ones that share a timestamp
    expected_ids_on_page = action_ids_with_increasing_timestamps[2:] + [action_ids_with_the_same_timestamp[0]]
    assert [resource_action.action_id for resource_action in resource_actions] == expected_ids_on_page


async def test_get_last_non_deploying_state_for_dependencies(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    async def assert_last_non_deploying_state(
        environment: uuid.UUID,
        resource_version_id: ResourceVersionIdStr,
        expected_states: Dict[ResourceVersionIdStr, const.ResourceState],
    ) -> None:
        rvid_to_resource_state = await data.Resource.get_last_non_deploying_state_for_dependencies(
            environment=environment, resource_version_id=Id.parse_id(resource_version_id)
        )
        assert expected_states == rvid_to_resource_state

    # V1
    cm = data.ConfigurationModel(version=1, environment=env.id)
    await cm.insert()

    rid_r1_v1 = "std::File[agent1,path=/etc/file1]"
    rid_r2_v1 = "std::File[agent1,path=/etc/file2]"
    rid_r3_v1 = "std::File[agent1,path=/etc/file3]"
    rid_r4_v1 = "std::File[agent1,path=/etc/file4]"

    rvid_r1_v1 = rid_r1_v1 + ",v=1"
    rvid_r2_v1 = rid_r2_v1 + ",v=1"
    rvid_r3_v1 = rid_r3_v1 + ",v=1"
    rvid_r4_v1 = rid_r4_v1 + ",v=1"

    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.available,
        last_non_deploying_status=const.NonDeployingResourceState.available,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "requires": [rid_r2_v1, rid_r3_v1, rid_r4_v1]},
    ).insert()
    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.deployed,
        last_non_deploying_status=const.NonDeployingResourceState.deployed,
        resource_version_id=rvid_r2_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()
    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.failed,
        last_non_deploying_status=const.NonDeployingResourceState.failed,
        resource_version_id=rvid_r3_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()
    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.available,
        last_non_deploying_status=const.NonDeployingResourceState.available,
        resource_version_id=rvid_r4_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()

    expected_states = {
        rvid_r2_v1: const.ResourceState.deployed,
        rvid_r3_v1: const.ResourceState.failed,
        rvid_r4_v1: const.ResourceState.available,
    }
    await assert_last_non_deploying_state(env.id, rvid_r1_v1, expected_states=expected_states)
    await assert_last_non_deploying_state(env.id, rvid_r2_v1, expected_states={})
    await assert_last_non_deploying_state(env.id, rvid_r3_v1, expected_states={})
    await assert_last_non_deploying_state(env.id, rvid_r4_v1, expected_states={})

    # V2
    cm = data.ConfigurationModel(version=2, environment=env.id)
    await cm.insert()

    rid_r2_v2 = "std::File[agent1,path=/etc/file2]"
    rid_r3_v2 = "std::File[agent1,path=/etc/file3]"

    rvid_r1_v2 = cast(ResourceVersionIdStr, "std::File[agent1,path=/etc/file1],v=2")
    rvid_r2_v2 = cast(ResourceVersionIdStr, "std::File[agent1,path=/etc/file2],v=2")
    rvid_r3_v2 = cast(ResourceVersionIdStr, "std::File[agent1,path=/etc/file3],v=2")
    rvid_r4_v2 = cast(ResourceVersionIdStr, "std::File[agent1,path=/etc/file4],v=2")
    rvid_r5_v2 = cast(ResourceVersionIdStr, "std::File[agent1,path=/etc/file5],v=2")

    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.skipped,
        last_non_deploying_status=const.NonDeployingResourceState.skipped,
        resource_version_id=rvid_r1_v2,
        attributes={"purge_on_delete": False, "requires": [rid_r2_v2, rid_r3_v2]},
    ).insert()
    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.failed,
        last_non_deploying_status=const.NonDeployingResourceState.failed,
        resource_version_id=rvid_r2_v2,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()
    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.deployed,
        last_non_deploying_status=const.NonDeployingResourceState.deployed,
        resource_version_id=rvid_r3_v2,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()
    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.deployed,
        last_non_deploying_status=const.NonDeployingResourceState.deployed,
        resource_version_id=rvid_r4_v2,
        attributes={"purge_on_delete": False, "requires": [rid_r3_v2]},
    ).insert()
    await data.Resource.new(
        environment=env.id,
        status=const.ResourceState.deployed,
        last_non_deploying_status=const.NonDeployingResourceState.deployed,
        resource_version_id=rvid_r5_v2,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()

    expected_states = {
        rvid_r2_v2: const.ResourceState.failed,
        rvid_r3_v2: const.ResourceState.deployed,
    }
    await assert_last_non_deploying_state(env.id, rvid_r1_v2, expected_states=expected_states)
    await assert_last_non_deploying_state(env.id, rvid_r2_v2, expected_states={})
    await assert_last_non_deploying_state(env.id, rvid_r3_v2, expected_states={})
    await assert_last_non_deploying_state(env.id, rvid_r4_v2, expected_states={rvid_r3_v2: const.ResourceState.deployed})
    await assert_last_non_deploying_state(env.id, rvid_r5_v2, expected_states={})


def test_validate_combined_filter():
    combined_filter, values = data.Resource.get_filter_for_combined_query_type(
        "status", {QueryType.IS_NOT_NULL: None, QueryType.CONTAINS: ["deployed"]}, 1
    )
    assert combined_filter == "status IS NOT NULL AND status = ANY ($1)"
    assert values == [["deployed"]]
    combined_filter, values = data.Resource.get_filter_for_combined_query_type(
        "status",
        {QueryType.IS_NOT_NULL: None, QueryType.CONTAINS: ["deployed", "orphaned"], QueryType.NOT_CONTAINS: ["deploying"]},
        1,
    )
    assert combined_filter == "status IS NOT NULL AND status = ANY ($1) AND NOT (status = ANY ($2))"
    assert values == [["deployed", "orphaned"], ["deploying"]]


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


async def test_retrieve_optional_field_no_default(init_dataclasses_and_load_schema):
    """
    verify that an optional field with no default value (returncode) exists on an object retrieved from the DB.
    """
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    started = datetime.datetime(2018, 7, 15, 12, 30)
    completed = datetime.datetime(2018, 7, 15, 13, 00)
    compile1 = data.Compile(environment=env.id, started=started, completed=completed)
    await compile1.insert()

    report = data.Report(started=datetime.datetime.now(), command="cmd", name="test", compile=compile1.id)
    await report.insert()

    report = await data.Report.get_by_id(report.id)
    assert report.returncode is None
