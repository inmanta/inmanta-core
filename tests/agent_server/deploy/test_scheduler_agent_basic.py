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
"""

import hashlib
import json
import typing
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Sequence

import pytest

import inmanta.types
from agent_server.deploy.scheduler_test_util import DummyCodeManager, make_requires
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.executor import ExecutorBlueprint, ResourceDetails, ResourceInstallSpec
from inmanta.config import Config
from inmanta.data import ResourceIdStr
from inmanta.deploy import state
from inmanta.protocol.common import custom_json_encoder
from inmanta.util import retry_limited


class DummyExecutor(executor.Executor):

    def __init__(self):
        self.execute_count = 0
        self.failed_resources = []

    async def execute(self, gid: uuid.UUID, resource_details: ResourceDetails, reason: str) -> None:
        self.execute_count += 1

    async def dry_run(self, resources: Sequence[ResourceDetails], dry_run_id: uuid.UUID) -> None:
        pass

    async def get_facts(self, resource: ResourceDetails) -> inmanta.types.Apireturn:
        pass

    async def open_version(self, version: int) -> None:
        pass

    async def close_version(self, version: int) -> None:
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


class TestAgent(Agent):

    def __init__(
        self,
        environment: Optional[uuid.UUID] = None,
    ):
        self.manager = DummyManager()
        super().__init__(environment)
        self.scheduler._code_manager = DummyCodeManager(self._client)

    def create_executor_manager(self) -> executor.ExecutorManager[executor.Executor]:
        return self.manager


@pytest.fixture
def environment() -> uuid.UUID:
    return "83d604a0-691a-11ef-ae04-c8f750463317"


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
    out = TestAgent(environment)
    await out.start_working()
    yield out
    await out.stop_working()


@pytest.fixture
def make_resource_minimal(environment):
    def make_resource_minimal(rid: str, values: dict[str, object], requires: list[str], version: int) -> state.ResourceDetails:
        attributes = dict(values)
        attributes["requires"] = requires
        out = dict(attributes=attributes, id=rid + f",v={version}", environment=environment, model=version)

        character = json.dumps(
            {k: v for k, v in attributes.items() if k not in ["requires", "provides", "version"]},
            default=custom_json_encoder,
            sort_keys=True,  # sort the keys for stable hashes when using dicts, see #5306
        )
        m = hashlib.md5()
        m.update(rid.encode("utf-8"))
        m.update(character.encode("utf-8"))
        attribute_hash = m.hexdigest()

        return state.ResourceDetails(out, attribute_hash)

    return make_resource_minimal


async def test_fixtures(agent: TestAgent, make_resource_minimal):
    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, {"value": "a"}, [], 5),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1], 5),
    }

    # FIXME: SANDER: It seems we immediatly deploy if a new version arrives, we don't wait for an explicit deploy call?
    # Is this by design?
    await agent.scheduler.new_version(5, resources, make_requires(resources))

    # assert len(agent.scheduler._work.agent_queues._agent_queues) == 1
    # agent_1_queue = agent.scheduler._work.agent_queues._agent_queues["agent1"]
    # assert agent_1_queue._unfinished_tasks == 1
    #
    # await agent.scheduler._work_once("agent1")
    #
    # assert agent_1_queue._unfinished_tasks == 1
    #
    # await agent.scheduler._work_once("agent1")
    #
    # assert agent_1_queue._unfinished_tasks == 0

    async def done():
        agent_1_queue = agent.scheduler._work.agent_queues._agent_queues.get("agent1")
        if not agent_1_queue:
            return False
        return agent_1_queue._unfinished_tasks == 0

    await retry_limited(done, 5)

    assert agent.executor_manager.executors["agent1"].execute_count == 2


async def test_removal(agent: TestAgent, make_resource_minimal):
    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "other::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, {"value": "a"}, [], 5),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1], 5),
    }

    await agent.scheduler.new_version(5, resources, make_requires(resources))

    assert len(agent.scheduler._state.get_types_for_agent("agent1")) == 2

    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, {"value": "a"}, [], 6),
    }

    await agent.scheduler.new_version(6, resources, make_requires(resources))

    assert len(agent.scheduler._state.get_types_for_agent("agent1")) == 1
    assert len(agent.scheduler._state.resources) == 1


# TODO: test failed resource with server
