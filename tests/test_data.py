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
from typing import Iterator, Optional

import asyncpg
import pytest
from asyncpg import Connection, ForeignKeyViolationError, Pool

import utils
from inmanta import const, data
from inmanta.const import AgentStatus, LogLevel
from inmanta.data import model  # noqa
from inmanta.data import ArgumentCollector, QueryType
from inmanta.deploy import state
from inmanta.resources import Id
from inmanta.types import ResourceIdStr, ResourceVersionIdStr


async def make_resource_set(environment: uuid.UUID, version: list[int]) -> data.ResourceSet:
    resource_set = data.ResourceSet(environment=environment, id=uuid.uuid4())
    await utils.insert_with_link_to_configuration_model(resource_set, versions=version)
    return resource_set


async def test_connect_too_small_connection_pool(postgres_db, database_name: str):
    pool: Pool = await data.connect_pool(
        postgres_db.host,
        postgres_db.port,
        database_name,
        postgres_db.user,
        postgres_db.password,
        create_db_schema=False,
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
        await data.disconnect_pool()


async def test_connect_default_parameters(postgres_db, database_name: str, create_db_schema: bool = False):
    pool: Pool = await data.connect_pool(
        postgres_db.host, postgres_db.port, database_name, postgres_db.user, postgres_db.password, create_db_schema
    )
    assert pool is not None
    try:
        async with pool.acquire() as connection:
            assert connection is not None
    finally:
        await data.disconnect_pool()


@pytest.mark.parametrize("min_size, max_size", [(-1, 1), (2, 1), (-2, -2)])
async def test_connect_invalid_parameters(postgres_db, min_size, max_size, database_name: str, create_db_schema: bool = False):
    with pytest.raises(ValueError):
        await data.connect_pool(
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
    """
    Basic connectivity test: using an incorrect port raises an error
    """
    port = unused_tcp_port_factory()
    with pytest.raises(OSError):
        await data.connect_pool("localhost", port, database_name, "testuser", None)


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
    all_db_document_classes: abc.Set[type[data.BaseDocument]] = utils.get_all_subclasses(data.BaseDocument) - {
        data.BaseDocument
    }
    exclude_enums = [state.HandlerResult, state.Blocked]  # These enums are modelled in the db using a varchar
    for cls in all_db_document_classes:
        enums: abc.Mapping[str, data.Field] = {
            name: field
            for name, field in cls.get_field_metadata().items()
            if issubclass(field.field_type, enum.Enum) and field.field_type not in exclude_enums
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
        cm = data.ConfigurationModel(version=version, environment=env.id, is_suitable_for_partial_compiles=False)
        await cm.insert()
        resource_set = await make_resource_set(env.id, [version])

        resource_ids = []
        for i in range(5):
            name = "file" + str(i)
            key = "std::testing::NullResource[agent1,name=" + name + "]"
            rvid = key + ",v=%d" % version
            res1 = data.Resource.new(
                environment=env.id,
                resource_version_id=rvid,
                resource_set=resource_set,
                attributes={"name": name},
            )
            await res1.insert()
            resource_ids.append((res1.environment, rvid))

        unknown_parameter = data.UnknownParameter(name="test", environment=env.id, version=version, source="")
        await unknown_parameter.insert()

        return project, env, agent_proc, [agi1, agi2], agent, resource_ids, unknown_parameter

    async def assert_project_exists(project, env, agent_proc, agent_instances, agent, resource_ids, unknown_parameter, exists):
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
        for environment, resource_version_id in resource_ids:
            id = Id.parse_id(resource_version_id)
            assert func(
                await data.Resource.get_resource_for_version(
                    environment=environment, resource_id=id.resource_str(), version=id.version
                )
            )
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
    cm = data.ConfigurationModel(version=version, environment=env.id, is_suitable_for_partial_compiles=False)
    await cm.insert()
    resource_set = await make_resource_set(env.id, [version])

    resource_ids = []
    for i in range(5):
        name = "file" + str(i)
        key = "std::testing::NullResource[agent1,name=" + name + "]"
        rvid = key + ",v=%d" % version
        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id=rvid,
            resource_set=resource_set,
            attributes={"name": name},
        )
        await res1.insert()
        resource_ids.append((res1.environment, rvid))

    resource_version_ids = [
        f"std::testing::NullResource[agent1,name=file0],v={version}",
        f"std::testing::NullResource[agent1,name=file1],v={version}",
    ]
    resource_action = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=resource_version_ids,
        action_id=uuid.uuid4(),
        action=const.ResourceAction.deploy,
        started=datetime.datetime.now(),
    )
    await resource_action.insert()

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
            await data.Resource.get_resource_for_version(
                environment=environment, resource_id=id.resource_str(), version=id.version
            )
        ) is not None
    assert await data.ResourceAction.get_by_id(resource_action.action_id) is not None
    assert (await data.UnknownParameter.get_by_id(unknown_parameter.id)) is not None
    assert (await env.get(data.AUTO_DEPLOY)) is True

    await env.clear()

    assert (await data.Project.get_by_id(project.id)) is not None
    assert (await data.Environment.get_by_id(env.id)) is not None
    assert (await data.AgentProcess.get_one(sid=agent_proc.sid)) is None
    assert (await data.AgentInstance.get_by_id(agi1.id)) is None
    assert (await data.AgentInstance.get_by_id(agi2.id)) is None
    assert (await data.Agent.get_one(environment=agent.environment, name=agent.name)) is None
    for environment, resource_version_id in resource_ids:
        id = Id.parse_id(resource_version_id)
        assert (
            await data.Resource.get_resource_for_version(
                environment=environment, resource_id=id.resource_str(), version=id.version
            )
        ) is None
    assert await data.ResourceAction.get_by_id(resource_action.action_id) is None
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


async def test_population_settings_dict_on_get_of_setting(init_dataclasses_and_load_schema):
    """
    Verify that executing the `Environment.get(<name_env_setting>)` method on an environment object which doesn't have the
    <name_env_setting> in its settings dictionary, doesn't override the value of the setting with the default value in
    the database when another transaction has written a value for this setting to the database.
    """
    # Create project and environment
    project = data.Project(name="proj")
    await project.insert()
    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    async def assert_setting_in_db(expected_available_versions_to_keep: int) -> None:
        """
        Verify that the state of the setting.available_versions_to_keep setting in the database matches the given
        expected_available_versions_to_keep.
        """
        async with data.Environment.get_connection() as connection:
            query = f"SELECT setting->'{data.AVAILABLE_VERSIONS_TO_KEEP}' FROM {data.Environment.table_name()} WHERE id=$1"
            result = await connection.fetchval(query, env.id)
            assert int(result) == expected_available_versions_to_keep

    # Get two environment object with an empty settings dict.
    env_obj1 = await data.Environment.get_by_id(env.id)
    env_obj2 = await data.Environment.get_by_id(env.id)

    # Add AVAILABLE_VERSIONS_TO_KEEP key to settings dict
    await env_obj1.set(data.AVAILABLE_VERSIONS_TO_KEEP, 5)

    assert assert_setting_in_db(5)
    # Make sure that get for AVAILABLE_VERSIONS_TO_KEEP on env_obj2 object doesn't override setting with default value.
    assert await env_obj2.get(data.AVAILABLE_VERSIONS_TO_KEEP) == 5
    assert assert_setting_in_db(5)


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


@pytest.mark.parametrize("env1_halted", [True, False])
@pytest.mark.parametrize("env2_halted", [True, False])
async def test_agentprocess_cleanup(init_dataclasses_and_load_schema, postgresql_client, env1_halted, env2_halted):
    # tests the agent process cleanup function with different combinations of halted environments

    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="env1", project=project.id, repo_url="", repo_branch="")
    await env1.insert()
    env2 = data.Environment(name="env2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    now = datetime.datetime.now()

    async def insert_agent_proc_and_instances(
        env_id: uuid.UUID, hostname: str, expired_proc: Optional[datetime.datetime], expired_instances: list[datetime.datetime]
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

    if env1_halted:
        await env1.update_fields(halted=True)
    if env2_halted:
        await env2.update_fields(halted=True)

    # Run cleanup twice to verify stability
    for i in range(2):
        # Perform cleanup
        await data.AgentProcess.cleanup(nr_expired_records_to_keep=1)
        # Assert outcome
        # Halting env1 has no impact on the cleanup: an expired instance will be kept in both cases
        # Halting env2 has an impact on the cleanup: if it's halted 5 expired instances in 2 processes will not be removed.
        await verify_nr_of_records(env1.id, hostname="proc1", expected_nr_procs=2, expected_nr_instances=2)
        await verify_nr_of_records(env1.id, hostname="proc2", expected_nr_procs=1, expected_nr_instances=1)
        await verify_nr_of_records(
            env2.id, hostname="proc2", expected_nr_procs=4 if env2_halted else 2, expected_nr_instances=8 if env2_halted else 3
        )
        # Assert records are deleted in the correct order
        query = """
            SELECT expired
            FROM agentprocess
            WHERE environment=$1 AND hostname=$2 AND expired IS NOT NULL
        """
        result = await postgresql_client.fetch(query, env2.id, "proc2")
        assert len(result) == 3 if env2_halted else 1
        if len(result) == 1:
            # if the cleanup was done (env2 not halted), verify the expired record that was kept is the right one.
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

    async def assert_paused(env_paused_map: dict[uuid.UUID, bool]) -> None:
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
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()
    resource_set = await make_resource_set(env.id, [version])

    # create resources
    key = "std::testing::NullResource[agent1,name=motd]"
    res1 = data.Resource.new(
        environment=env.id, resource_version_id=key + ",v=%d" % version, resource_set=resource_set, attributes={"name": "motd"}
    )
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
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=0,
            version_info={},
            is_suitable_for_partial_compiles=False,
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
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=0,
            version_info={},
            is_suitable_for_partial_compiles=False,
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


async def test_model_get_list(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env1.insert()
    env2 = data.Environment(name="prod", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    for env in [env1, env2]:
        for i in range(2):
            cm = data.ConfigurationModel(
                environment=env.id,
                version=i,
                date=datetime.datetime.now(),
                total=0,
                version_info={},
                is_suitable_for_partial_compiles=False,
            )
            await cm.insert()
            resource_set = await make_resource_set(env.id, [i])

            for r in range(3):
                res = data.Resource.new(
                    environment=env.id,
                    resource_version_id=f"std::testing::NullResource[agent1,name=file{r}],v={i}",
                    resource_set=resource_set,
                    attributes={"purge_on_delete": False, "name": f"file{r}"},
                )
                await res.insert()

    for env in [env1, env2]:
        cms = await data.ConfigurationModel.get_list(environment=env.id)
        assert len(cms) == 2
        for c in cms:
            assert c.environment == env.id

    cms = await data.ConfigurationModel.get_list(environment=uuid.uuid4())
    assert not cms


async def test_model_serialization(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    now = datetime.datetime.now().astimezone()
    cm = data.ConfigurationModel(
        environment=env.id, version=version, date=now, total=1, version_info={}, is_suitable_for_partial_compiles=False
    )
    await cm.insert()

    resource_set = await make_resource_set(env.id, [version])

    name = "file"
    key = "std::testing::NullResource[agent1,name=" + name + "]"
    resource = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        resource_set=resource_set,
        attributes={"name": name},
    )
    await resource.insert()

    cm = await data.ConfigurationModel.get_one(environment=env.id, version=version)
    dct = cm.to_dict()
    assert dct["version"] == version
    assert dct["environment"] == env.id
    assert dct["date"] == now
    assert not dct["released"]
    assert dct["version_info"] == {}


async def test_model_delete_cascade(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    environments = []
    for i in range(0, 2):
        env = data.Environment(name=f"dev{i}", project=project.id, repo_url="", repo_branch="")
        environments.append(env.id)
        await env.insert()

        version = int(time.time())
        cm = data.ConfigurationModel(
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=0,
            version_info={},
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()

        name = "file"
        key = "std::testing::NullResource[agent1,name=" + name + "]"
        resource_set = await make_resource_set(env.id, [version])
        rvid = key + ",v=%d" % version

        resource = data.Resource.new(
            environment=env.id, resource_version_id=rvid, resource_set=resource_set, attributes={"name": name}
        )
        await resource.insert()
        parameter = data.Parameter(
            name="param",
            value="test_val",
            environment=env.id,
            source="test",
            updated=datetime.datetime.now(),
            resource_id=key,
            expires=True,
        )
        await parameter.insert()

        unknown_parameter = data.UnknownParameter(name="test", environment=env.id, version=version, source="")
        await unknown_parameter.insert()

    # delete the last cm created
    await cm.delete_cascade()

    id = Id.parse_resource_version_id(rvid)
    assert (
        await data.Resource.get_resource_for_version(
            environment=resource.environment, resource_id=id.resource_str(), version=id.version
        )
    ) is None
    assert (await data.UnknownParameter.get_by_id(unknown_parameter.id)) is None

    # Resources and Parameters on other environments remain untouched
    assert len(await data.Resource.get_list(environment=environments[0])) == 1
    assert len(await data.Parameter.get_list(environment=environments[0])) == 1
    assert len(await data.UnknownParameter.get_list(environment=environments[0])) == 1


async def test_model_get_version_nr_latest_version(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env_dev = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env_dev.insert()
    env_prod = data.Environment(name="prod", project=project.id, repo_url="", repo_branch="")
    await env_prod.insert()

    now = datetime.datetime.now()
    await data.ConfigurationModel(
        environment=env_dev.id, version=4, total=0, date=now, released=True, is_suitable_for_partial_compiles=False
    ).insert()
    await data.ConfigurationModel(
        environment=env_dev.id, version=7, total=0, date=now, released=True, is_suitable_for_partial_compiles=False
    ).insert()
    await data.ConfigurationModel(
        environment=env_dev.id, version=9, total=0, date=now, released=False, is_suitable_for_partial_compiles=False
    ).insert()

    await data.ConfigurationModel(
        environment=env_prod.id, version=15, total=0, date=now, released=False, is_suitable_for_partial_compiles=False
    ).insert()
    await data.ConfigurationModel(
        environment=env_prod.id, version=11, total=0, date=now, released=False, is_suitable_for_partial_compiles=False
    ).insert()

    assert await data.ConfigurationModel.get_version_nr_latest_version(env_dev.id) == 7
    assert await data.ConfigurationModel.get_version_nr_latest_version(env_prod.id) is None
    assert await data.ConfigurationModel.get_version_nr_latest_version(uuid.uuid4()) is None


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
        is_suitable_for_partial_compiles=False,
    )
    await cm1.insert()

    resource_set = await make_resource_set(env.id, [version])

    resource_ids = []
    for i in range(1, 11):
        rvid = "std::testing::NullResource[agent1,name=file%d],v=%d" % (i, version)
        res = data.Resource.new(
            environment=env.id,
            resource_version_id=rvid,
            resource_set=resource_set,
            attributes={"name": "motd", "purge_on_delete": True, "purged": False},
        )
        await res.insert()
        resource_ids.append(rvid)

    resources = await data.Resource.get_resources(env.id, resource_ids)
    assert len(resources) == len(resource_ids)

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
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()
    resource_set = await make_resource_set(env.id, [version])

    for i in range(1, 11):
        rvid = "std::testing::NullResource[agent1,name=file%d],v=%d" % (i, version)
        res = data.Resource.new(
            environment=env.id,
            resource_version_id=rvid,
            resource_set=resource_set,
            attributes={"name": "motd", "purge_on_delete": True, "purged": False},
        )
        await res.insert()
        resource_ids_version_one.append(rvid)

    resource_ids_version_two = []
    version += 1
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        released=True,
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    resource_set = await make_resource_set(env.id, [version])

    for i in range(11, 21):
        rvid = "std::testing::NullResource[agent2,path=file%d],v=%d" % (i, version)
        res = data.Resource.new(
            environment=env.id,
            resource_version_id=rvid,
            resource_set=resource_set,
            attributes={"name": "motd", "purge_on_delete": True, "purged": False},
        )
        await res.insert()
        resource_ids_version_two.append(rvid)

    for version in range(3, 5):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=1,
            version_info={},
            released=True,
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()

    resource_set = await make_resource_set(env.id, [3])

    async def make_with_status(i, is_undefined=False):
        rvid = "std::testing::NullResource[agent3,path=file%d],v=3" % i
        res = data.Resource.new(
            environment=env.id,
            resource_version_id=rvid,
            resource_set=resource_set,
            is_undefined=is_undefined,
            attributes={"path": "motd", "purge_on_delete": True, "purged": False},
        )
        await res.insert()
        return Id.parse_id(rvid)

    d = await make_with_status(1)
    s = await make_with_status(2)
    su = await make_with_status(3)
    u = await make_with_status(4, is_undefined=True)

    # Populate rps for version 3
    await data.ResourcePersistentState.populate_for_version(environment=env.id, model_version=3)

    # Make deployed
    rps_d = await data.ResourcePersistentState.get_one(environment=env.id, resource_id=d.resource_str())
    assert rps_d
    await rps_d.update_fields(
        last_non_deploying_status=const.NonDeployingResourceState.deployed,
        current_intent_attribute_hash="dummy-hash",
        last_deployed_attribute_hash="dummy-hash",
    )

    # Make skipped
    rps_s = await data.ResourcePersistentState.get_one(environment=env.id, resource_id=s.resource_str())
    assert rps_s
    await rps_s.update_fields(last_non_deploying_status=const.NonDeployingResourceState.skipped)

    # Make skipped for undefined
    rps_su = await data.ResourcePersistentState.get_one(environment=env.id, resource_id=su.resource_str())
    assert rps_su
    await rps_su.update_fields(blocked=state.Blocked.BLOCKED)

    # Assert state of resources

    # Mock a scheduler
    scheduler = data.Scheduler(environment=env.id, last_processed_model_version=3)
    await scheduler.insert()

    version, states = await data.Resource.get_latest_resource_states(env.id)
    assert version == 3
    assert states[d.resource_str()] == const.ResourceState.deployed
    assert states[s.resource_str()] == const.ResourceState.skipped
    assert states[su.resource_str()] == const.ResourceState.skipped_for_undefined
    assert states[u.resource_str()] == const.ResourceState.undefined

    resources = await data.Resource.get_resources_for_version(env.id, 1)
    assert len(resources) == 10
    assert sorted(resource_ids_version_one) == sorted([x.resource_id + ",v=1" for x in resources])
    resources = await data.Resource.get_resources_for_version(env.id, 2)
    assert len(resources) == 10
    assert sorted(resource_ids_version_two) == sorted([x.resource_id + ",v=2" for x in resources])
    resources = await data.Resource.get_resources_for_version(env.id, 4)
    assert resources == []

    resources = await data.Resource.get_resources_for_version(env.id, 3)
    assert len(resources) == 4
    assert sorted([x.resource_id + ",v=3" for x in resources]) == sorted(
        [d.resource_version_str(), s.resource_version_str(), u.resource_version_str(), su.resource_version_str()]
    )


async def test_get_resources_in_latest_version(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for version in range(1, 3):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=2,
            version_info={},
            released=True,
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()
        resource_set = await make_resource_set(env.id, [version])

        for i in range(1, 3):
            res = data.Resource.new(
                environment=env.id,
                resource_version_id="std::testing::NullResource[agent1,name=file%d],v=%d" % (i, version),
                resource_set=resource_set,
                attributes={"name": f"motd{i}", "purge_on_delete": True, "purged": False},
            )
            await res.insert()

    resources = await data.Resource.get_resources_in_latest_version_as_dto(
        env.id,
        "std::testing::NullResource",
        {"name": "motd1", "purge_on_delete": True},
    )
    assert len(resources) == 1
    resource = resources[0]
    assert resource.resource_id == "std::testing::NullResource[agent1,name=file1]"
    assert resource.resource_set is None  # shared set
    assert resource.attributes == {"name": "motd1", "purge_on_delete": True, "purged": False}

    cm = data.ConfigurationModel(
        environment=env.id,
        version=3,
        date=datetime.datetime.now(),
        total=2,
        version_info={},
        released=True,
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()
    resources = await data.Resource.get_resources_in_latest_version_as_dto(
        env.id, "std::testing::NullResource", {"name": "motd1", "purge_on_delete": True}
    )
    assert len(resources) == 0


async def test_model_get_resources_for_version_optional_args(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=3,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    resource_set = await make_resource_set(env.id, [version])

    async def insert_resource(env_id, version, agent_name, name, is_undefined):
        resource_version_id = f"std::testing::NullResource[{agent_name},name={name}],v={version}"
        resource = data.Resource.new(
            environment=env_id,
            resource_version_id=resource_version_id,
            resource_set=resource_set,
            attributes={"name": name},
            is_undefined=is_undefined,
        )
        await resource.insert()

    await insert_resource(env.id, version, "agent1", "path1", is_undefined=False)
    await insert_resource(env.id, version, "agent2", "path2", is_undefined=False)
    await insert_resource(env.id, version, "agent1", "path3", is_undefined=True)

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
        is_suitable_for_partial_compiles=False,
    )
    await cm1.insert()
    resource_set = await make_resource_set(env.id, [version])

    routes = {"8.0.0.0/8": "1.2.3.4", "0.0.0.0/0": "127.0.0.1"}
    rvid = "std::testing::NullResource[agent1,name=router],v=%d" % version
    res = data.Resource.new(
        environment=env.id,
        resource_version_id=rvid,
        resource_set=resource_set,
        attributes={"name": "router", "purge_on_delete": True, "purged": False, "routes": routes},
    )
    await res.insert()

    resources = await data.Resource.get_resources(env.id, [rvid])
    assert len(resources) == 1

    assert resources[0].attributes["routes"] == routes


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
            is_suitable_for_partial_compiles=False,
        )
        await cm1.insert()

    rvids = [f"std::testing::NullResource[agent1,name=file1],v={i}" for i in range(1, 4)]
    resource_sets = [await make_resource_set(env.id, [i]) for i in range(1, 4)]
    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id=rvids[0],
        resource_set=resource_sets[0],
        attributes={"name": "file1", "purge_on_delete": True, "purged": False},
    )
    res2 = data.Resource.new(
        environment=env.id,
        resource_version_id=rvids[1],
        resource_set=resource_sets[1],
        attributes={"name": "file1", "purge_on_delete": True, "purged": False},
    )
    res3 = data.Resource.new(
        environment=env.id,
        resource_version_id=rvids[2],
        resource_set=resource_sets[2],
        attributes={"name": "file1", "purge_on_delete": True, "purged": True},
    )
    await res1.insert()
    await res2.insert()
    await res3.insert()

    assert res1.attribute_hash is not None
    assert res1.attribute_hash == res2.attribute_hash
    assert res3.attribute_hash is not None
    assert res1.attribute_hash != res3.attribute_hash

    readres = await data.Resource.get_resources(env.id, resource_version_ids=rvids)

    # Use resource_set to determine which resource is which
    resource_map = {r.resource_set: r for r in readres}
    res1 = resource_map[res1.resource_set]
    res2 = resource_map[res2.resource_set]
    res3 = resource_map[res3.resource_set]

    assert res1.attribute_hash is not None
    assert res1.attribute_hash == res2.attribute_hash
    assert res3.attribute_hash is not None
    assert res1.attribute_hash != res3.attribute_hash


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
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    resource_set = await make_resource_set(env.id, [version])

    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::testing::NullResource[agent1,name=file1],v=1",
        resource_set=resource_set,
        attributes={"name": "file2"},
    )
    await res1.insert()

    res2 = data.Resource.new(
        environment=env.id,
        resource_version_id="std::testing::NullResource[agent1,name=file2],v=1",
        resource_set=resource_set,
        attributes={"name": "file2"},
    )
    await res2.insert()

    now = datetime.datetime.now().astimezone()
    action_id = uuid.uuid4()
    resource_version_ids = [
        "std::testing::NullResource[agent1,name=file1],v=1",
        "std::testing::NullResource[agent1,name=file2],v=1",
    ]
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
        environment=env.id,
        version=version,
        date=datetime.datetime.now().astimezone(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    resource_set = await make_resource_set(env.id, [version])
    rv_id = f"std::testing::NullResource[agent1,name=motd],v={version}"
    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id=rv_id,
        resource_set=resource_set,
        attributes={"name": "file2"},
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
    resource_actions = await data.ResourceAction.get_log(env.id, "std::testing::NullResource[agent11,name=motd],v=1")
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
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    resource_set = await make_resource_set(env.id, [version])
    rvid = "std::testing::NullResource[agent1,name=file1],v=1"
    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id=rvid,
        resource_set=resource_set,
        attributes={"name": "file2"},
    )
    await res1.insert()

    now = datetime.datetime.now()
    ra = data.ResourceAction(
        environment=env.id,
        version=version,
        resource_version_ids=[rvid],
        action_id=uuid.uuid4(),
        action=const.ResourceAction.store,
        started=now,
        finished=now,
        messages=[data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=2)],
    )
    await ra.insert()


@pytest.mark.parametrize("halted", [True, False])
async def test_get_updated_before_active_env(init_dataclasses_and_load_schema, halted):
    # verify the call to "get_updated_before". If the env is halted it shouldn't return any result
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
        is_suitable_for_partial_compiles=False,
    )
    await cm1.insert()

    resource_set = await make_resource_set(env.id, [version])
    res = data.Resource.new(
        environment=env.id,
        resource_version_id=f"test::SetExpiringFact[agent1,key=key1],v={version}",
        resource_set=resource_set,
        attributes={"key": "key1", "purge_on_delete": True, "purged": False},
    )
    await res.insert()

    if halted:
        await env.update_fields(halted=True)

    time1 = datetime.datetime(2018, 7, 14, 12, 30)
    time2 = datetime.datetime(2018, 7, 16, 12, 30)
    time3 = datetime.datetime(2018, 7, 12, 12, 30)

    parameters = []
    for current_time in [time1, time2, time3]:
        t = current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")
        parameter = data.Parameter(
            name="param_" + t,
            value="test_val_" + t,
            environment=env.id,
            source="test",
            updated=current_time,
            resource_id="test::SetExpiringFact[agent1,key=key1]",
            expires=True,
        )
        parameters.append(parameter)
        await parameter.insert()

    updated_before = await data.Parameter.get_updated_before_active_env(datetime.datetime(2018, 7, 12, 12, 30))
    assert len(updated_before) == 0
    updated_before = await data.Parameter.get_updated_before_active_env(datetime.datetime(2018, 7, 14, 12, 30))
    assert len(updated_before) == (0 if halted else 1)
    if not halted:
        assert (updated_before[0].environment, updated_before[0].name) == (parameters[2].environment, parameters[2].name)
    updated_before = await data.Parameter.get_updated_before_active_env(datetime.datetime(2018, 7, 15, 12, 30))
    list_of_ids = [(x.environment, x.name) for x in updated_before]
    assert len(updated_before) == (0 if halted else 2)
    if not halted:
        assert (parameters[0].environment, parameters[0].name) in list_of_ids
        assert (parameters[2].environment, parameters[2].name) in list_of_ids


async def test_parameter_list_parameters(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    metadata_param1 = {"test1": "testval1", "test2": "testval2"}
    parameter1 = data.Parameter(
        name="param1", value="val", environment=env.id, source="test", metadata=metadata_param1, expires=False
    )
    await parameter1.insert()

    metadata_param2 = {"test3": "testval3"}
    parameter2 = data.Parameter(
        name="param2", value="val", environment=env.id, source="test", metadata=metadata_param2, expires=False
    )
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
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    dryrun = await data.DryRun.create(env.id, version, 10, 5)

    resource_version_id = "std::testing::NullResource[agent1,name=motd],v=%s" % version
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
    links = {"self": ["link-1"], "instances": ["link-2", "link-3"]}
    compile2 = data.Compile(environment=env.id, links=links)
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
    # Assert that links are passed to the CompileReport
    assert report_of_compile["links"] == links


async def test_match_tables_in_db_against_table_definitions_in_orm(
    postgres_db, database_name, postgresql_client, init_dataclasses_and_load_schema
):
    table_names = await postgresql_client.fetch(
        "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public'"
    )
    table_names_in_database = [x["table_name"] for x in table_names]
    table_names_in_classes_list = [x.table_name() for x in data._classes]
    # Schema management table and join tables are not in the classes list.
    join_tables = {
        "schemamanager",
        "resourceaction_resource",
        "role_assignment",
        "resource_set_configuration_model",
        "resource_diff",
    }
    # The following tables are not in the classes list, they are managed via the sqlalchemy ORM.
    sql_alchemy_tables: set[str] = {"inmanta_module", "module_files", "agent_modules"}
    assert len(table_names_in_classes_list) + len(join_tables) + len(sql_alchemy_tables) == len(table_names_in_database)
    for item in table_names_in_classes_list:
        # The DB table name for the User class is named inmanta_user
        if item == "user":
            item = "inmanta_user"
        assert item in table_names_in_database


@pytest.mark.parametrize("env1_halted", [True, False])
@pytest.mark.parametrize("env2_halted", [True, False])
async def test_purge_log_and_diff(postgresql_client, init_dataclasses_and_load_schema, env1_halted, env2_halted):
    """
    Tests ResourceAction.purge_logs and ResourcePersistentState.persist_non_compliant_diff/purge_old_logs
    """
    project = data.Project(name="test")
    await project.insert()

    envs = []

    timestamp_eight_days_ago = datetime.datetime.now().astimezone() - datetime.timedelta(days=8)
    timestamp_six_days_ago = datetime.datetime.now().astimezone() - datetime.timedelta(days=6)

    res1_id = ResourceIdStr("std::testing::NullResource[agent1,name=file1]")
    res1_vid = f"{res1_id},v=1"

    for i in range(2):
        env = data.Environment(name=f"dev-{i}", project=project.id, repo_url="", repo_branch="")
        await env.insert()
        envs.append(env)

        version = 1
        cm = data.ConfigurationModel(
            environment=env.id,
            version=version,
            date=datetime.datetime.now(),
            total=1,
            version_info={},
            released=True,
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()
        resource_set = await make_resource_set(env.id, [version])

        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id=res1_vid,
            resource_set=resource_set,
            attributes={"name": "file2"},
        )
        await res1.insert()

        # ResourceAction 1

        log_line_ra1 = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=1)
        action_id = uuid.uuid4()
        ra1 = data.ResourceAction(
            environment=env.id,
            version=version,
            resource_version_ids=[res1_vid],
            action_id=action_id,
            action=const.ResourceAction.store,
            started=timestamp_eight_days_ago,
            finished=datetime.datetime.now(),
            messages=[log_line_ra1],
        )
        await ra1.insert()

        res2_vid = "std::testing::NullResource[agent1,name=file2],v=1"
        res2 = data.Resource.new(
            environment=env.id,
            resource_version_id=res2_vid,
            resource_set=resource_set,
            attributes={"name": "file2"},
        )
        await res2.insert()

        # ResourceAction 2
        log_line_ra2 = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=2)
        action_id = uuid.uuid4()
        ra2 = data.ResourceAction(
            environment=env.id,
            version=version,
            resource_version_ids=[res2_vid],
            action_id=action_id,
            action=const.ResourceAction.store,
            started=timestamp_six_days_ago,
            finished=datetime.datetime.now(),
            messages=[log_line_ra2],
        )
        await ra2.insert()

        await data.ResourcePersistentState.populate_for_version(env.id, model_version=1)

        # Create 3 different diffs 2 inactive/outdated diffs and one that is still referenced by the rps table (active):
        # 1 diff past the time limit (inactive)
        # 1 diff still in the time limit (inactive)
        # 1 diff past the time limit (active)
        # In practice, having a fresher inactive diff will not happen.
        example_diff = {"name": {"current": None, "desired": "file1"}}
        await data.ResourcePersistentState.persist_non_compliant_diff(
            env.id, res1_id, created_at=timestamp_eight_days_ago, diff=example_diff
        )
        await data.ResourcePersistentState.persist_non_compliant_diff(
            env.id, res1_id, created_at=timestamp_six_days_ago, diff=example_diff
        )
        diff_id = await data.ResourcePersistentState.persist_non_compliant_diff(
            env.id, res1_id, created_at=timestamp_eight_days_ago, diff=example_diff
        )
        rps1 = await data.ResourcePersistentState.get_one(environment=env.id, resource_id=res1_id)
        assert rps1
        await rps1.update(non_compliant_diff=diff_id)

    if env1_halted:
        await envs[0].update_fields(halted=True)
    if env2_halted:
        await envs[1].update_fields(halted=True)

    # Make the retention time for the second environment shorter than the default 7 days
    await envs[1].set(data.RESOURCE_ACTION_LOGS_RETENTION, value=2)

    assert len(await data.ResourceAction.get_list()) == 4  # Two ra's in each environment
    await data.ResourceAction.purge_logs()
    number_ra_env1 = 2 if env1_halted else 1  # if not halted one is cleaned up
    number_ra_env2 = 2 if env2_halted else 0  # if not halted both are cleaned up
    assert len(await data.ResourceAction.get_list()) == number_ra_env1 + number_ra_env2
    remaining_resource_action = (await data.ResourceAction.get_list())[0]

    # verify that after a cleanup (without halted envs) the remaining record is the right one.
    if not (env1_halted or env2_halted):
        assert remaining_resource_action.environment == envs[0].id
        assert remaining_resource_action.started == timestamp_six_days_ago

    resource_diffs = await postgresql_client.fetch("SELECT * FROM public.resource_diff")
    assert len(resource_diffs) == 6  # 3 diffs in each environment
    await data.ResourcePersistentState.purge_old_diffs()
    number_diffs_env1 = 3 if env1_halted else 2  # if not halted one inactive diff is cleaned up
    number_diffs_env2 = 3 if env2_halted else 1  # if not halted both inactive diffs are cleaned up
    resource_diffs = await postgresql_client.fetch("SELECT * FROM public.resource_diff")
    assert len(resource_diffs) == number_diffs_env2 + number_diffs_env1

    if not env1_halted:
        rps_1 = await data.ResourcePersistentState.get_one(environment=envs[0].id, resource_id=res1_id)
        env_1_diffs = [diff for diff in resource_diffs if diff["environment"] == envs[0].id]
        assert len(env_1_diffs) == number_diffs_env1
        active_diff = [diff for diff in env_1_diffs if diff["created"] == timestamp_eight_days_ago]
        assert len(active_diff) == 1
        assert rps_1.non_compliant_diff == active_diff[0]["id"]
        inactive_diff = [diff for diff in env_1_diffs if diff["created"] == timestamp_six_days_ago]
        assert len(inactive_diff) == 1
        assert rps_1.non_compliant_diff != inactive_diff[0]["id"]

    if not env2_halted:
        rps_1 = await data.ResourcePersistentState.get_one(environment=envs[1].id, resource_id=res1_id)
        env_2_diffs = [diff for diff in resource_diffs if diff["environment"] == envs[1].id]
        assert len(env_2_diffs) == number_diffs_env2
        assert rps_1.non_compliant_diff == env_2_diffs[0]["id"]


async def test_insert_many(init_dataclasses_and_load_schema):
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
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    resource_set = await make_resource_set(env.id, [version])
    rvid = "std::testing::NullResource[agent1,name=file1],v=%s" % version
    res1 = data.Resource.new(
        environment=env.id,
        resource_version_id=rvid,
        resource_set=resource_set,
        attributes={"attr": [{"a": 1, "b": "c"}]},
    )
    await res1.insert()

    id = Id.parse_resource_version_id(rvid)
    res = await data.Resource.get_resource_for_version(
        environment=res1.environment, resource_id=id.resource_str(), version=id.version
    )

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
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    # Add multiple versions of model
    for i in range(1, 11):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.datetime.now() + datetime.timedelta(minutes=i),
            total=1,
            version_info={},
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()

    # Add resource action for motd
    motd_first_start_time = datetime.datetime.now()

    async def make_file_resourceaction(version, offset=0, name="motd", log_level=logging.INFO):
        rvid = f"std::testing::NullResource[agent1,name={name}],v={version}"
        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id=rvid,
            resource_set=await make_resource_set(env.id, [version]),
            attributes={"attr": [{"a": 1, "b": "c"}], "name": name},
        )
        await res1.insert()
        action_id = uuid.uuid4()
        resource_action = data.ResourceAction(
            environment=env.id,
            version=version,
            resource_version_ids=[rvid],
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
    resource_set = await make_resource_set(env.id, [version])
    for i in range(5):
        name = "file" + str(i)
        key = "std::testing::NullResource[agent1,name=" + name + "]"
        rvid = key + ",v=%d" % version
        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id=rvid,
            resource_set=resource_set,
            attributes={"name": name},
        )
        await res1.insert()
        resource_ids.append((res1.environment, rvid))

    # Add resource actions for file
    for i in range(5):
        resource_action = data.ResourceAction(
            environment=env.id,
            version=version,
            resource_version_ids=[f"std::testing::NullResource[agent1,name=file{str(i)}],v={version}"],
            action_id=uuid.uuid4(),
            action=const.ResourceAction.dryrun,
            started=datetime.datetime.now() + datetime.timedelta(minutes=i),
        )
        await resource_action.insert()

    # Add resource and resourceaction for host
    key = "std::Host[agent1,name=host1]"
    resource_version_id = key + ",v=%d" % version
    res1 = data.Resource.new(
        environment=env.id, resource_version_id=resource_version_id, resource_set=resource_set, attributes={"name": "host1"}
    )
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
    res1 = data.Resource.new(
        environment=env.id, resource_version_id=resource_version_id, resource_set=resource_set, attributes={"name": "host1"}
    )
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
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, attribute="name", attribute_value="motd")
    assert len(resource_actions) == 11

    # Get everything that starts with "/etc/file"
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, attribute="name", attribute_value="file")
    assert len(resource_actions) == 5

    # Get all files
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, resource_type="std::testing::NullResource")
    assert len(resource_actions) == 16

    # Get everything from agent 2
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, agent="agent2")
    assert len(resource_actions) == 1

    # Get everything of type host
    resource_actions = await data.ResourceAction.query_resource_actions(env.id, resource_type="std::Host")
    assert len(resource_actions) == 2

    # Get only the last 5 file resource actions
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id, resource_type="std::testing::NullResource", limit=5
    )
    assert len(resource_actions) == 5

    # Query actions older than the first
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
        limit=5,
        last_timestamp=motd_first_start_time,
    )
    assert len(resource_actions) == 0

    # Query the latest actions
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
        limit=5,
        last_timestamp=motd_first_start_time + datetime.timedelta(minutes=12),
    )
    assert len(resource_actions) == 5
    assert [resource_action.version for resource_action in resource_actions] == [10, 9, 8, 7, 6], resource_actions

    # Continue from the last one's timestamp
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
        limit=5,
        last_timestamp=resource_actions[-1].started,
    )
    assert len(resource_actions) == 5
    assert [resource_action.version for resource_action in resource_actions] == [5, 4, 3, 2, 1]

    # Query with first_timestamp
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
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
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.datetime.now(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()
    # Add multiple versions of model
    for i in range(1, 12):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.datetime.now(),
            total=1,
            version_info={},
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()

    for i in range(1, 12):

        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id="std::testing::NullResource[agent1,name=motd],v=%s" % str(i),
            resource_set=await make_resource_set(env.id, [i]),
            attributes={"attr": [{"a": 1, "b": "c"}], "name": "motd"},
        )
        await res1.insert()

    # Add resource actions for motd
    motd_first_start_time = datetime.datetime.now()
    earliest_action_id = uuid.uuid4()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=1,
        resource_version_ids=[f"std::testing::NullResource[agent1,name=motd],v={1}"],
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
            resource_version_ids=[f"std::testing::NullResource[agent1,name=motd],v={i}"],
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
            resource_version_ids=[f"std::testing::NullResource[agent1,name=motd],v={i}"],
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
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
        limit=2,
        last_timestamp=motd_first_start_time + datetime.timedelta(minutes=6),
    )
    assert len(resource_actions) == 2
    assert [resource_action.action_id for resource_action in resource_actions] == action_ids_with_the_same_timestamp[:2]
    # Querying pages based on last_timestamp and action_id from the previous query
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
        limit=2,
        action_id=resource_actions[1].action_id,
        last_timestamp=resource_actions[1].started,
    )
    assert len(resource_actions) == 2
    assert [resource_action.action_id for resource_action in resource_actions] == action_ids_with_the_same_timestamp[2:4]
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
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
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
        limit=4,
        first_timestamp=motd_first_start_time - datetime.timedelta(seconds=30),
    )
    assert len(resource_actions) == 4
    assert [resource_action.action_id for resource_action in resource_actions] == action_ids_with_the_same_timestamp[1:5]
    # Page forward in time
    resource_actions = await data.ResourceAction.query_resource_actions(
        env.id,
        resource_type="std::testing::NullResource",
        attribute="name",
        attribute_value="motd",
        limit=4,
        action_id=resource_actions[0].action_id,
        first_timestamp=resource_actions[0].started,
    )
    assert len(resource_actions) == 4
    #  First three of the increasing ones and the first of the ones that share a timestamp
    expected_ids_on_page = action_ids_with_increasing_timestamps[2:] + [action_ids_with_the_same_timestamp[0]]
    assert [resource_action.action_id for resource_action in resource_actions] == expected_ids_on_page


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


async def test_get_current_resource_state(server, environment, client, clienthelper, agent):
    """
    Verify the behavior of the Resource.get_current_resource_state() method.
    """
    # Create version 1 with available resource. Don't release the version yet
    version1 = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version1,
        resources=[
            {
                "id": f"std::testing::NullResource[agent1,name=test1],v={version1}",
                "val": "val",
                "requires": [],
            },
        ],
        resource_state={},
        module_version_info={},
    )
    assert result.code == 200, result.result

    state: Optional[const.ResourceState] = await data.Resource.get_current_resource_state(
        env=environment,
        rid="std::testing::NullResource[agent1,name=test1]",
    )
    assert state is None

    # Release version
    result = await client.release_version(tid=environment, id=version1)
    assert result.code == 200

    await utils.wait_until_deployment_finishes(client, environment, version=version1)

    state: Optional[const.ResourceState] = await data.Resource.get_current_resource_state(
        env=environment,
        rid="std::testing::NullResource[agent1,name=test1]",
    )
    assert state is const.ResourceState.unavailable  # executor fails to load handler code because we never pushed any code

    # Create version 2 with undefined resource. Don't release the version yet.
    version2 = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version2,
        resources=[
            {
                "id": f"std::testing::NullResource[agent1,name=test1],v={version2}",
                "val": "val",
                "requires": [],
            },
        ],
        resource_state={"std::testing::NullResource[agent1,name=test1]": const.ResourceState.undefined},
        module_version_info={},
    )
    assert result.code == 200, result.result

    # Assert we see the state of the released version
    state: Optional[const.ResourceState] = await data.Resource.get_current_resource_state(
        env=environment,
        rid="std::testing::NullResource[agent1,name=test1]",
    )
    assert state is const.ResourceState.unavailable

    result = await client.release_version(tid=environment, id=version2)
    assert result.code == 200

    await utils.wait_until_deployment_finishes(client, environment, version=version2)

    state: Optional[const.ResourceState] = await data.Resource.get_current_resource_state(
        env=environment,
        rid="std::testing::NullResource[agent1,name=test1]",
    )
    assert state is const.ResourceState.undefined


@pytest.mark.slowtest
async def test_get_partial_resources_since_version_raw(environment, server, postgresql_client, client):
    """
    Verify the behavior of the get_partial_resources_since_version_raw and get_resources_for_version_raw methods,
    used by the scheduler to apply partial and full versions respectively.

    Setup:
        - Generate `nb_resource_sets` sets with integers as names
        - Each set contains `nb_resources_per_set` resources
        - Resource ids are predictable: `...,id={resource_set}-{resource_index}`
        - Resources contain a single attribute (other than required ones) `exported`: the version in which it was exported

    Test approach:
        for a few different `partial_size` sizes of partial:
            - Choose `partial_size` resource sets, evenly distributed over all sets (e.g. sets 1, 11, 21, ...)
            - Regenerate these sets as described in setup and do a `put_partial` and release
            - Verify results of `get_partial_resources_since_version_raw` and `get_resources_for_version_raw`:
                Verify that the methods return only the differing resource sets, and the appropriate resources
                for those sets.

        Verify behavior of the two methods for some special scenarios: multiple versions, non-released versions,
        deleted sets, ...
    """
    nb_resource_sets: int = 100
    nb_resources_per_set: int = 100

    def get_resource_set_names(partial_size: int) -> Iterator[str]:
        if partial_size == 0:
            return iter(())
        return (str(i) for i in range(1, nb_resource_sets + 1, max(nb_resource_sets // partial_size, 1)))

    def get_resource_id(resource_set: str, index: int, *, version: Optional[int] = None) -> ResourceVersionIdStr:
        without_version = ResourceIdStr(f"mymodule::Myresource[myagent,id={resource_set}-{index}]")
        return ResourceVersionIdStr(f"{without_version},v={version}") if version is not None else without_version

    async def release(version: Optional[int] = None) -> None:
        """
        Mark all versions as released, without actually releasing it.
        """
        condition = f"WHERE version = {version}" if version is not None else ""
        await postgresql_client.execute(f"UPDATE configurationmodel SET released=true {condition}")

    # set up initial state by releasing a single base version
    version: int = await client.reserve_version(tid=environment).value()
    result = await client.put_version(
        tid=environment,
        version=version,
        module_version_info={},
        resources=[
            {"id": get_resource_id(s, i, version=version), "requires": [], "exported": version}
            for s in get_resource_set_names(nb_resource_sets)
            for i in range(nb_resources_per_set)
        ],
        resource_sets={
            get_resource_id(s, i): s for s in get_resource_set_names(nb_resource_sets) for i in range(nb_resources_per_set)
        },
    )
    assert result.code == 200, result.result
    await release()

    all_models: list[tuple[int, object]] = []
    full_models: list[tuple[int, object]] = []
    partial_size: int  # number of resource sets in a partial export
    for iteration, partial_size in enumerate([0, 1, 3, 10, 25]):  # choose size for partially overlapping sets
        base_version: int = iteration + 1
        new_version: int = base_version + 1

        # build up data sets before starting timer
        resources = [
            {"id": get_resource_id(s, i, version=0), "requires": [], "exported": new_version}
            for s in get_resource_set_names(partial_size)
            for i in range(nb_resources_per_set)
        ]
        resource_sets = {
            get_resource_id(s, i): s for s in get_resource_set_names(partial_size) for i in range(nb_resources_per_set)
        }

        insert_start: float = time.monotonic()
        await client.put_partial(
            tid=environment,
            module_version_info={},
            resources=resources,
            resource_sets=resource_sets,
        ).value()
        insert_done: float = time.monotonic()

        await release()
        # Tell postgres to analyze after major update. During normal operation this is handled by autovacuum daemon
        await postgresql_client.execute("ANALYZE")

        fetch_start: float = time.monotonic()
        models = await data.Resource.get_partial_resources_since_version_raw(
            environment=environment,
            since=base_version,
            projection=["resource_id"],
            connection=postgresql_client,
        )
        fetch_done: float = time.monotonic()

        full_fetch_start: float = time.monotonic()
        full_model = await data.Resource.get_resources_for_version_raw(
            # don't specify version to get latest one. Further down we test behavior with version specified
            environment=environment,
            projection=["resource_id"],
            project_attributes=["exported"],
            connection=postgresql_client,
        )
        full_fetch_done: float = time.monotonic()

        # show with pytest -s
        print(
            f"with {iteration + 1 : >4,} older versions with {nb_resource_sets : >4,} resource sets of size"
            f" {nb_resources_per_set : >4,} each, an export for {partial_size : >4,} resource sets took"
            f" {1000 * (insert_done - insert_start) : >5,.0f}ms to export, {1000 * (fetch_done - fetch_start) : >3,.0f}ms"
            f" to fetch and {1000 * (full_fetch_done - full_fetch_start) : >3,.0f}ms to fetch the full version"
        )

        # verify the result
        assert len(models) == 1
        version, resource_sets = models[0]
        assert version == new_version
        assert resource_sets.keys() == set(get_resource_set_names(partial_size))
        for resource_set, resources in resource_sets.items():
            assert {r["resource_id"] for r in resources} == {
                f"mymodule::Myresource[myagent,id={resource_set}-{i}]" for i in range(nb_resources_per_set)
            }
        all_models.extend(models)

        assert full_model is not None
        assert full_model[0] == version
        assert full_model[1].keys() == set(str(i) for i in range(1, nb_resource_sets + 1))
        for resource_set, resources in full_model[1].items():
            expected_version: int
            for version, version_sets in reversed(all_models):
                if resource_set in version_sets:
                    expected_version = version
                    break
            else:
                expected_version = 1

            assert {r["resource_id"] for r in resources} == {
                f"mymodule::Myresource[myagent,id={resource_set}-{i}]" for i in range(nb_resources_per_set)
            }
            assert all(r["exported"] == expected_version for r in resources)
        full_models.append(full_model)

    # verify get_resources_for_version_raw behavior with version specified
    for full_model in full_models:
        by_version = await data.Resource.get_resources_for_version_raw(
            environment=environment,
            version=full_model[0],
            projection=["resource_id"],
            project_attributes=["exported"],
            connection=postgresql_client,
        )
        assert by_version == full_model

    # verify both methods' behavior when the specified version doesn't exist
    resources_for_non_existent_version = await data.Resource.get_resources_for_version_raw(
        environment=environment,
        version=new_version + 1,
        projection=["resource_id"],
        project_attributes=["exported"],
        connection=postgresql_client,
    )
    assert resources_for_non_existent_version is None
    with pytest.raises(data.PartialBaseMissing):
        await data.Resource.get_partial_resources_since_version_raw(
            environment=environment,
            since=new_version + 1,
            projection=["resource_id"],
            connection=postgresql_client,
        )
    # or when it does exist but it is already the latest
    no_partial_updates = await data.Resource.get_partial_resources_since_version_raw(
        environment=environment,
        since=new_version,
        projection=["resource_id"],
        connection=postgresql_client,
    )
    assert no_partial_updates == []

    # push a new version without releasing it
    base_version = new_version
    new_version += 1
    await client.put_partial(
        tid=environment,
        module_version_info={},
        resources=[],
        resource_sets={},
    ).value()

    # get_resources_for_version_raw can fetch non-released versions when requested
    resources_for_non_released_version = await data.Resource.get_resources_for_version_raw(
        environment=environment,
        version=new_version,
        projection=["resource_id"],
        project_attributes=["exported"],
        connection=postgresql_client,
    )
    assert resources_for_non_released_version is not None
    assert resources_for_non_released_version[0] == new_version
    # but default is still latest released
    latest_released_version = await data.Resource.get_resources_for_version_raw(
        environment=environment,
        version=None,
        projection=["resource_id"],
        project_attributes=["exported"],
        connection=postgresql_client,
    )
    assert latest_released_version is not None
    assert latest_released_version[0] == new_version - 1

    # verify that the method can fetch multiple models at once, as a sequence of partial diffs, and excludes the non-released
    models = await data.Resource.get_partial_resources_since_version_raw(
        environment=environment,
        since=1,
        projection=["resource_id"],
        connection=postgresql_client,
    )
    assert models == all_models

    # delete a resource set
    base_version = new_version
    new_version += 1
    await client.put_partial(
        tid=environment,
        module_version_info={},
        resources=[],
        resource_sets={},
        removed_resource_sets=["10"],
    ).value()

    await release(version=new_version)

    # verify that the partial diff contains the deleted set as empty
    models = await data.Resource.get_partial_resources_since_version_raw(
        environment=environment,
        since=base_version - 1,  # -1 because previous version was not released
        projection=["resource_id"],
        connection=postgresql_client,
    )
    assert len(models) == 1
    version, resource_sets = models[0]
    assert version == new_version
    assert resource_sets == {"10": []}
