import pytest
import asyncpg
import datetime
import uuid
import time
import logging
from inmanta import data_pg as data, const

SCHEMA_FILE="misc/postgresql/pg_schema.sql"


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

@pytest.fixture
async def init_dataclasses(postgresql_proc):
    connection = await asyncpg.connect('postgresql://%s@%s:%d/' % (postgresql_proc.user, postgresql_proc.host, postgresql_proc.port))
    await data.load_schema(connection)
    data.set_connection(connection)
    yield
    await connection.close()


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
    await data.load_schema(postgresql_client)
    table_names = await postgresql_client.fetch("SELECT table_name FROM information_schema.tables "
                                                "WHERE table_schema='public'")
    table_names = [x["table_name"] for x in table_names]
    for table_name in ["project", "environment", "configurationmodel", "resource", "resourceaction",
                       "code", "unknownparameter", "agentprocess", "agentinstance", "agent"]:
        assert table_name in table_names









@pytest.mark.asyncio
async def test_project(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()

    projects = await data.Project.get_list(name="test")
    assert len(projects) == 1
    assert projects[0].id == project.id

    other = await data.Project.get_by_id(project.id)
    assert project != other
    assert project.id == other.id


@pytest.mark.asyncio
async def test_project_unique(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()

    project = data.Project(name="test")
    with pytest.raises(asyncpg.exceptions.UniqueViolationError):
        await project.insert()


@pytest.mark.asyncio
async def test_environment(init_dataclasses):
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
async def test_agent_process(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    agent_proc = data.AgentProcess(hostname="testhost",
                                   environment=env.id,
                                   first_seen=datetime.datetime.now(),
                                   last_seen=datetime.datetime.now(),
                                   sid=uuid.uuid4())
    await agent_proc.insert()

    agi1 = data.AgentInstance(process=agent_proc.id, name="agi1", tid=env.id)
    await agi1.insert()
    agi2 = data.AgentInstance(process=agent_proc.id, name="agi2", tid=env.id)
    await agi2.insert()

    agent = data.Agent(environment=env.id, name="agi1", last_failover=datetime.datetime.now(), paused=False, id_primary=agi1.id)
    agent = await agent.insert()

    agents = await data.Agent.get_list()
    assert len(agents) == 1
    agent = agents[0]

    primary_instance = await data.AgentInstance.get_by_id(agent.id_primary)
    primary_process = await data.AgentProcess.get_by_id(primary_instance.process)
    assert primary_process.id == agent_proc.id


@pytest.mark.asyncio
async def test_config_model(init_dataclasses):
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
async def test_model_list(init_dataclasses):
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
async def test_resource_purge_on_delete(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()
    version = 1
    # model 1
    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=2, version_info={},
                                  released=True, deployed=True)
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
async def test_issue_422(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()
    version = 1
    # model 1
    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=1, version_info={},
                                  released=True, deployed=True)
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
async def test_get_latest_resource(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()
    key = "std::File[agent1,path=/etc/motd]"
    res11 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=1", status=const.ResourceState.deployed,
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    await res11.insert()

    res12 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=2", status=const.ResourceState.deployed,
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True})
    await res12.insert()

    res = await data.Resource.get_latest_version(env.id, key)
    assert res.model == 2


@pytest.mark.asyncio
async def test_resource_action(postgresql_client, init_dataclasses):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()
    action_id = uuid.uuid4()

    resource_action = data.ResourceAction(environment=env.id, resource_version_ids=[], action_id=action_id,
                                          action=const.ResourceAction.deploy, started=datetime.datetime.now())
    await resource_action.insert()

    resource_action.add_changes({"rid": {"field1": {"old": "a", "new": "b"}, "field2": {}}})
    await resource_action.save()

    query = "SELECT * FROM resourceaction"
    results = await postgresql_client.fetch(query)
    print(results[0]["changes"])

    resource_action.add_changes({"rid": {"field2": {"old": "c", "new": "d"}, "field3": {}}})
    await resource_action.save()

    resource_action.add_logs([{}, {}])
    await resource_action.save()

    resource_action.add_logs([{}, {}])
    await resource_action.save()

    ra = await data.ResourceAction.get_by_id(resource_action.id)

    query = "SELECT * FROM resourceaction"
    results = await postgresql_client.fetch(query)
    print(results[0]["changes"])

    assert len(ra.changes["rid"]) == 3
    assert len(ra.messages) == 4

    assert ra.changes["rid"]["field1"]["old"] == "a"
    assert ra.changes["rid"]["field1"]["new"] == "b"
    assert ra.changes["rid"]["field2"]["old"] == "c"
    assert ra.changes["rid"]["field2"]["new"] == "d"
    assert ra.changes["rid"]["field3"] == {}

    assert ra.logs


@pytest.mark.asyncio
async def test_get_resources(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()
    resource_ids = []
    for i in range(1, 11):
        res = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,path=/tmp/file%d],v=1" % i,
                                status=const.ResourceState.deployed,
                                attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
        await res.insert()
        resource_ids.append(res.resource_version_id)

    resources = await data.Resource.get_resources(env.id, resource_ids)
    assert len(resources) == len(resource_ids)
    assert sorted([x.resource_version_id for x in resources]) == sorted(resource_ids)

    resources = await data.Resource.get_resources(env.id, [resource_ids[0], "abcd"])
    assert len(resources) == 1


@pytest.mark.asyncio
async def test_escaped_resources(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()
    routes = {"8.0.0.0/8": "1.2.3.4", "0.0.0.0/0": "127.0.0.1"}
    res = data.Resource.new(environment=env.id, resource_version_id="std::File[agent1,name=router],v=1",
                            status=const.ResourceState.deployed,
                            attributes={"name": "router", "purge_on_delete": True, "purged": False, "routes": routes})
    await res.insert()
    resource_id = res.resource_version_id

    resources = await data.Resource.get_resources(env.id, [resource_id])
    assert len(resources) == 1

    assert resources[0].attributes["routes"] == routes


@pytest.mark.asyncio
async def test_data_document_recursion(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()
    now = datetime.datetime.now()
    ra = data.ResourceAction(environment=env.id, resource_version_ids=["id"], action_id=uuid.uuid4(),
                             action=const.ResourceAction.store, started=now, finished=now,
                             messages=[data.LogLine.log(logging.INFO, "Successfully stored version %(version)d",
                                                        version=2)])
    await ra.insert()


@pytest.mark.asyncio
async def test_resource_provides(init_dataclasses):
    env_id = uuid.uuid4()
    res1 = data.Resource.new(environment=env_id, resource_version_id="std::File[agent1,path=/etc/file1],v=1",
                             status=const.ResourceState.deployed,
                             attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    res2 = data.Resource.new(environment=env_id, resource_version_id="std::File[agent1,path=/etc/file2],v=1",
                             status=const.ResourceState.deployed,
                             attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})

    print(id(res1.provides) == id(res2.provides))
    res1.provides.append(res2.resource_version_id)
    assert len(res2.provides) == 0


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
async def test_undeployable_cache_lazy(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()
    version = 1

    cm1 = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(), total=5, version_info={},
                                  released=False, deployed=False)
    await cm1.insert()
    await populate_model(env.id, version)

    assert cm1.undeployable is None

    undep = await cm1.get_undeployable()
    assert undep == ["std::File[agent1,path=/tmp/%d]" % (3)]

    assert cm1.undeployable is not None

    undep = await cm1.get_undeployable()
    assert undep == ["std::File[agent1,path=/tmp/%d]" % (3)]

    cm1 = await data.ConfigurationModel.get_version(env.id, version)

    assert cm1.undeployable is not None

    undep = await cm1.get_undeployable()
    assert undep == ["std::File[agent1,path=/tmp/%d]" % (3)]


@pytest.mark.asyncio
async def test_undeployable_skip_cache_lazy(init_dataclasses):
    project = data.Project(name="test")
    await project.insert()
    env = data.Environment(name="dev", project=project.id)
    await env.insert()
    version = 2
    cm1 = data.ConfigurationModel(environment=env.id,
                                  version=version,
                                  date=datetime.datetime.now(),
                                  total=5,
                                  version_info={},
                                  released=False, deployed=False)

    await cm1.insert()
    await populate_model(env.id, version)

    assert cm1.skipped_for_undeployable is None

    undep = await cm1.get_skipped_for_undeployable()
    assert undep == ["std::File[agent1,path=/tmp/%d]" % (4), "std::File[agent1,path=/tmp/%d]" % (5)]

    assert cm1.skipped_for_undeployable is not None

    undep = await cm1.get_skipped_for_undeployable()
    assert undep == ["std::File[agent1,path=/tmp/%d]" % (4), "std::File[agent1,path=/tmp/%d]" % (5)]

    cm1 = await data.ConfigurationModel.get_version(env.id, version)

    assert cm1.skipped_for_undeployable is not None

    undep = await cm1.get_skipped_for_undeployable()
    assert undep == ["std::File[agent1,path=/tmp/%d]" % (4), "std::File[agent1,path=/tmp/%d]" % (5)]

