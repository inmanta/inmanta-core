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

import asyncio
import hashlib
import json
import typing
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Mapping, Optional, Sequence

import pytest

import inmanta.types
from agent_server.deploy.scheduler_test_util import DummyCodeManager, make_requires
from inmanta import const, util
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.executor import ResourceDetails, ResourceInstallSpec
from inmanta.config import Config
from inmanta.data import ResourceIdStr
from inmanta.deploy import state, tasks, work
from inmanta.protocol.common import custom_json_encoder

FAIL_DEPLOY: str = "fail_deploy"

async def retry_limited_fast(
    fun: Callable[[], bool],
    timeout: float = 0.1,
    interval: float = 0.005,
) -> None:
    """
    Override defaults for the retry_limited function.

    This test case has many invocations of it, where very fast resolution is expected, so we increase test
    performance by polling frequently and setting a low timeout.
    """
    await util.retry_limited(fun, timeout=timeout, interval=interval)


class DummyExecutor(executor.Executor):

    def __init__(self):
        self.execute_count = 0
        self.dry_run_count = 0
        self.facts_count = 0
        self.failed_resources = {}
        self.mock_versions = {}

    def reset_counters(self) -> None:
        self.execute_count = 0
        self.dry_run_count = 0
        self.facts_count = 0

    async def execute(self, gid: uuid.UUID, resource_details: ResourceDetails, reason: str) -> const.ResourceState:
        self.execute_count += 1
        return (
            const.ResourceState.failed
            if resource_details.attributes.get(FAIL_DEPLOY, False) is True
            else const.ResourceState.deployed
        )

    async def dry_run(self, resources: Sequence[ResourceDetails], dry_run_id: uuid.UUID) -> None:
        self.dry_run_count += 1

    async def get_facts(self, resource: ResourceDetails) -> inmanta.types.Apireturn:
        self.facts_count += 1

    async def open_version(self, version: int) -> None:
        pass

    async def close_version(self, version: int) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def join(self) -> None:
        pass


class ManagedExecutor(DummyExecutor):
    """
    Dummy executor that can be driven explicitly by a test case.

    Executor behavior must be controlled through the `deploys` property. It exposes a mapping from resource ids
    to futures. Simply set the desired outcome as the result on the appropriate future.
    """

    def __init__(self) -> None:
        super().__init__()
        self._deploys: dict[ResourceIdStr, asyncio.Future[const.ResourceState]] = {}

    @property
    def deploys(self) -> Mapping[ResourceIdStr, asyncio.Future[const.ResourceState]]:
        return self._deploys

    async def stop(self) -> None:
        # resolve hanging futures to prevent test hanging during teardown
        for deploy in self._deploys.values():
            deploy.set_result(const.ResourceState.undefined)

    async def execute(self, gid: uuid.UUID, resource_details: ResourceDetails, reason: str) -> const.ResourceState:
        assert resource_details.rid not in self._deploys
        self._deploys[resource_details.rid] = asyncio.get_running_loop().create_future()
        # wait until the test case sets desired resource state
        result: const.ResourceState = await self._deploys[resource_details.rid]
        del self._deploys[resource_details.rid]
        self.execute_count += 1
        return result


class DummyManager(executor.ExecutorManager[executor.Executor]):

    def __init__(self):
        self.executors = {}
        self._managed_executors: list[ManagedExecutor] = []

    def register_managed_executor(self, agent_name: str, executor: ManagedExecutor) -> None:
        self.executors[agent_name] = executor
        self._managed_executors.append(executor)

    def reset_executor_counters(self) -> None:
        for ex in self.executors.values():
            ex.reset_counters()

    def register_managed_executor(self, agent_name: str, executor: ManagedExecutor) -> None:
        self.executors[agent_name] = executor

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
        for ex in self.executors.values():
            await ex.stop()

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
async def agent(environment, config):
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
    def make_resource_minimal(rid: str, values: dict[str, object], requires: list[str]) -> state.ResourceDetails:
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
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1]),
    }

    await agent.scheduler._new_version(5, resources, make_requires(resources))

    async def done():
        agent_1_queue = agent.scheduler._work.agent_queues._agent_queues.get("agent1")
        if not agent_1_queue:
            return False
        return agent_1_queue._unfinished_tasks == 0

    await retry_limited_fast(done)

    assert agent.executor_manager.executors["agent1"].execute_count == 2


async def test_deploy_scheduled_set(agent: TestAgent, make_resource_minimal) -> None:
    """
    Verify the behavior of various scheduler intricacies relating to which resources are added to the scheduled work,
    depending on resource status and in-progress or already scheduled deploys.
    """
    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent2,name=2]")
    rid3 = ResourceIdStr("test::Resource[agent3,name=3]")

    # make agent1 and agent2's executors managed, leave the agent3 to execute without delay
    executor1: ManagedExecutor = ManagedExecutor()
    executor2: ManagedExecutor = ManagedExecutor()
    agent.executor_manager.register_managed_executor("agent1", executor1)
    agent.executor_manager.register_managed_executor("agent2", executor2)

    def make_resources(
        *,
        version: int,
        r1_value: Optional[int],
        r2_value: Optional[int],
        r3_value: Optional[int],
        requires: Optional[Mapping[ResourceIdStr, Sequence[ResourceIdStr]]] = None,
        r3_fail: bool = False,
    ) -> dict[ResourceIdStr, state.ResourceDetails]:
        """
        Returns three resources with a single attribute, whose value is set by the value parameters. The fail parameters
        control whether the executor should fail or deploy successfully.

        Setting a resource value to None strips it from the model.

        Unless explicitly overridden, the resources depend on one another like r1 -> r2 -> r3 (r1 provides r2 etc) and events
        are disabled.
        """
        requires = requires if requires is not None else {
            rid2: [rid1] if r1_value is not None else [],
            rid3: [rid2] if r2_value is not None else [],
        }
        return {
            ResourceIdStr(rid): make_resource_minimal(
                rid, values={"value": value, FAIL_DEPLOY: fail}, requires=requires.get(rid, [])
            )
            for rid, value, fail
            in [
                (rid1, r1_value, False),
                (rid2, r2_value, False),
                (rid3, r3_value, r3_fail),
            ]
            if value is not None
        }

    # first deploy
    resources: Mapping[ResourceIdStr, state.ResourceDetails]
    resources = make_resources(version=1, r1_value=0, r2_value=0, r3_value=0)
    await agent.scheduler._new_version(1, resources, make_requires(resources))

    def done():
        for agent_name in ("agent1", "agent2", "agent3"):
            queue = agent.scheduler._work.agent_queues._agent_queues.get(agent_name)
            if not queue or queue._unfinished_tasks != 0:
                return False
        return True

    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)

    await retry_limited_fast(done)

    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 1
    assert rid2 not in executor2.deploys, f"deploy for {rid2} should have finished"

    ###################################################################
    # Verify deploy behavior when everything is in a known good state #
    ###################################################################
    agent.executor_manager.reset_executor_counters()
    await agent.scheduler.deploy()
    # nothing new has run or is scheduled
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ############################################################
    # Verify deploy behavior when a task is in known bad state #
    ############################################################
    agent.executor_manager.reset_executor_counters()
    # release a change to r2
    resources = make_resources(version=2, r1_value=0, r2_value=1, r3_value=0)
    await agent.scheduler._new_version(2, resources, make_requires(resources))
    # model handler failure
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.failed)
    # wait until r2 is done
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 1
    )

    # call deploy
    await agent.scheduler.deploy()
    # everything but r2 was in known good state => only r2 got another deploy
    await retry_limited_fast(lambda: rid2 in executor2.deploys)

    # finish up: set r2 result and wait until it's done
    executor2.deploys[rid2].set_result(const.ResourceState.failed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 2
    )
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ######################################################################################################
    # Verify deploy behavior when a task is in known bad state but a deploy is already scheduled/running #
    ######################################################################################################
    agent.executor_manager.reset_executor_counters()
    # call deploy again => schedules r2
    await agent.scheduler.deploy()
    # wait until r2 is running, then call deploy once more
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    await agent.scheduler.deploy()
    # verify that r2 did not get scheduled again, since it is already running for the same intent
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 1

    # same principle, this time through new_version instead of deploy -> release change to r3
    resources = make_resources(version=3, r1_value=0, r2_value=1, r3_value=1)
    await agent.scheduler._new_version(3, resources, make_requires(resources))
    # verify that only r3 was newly scheduled
    await retry_limited_fast(
        lambda: agent.scheduler._work._waiting.keys() == {rid3}
    )
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 1
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # redeploy again, but r3 is already scheduled
    await agent.scheduler.deploy()
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 1
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # release change for r2
    resources = make_resources(version=4, r1_value=0, r2_value=2, r3_value=1)
    await agent.scheduler._new_version(4, resources, make_requires(resources))
    # r2 got new intent => should be scheduled now even though it is already running
    await retry_limited_fast(
        lambda: len(agent.scheduler._work.agent_queues) == 1
    )
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 1
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid2)}  # one task scheduled
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}  # and one running

    # finish up
    # finish r2 deploy, failing it once more, twice
    executor2.deploys[rid2].set_result(const.ResourceState.failed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 1
    )
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.failed)
    assert agent.scheduler._work._waiting.keys() == {rid3}, f"{rid3} should still be waiting for {rid2}"
    # wait until r3 is done (executed after r2)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent3"].execute_count == 1
    )
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.executor_manager.executors["agent3"].execute_count == 1
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    #####################################################################
    # Verify repair behavior when a deploy is already scheduled/running #
    #####################################################################
    agent.executor_manager.reset_executor_counters()
    # release a change to r2 and r3, drop r2->r1 requires to simplify wait conditions
    resources = make_resources(version=5, r1_value=0, r2_value=3, r3_value=2, requires={rid3: [rid2]})
    await agent.scheduler._new_version(5, resources, make_requires(resources))
    # wait until r2 is running
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    # call repair, verify that only r1 is scheduled because r2 and r3 are running or scheduled respectively
    await agent.scheduler.repair()
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._work._waiting.keys() == {rid3}
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}
    # finish deploy
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent3"].execute_count == 1)

    ################################################
    # Verify deferring when requires are scheduled #
    ################################################
    agent.executor_manager.reset_executor_counters()
    # set up initial state
    resources = make_resources(version=6, r1_value=0, r2_value=3, r3_value=2)
    await agent.scheduler._new_version(6, resources, make_requires(resources))
    await retry_limited_fast(done)
    # force r2 in the queue by releasing two changes for it
    resources = make_resources(version=7, r1_value=0, r2_value=4, r3_value=2)
    await agent.scheduler._new_version(7, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    resources = make_resources(version=8, r1_value=0, r2_value=5, r3_value=2)
    await agent.scheduler._new_version(8, resources, make_requires(resources))
    # reset counters and assert expected start state
    agent.executor_manager.reset_executor_counters()
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid2)}
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # release a change to r1
    resources = make_resources(version=9, r1_value=1, r2_value=5, r3_value=2)
    await agent.scheduler._new_version(9, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # assert that queued r2 got moved out of the agent queues back to the waiting set
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid) for rid in (rid1, rid2)}

    # finish r1 and a single r2
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    assert len(agent.scheduler._work._waiting) == 0

    # release another change to r1
    resources = make_resources(version=10, r1_value=2, r2_value=5, r3_value=2)
    await agent.scheduler._new_version(10, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # assert that r2 got rescheduled because both it and its dependency have an update available while r2 is still running
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid) for rid in (rid1, rid2)}

    # finish all deploys
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 2)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 3)
    # verify total number of deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 3
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ################################################################
    # Verify scheduler behavior when requires are added or removed #
    ################################################################
    agent.executor_manager.reset_executor_counters()
    # set up initial state:
    # force r1 and r2 in the scheduled work and keep their respective agents occupied by releasing two changes for them
    # start with r2 only so its agent picks it up (no scheduled requires)
    resources = make_resources(version=11, r1_value=2, r2_value=6, r3_value=2)
    await agent.scheduler._new_version(11, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    # repeat for r1
    resources = make_resources(version=12, r1_value=3, r2_value=6, r3_value=2)
    await agent.scheduler._new_version(12, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # release one more change for both to force them in the scheduled work
    resources = make_resources(version=13, r1_value=4, r2_value=7, r3_value=2)
    await agent.scheduler._new_version(13, resources, make_requires(resources))
    # assert expected initial state
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid1)}
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid) for rid in (rid1, rid2)}

    # release new version: no changes to resources but drop requires
    resources = make_resources(version=14, r1_value=4, r2_value=7, r3_value=2, requires={})
    await agent.scheduler._new_version(14, resources, make_requires(resources))
    # assert that r2 is no longer blocked
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid) for rid in (rid1, rid2)}

    # release new version: no changes to resources but add requires in the other direction
    resources = make_resources(version=15, r1_value=4, r2_value=7, r3_value=2, requires={rid1: [rid2]})
    await agent.scheduler._new_version(15, resources, make_requires(resources))
    # assert that r1 has become blocked now
    assert agent.scheduler._work._waiting.keys() == {rid1}
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid2)}

    # advanced scenario: update resource + flip requires in one go
    resources = make_resources(version=16, r1_value=5, r2_value=8, r3_value=2)
    await agent.scheduler._new_version(16, resources, make_requires(resources))
    # assert that r2 has become blocked again
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid1)}

    # finish up: finish all waiting deploys
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 2)
    # verify total number of deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ##########################################################
    # Verify scheduler behavior when a stale deploy finishes #
    ##########################################################
    agent.executor_manager.reset_executor_counters()

    # assert pre resource state
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        status=state.ResourceStatus.UP_TO_DATE,
        deployment_result=state.DeploymentResult.DEPLOYED,
    )
    assert rid1 not in agent.scheduler._state.dirty
    # set up initial state: release two changes for r1 -> the second makes the first stale
    resources = make_resources(version=17, r1_value=6, r2_value=8, r3_value=2)
    await agent.scheduler._new_version(17, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # additionally release a change for r2 so that it blocks on r1 finishing
    resources = make_resources(version=18, r1_value=7, r2_value=9, r3_value=2)
    await agent.scheduler._new_version(18, resources, make_requires(resources))
    # assert resource state after releasing changes
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        status=state.ResourceStatus.HAS_UPDATE,
        deployment_result=state.DeploymentResult.DEPLOYED,
    )
    assert rid1 in agent.scheduler._state.dirty

    # finish stale deploy
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # verify that state remained the same
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        status=state.ResourceStatus.HAS_UPDATE,
        deployment_result=state.DeploymentResult.DEPLOYED,
    )
    assert rid1 in agent.scheduler._state.dirty
    # verify that r2 is still blocked on r1
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid1)}

    # finish all deploys
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    # assert final state and total deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        status=state.ResourceStatus.UP_TO_DATE,
        deployment_result=state.DeploymentResult.DEPLOYED,
    )
    assert rid1 not in agent.scheduler._state.dirty

    #######################################################################
    # Verify scheduler behavior when a resource is dropped from the model #
    #######################################################################
    agent.executor_manager.reset_executor_counters()

    # set up initial state: r1 running, second r1 queued, r2 blocked on r1, r3 blocked on r2
    resources = make_resources(version=19, r1_value=8, r2_value=9, r3_value=2)
    await agent.scheduler._new_version(19, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    resources = make_resources(version=20, r1_value=9, r2_value=10, r3_value=3)
    await agent.scheduler._new_version(20, resources, make_requires(resources))
    # assert initial state
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._work._waiting.keys() == {rid2, rid3}
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid1)}
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid1)}

    # release new model version without r1 or r2
    resources = make_resources(version=21, r1_value=None, r2_value=None, r3_value=3)
    await agent.scheduler._new_version(21, resources, make_requires(resources))
    # verify that running r1 is not affected but scheduled r1 and r2 are dropped (from queue and waiting respectively),
    # unblocking r3
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent3"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 1
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid1)}

    # finish last deploy
    executor1.deploys[rid1].set_result(const.ResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 1
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0


    # TODO: test for scheduler state -> deployment result, resource status, dirty, ...?


async def test_deploy_event_propagation(agent: TestAgent, make_resource_minimal):
    """
    Ensure that events are propagated when a deploy finishes
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent2,name=2]"
    rid3 = "test::Resource[agent3,name=3]"

    # make agent2's executor managed, leave the others to execute without delay
    executor2: ManagedExecutor = ManagedExecutor()
    agent.executor_manager.register_managed_executor("agent2", executor2)

    def make_resources(
        *,
        version: int,
        r1_value: Optional[int],
        r2_value: Optional[int],
        r3_value: Optional[int],
        requires: Optional[Mapping[ResourceIdStr, Sequence[ResourceIdStr]]] = None,
        r1_send_event: bool = True,
        r2_send_event: bool = False,
        r1_fail: bool = False,
    ) -> dict[ResourceIdStr, state.ResourceDetails]:
        """
        Returns three resources with a single attribute, whose value is set by the value parameters. The fail parameters
        control whether the executor should fail or deploy successfully.

        Setting a resource value to None strips it from the model.

        Unless explicitly overridden, the resources depend on one another like r1 -> r2 -> r3 (r1 provides r2 etc), but only r1
        sends events.
        """
        requires = requires if requires is not None else {
            rid2: [rid1] if r1_value is not None else [],
            rid3: [rid2] if r2_value is not None else [],
        }
        return {
            ResourceIdStr(rid): make_resource_minimal(
                rid, values={"value": value, "send_event": send_event, FAIL_DEPLOY: fail}, requires=requires.get(rid, [])
            )
            for rid, value, send_event, fail
            in [
                (rid1, r1_value, r1_send_event, r1_fail),
                (rid2, r2_value, r2_send_event, False),
                (rid3, r3_value, False, False),
            ]
            if value is not None
        }

    resources: Mapping[ResourceIdStr, state.ResourceDetails]
    resources = make_resources(version=5, r1_value=0, r2_value=0, r3_value=0)
    await agent.scheduler._new_version(5, resources, make_requires(resources))

    def done():
        agent_3_queue = agent.scheduler._work.agent_queues._agent_queues.get("agent3")
        if not agent_3_queue:
            return False
        return agent_3_queue._unfinished_tasks == 0

    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(done)

    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 1

    ##################################
    # Verify basic event propagation #
    ##################################
    agent.executor_manager.reset_executor_counters()
    # make a change to r2 only -> verify that only r2 gets redeployed because it has send_event=False
    resources = make_resources(version=6, r1_value=0, r2_value=1, r3_value=0)
    await agent.scheduler._new_version(6, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 1
    )
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0

    # make a change to r1 only -> verify that r2 gets deployed due to event propagation
    agent.executor_manager.reset_executor_counters()
    resources = make_resources(version=7, r1_value=1, r2_value=1, r3_value=0)
    await agent.scheduler._new_version(7, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 1
    )
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    # verify that r3 didn't get an event, i.e. it did not deploy and it is not scheduled or executing
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    #########################
    # Verify failure events #
    #########################
    agent.executor_manager.reset_executor_counters()
    # release change to r1, and make its deploy fail
    resources = make_resources(version=8, r1_value=2, r2_value=1, r3_value=0, r1_fail=True)
    await agent.scheduler._new_version(8, resources, make_requires(resources))
    # assert that r2 got deployed through event propagation
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 1
    )
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ################################################################
    # Verify event propagation when dependant is already deploying #
    ################################################################
    # this scenario is a rare race, but still important not to miss events
    agent.executor_manager.reset_executor_counters()

    # hang r2 in the running state by releasing an update for it
    resources = make_resources(version=9, r1_value=2, r2_value=2, r3_value=0)
    await agent.scheduler._new_version(9, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid2 in executor2.deploys)

    # reset counters and assert start state
    agent.executor_manager.reset_executor_counters()
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # trigger an event by releasing a change for r1
    resources = make_resources(version=10, r1_value=3, r2_value=2, r3_value=0)
    await agent.scheduler._new_version(10, resources, make_requires(resources))
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent1"].execute_count == 1
    )
    # assert that r2 was rescheduled due to the event, even though it is already deploying for its latest intent
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid2)}
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # verify that it suffices for r2 to be already scheduled (vs deploying above), i.e. it does not get scheduled twice
    # trigger an event by releasing a change for r1
    resources = make_resources(version=11, r1_value=4, r2_value=2, r3_value=0)
    await agent.scheduler._new_version(11, resources, make_requires(resources))
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent1"].execute_count == 2
    )
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid2)}
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # finish up: deploy r2 twice
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 1
    )
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.ResourceState.failed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 2
    )

    # verify total number of deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 2  # two changes
    assert agent.executor_manager.executors["agent2"].execute_count == 2  # two events
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ##############################################
    # Verify event propagation for stale deploys #
    ##############################################
    # Stale deploys are not expected to send out events.
    # Rationale:
    # - most event listeners (e.g. lsm) care only about events for the latest intent
    # - those that might care about stale events would be blocked on the new non-stale dependency anyway
    #   and will be notified by it
    agent.executor_manager.reset_executor_counters()
    # release a new version with an update to r2, where it sends events
    resources = make_resources(version=12, r1_value=4, r2_value=3, r3_value=0, r2_send_event=True)
    await agent.scheduler._new_version(12, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    # release another change to r2, making the currently running deploy stale
    resources = make_resources(version=13, r1_value=4, r2_value=4, r3_value=0, r2_send_event=True)
    await agent.scheduler._new_version(13, resources, make_requires(resources))

    # verify expected intermediate state
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.keys() == {tasks.Deploy(resource=rid2)}
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # finish stale r2 deploy and verify that it does not send out an event
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent2"].execute_count == 1
    )
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # finish up: deploy r2 and r3 (this time it does get an event from non-stale r2)
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(
        lambda: agent.executor_manager.executors["agent3"].execute_count == 1
    )

    # verify total number of deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 2  # two changes
    assert agent.executor_manager.executors["agent3"].execute_count == 1  # one non-stale event
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ##################################################
    # Verify event propagation for dropped resources #
    ##################################################
    # A special case of a stale deploy: the resource that finished deploying does not exist at all anymore in the new version
    # => should not produce events
    agent.executor_manager.reset_executor_counters()
    # release a new version with an update to r2, where it sends events
    resources = make_resources(version=13, r1_value=4, r2_value=5, r3_value=0, r2_send_event=True)
    await agent.scheduler._new_version(13, resources, make_requires(resources))
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    # drop r2, making the currently running deploy stale
    resources = make_resources(version=14, r1_value=4, r2_value=None, r3_value=0)
    await agent.scheduler._new_version(14, resources, make_requires(resources))

    # verify expected intermediate state
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert agent.scheduler._work.agent_queues._in_progress == {tasks.Deploy(resource=rid2)}

    # finish stale r2 deploy and verify that it doesn't send out an event
    executor2.deploys[rid2].set_result(const.ResourceState.deployed)
    await retry_limited_fast(
        lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0
    )
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0


    # TODO: test receive_events


async def test_removal(agent: TestAgent, make_resource_minimal):
    """
    Test that resources are removed from the state store correctly
    """
    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "other::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, {"value": "a"}, []),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1]),
    }

    await agent.scheduler._new_version(5, resources, make_requires(resources))

    assert len(agent.scheduler.get_types_for_agent("agent1")) == 2

    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, {"value": "a"}, []),
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
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1]),
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

    await retry_limited_fast(done)

    assert agent.executor_manager.executors["agent1"].dry_run_count == 2


async def test_get_facts(agent: TestAgent, make_resource_minimal):
    """
    Ensure the simples deploy scenario works: 2 dependant resources
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
        ResourceIdStr(rid2): make_resource_minimal(rid2, {"value": "a"}, [rid1]),
    }

    await agent.scheduler._new_version(5, resources, make_requires(resources))

    await agent.scheduler.get_facts({"id": rid1})

    async def done():
        agent_1_queue = agent.scheduler._work.agent_queues._agent_queues.get("agent1")
        if not agent_1_queue:
            return False
        return agent_1_queue._unfinished_tasks == 0

    await retry_limited_fast(done)

    assert agent.executor_manager.executors["agent1"].facts_count == 1
