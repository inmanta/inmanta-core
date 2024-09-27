"""
    Copyright 2024 Inmanta

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

    This file is intended to contain test that use the agent/scheduler combination in isolation: no server, no executor
"""

import hashlib
import json
import typing
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Mapping, Optional, Sequence

import pytest

import inmanta.types
from agent_server.deploy.scheduler_test_util import DummyCodeManager, make_requires
from inmanta import const
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.executor import ResourceDetails, ResourceInstallSpec
from inmanta.config import Config
from inmanta.data import ResourceIdStr
from inmanta.deploy import state
from inmanta.deploy.work import TaskPriority
from inmanta.protocol.common import custom_json_encoder
from inmanta.util import retry_limited


class DummyExecutor(executor.Executor):

    def __init__(self):
        self.execute_count = 0
        self.dry_run_count = 0
        self.facts_count = 0
        self.failed_resources = {}
        self.mock_versions = {}

    async def execute(self, gid: uuid.UUID, resource_details: ResourceDetails, reason: str) -> const.ResourceState:
        self.execute_count += 1
        return const.ResourceState.deployed

    async def dry_run(self, resources: Sequence[ResourceDetails], dry_run_id: uuid.UUID) -> None:
        self.dry_run_count += 1

    async def get_facts(self, resource: ResourceDetails) -> inmanta.types.Apireturn:
        self.facts_count += 1

    async def open_version(self, version: int) -> None:
        pass

    async def close_version(self, version: int) -> None:
        pass

    async def join(self) -> None:
        pass


class DummyManager(executor.ExecutorManager[executor.Executor]):

    def __init__(self):
        self.executors = {}

    async def get_executor(
        self, agent_name: str, agent_uri: str, code: typing.Collection[ResourceInstallSpec]
    ) -> DummyExecutor:
        if agent_name not in self.executors:
            self.executors[agent_name] = DummyExecutor()
        return self.executors[agent_name]

    async def stop_for_agent(self, agent_name: str) -> list[DummyExecutor]:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor], timeout: float) -> None:
        pass


async def pass_method():
    pass


class TestAgent(Agent):

    def __init__(
        self,
        environment: Optional[uuid.UUID] = None,
    ):
        super().__init__(environment)
        self.executor_manager = DummyManager()
        self.scheduler.executor_manager = self.executor_manager
        self.scheduler.code_manager = DummyCodeManager(self._client)
        # Bypass DB
        self.scheduler.read_version = pass_method
        self.scheduler.mock_versions = {}

        async def build_resource_mappings_from_db(version: int | None) -> Mapping[ResourceIdStr, ResourceDetails]:
            return self.scheduler.mock_versions[version]

        self.scheduler._build_resource_mappings_from_db = build_resource_mappings_from_db


@pytest.fixture
def environment() -> uuid.UUID:
    return uuid.UUID("83d604a0-691a-11ef-ae04-c8f750463317")


@pytest.fixture
async def config(inmanta_config, tmp_path):
    Config.set("config", "state-dir", str(tmp_path))
    Config.set("config", "log-dir", str(tmp_path / "logs"))
    Config.set("server", "agent-timeout", "2")
    Config.set("agent", "agent-repair-interval", "0")
    Config.set("agent", "executor-mode", "forking")
    Config.set("agent", "executor-venv-retention-time", "60")
    Config.set("agent", "executor-retention-time", "10")


@pytest.fixture
async def agent(environment, config, event_loop):
    """
    Provide a new agent, with a scheduler that uses the dummy executor

    Allows testing without server, or executor
    """
    out = TestAgent(environment)
    await out.start_working()
    yield out
    await out.stop_working()


@pytest.fixture
def make_resource_minimal(environment):
    def make_resource_minimal(rid: str, values: dict[str, object], requires: list[str], version: int) -> state.ResourceDetails:
        """Produce a resource that is valid to the scheduler"""
        attributes = dict(values)
        attributes["requires"] = requires
        character = json.dumps(
            {k: v for k, v in attributes.items() if k not in ["requires", "provides", "version"]},
            default=custom_json_encoder,
            sort_keys=True,  # sort the keys for stable hashes when using dicts, see #5306
        )
        m = hashlib.md5()
        m.update(rid.encode("utf-8"))
        m.update(character.encode("utf-8"))
        attribute_hash = m.hexdigest()

        return state.ResourceDetails(resource_id=rid, attributes=attributes, attribute_hash=attribute_hash)

    return make_resource_minimal


async def test_basic_deploy(agent: TestAgent, make_resource_minimal):
    """
    Ensure the simples deploy scenario works: 2 dependant resources
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[], version=5),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1], 5),
    }

    await agent.scheduler._new_version(5, resources, make_requires(resources))

    async def done():
        agent_1_queue = agent.scheduler._work.agent_queues._agent_queues.get("agent1")
        if not agent_1_queue:
            return False
        return agent_1_queue._unfinished_tasks == 0

    await retry_limited(done, 5)

    assert agent.executor_manager.executors["agent1"].execute_count == 2


async def test_removal(agent: TestAgent, make_resource_minimal):
    """
    Test that resources are removed from the state store correctly
    """
    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "other::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, {"value": "a"}, [], 5),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1], 5),
    }

    await agent.scheduler._new_version(5, resources, make_requires(resources))

    assert len(agent.scheduler.get_types_for_agent("agent1")) == 2

    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, {"value": "a"}, [], 6),
    }

    await agent.scheduler._new_version(6, resources, make_requires(resources))

    assert len(agent.scheduler.get_types_for_agent("agent1")) == 1
    assert len(agent.scheduler._state.resources) == 1


async def test_dryrun(agent: TestAgent, make_resource_minimal, monkeypatch):
    """
    Ensure the simples deploy scenario works: 2 dependant resources
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[], version=5),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1], 5),
    }

    agent.scheduler.mock_versions[5] = resources

    dryrun = uuid.uuid4()
    await agent.scheduler.dryrun(dryrun, 5)

    async def done():
        agent_1_queue = agent.scheduler._work.agent_queues._agent_queues.get("agent1")
        if not agent_1_queue:
            return False
        print(agent_1_queue._unfinished_tasks)
        return agent_1_queue._unfinished_tasks == 0

    await retry_limited(done, 5)

    assert agent.executor_manager.executors["agent1"].dry_run_count == 2


async def test_get_facts(agent: TestAgent, make_resource_minimal):
    """
    Ensure the simples deploy scenario works: 2 dependant resources
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[], version=5),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1], 5),
    }

    await agent.scheduler._new_version(5, resources, make_requires(resources))

    await agent.scheduler.get_facts({"id": rid1})

    async def done():
        agent_1_queue = agent.scheduler._work.agent_queues._agent_queues.get("agent1")
        if not agent_1_queue:
            return False
        return agent_1_queue._unfinished_tasks == 0

    await retry_limited(done, 5)

    assert agent.executor_manager.executors["agent1"].facts_count == 1


async def test_scheduler_priority(agent: TestAgent, environment, make_resource_minimal):
    """
    Ensure that the tasks are placed in the queue in the correct order
    """

    await agent.stop()

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[], version=5),
    }

    agent.scheduler.mock_versions[5] = resources

    await agent.scheduler.get_facts({"id": rid1})

    await agent.scheduler._new_version(5, resources, make_requires(resources))

    await agent.scheduler.deploy(TaskPriority.INTERVAL_DEPLOY)

    dryrun = uuid.uuid4()
    await agent.scheduler.dryrun(dryrun, 5)

    await agent.trigger_update(environment, "$__scheduler", incremental_deploy=False)
    await agent.trigger_update(environment, "$__scheduler", incremental_deploy=True)

    await agent.scheduler.repair(TaskPriority.INTERVAL_REPAIR)

    agent_1_queue = agent.scheduler._work.agent_queues.sorted("agent1")
    assert len(agent_1_queue) == 7

    await agent.start_working()
