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

import datetime
import enum
import logging
import time
import uuid
from collections import abc
from collections.abc import Mapping
from datetime import UTC
from typing import Optional, cast

import asyncpg
import pytest
from asyncpg import Connection, ForeignKeyViolationError

import sqlalchemy
import utils
from inmanta import const, data, util
from inmanta.const import AgentStatus, LogLevel
from inmanta.data import ArgumentCollector, QueryType, get_engine, start_engine, stop_engine
from inmanta.deploy import state
from inmanta.resources import Id
from inmanta.types import ResourceVersionIdStr


async def test_connect_too_small_connection_pool(sqlalchemy_url_parameters: Mapping[str, str]):
    await start_engine(
        **sqlalchemy_url_parameters,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
    )
    engine = get_engine()
    assert engine is not None
    connection: Connection = await engine.connect()

    try:
        with pytest.raises(sqlalchemy.exc.TimeoutError):
            await engine.connect()
    finally:
        await connection.close()
        await stop_engine()


async def test_connect_default_parameters(sql_alchemy_engine):
    assert sql_alchemy_engine is not None
    async with sql_alchemy_engine.connect() as connection:
        assert connection is not None


async def test_connection_failure(postgres_db, unused_tcp_port_factory, database_name, clean_reset):
    wrong_port = unused_tcp_port_factory()

    await start_engine(
        database_username=postgres_db.user,
        database_password=postgres_db.password,
        database_host=postgres_db.host,
        database_port=wrong_port,
        database_name=database_name,
    )
    engine = get_engine()
    with pytest.raises(ConnectionRefusedError):
        async with engine.connect() as _:
            pass

    await stop_engine()

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
    exclude_enums = [state.DeployResult, state.Blocked]  # These enums are modelled in the db using a varchar
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

        resource_ids = []
        for i in range(5):
            name = "file" + str(i)
            key = "std::testing::NullResource[agent1,name=" + name + "]"
            res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"name": name})
            await res1.insert()
            resource_ids.append((res1.environment, res1.resource_version_id))

        code = data.Code(version=version, resource="std::testing::NullResource", environment=env.id)
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
        for environment, resource_version_id in resource_ids:
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
    cm = data.ConfigurationModel(version=version, environment=env.id, is_suitable_for_partial_compiles=False)
    await cm.insert()

    resource_ids = []
    for i in range(5):
        name = "file" + str(i)
        key = "std::testing::NullResource[agent1,name=" + name + "]"
        res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"name": name})
        await res1.insert()
        resource_ids.append((res1.environment, res1.resource_version_id))

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

    code = data.Code(version=version, resource="std::testing::NullResource", environment=env.id)
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

    await env.clear()

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
#
#
# @pytest.mark.parametrize("env1_halted", [True, False])
# @pytest.mark.parametrize("env2_halted", [True, False])
# async def test_agentprocess_cleanup(init_dataclasses_and_load_schema, postgresql_client, env1_halted, env2_halted):
#     # tests the agent process cleanup function with different combinations of halted environments
#
#     project = data.Project(name="test")
#     await project.insert()
#
#     env1 = data.Environment(name="env1", project=project.id, repo_url="", repo_branch="")
#     await env1.insert()
#     env2 = data.Environment(name="env2", project=project.id, repo_url="", repo_branch="")
#     await env2.insert()
#
#     now = datetime.datetime.now()
#
#     async def insert_agent_proc_and_instances(
#         env_id: uuid.UUID, hostname: str, expired_proc: Optional[datetime.datetime], expired_instances: list[datetime.datetime]
#     ) -> None:
#         agent_proc = data.AgentProcess(hostname=hostname, environment=env_id, expired=expired_proc, sid=uuid.uuid4())
#         await agent_proc.insert()
#         for i in range(len(expired_instances)):
#             agent_instance = data.AgentInstance(
#                 id=uuid.uuid4(), process=agent_proc.sid, name=f"agent_instance{i}", expired=expired_instances[i], tid=env_id
#             )
#             await agent_instance.insert()
#
#     async def verify_nr_of_records(env: uuid.UUID, hostname: str, expected_nr_procs: int, expected_nr_instances: int):
#         # Verify expected_nr_procs
#         result = await data.AgentProcess.get_list(environment=env, hostname=hostname)
#         assert len(result) == expected_nr_procs, result
#         # Verify expected_nr_instances
#         query = """
#             SELECT count(*)
#             FROM agentprocess AS proc INNER JOIN agentinstance AS instance ON proc.sid=instance.process
#             WHERE environment=$1 AND hostname=$2
#         """
#         result = await postgresql_client.fetch(query, env, hostname)
#         assert result[0]["count"] == expected_nr_instances, result
#
#     # Setup env1
#     await insert_agent_proc_and_instances(env1.id, "proc1", None, [None])
#     await insert_agent_proc_and_instances(env1.id, "proc1", datetime.datetime(2020, 1, 1, 1, 0), [now])
#     await insert_agent_proc_and_instances(env1.id, "proc2", None, [None])
#     # Setup env2
#     await insert_agent_proc_and_instances(env2.id, "proc2", None, [None, None])
#     await insert_agent_proc_and_instances(env2.id, "proc2", datetime.datetime(2020, 1, 1, 1, 0), [now, now, now])
#     await insert_agent_proc_and_instances(env2.id, "proc2", datetime.datetime(2020, 1, 1, 2, 0), [now, now])
#     await insert_agent_proc_and_instances(env2.id, "proc2", datetime.datetime(2020, 1, 1, 3, 0), [now])
#
#     if env1_halted:
#         await env1.update_fields(halted=True)
#     if env2_halted:
#         await env2.update_fields(halted=True)
#
#     # Run cleanup twice to verify stability
#     for i in range(2):
#         # Perform cleanup
#         await data.AgentProcess.cleanup(nr_expired_records_to_keep=1)
#         # Assert outcome
#         # Halting env1 has no impact on the cleanup: an expired instance will be kept in both cases
#         # Halting env2 has an impact on the cleanup: if it's halted 5 expired instances in 2 processes will not be removed.
#         await verify_nr_of_records(env1.id, hostname="proc1", expected_nr_procs=2, expected_nr_instances=2)
#         await verify_nr_of_records(env1.id, hostname="proc2", expected_nr_procs=1, expected_nr_instances=1)
#         await verify_nr_of_records(
#             env2.id, hostname="proc2", expected_nr_procs=4 if env2_halted else 2, expected_nr_instances=8 if env2_halted else 3
#         )
#         # Assert records are deleted in the correct order
#         query = """
#             SELECT expired
#             FROM agentprocess
#             WHERE environment=$1 AND hostname=$2 AND expired IS NOT NULL
#         """
#         result = await postgresql_client.fetch(query, env2.id, "proc2")
#         assert len(result) == 3 if env2_halted else 1
#         if len(result) == 1:
#             # if the cleanup was done (env2 not halted), verify the expired record that was kept is the right one.
#             assert result[0]["expired"] == datetime.datetime(2020, 1, 1, 3, 0).astimezone()
#
#
# async def test_delete_agentinstance_which_is_primary(init_dataclasses_and_load_schema):
#     """
#     It should be impossible to delete an AgentInstance record which is references
#     from the Agent stable.
#     """
#     project = data.Project(name="test")
#     await project.insert()
#     env = data.Environment(name="env1", project=project.id, repo_url="", repo_branch="")
#     await env.insert()
#
#     agent_proc = data.AgentProcess(hostname="test", environment=env.id, expired=None, sid=uuid.uuid4())
#     await agent_proc.insert()
#     agent_instance = data.AgentInstance(
#         id=uuid.uuid4(), process=agent_proc.sid, name="agent_instance", expired=None, tid=env.id
#     )
#     await agent_instance.insert()
#     agent = data.Agent(environment=env.id, name="test", id_primary=agent_instance.id)
#     await agent.insert()
#
#     with pytest.raises(ForeignKeyViolationError):
#         await agent_instance.delete()
#
#
# async def test_agent_instance(init_dataclasses_and_load_schema):
#     project = data.Project(name="test")
#     await project.insert()
#
#     env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
#     await env.insert()
#
#     sid = uuid.uuid4()
#     agent_proc = data.AgentProcess(
#         hostname="testhost", environment=env.id, first_seen=datetime.datetime.now(), last_seen=datetime.datetime.now(), sid=sid
#     )
#     await agent_proc.insert()
#
#     agi1_name = "agi1"
#     agi1 = data.AgentInstance(process=agent_proc.sid, name=agi1_name, tid=env.id)
#     await agi1.insert()
#     agi2_name = "agi2"
#     agi2 = data.AgentInstance(process=agent_proc.sid, name=agi2_name, tid=env.id)
#     await agi2.insert()
#
#     active_instances = await data.AgentInstance.active()
#     assert len(active_instances) == 2
#     assert agi1.id in [x.id for x in active_instances]
#     assert agi2.id in [x.id for x in active_instances]
#
#     current_instances = await data.AgentInstance.active_for(env.id, agi1_name)
#     assert len(current_instances) == 1
#     assert current_instances[0].id == agi1.id
#     current_instances = await data.AgentInstance.active_for(env.id, agi2_name)
#     assert len(current_instances) == 1
#     assert current_instances[0].id == agi2.id
#
#     await data.AgentInstance.log_instance_expiry(sid=agent_proc.sid, endpoints={agi1_name}, now=datetime.datetime.now())
#
#     active_instances = await data.AgentInstance.active()
#     assert len(active_instances) == 1
#     assert agi1.id not in [x.id for x in active_instances]
#     assert agi2.id in [x.id for x in active_instances]
#
#     current_instances = await data.AgentInstance.active_for(env.id, agi1_name)
#     assert len(current_instances) == 0
#     current_instances = await data.AgentInstance.active_for(env.id, agi2_name)
#     assert len(current_instances) == 1
#     assert current_instances[0].id == agi2.id
#
#     await data.AgentInstance.log_instance_creation(process=agent_proc.sid, endpoints={agi1_name}, tid=env.id)
#     current_instances = await data.AgentInstance.active_for(env.id, agi1_name)
#     assert len(current_instances) == 1
#     assert current_instances[0].id == agi1.id
#
#
# async def test_agent(init_dataclasses_and_load_schema):
#     project = data.Project(name="test")
#     await project.insert()
#
#     env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
#     await env.insert()
#
#     sid = uuid.uuid4()
#     agent_proc = data.AgentProcess(
#         hostname="testhost", environment=env.id, first_seen=datetime.datetime.now(), last_seen=datetime.datetime.now(), sid=sid
#     )
#     await agent_proc.insert()
#
#     agi1_name = "agi1"
#     agi1 = data.AgentInstance(process=agent_proc.sid, name=agi1_name, tid=env.id)
#     await agi1.insert()
#
#     agent1 = data.Agent(
#         environment=env.id, name="agi1_agent1", last_failover=datetime.datetime.now(), paused=False, id_primary=agi1.id
#     )
#     await agent1.insert()
#     agent2 = data.Agent(environment=env.id, name="agi1_agent2", paused=False)
#     await agent2.insert()
#     agent3 = data.Agent(environment=env.id, name="agi1_agent3", paused=True)
#     await agent3.insert()
#
#     agents = await data.Agent.get_list()
#     assert len(agents) == 3
#     for agent in agents:
#         assert (agent.name, agent.environment) in [(a.name, a.environment) for a in [agent1, agent2, agent3]]
#
#     for agent in [agent1, agent2, agent3]:
#         retrieved_agent = await agent.get(agent.environment, agent.name)
#         assert retrieved_agent is not None
#         assert retrieved_agent.environment == agent.environment
#         assert retrieved_agent.name == agent.name
#
#     assert agent1.get_status() == AgentStatus.up
#     assert agent2.get_status() == AgentStatus.down
#     assert agent3.get_status() == AgentStatus.paused
#
#     for agent in [agent1, agent2, agent3]:
#         assert AgentStatus(agent.to_dict()["state"]) == agent.get_status()
#
#     await agent1.update_fields(paused=True)
#     assert agent1.get_status() == AgentStatus.paused
#
#     await agent2.update_fields(primary=agi1.id)
#     assert agent2.get_status() == AgentStatus.up
#
#     await agent3.update_fields(paused=False)
#     assert agent3.get_status() == AgentStatus.down
#
#     primary_instance = await data.AgentInstance.get_by_id(agent1.primary)
#     primary_process = await data.AgentProcess.get_one(sid=primary_instance.process)
#     assert primary_process.sid == agent_proc.sid
#
#
# async def test_pause_agent_endpoint_set(environment):
#     """
#     Test the pause() method in the Agent class
#     """
#     env_id = uuid.UUID(environment)
#     agent_name = "test"
#     agent = data.Agent(environment=env_id, name=agent_name, last_failover=datetime.datetime.now(), paused=False)
#     await agent.insert()
#
#     # Verify not paused
#     agent = await data.Agent.get_one(environment=env_id, name=agent_name)
#     assert not agent.paused
#
#     # Pause
#     paused_agents = await data.Agent.pause(env=env_id, endpoint=agent_name, paused=True)
#     assert paused_agents == [agent_name]
#     agent = await data.Agent.get_one(environment=env_id, name=agent_name)
#     assert agent.paused
#
#     # Unpause
#     paused_agents = await data.Agent.pause(env=env_id, endpoint=agent_name, paused=False)
#     assert paused_agents == [agent_name]
#     agent = await data.Agent.get_one(environment=env_id, name=agent_name)
#     assert not agent.paused
#
#
# async def test_pause_all_agent_in_environment(init_dataclasses_and_load_schema):
#     project = data.Project(name="test")
#     await project.insert()
#     env1 = data.Environment(name="env1", project=project.id)
#     await env1.insert()
#     env2 = data.Environment(name="env2", project=project.id)
#     await env2.insert()
#
#     await data.Agent(environment=env1.id, name="agent1", last_failover=datetime.datetime.now(), paused=False).insert()
#     await data.Agent(environment=env1.id, name="agent2", last_failover=datetime.datetime.now(), paused=False).insert()
#     await data.Agent(environment=env2.id, name="agent3", last_failover=datetime.datetime.now(), paused=False).insert()
#     agents_in_env1 = ["agent1", "agent2"]
#
#     async def assert_paused(env_paused_map: dict[uuid.UUID, bool]) -> None:
#         for env_id, paused in env_paused_map.items():
#             agents = await data.Agent.get_list(environment=env_id)
#             assert all([a.paused == paused for a in agents])
#
#     # Test initial state
#     await assert_paused(env_paused_map={env1.id: False, env2.id: False})
#     # Pause env1 and pause again
#     for _ in range(2):
#         paused_agents = await data.Agent.pause(env1.id, endpoint=None, paused=True)
#         assert sorted(paused_agents) == sorted(agents_in_env1)
#         await assert_paused(env_paused_map={env1.id: True, env2.id: False})
#     # Unpause env1 and pause again
#     for _ in range(2):
#         paused_agents = await data.Agent.pause(env1.id, endpoint=None, paused=False)
#         assert sorted(paused_agents) == sorted(agents_in_env1)
#         await assert_paused(env_paused_map={env1.id: False, env2.id: False})
#
#
# async def test_config_model(init_dataclasses_and_load_schema):
#     project = data.Project(name="test")
#     await project.insert()
#
#     env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
#     await env.insert()
#
#     version = int(time.time())
#     cm = data.ConfigurationModel(
#         environment=env.id,
#         version=version,
#         date=datetime.datetime.now(),
#         total=1,
#         version_info={},
#         is_suitable_for_partial_compiles=False,
#     )
#     await cm.insert()
#
#     # create resources
#     key = "std::testing::NullResource[agent1,name=motd]"
#     res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"name": "motd"})
#     await res1.insert()
#
#     agents = await data.ConfigurationModel.get_agents(env.id, version)
#     assert len(agents) == 1
#     assert "agent1" in agents
#
#
# async def test_model_list(init_dataclasses_and_load_schema):
#     project = data.Project(name="test")
#     await project.insert()
#
#     env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
#     await env.insert()
#
#     for version in range(1, 20):
#         cm = data.ConfigurationModel(
#             environment=env.id,
#             version=version,
#             date=datetime.datetime.now(),
#             total=0,
#             version_info={},
#             is_suitable_for_partial_compiles=False,
#         )
#         await cm.insert()
#
#     versions = await data.ConfigurationModel.get_versions(env.id, 0, 1)
#     assert len(versions) == 1
#     assert versions[0].version == 19
#
#     versions = await data.ConfigurationModel.get_versions(env.id, 1, 1)
#     assert len(versions) == 1
#     assert versions[0].version == 18
#
#     versions = await data.ConfigurationModel.get_versions(env.id)
#     assert len(versions) == 19
#     assert versions[0].version == 19
#     assert versions[-1].version == 1
#
#     versions = await data.ConfigurationModel.get_versions(env.id, 10)
#     assert len(versions) == 9
#     assert versions[0].version == 9
#     assert versions[-1].version == 1
