"""
    Copyright 2016 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@inmanta.com
"""
import uuid
import datetime
import time

from inmanta import data
import pytest
import pymongo
from inmanta.data import ConfigurationModel


class Doc(data.BaseDocument):
    name = data.Field(field_type=str, required=True)
    field1 = data.Field(field_type=str, default=None)
    field2 = data.Field(field_type=bool, default=False)
    field3 = data.Field(field_type=list, default=[])

    __indexes__ = [
        dict(keys=[("name", pymongo.ASCENDING)], unique=True)
    ]


@pytest.mark.gen_test
def test_motor(motor):
    yield motor.testCollection.insert({"a": 1, "b": "abcd"})
    results = yield motor.testCollection.find_one({"a": {"$gt": 0}})

    assert("_id" in results)

    yield motor.testCollection.insert({"a": {"b": {"c": 1}}})
    results = motor.testCollection.find({})

    while (yield results.fetch_next):
        assert("a" in results.next_object())


def test_collection_naming():
    assert(Doc.collection_name() == "Doc")


def test_document_def():
    t = Doc(name="doc")
    try:
        t.id = "1234"
        assert(False)
    except TypeError:
        pass

    t.id = uuid.uuid4()
    json = t.to_dict()

    assert("id" in json)
    assert("_id" in t.to_dict(mongo_pk=True))


@pytest.mark.gen_test
def test_document_insert(motor):
    Doc.set_connection(motor)

    d = Doc(name="test")

    yield d.insert()
    docs = yield motor.Doc.find({}).to_list(length=10)
    assert(len(docs) == 1)

    doc = yield Doc.get_by_id(d.id)
    assert(doc.name == d.name)


@pytest.mark.gen_test
def test_get_by_id(motor):
    Doc.set_connection(motor)

    d = Doc(name="test")
    yield d.insert()

    d1 = yield Doc.get_by_id(d.id)
    assert(d1.name == d.name)

    d2 = yield Doc.get_by_id(uuid.uuid4())
    assert(d2 is None)


@pytest.mark.gen_test
def test_defaults(motor):
    Doc.set_connection(motor)

    d = Doc(name="test")
    yield d.insert()

    assert(d.to_dict()["field1"] is None)

    assert(not d.field2)

    d2 = yield Doc.get_by_id(d.id)
    d2.insert()

    assert(not d2.field2)

    d.field3.append(1)


@pytest.mark.gen_test
def test_document_update(motor):
    Doc.set_connection(motor)

    d = Doc(name="test")
    yield d.insert()

    yield d.update(name="test2")
    result = yield motor.Doc.find_one({"name": "test2"})
    assert("name" in result)


@pytest.mark.gen_test
def test_document_delete(motor):
    Doc.set_connection(motor)

    d = Doc(name="test")
    yield d.insert()
    yield Doc.delete_all(name="test")

    docs = yield Doc.get_list()
    assert(len(docs) == 0)


@pytest.mark.gen_test
def test_project(data_module):
    project = data.Project(name="test")
    yield project.insert()

    projects = yield data.Project.get_list(name="test")
    assert len(projects) == 1
    assert projects[0].id == project.id

    other = yield data.Project.get_by_id(project.id)
    assert project != other
    assert project.id == other.id


@pytest.mark.gen_test
def test_project_unique(data_module):
    project = data.Project(name="test")
    yield project.insert()

    project = data.Project(name="test")
    with pytest.raises(pymongo.errors.DuplicateKeyError):
        yield project.insert()


@pytest.mark.gen_test
def test_environment(data_module):
    project = data.Project(name="test")
    yield project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    yield env.insert()
    assert env.project == project.id

    yield project.delete_cascade()

    projects = yield data.Project.get_list()
    envs = yield data.Environment.get_list()
    assert len(projects) == 0
    assert len(envs) == 0


@pytest.mark.gen_test
def test_agent_process(data_module):
    project = data.Project(name="test")
    yield project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    yield env.insert()

    agent_proc = data.AgentProcess(hostname="testhost",
                                   environment=env.id,
                                   first_seen=datetime.datetime.now(),
                                   last_seen=datetime.datetime.now(),
                                   sid=uuid.uuid4())
    yield agent_proc.insert()

    agi1 = data.AgentInstance(process=agent_proc.id, name="agi1", tid=env.id)
    yield agi1.insert()
    agi2 = data.AgentInstance(process=agent_proc.id, name="agi2", tid=env.id)
    yield agi2.insert()

    agent = data.Agent(environment=env.id, name="agi1", last_failover=datetime.datetime.now(), paused=False, primary=agi1.id)
    agent = yield agent.insert()

    agents = yield data.Agent.get_list()
    assert len(agents) == 1
    agent = agents[0]

    primary_instance = yield data.AgentInstance.get_by_id(agent.primary)
    primary_process = yield data.AgentProcess.get_by_id(primary_instance.process)
    assert primary_process.id == agent_proc.id


@pytest.mark.gen_test
def test_config_model(data_module):
    project = data.Project(name="test")
    yield project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    yield env.insert()

    version = int(time.time())
    cm = data.ConfigurationModel(environment=env.id, version=version, date=datetime.datetime.now(),
                                 total=1, version_info={})
    yield cm.insert()

    # create resources
    key = "std::File[agent1,path=/etc/motd]"
    res1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": "/etc/motd"})
    yield res1.insert()

    agents = yield data.ConfigurationModel.get_agents(env.id, version)
    assert(len(agents) == 1)
    assert("agent1" in agents)


@pytest.mark.gen_test
def test_model_list(data_module):
    env_id = uuid.uuid4()

    for version in range(1, 20):
        cm = data.ConfigurationModel(environment=env_id, version=version, date=datetime.datetime.now(), total=0,
                                     version_info={})
        yield cm.insert()

    versions = yield ConfigurationModel.get_versions(env_id, 0, 1)
    assert(len(versions) == 1)
    assert(versions[0].version == 19)

    versions = yield ConfigurationModel.get_versions(env_id, 1, 1)
    assert(len(versions) == 1)
    assert(versions[0].version == 18)

    versions = yield ConfigurationModel.get_versions(env_id)
    assert(len(versions) == 19)
    assert(versions[0].version == 19)
    assert(versions[-1].version == 1)

    versions = yield ConfigurationModel.get_versions(env_id, 10)
    assert(len(versions) == 9)
    assert(versions[0].version == 9)
    assert(versions[-1].version == 1)


@pytest.mark.gen_test
def test_resource_purge_on_delete(data_module):
    env_id = uuid.uuid4()

    # model 1
    cm1 = data.ConfigurationModel(environment=env_id, version=1, date=datetime.datetime.now(), total=2, version_info={},
                                  released=True, deployed=True)
    yield cm1.insert()

    res11 = data.Resource.new(environment=env_id, resource_version_id="std::File[agent1,path=/etc/motd],v=1", status="deployed",
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    yield res11.insert()

    res12 = data.Resource.new(environment=env_id, resource_version_id="std::File[agent2,path=/etc/motd],v=1", status="deployed",
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True})
    yield res12.insert()

    # model 2
    cm2 = data.ConfigurationModel(environment=env_id, version=2, date=datetime.datetime.now(), total=1, version_info={},
                                  released=False, deployed=False)
    yield cm2.insert()

    res21 = data.Resource.new(environment=env_id, resource_version_id="std::File[agent5,path=/etc/motd],v=2",
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    yield res21.insert()

    # model 3
    cm3 = data.ConfigurationModel(environment=env_id, version=3, date=datetime.datetime.now(), total=0, version_info={})
    yield cm3.insert()

    to_purge = yield data.Resource.get_deleted_resources(env_id, 3)

    assert(len(to_purge) == 1)
    assert(to_purge[0].model == 1)
    assert(to_purge[0].resource_id == "std::File[agent1,path=/etc/motd]")


@pytest.mark.gen_test
def test_get_latest_resource(data_module):
    env_id = uuid.uuid4()
    key = "std::File[agent1,path=/etc/motd]"
    res11 = data.Resource.new(environment=env_id, resource_version_id=key + ",v=1", status="deployed",
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": False})
    yield res11.insert()

    res12 = data.Resource.new(environment=env_id, resource_version_id=key + ",v=2", status="deployed",
                              attributes={"path": "/etc/motd", "purge_on_delete": True, "purged": True})
    yield res12.insert()

    res = yield data.Resource.get_latest_version(env_id, key)
    assert(res.model == 2)


@pytest.mark.gen_test
def test_snapshot(data_module):
    env_id = uuid.uuid4()

    snap = data.Snapshot(environment=env_id, model=1, name="a", started=datetime.datetime.now(), resources_todo=1)
    yield snap.insert()

    s = yield data.Snapshot.get_by_id(snap.id)
    yield s.resource_updated(10)
    assert(s.resources_todo == 0)
    assert(s.total_size == 10)
    assert(s.finished is not None)

    s = yield data.Snapshot.get_by_id(snap.id)
    assert(s.resources_todo == 0)
    assert(s.total_size == 10)
    assert(s.finished is not None)

    yield s.delete_cascade()
    result = yield data.Snapshot.get_list()
    assert(len(result) == 0)
