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

from inmanta import data
from inmanta.data import AgentInstance, Agent
import pytest


@pytest.mark.usefixtures("motorengine")
class TestProjectTestCase:

    @pytest.mark.gen_test
    def testProject(self):
        project = data.Project(name="test", uuid=uuid.uuid4())
        project = yield project.save()

        projects = yield data.Project.objects.filter(name="test").find_all()  # @UndefinedVariable
        assert len(projects) == 1
        assert projects[0].uuid == project.uuid

        other = yield data.Project.get_uuid(project.uuid)
        assert project != other
        assert project.uuid == other.uuid

    @pytest.mark.gen_test
    def testEnvironment(self):
        project = data.Project(name="test", uuid=uuid.uuid4())
        project = yield project.save()

        env = yield data.Environment.objects.create(uuid=uuid.uuid4(),  # @UndefinedVariable
                                                    name="dev", project_id=project.uuid, repo_url="", repo_branch="")
        assert env.project_id == project.uuid

        yield project.delete_cascade()

        f1 = data.Project.objects.find_all()  # @UndefinedVariable
        f2 = data.Environment.objects.find_all()  # @UndefinedVariable
        projects, envs = yield [f1, f2]
        assert len(projects) == 0
        assert len(envs) == 0

    @pytest.mark.gen_test
    def testAgentProcess(self):
        project = data.Project(name="test", uuid=uuid.uuid4())
        project = yield project.save()

        env = yield data.Environment.objects.create(uuid=uuid.uuid4(),  # @UndefinedVariable
                                                    name="dev", project_id=project.uuid, repo_url="", repo_branch="")
        env = yield env.save()

        agentProc = data.AgentProcess(uuid=uuid.uuid4(),
                                      hostname="testhost",
                                      environment_id=env.uuid,
                                      first_seen=datetime.datetime.now(),
                                      last_seen=datetime.datetime.now(),
                                      sid=uuid.uuid4())
        agentProc = yield agentProc.save()

        agi1 = AgentInstance(uuid=uuid.uuid4(), process=agentProc, name="agi1", tid=env.uuid)
        agi1 = yield agi1.save()
        agi2 = AgentInstance(uuid=uuid.uuid4(), process=agentProc, name="agi2", tid=env.uuid)
        agi2 = yield agi2.save()

        agent = Agent(environment=env, name="agi1", last_failover=datetime.datetime.now(), paused=False, primary=agi1)
        agent = yield agent.save()

        agents = yield Agent.objects.find_all()
        assert len(agents) == 1
        agent = agents[0]
        yield agent.load_references()
        yield agent.primary.load_references()
        assert agent.primary.process.uuid == agentProc.uuid
