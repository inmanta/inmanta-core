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
import pytest
import asyncpg
import datetime
import uuid
import time
import logging
import inspect
import types
import pkgutil

from inmanta import data, const
from inmanta.const import LogLevel
from asyncpg import PostgresSyntaxError


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
async def test_project(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    assert projects[0].id == project.id

    other = await data.Project.get_by_id(project.id)
    assert project != other
    assert project.id == other.id


@pytest.mark.asyncio
async def test_project_unique(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    project = data.Project(name="test")
    with pytest.raises(asyncpg.UniqueViolationError):
        await project.insert()


def test_project_no_project_name(init_dataclasses_and_load_schema):
    with pytest.raises(AttributeError):
        data.Project()


@pytest.mark.asyncio
async def test_project_cascade_delete(init_dataclasses_and_load_schema):

    async def create_full_environment(project_name, environment_name):
        project = data.Project(name=project_name)
        await project.insert()

        env = data.Environment(name=environment_name, project=project.id, repo_url="", repo_branch="")
        await env.insert()

        agent_proc = data.AgentProcess(hostname="testhost",
                                       environment=env.id,
                                       first_seen=datetime.datetime.now(),
                                       last_seen=datetime.datetime.now(),
                                       sid=uuid.uuid4())
        await agent_proc.insert()

        agi1 = data.AgentInstance(process=agent_proc.sid, name="agi1", tid=env.id)
        await agi1.insert()
        agi2 = data.AgentInstance(process=agent_proc.sid, name="agi2", tid=env.id)
        await agi2.insert()

        agent = data.Agent(environment=env.id, name="agi1", last_failover=datetime.datetime.now(), paused=False,
                           primary=agi1.id)
        await agent.insert()

        version = int(time.time())
        cm = data.ConfigurationModel(version=version, environment=env.id)
        await cm.insert()

        resource_ids = []
        for i in range(5):
            path = "/etc/file" + str(i)
            key = "std::File[agent1,path=" + path + "]"
            res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version,
                                     attributes={"path": path})
            await res1.insert()
            resource_ids.append((res1.environment, res1.resource_version_id))

        code = data.Code(version=version, resource="std::File", environment=env.id)
        await code.insert()

        unknown_parameter = data.UnknownParameter(name="test", environment=env.id, version=version, source="")
        await unknown_parameter.insert()

        return project, env, agent_proc, [agi1, agi2], agent, resource_ids, code, unknown_parameter

    async def assert_project_exists(project, env, agent_proc, agent_instances, agent, resource_ids, code, unknown_parameter,
                                    exists):
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
            assert func(await data.Resource.get_one(environment=environment, resource_version_id=resource_version_id))
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_environment_no_environment_name(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    with pytest.raises(AttributeError):
        data.Environment(project=project.id, repo_url="", repo_branch="")


@pytest.mark.asyncio
async def test_environment_no_project_id(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    with pytest.raises(AttributeError):
        data.Environment(name="dev", repo_url="", repo_branch="")


@pytest.mark.asyncio
async def test_environment_cascade_content_only(init_dataclasses_and_load_schema):
    project = data.Project(name="proj")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    agent_proc = data.AgentProcess(hostname="testhost",
                                   environment=env.id,
                                   first_seen=datetime.datetime.now(),
                                   last_seen=datetime.datetime.now(),
                                   sid=uuid.uuid4())
    await agent_proc.insert()

    agi1 = data.AgentInstance(process=agent_proc.sid, name="agi1", tid=env.id)
    await agi1.insert()
    agi2 = data.AgentInstance(process=agent_proc.sid, name="agi2", tid=env.id)
    await agi2.insert()

    agent = data.Agent(environment=env.id, name="agi1", last_failover=datetime.datetime.now(), paused=False, primary=agi1.id)
    await agent.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(version=version, environment=env.id)
    await cm.insert()

    resource_ids = []
    for i in range(5):
        path = "/etc/file" + str(i)
        key = "std::File[agent1,path=" + path + "]"
        res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version,
                                 attributes={"path": path})
        await res1.insert()
        resource_ids.append((res1.environment, res1.resource_version_id))

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
        assert (await data.Resource.get_one(environment=environment, resource_version_id=resource_version_id)) is not None
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
        assert (await data.Resource.get_one(environment=environment, resource_version_id=resource_version_id)) is None
    assert (await data.Code.get_one(environment=code.environment, version=code.version)) is None
    assert (await data.UnknownParameter.get_by_id(unknown_parameter.id)) is None
    assert (await env.get(data.AUTO_DEPLOY)) is True


@pytest.mark.asyncio
async def test_environment_set_setting_parameter(init_dataclasses_and_load_schema):
    project = data.Project(name="proj")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    assert (await env.get(data.AUTO_DEPLOY)) is False
    await env.set(data.AUTO_DEPLOY, True)
    assert (await env.get(data.AUTO_DEPLOY)) is True
    await env.unset(data.AUTO_DEPLOY)
    assert (await env.get(data.AUTO_DEPLOY)) is False

    with pytest.raises(KeyError):
        await env.set("set_non_existing_parameter", 1)
    with pytest.raises(KeyError):
        await env.get("get_non_existing_parameter")
    with pytest.raises(AttributeError):
        await env.set(data.AUTO_DEPLOY, 5)


@pytest.mark.asyncio
async def test_environment_deprecated_setting(init_dataclasses_and_load_schema, caplog):
    project = data.Project(name="proj")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for (deprecated_option, new_option) in [(data.AUTOSTART_AGENT_INTERVAL, data.AUTOSTART_AGENT_DEPLOY_INTERVAL),
                                            (data.AUTOSTART_SPLAY, data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)]:
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


@pytest.mark.asyncio
async def test_agent_process(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    sid = uuid.uuid4()
    agent_proc = data.AgentProcess(hostname="testhost",
                                   environment=env.id,
                                   first_seen=datetime.datetime.now(),
                                   last_seen=datetime.datetime.now(),
                                   sid=sid)
    await agent_proc.insert()

    agi1 = data.AgentInstance(process=agent_proc.sid, name="agi1", tid=env.id)
    await agi1.insert()
    agi2 = data.AgentInstance(process=agent_proc.sid, name="agi2", tid=env.id)
    await agi2.insert()

    agent_procs = await data.AgentProcess.get_by_env(env=env.id)
    assert len(agent_procs) == 1
    assert agent_procs[0].sid == agent_proc.sid

    assert (await data.AgentProcess.get_by_sid(sid)).sid == agent_proc.sid
    assert (await data.AgentProcess.get_by_sid(uuid.UUID(int=1))) is None

    live_procs = await data.AgentProcess.get_live()
    assert len(live_procs) == 1
    assert live_procs[0].sid == agent_proc.sid

    live_by_env_procs = await data.AgentProcess.get_live_by_env(env=env.id)
    assert len(live_by_env_procs) == 1
    assert live_by_env_procs[0].sid == agent_proc.sid

    await agent_proc.update_fields(expired=datetime.datetime.now())

    live_procs = await data.AgentProcess.get_live()
    assert len(live_procs) == 0

    live_by_env_procs = await data.AgentProcess.get_live_by_env(env=env.id)
    assert len(live_by_env_procs) == 0

    await agent_proc.delete_cascade()

    assert (await data.AgentProcess.get_one(sid=agent_proc.sid)) is None
    assert (await data.AgentInstance.get_by_id(agi1.id)) is None
    assert (await data.AgentInstance.get_by_id(agi2.id)) is None


@pytest.mark.asyncio
async def test_agent_instance(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    sid = uuid.uuid4()
    agent_proc = data.AgentProcess(hostname="testhost",
                                   environment=env.id,
                                   first_seen=datetime.datetime.now(),
                                   last_seen=datetime.datetime.now(),
                                   sid=sid)
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

    await agi1.update_fields(expired=datetime.datetime.now())

    active_instances = await data.AgentInstance.active()
    assert len(active_instances) == 1
    assert agi1.id not in [x.id for x in active_instances]
    assert agi2.id in [x.id for x in active_instances]

    current_instances = await data.AgentInstance.active_for(env.id, agi1_name)
    assert len(current_instances) == 0
    current_instances = await data.AgentInstance.active_for(env.id, agi2_name)
    assert len(current_instances) == 1
    assert current_instances[0].id == agi2.id


@pytest.mark.asyncio
async def test_agent(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    sid = uuid.uuid4()
    agent_proc = data.AgentProcess(hostname="testhost",
                                   environment=env.id,
                                   first_seen=datetime.datetime.now(),
                                   last_seen=datetime.datetime.now(),
                                   sid=sid)
    await agent_proc.insert()

    agi1_name = "agi1"
    agi1 = data.AgentInstance(process=agent_proc.sid, name=agi1_name, tid=env.id)
    await agi1.insert()

    agent1 = data.Agent(environment=env.id, name="agi1_agent1", last_failover=datetime.datetime.now(), paused=False,
                        primary=agi1.id)
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

    assert agent1.get_status() == "up"
    assert agent2.get_status() == "down"
    assert agent3.get_status() == "paused"

    for agent in [agent1, agent2, agent3]:
        assert agent.to_dict()["state"] == agent.get_status()

    await agent1.update_fields(paused=True)
    assert agent1.get_status() == "paused"

    await agent2.update_fields(primary=agi1.id)
    assert agent2.get_status() == "up"

    await agent3.update_fields(paused=False)
    assert agent3.get_status() == "down"

    primary_instance = await data.AgentInstance.get_by_id(agent1.primary)
    primary_process = await data.AgentProcess.get_one(sid=primary_instance.process)
    assert primary_process.sid == agent_proc.sid


@pytest.mark.asyncio
async def test_config_model(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(),
                                 total=1, version_info={})
    await cm.insert()

    # create resources
    key = "std::File[agent1,path=/etc/motd]"
    res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": "/etc/motd"})
    await res1.insert()

    agents = await data.ConfigurationModel.get_agents(env.id, version)
    assert len(agents) == 1
    assert "agent1" in agents


@pytest.mark.asyncio
async def test_model_list(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for version in range(1, 20):
        cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=0,
                                     version_info={})
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


@pytest.mark.asyncio
async def test_model_get_latest_version(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    cms = []
    for version in range(1, 5):
        cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=0,
                                     version_info={})
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


@pytest.mark.asyncio
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
    resource = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version,
                                 attributes={"path": path})
    await resource.insert()

    assert cm.done == 0
    await resource.update_fields(status=const.ResourceState.deployed)
    cm = await data.ConfigurationModel.get_one(version=version, environment=env.id)
    assert cm.done == 1


@pytest.mark.parametrize("resource_state, should_be_deployed", [
    (const.ResourceState.unavailable, True),
    (const.ResourceState.skipped, True),
    (const.ResourceState.deployed, True),
    (const.ResourceState.failed, True),
    (const.ResourceState.deploying, False),
    (const.ResourceState.available, False),
    (const.ResourceState.cancelled, True),
    (const.ResourceState.undefined, True),
    (const.ResourceState.skipped_for_undefined, True),
    (const.ResourceState.processing_events, False),
])
@pytest.mark.asyncio
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
    resource = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version,
                                 attributes={"path": path})
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


@pytest.mark.asyncio
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
                    res = data.Resource.new(environment=env.id, status=const.ResourceState.deployed,
                                            resource_version_id=f"std::File[agent1,path=/etc/file{r}],v={i}",
                                            attributes={"purge_on_delete": False}, last_deploy=datetime.datetime.now())
                else:
                    res = data.Resource.new(environment=env.id, status=const.ResourceState.deploying,
                                            resource_version_id=f"std::File[agent1,path=/etc/file{r}],v={i}",
                                            attributes={"purge_on_delete": False})
                await res.insert()

    for env in [env1, env2]:
        cms = await data.ConfigurationModel.get_list(environment=env.id)
        assert len(cms) == 2
        for c in cms:
            assert c.environment == env.id
            assert c.done == 2

    cms = await data.ConfigurationModel.get_list(environment=uuid.uuid4())
    assert not cms


@pytest.mark.asyncio
async def test_model_serialization(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = int(time.time())
    now = datetime.datetime.now()
    cm = data.ConfigurationModel(environment=env.id, version=version, date=now, total=1, version_info={})
    await cm.insert()

    assert cm.done == 0

    path = "/etc/file"
    key = "std::File[agent1,path=" + path + "]"
    resource = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version,
                                 attributes={"path": path}, status=const.ResourceState.deployed)
    await resource.insert()

    cm = await data.ConfigurationModel.get_one(environment=env.id, version=version)
    dct = cm.to_dict()
    assert dct['version'] == version
    assert dct['environment'] == env.id
    assert dct['date'] == now
    assert not dct['released']
    assert not dct['deployed']
    assert dct['result'] == const.VersionState.pending
    assert dct['version_info'] == {}
    assert dct['total'] == 1
    assert dct['done'] == 1
    assert dct['status'] == {str(uuid.uuid5(env.id, key)): {"id": key, "status": const.ResourceState.deployed.name}}


@pytest.mark.asyncio
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
    resource = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version,
                                 attributes={"path": path})
    await resource.insert()

    code = data.Code(version=version, resource="std::File", environment=env.id)
    await code.insert()

    unknown_parameter = data.UnknownParameter(name="test", environment=env.id, version=version, source="")
    await unknown_parameter.insert()

    await cm.delete_cascade()

    assert (await data.ConfigurationModel.get_list()) == []
    assert (await data.Resource.get_one(environment=resource.environment,
                                        resource_version_id=resource.resource_version_id)) is None
    assert (await data.Code.get_one(environment=code.environment,
                                    resource=code.resource,
                                    version=code.version)) is None
    assert (await data.UnknownParameter.get_by_id(unknown_parameter.id)) is None


@pytest.mark.asyncio
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


@pytest.mark.parametrize("resource_state, version_state", [
    (const.ResourceState.deployed, const.VersionState.success),
    (const.ResourceState.failed, const.VersionState.failed),
    (const.ResourceState.undefined, const.VersionState.failed),
    (const.ResourceState.skipped_for_undefined, const.VersionState.failed),
    (const.ResourceState.cancelled, const.VersionState.failed),
    (const.ResourceState.skipped, const.VersionState.failed)
])
@pytest.mark.asyncio
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
    resource1 = data.Resource.new(environment=env.id, resource_version_id=key1 + ",v=%d" % version,
                                  attributes={"path": path1}, status=resource_state)
    await resource1.insert()

    path2 = "/etc/file2"
    key2 = "std::File[agent1,path=" + path2 + "]"
    resource2 = data.Resource.new(environment=env.id, resource_version_id=key2 + ",v=%d" % version,
                                  attributes={"path": path2}, status=const.ResourceState.deployed)
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
        return data.Resource.new(environment=env_id, resource_version_id=get_id(n),
                                 status=status,
                                 attributes={"path": get_path(n),
                                             "purge_on_delete": False,
                                             "purged": False,
                                             "requires": requires})

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


@pytest.mark.asyncio
async def test_resource_purge_on_delete(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # model 1
    version = 1
    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=2,
                                  version_info={}, released=True, deployed=True)
    await cm1.insert()

    res11 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % version,
                              status=const.ResourceState.deployed,
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    await res11.insert()

    res12 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent2,path=/etc/motd],v=%s" % version,
                              status=const.ResourceState.deployed,
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True})
    await res12.insert()

    # model 2 (multiple undeployed versions)
    while version < 10:
        version += 1
        cm2 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                      version_info={}, released=False, deployed=False)
        await cm2.insert()

        res21 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent5,path=/etc/motd],v=%s" % version,
                                  status=const.ResourceState.available,
                                  attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
        await res21.insert()

    # model 3
    version += 1
    cm3 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=0, version_info={})
    await cm3.insert()

    to_purge = await data.Resource.get_deleted_resources(env.id, version, set())

    assert len(to_purge) == 1
    assert to_purge[0].model == 1
    assert to_purge[0].resource_id == "std::File[agent1,path=/etc/motd]"


@pytest.mark.asyncio
async def test_issue_422(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # model 1
    version = 1
    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=True, deployed=True)
    await cm1.insert()

    res11 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % version,
                              status=const.ResourceState.deployed,
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    await res11.insert()

    # model 2 (multiple undeployed versions)
    version += 1
    cm2 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=False, deployed=False)
    await cm2.insert()

    res21 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % version,
                              status=const.ResourceState.available,
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    await res21.insert()

    # model 3
    version += 1
    cm3 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=0, version_info={})
    await cm3.insert()

    to_purge = await data.Resource.get_deleted_resources(env.id, version, set())

    assert len(to_purge) == 1
    assert to_purge[0].model == 1
    assert to_purge[0].resource_id == "std::File[agent1,path=/etc/motd]"


@pytest.mark.asyncio
async def test_get_latest_resource(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    key = "std::File[agent1,path=/etc/motd]"
    assert (await data.Resource.get_latest_version(env.id, key)) is None

    version = 1
    cm2 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=False, deployed=False)
    await cm2.insert()
    res11 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version,
                              status=const.ResourceState.deployed,
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    await res11.insert()

    version = 2
    cm2 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=False, deployed=False)
    await cm2.insert()
    res12 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version,
                              status=const.ResourceState.deployed,
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True})
    await res12.insert()

    res = await data.Resource.get_latest_version(env.id, key)
    assert res.model == 2


@pytest.mark.asyncio
async def test_get_resources(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=True, deployed=True)
    await cm1.insert()

    resource_ids = []
    for i in range(1, 11):
        res = data.Resource.new(environment=env.id,
                                resource_version_id="std::File[agent1,path=/tmp/file%d],v=%d" % (i, version),
                                status=const.ResourceState.deployed,
                                attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
        await res.insert()
        resource_ids.append(res.resource_version_id)

    resources = await data.Resource.get_resources(env.id, resource_ids)
    assert len(resources) == len(resource_ids)
    assert sorted([x.resource_version_id for x in resources]) == sorted(resource_ids)

    resources = await data.Resource.get_resources(env.id, [resource_ids[0], "abcd"])
    assert len(resources) == 1

    resources = await data.Resource.get_resources(env.id, [])
    assert len(resources) == 0


@pytest.mark.asyncio
async def test_model_get_resources_for_version(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    resource_ids_version_one = []
    version = 1
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                 version_info={}, released=True, deployed=True)
    await cm.insert()
    for i in range(1, 11):
        res = data.Resource.new(environment=env.id,
                                resource_version_id="std::File[agent1,path=/tmp/file%d],v=%d" % (i, version),
                                status=const.ResourceState.deployed,
                                attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
        await res.insert()
        resource_ids_version_one.append(res.resource_version_id)

    resource_ids_version_two = []
    version += 1
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                 version_info={}, released=True, deployed=True)
    await cm.insert()
    for i in range(11, 21):
        res = data.Resource.new(environment=env.id,
                                resource_version_id="std::File[agent2,path=/tmp/file%d],v=%d" % (i, version),
                                status=const.ResourceState.deployed,
                                attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
        await res.insert()
        resource_ids_version_two.append(res.resource_version_id)

    for version in range(3, 5):
        cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                     version_info={}, released=True, deployed=True)
        await cm.insert()

    async def make_with_status(i, status):
        res = data.Resource.new(environment=env.id, resource_version_id="std::File[agent3,path=/tmp/file%d],v=3" % i,
                                status=status,
                                attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
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


@pytest.mark.asyncio
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
        resource = data.Resource.new(environment=env_id,
                                     resource_version_id=resource_version_id,
                                     attributes={"path": path},
                                     status=status)
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


@pytest.mark.asyncio
async def test_escaped_resources(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=True, deployed=True)
    await cm1.insert()

    routes = {"8.0.0.0/8": "1.2.3.4", "0.0.0.0/0": "127.0.0.1"}
    res = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,name=router],v=%d" % version,
                            status=const.ResourceState.deployed,
                            attributes={"name": "router", "purge_on_delete": True, "purged": False, "routes": routes})
    await res.insert()
    resource_id = res.resource_version_id

    resources = await data.Resource.get_resources(env.id, [resource_id])
    assert len(resources) == 1

    assert resources[0].attributes["routes"] == routes


@pytest.mark.asyncio
async def test_resource_provides(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=True, deployed=True)
    await cm1.insert()

    res1 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file1],v=%d" % version,
                             status=const.ResourceState.deployed,
                             attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    res2 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file2],v=%d" % version,
                             status=const.ResourceState.deployed,
                             attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
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


@pytest.mark.asyncio
async def test_resource_hash(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for version in range(1, 4):
        cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                      version_info={}, released=True, deployed=True)
        await cm1.insert()

    res1 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file1],v=1",
                             status=const.ResourceState.deployed,
                             attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    res2 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file1],v=2",
                             status=const.ResourceState.deployed,
                             attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    res3 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file1],v=3",
                             status=const.ResourceState.deployed,
                             attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True})
    await res1.insert()
    await res2.insert()
    await res3.insert()

    assert res1.attribute_hash is not None
    assert res1.attribute_hash == res2.attribute_hash
    assert res3.attribute_hash is not None
    assert res1.attribute_hash != res3.attribute_hash

    readres = await data.Resource.get_resources(env.id,
                                                [res1.resource_version_id, res2.resource_version_id, res3.resource_version_id])

    resource_map = {r.resource_version_id: r for r in readres}
    res1 = resource_map[res1.resource_version_id]
    res2 = resource_map[res2.resource_version_id]
    res3 = resource_map[res3.resource_version_id]

    assert res1.attribute_hash is not None
    assert res1.attribute_hash == res2.attribute_hash
    assert res3.attribute_hash is not None
    assert res1.attribute_hash != res3.attribute_hash


@pytest.mark.asyncio
async def test_resources_report(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # model 1
    version = 1
    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=True, deployed=True)
    await cm1.insert()

    res11 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file1],v=%s" % version,
                              status=const.ResourceState.deployed, last_deploy=datetime.datetime(2018, 7, 14, 12, 30),
                              attributes={"path": "/etc/file1"})
    await res11.insert()
    res12 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file2],v=%s" % version,
                              status=const.ResourceState.deployed, last_deploy=datetime.datetime(2018, 7, 14, 12, 30),
                              attributes={"path": "/etc/file2"})
    await res12.insert()

    # model 2
    version += 1
    cm2 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=False, deployed=False)
    await cm2.insert()
    res21 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file1],v=%s" % version,
                              status=const.ResourceState.available,
                              attributes={"path": "/etc/file1"})
    await res21.insert()
    res22 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file3],v=%s" % version,
                              status=const.ResourceState.available,
                              attributes={"path": "/etc/file3"})
    await res22.insert()

    # model 3
    version += 1
    cm3 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                  version_info={}, released=True, deployed=True)
    await cm3.insert()

    res31 = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/etc/file2],v=%s" % version,
                              status=const.ResourceState.deployed, last_deploy=datetime.datetime(2018, 7, 14, 14, 30),
                              attributes={"path": "/etc/file2"})
    await res31.insert()

    report = await data.Resource.get_resources_report(env.id)
    assert len(report) == 3
    report_as_map = {x["resource_id"]: x for x in report}
    for i in range(1, 4):
        assert f"std::File[agent1,path=/etc/file{i}]" in report_as_map

    assert report_as_map["std::File[agent1,path=/etc/file1]"]["resource_type"] == "std::File"
    assert report_as_map["std::File[agent1,path=/etc/file1]"]["deployed_version"] == 1
    assert report_as_map["std::File[agent1,path=/etc/file1]"]["latest_version"] == 2
    assert report_as_map["std::File[agent1,path=/etc/file1]"]["last_deploy"] == datetime.datetime(2018, 7, 14, 12, 30)
    assert report_as_map["std::File[agent1,path=/etc/file1]"]["agent"] == "agent1"

    assert report_as_map["std::File[agent1,path=/etc/file2]"]["resource_type"] == "std::File"
    assert report_as_map["std::File[agent1,path=/etc/file2]"]["deployed_version"] == 3
    assert report_as_map["std::File[agent1,path=/etc/file2]"]["latest_version"] == 3
    assert report_as_map["std::File[agent1,path=/etc/file2]"]["last_deploy"] == datetime.datetime(2018, 7, 14, 14, 30)
    assert report_as_map["std::File[agent1,path=/etc/file2]"]["agent"] == "agent1"

    assert report_as_map["std::File[agent1,path=/etc/file3]"]["resource_type"] == "std::File"
    assert report_as_map["std::File[agent1,path=/etc/file3]"]["deployed_version"] is None
    assert report_as_map["std::File[agent1,path=/etc/file3]"]["latest_version"] == 2
    assert report_as_map["std::File[agent1,path=/etc/file3]"]["last_deploy"] is None
    assert report_as_map["std::File[agent1,path=/etc/file3]"]["agent"] == "agent1"


@pytest.mark.asyncio
async def test_resources_delete_cascade(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                 version_info={}, released=True, deployed=True)
    await cm.insert()

    res1 = data.Resource.new(environment=env.id,
                             resource_version_id="std::File[agent1,path=/etc/file1],v=%s" % version,
                             status=const.ResourceState.deployed, last_deploy=datetime.datetime.now(),
                             attributes={"path": "/etc/file1"})
    await res1.insert()
    res2 = data.Resource.new(environment=env.id,
                             resource_version_id="std::File[agent1,path=/etc/file2],v=%s" % version,
                             status=const.ResourceState.deployed, last_deploy=datetime.datetime.now(),
                             attributes={"path": "/etc/file1"})
    await res2.insert()
    action_id_resource_action_1 = uuid.uuid4()
    resource_action1 = data.ResourceAction(environment=env.id, resource_version_ids=[res1.resource_version_id],
                                           action_id=action_id_resource_action_1, action=const.ResourceAction.deploy,
                                           started=datetime.datetime.now())
    await resource_action1.insert()

    action_id_resource_action_2 = uuid.uuid4()
    resource_action2 = data.ResourceAction(environment=env.id, resource_version_ids=[res2.resource_version_id],
                                           action_id=action_id_resource_action_2, action=const.ResourceAction.deploy,
                                           started=datetime.datetime.now())
    await resource_action2.insert()

    await res1.delete_cascade()

    assert (await data.Resource.get_one(environment=res1.environment, resource_version_id=res1.resource_version_id)) is None
    assert (await data.ResourceAction.get_one(action_id=resource_action1.action_id)) is None
    resource = await data.Resource.get_one(environment=res2.environment, resource_version_id=res2.resource_version_id)
    assert resource is not None
    assert (resource.environment, resource.resource_version_id) == (res2.environment, res2.resource_version_id)
    resource_action = await data.ResourceAction.get_one(action_id=resource_action2.action_id)
    assert resource_action is not None
    assert resource_action.action_id == resource_action2.action_id
    resource_version_ids = await data.ResourceVersionId.get_list(environment=env.id)
    assert len(resource_version_ids) == 1
    assert resource_version_ids[0].action_id == action_id_resource_action_2


@pytest.mark.asyncio
async def test_resource_action(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    now = datetime.datetime.now()
    action_id = uuid.uuid4()
    resource_version_ids = ["std::File[agent1,path=/etc/file1],v=1", "std::File[agent1,path=/etc/file2],v=1"]
    resource_action = data.ResourceAction(environment=env.id, resource_version_ids=resource_version_ids, action_id=action_id,
                                          action=const.ResourceAction.deploy, started=now)
    await resource_action.insert()

    resource_action.add_changes({"rid": {"field1": {"old": "a", "new": "b"}, "field2": {}}})
    await resource_action.save()

    resource_action.add_changes({"rid": {"field2": {"old": "c", "new": "d"}, "field3": ['removed', 'installed']}})
    await resource_action.save()

    resource_action.add_logs([{}, {}])
    await resource_action.save()

    resource_action.add_logs([{}, {}])
    await resource_action.save()

    resource_action.set_field("status", const.ResourceState.failed)
    await resource_action.save()

    ra_via_get_by_id = await data.ResourceAction.get_one(action_id=resource_action.action_id)
    ra_list = await data.ResourceAction.get_list(action_id=resource_action.action_id)
    assert len(ra_list) == 1
    ra_via_get_list = ra_list[0]
    ra_via_get = await data.ResourceAction.get(action_id=resource_action.action_id)
    for ra in [ra_via_get_by_id, ra_via_get_list, ra_via_get]:
        assert ra.action_id == action_id
        assert ra.action == const.ResourceAction.deploy
        assert ra.started == now
        assert ra.finished is None

        assert len(ra.resource_version_ids) == 2
        assert sorted(ra.resource_version_ids) == sorted(resource_version_ids)

        assert len(ra.changes["rid"]) == 3
        assert ra.changes["rid"]["field1"]["old"] == "a"
        assert ra.changes["rid"]["field1"]["new"] == "b"
        assert ra.changes["rid"]["field2"]["old"] == "c"
        assert ra.changes["rid"]["field2"]["new"] == "d"
        assert ra.changes["rid"]["field3"] == ['removed', 'installed']
        assert ra.status == const.ResourceState.failed

        assert len(ra.messages) == 4
        for message in ra.messages:
            assert message == {}


@pytest.mark.asyncio
async def test_resource_action_get_logs(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    for i in range(1, 11):
        action_id = uuid.uuid4()
        resource_action = data.ResourceAction(environment=env.id,
                                              resource_version_ids=["std::File[agent1,path=/etc/motd],v=%1"],
                                              action_id=action_id,
                                              action=const.ResourceAction.deploy,
                                              started=datetime.datetime.now())
        await resource_action.insert()
        resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=i)])
        await resource_action.save()

    action_id = uuid.uuid4()

    resource_action = data.ResourceAction(environment=env.id,
                                          resource_version_ids=["std::File[agent1,path=/etc/motd],v=%1"],
                                          action_id=action_id,
                                          action=const.ResourceAction.dryrun,
                                          started=datetime.datetime.now())
    await resource_action.insert()
    times = datetime.datetime.now()
    resource_action.add_logs([data.LogLine.log(logging.WARNING, "warning version %(version)d", version=100, timestamp=times)])
    await resource_action.save()

    resource_actions = await data.ResourceAction.get_log(env.id,
                                                         "std::File[agent1,path=/etc/motd],v=%1")
    assert len(resource_actions) == 11
    for i in range(len(resource_actions)):
        action = resource_actions[i]
        if i == 0:
            assert action.action == const.ResourceAction.dryrun
        else:
            assert action.action == const.ResourceAction.deploy
    resource_actions = await data.ResourceAction.get_log(env.id,
                                                         "std::File[agent1,path=/etc/motd],v=%1",
                                                         const.ResourceAction.dryrun.name)
    assert len(resource_actions) == 1
    action = resource_actions[0]
    assert action.action == const.ResourceAction.dryrun
    assert action.messages[0]["level"] == LogLevel.WARNING.name
    assert action.messages[0]["timestamp"] == times
    resource_actions = await data.ResourceAction.get_log(env.id,
                                                         "std::File[agent1,path=/etc/motd],v=%1",
                                                         const.ResourceAction.deploy.name, limit=2)
    assert len(resource_actions) == 2
    for action in resource_actions:
        assert len(action.messages) == 1
        assert action.messages[0]["level"] == LogLevel.INFO.name


@pytest.mark.asyncio
async def test_data_document_recursion(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    now = datetime.datetime.now()
    ra = data.ResourceAction(environment=env.id,
                             resource_version_ids=["test"],
                             action_id=uuid.uuid4(),
                             action=const.ResourceAction.store,
                             started=now,
                             finished=now,
                             messages=[data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=2)])
    await ra.insert()


@pytest.mark.asyncio
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

    def assert_match_code(code1, code2):
        assert code1 is not None
        assert code2 is not None
        assert code1.environment == code1.environment
        assert code1.resource == code2.resource
        assert code1.version == code2.version
        shared_keys_source_refs = [k for k in code1.source_refs
                                   if k in code2.source_refs and code1.source_refs[k] == code2.source_refs[k]]
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
    assert len(code_list) == 0


@pytest.mark.asyncio
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
        parameter = data.Parameter(name="param_" + t, value="test_val_" + t, environment=env.id, source="test",
                                   updated=current_time)
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_form(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    form = data.Form(environment=env.id, form_type="a type")
    await form.insert()
    other_form = data.Form(environment=env.id, form_type="other type")
    await other_form.insert()

    retrieved_form = await data.Form.get_form(env.id, "a type")
    assert retrieved_form is not None
    assert (retrieved_form.environment, retrieved_form.form_type) == (form.environment, form.form_type)

    non_existing_form = await data.Form.get_form(env.id, "non-existing-form")
    assert non_existing_form is None


@pytest.mark.asyncio
async def test_formrecord(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    form = data.Form(environment=env.id, form_type="a type")
    await form.insert()

    fields_for_record = {"field1": "val1", "field2": "val2"}
    changed = datetime.datetime.now()
    formrecord = data.FormRecord(environment=env.id, form=form.form_type, fields=fields_for_record, changed=changed)
    await formrecord.insert()

    results = await data.FormRecord.get_list()
    assert len(results) == 1
    result = results[0]
    assert result.id == formrecord.id
    assert len(result.fields) == 2
    for key, value in fields_for_record.items():
        assert result.fields[key] == value
    assert result.changed == formrecord.changed


@pytest.mark.asyncio
async def test_compile_get_reports(init_dataclasses_and_load_schema):
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

    retrieved_compiles = await data.Compile.get_reports(env.id, None, None, None)
    assert len(retrieved_compiles) == 3
    assert retrieved_compiles[0]["id"] == compiles[1].id
    assert retrieved_compiles[1]["id"] == compiles[0].id
    assert retrieved_compiles[2]["id"] == compiles[2].id

    limit = 1
    retrieved_compiles = await data.Compile.get_reports(env.id, 1, None, None)
    assert len(retrieved_compiles) == 1
    assert retrieved_compiles[0]["id"] == compiles[1].id

    start_time = datetime.datetime(2018, 7, 13, 12, 30)
    retrieved_compiles = await data.Compile.get_reports(env.id, None, start_time, None)
    assert len(retrieved_compiles) == 2
    assert retrieved_compiles[0]["id"] == compiles[1].id
    assert retrieved_compiles[1]["id"] == compiles[0].id

    end_time = datetime.datetime(2018, 7, 15, 12, 30)
    retrieved_compiles = await data.Compile.get_reports(env.id, None, None, end_time)
    assert len(retrieved_compiles) == 2
    assert retrieved_compiles[0]["id"] == compiles[0].id
    assert retrieved_compiles[1]["id"] == compiles[2].id

    retrieved_compiles = await data.Compile.get_reports(env.id, limit, start_time, end_time)
    assert len(retrieved_compiles) == 1
    assert retrieved_compiles[0]["id"] == compiles[0].id


@pytest.mark.asyncio
async def test_compile_get_report(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # Compile 1
    started = datetime.datetime(2018, 7, 15, 12, 30)
    completed = datetime.datetime(2018, 7, 15, 13, 00)
    compile1 = data.Compile(environment=env.id, started=started, completed=completed)
    await compile1.insert()

    report_of_compile = await data.Compile.get_report(compile1.id)
    assert report_of_compile["reports"] == []

    report11 = data.Report(started=datetime.datetime.now(), completed=datetime.datetime.now(),
                           command="cmd", name="test", compile=compile1.id)
    await report11.insert()
    report12 = data.Report(started=datetime.datetime.now(), completed=datetime.datetime.now(),
                           command="cmd", name="test", compile=compile1.id)
    await report12.insert()

    # Compile 2
    compile2 = data.Compile(environment=env.id)
    await compile2.insert()
    report21 = data.Report(started=datetime.datetime.now(), completed=datetime.datetime.now(),
                           command="cmd", name="test", compile=compile2.id)
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


@pytest.mark.asyncio
async def test_match_tables_in_db_against_table_definitions_in_orm(postgres_db, database_name, postgresql_client,
                                                                   init_dataclasses_and_load_schema):
    table_names = await postgresql_client.fetch("SELECT table_name FROM information_schema.tables "
                                                "WHERE table_schema='public'")
    table_names_in_database = [x["table_name"] for x in table_names]
    table_names_in_classes_list = [x.__name__.lower() for x in data._classes]
    assert len(table_names_in_classes_list) == len(table_names_in_database)
    for item in table_names_in_classes_list:
        assert item in table_names_in_database


@pytest.mark.asyncio
async def test_dbschema_update_db_schema(postgresql_client, init_dataclasses_and_load_schema, get_columns_in_db_table):
    async def update_function1(connection):
        await connection.execute("CREATE TABLE public.tab(id integer primary key, val varchar NOT NULL);")

    async def update_function2(connection):
        await connection.execute("ALTER TABLE public.tab DROP COLUMN val;")

    current_db_version = await data.SchemaVersion.get_current_version()
    version_update1 = current_db_version + 1
    version_update2 = current_db_version + 2
    update_function_map = {version_update1: update_function1, version_update2: update_function2}

    db_schema = data.DBSchema()
    await db_schema._update_db_schema(update_function_map, postgresql_client)

    assert (await data.SchemaVersion.get_current_version()) == version_update2
    assert sorted(["id"]) == sorted(await get_columns_in_db_table("tab"))


@pytest.mark.asyncio
async def test_dbschema_update_db_schema_failure(postgresql_client, init_dataclasses_and_load_schema, get_columns_in_db_table):
    async def update_function(connection):
        # Syntax error should trigger database rollback
        await connection.execute("CREATE TABE public.tab(id integer primary key, val varchar NOT NULL);")

    current_db_version = await data.SchemaVersion.get_current_version()
    new_db_version = current_db_version + 1
    update_function_map = {new_db_version: update_function}

    db_schema = data.DBSchema()
    try:
        await db_schema._update_db_schema(update_function_map, postgresql_client)
    except PostgresSyntaxError:
        pass

    # Assert rollback
    assert (await data.SchemaVersion.get_current_version()) == current_db_version
    assert (await postgresql_client.fetchval("SELECT table_name FROM information_schema.tables "
                                             "WHERE table_schema='public' AND table_name='tab'")) is None

    async def update_function(connection):
        # Fix syntax issue
        await connection.execute("CREATE TABLE public.tab(id integer primary key, val varchar NOT NULL);")

    update_function_map[new_db_version] = update_function
    await db_schema._update_db_schema(update_function_map, postgresql_client)

    # Assert update
    assert (await data.SchemaVersion.get_current_version()) == new_db_version
    assert sorted(["id", "val"]) == sorted(await get_columns_in_db_table("tab"))


@pytest.mark.asyncio
async def test_dbschema_get_dct_with_update_functions():
    module_names = [modname for _, modname, ispkg in pkgutil.iter_modules(data.DBSchema.PACKAGE_WITH_UPDATE_FILES.__path__)
                    if not ispkg]
    all_versions = [int(mod_name[1:]) for mod_name in module_names]

    db_schema = data.DBSchema()
    update_function_map = await db_schema._get_dct_with_update_functions()
    assert sorted(all_versions) == sorted(update_function_map.keys())
    for version, update_function in update_function_map.items():
        assert version >= 0
        assert isinstance(update_function, types.FunctionType)
        assert update_function.__name__ == "update"
        assert inspect.getfullargspec(update_function)[0] == ["connection"]

    # Test behavior of "versions_higher_than" parameter
    lowest_version = min(update_function_map.keys())
    one_version_higher_than_lowest_version = lowest_version + 1

    restricted_function_map = await db_schema._get_dct_with_update_functions(one_version_higher_than_lowest_version)
    assert len(restricted_function_map) == len(update_function_map) - 1
    assert lowest_version not in restricted_function_map


@pytest.mark.asyncio
async def test_purgelog_test(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # ResourceAction 1
    timestamp_ra1 = datetime.datetime.now() - datetime.timedelta(days=8)
    log_line_ra1 = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=1)
    action_id = uuid.uuid4()
    ra1 = data.ResourceAction(environment=env.id, resource_version_ids=["id1"], action_id=action_id,
                              action=const.ResourceAction.store, started=timestamp_ra1, finished=datetime.datetime.now(),
                              messages=[log_line_ra1])
    await ra1.insert()

    # ResourceAction 2
    timestamp_ra2 = datetime.datetime.now() - datetime.timedelta(days=6)
    log_line_ra2 = data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=2)
    action_id = uuid.uuid4()
    ra2 = data.ResourceAction(environment=env.id, resource_version_ids=["id2"], action_id=action_id,
                              action=const.ResourceAction.store, started=timestamp_ra2, finished=datetime.datetime.now(),
                              messages=[log_line_ra2])
    await ra2.insert()

    assert len(await data.ResourceAction.get_list()) == 2
    await data.ResourceAction.purge_logs()
    assert len(await data.ResourceAction.get_list()) == 1
    remaining_resource_action = (await data.ResourceAction.get_list())[0]
    assert remaining_resource_action.action_id == ra2.action_id


@pytest.mark.asyncio
async def test_insert_many(init_dataclasses_and_load_schema, postgresql_client):
    project1 = data.Project(name="proj1")
    project2 = data.Project(name="proj2")
    projects = [project1, project2]
    await data.Project.insert_many(projects)

    result = await data.Project.get_list()
    project_names_in_result = [res.name for res in result]

    assert len(project_names_in_result) == 2
    assert sorted(["proj1", "proj2"]) == sorted(project_names_in_result)


@pytest.mark.asyncio
async def test_resources_json(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1,
                                 version_info={}, released=True, deployed=True)
    await cm.insert()

    res1 = data.Resource.new(environment=env.id,
                             resource_version_id="std::File[agent1,path=/etc/file1],v=%s" % version,
                             status=const.ResourceState.deployed, last_deploy=datetime.datetime.now(),
                             attributes={"attr": [{"a": 1, "b": "c"}]})
    await res1.insert()

    res = await data.Resource.get_one(environment=res1.environment, resource_version_id=res1.resource_version_id)

    assert res1.attributes == res.attributes
