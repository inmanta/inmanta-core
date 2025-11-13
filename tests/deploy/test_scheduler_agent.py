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
import datetime
import hashlib
import itertools
import json
import logging
import typing
import uuid
from collections.abc import Awaitable, Callable, Collection, Set
from concurrent.futures import ThreadPoolExecutor
from typing import Mapping, Optional, Sequence

import pytest

import utils
from deploy.scheduler_mocks import FAIL_DEPLOY, DummyExecutor, ManagedExecutor, TestAgent, TestScheduler
from inmanta import const, data, util
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.executor import ModuleInstallSpec, ResourceDetails
from inmanta.config import Config
from inmanta.deploy import state, tasks
from inmanta.deploy.scheduler import ModelVersion, ResourceScheduler
from inmanta.deploy.state import Blocked, Compliance, DeployResult
from inmanta.deploy.work import ScheduledWork, TaskPriority
from inmanta.protocol.common import custom_json_encoder
from inmanta.resources import Id
from inmanta.types import ResourceIdStr
from inmanta.util import retry_limited
from utils import make_requires


def model_version(
    version: int,
    *,
    resources: Mapping[ResourceIdStr, state.ResourceIntent],
    requires: Optional[Mapping[ResourceIdStr, Set[ResourceIdStr]]] = None,
    resource_sets: Optional[Mapping[Optional[str], Set[ResourceIdStr]]] = None,
    undefined: Optional[Set[ResourceIdStr]] = None,
    partial: bool = False,
) -> ModelVersion:
    return ModelVersion(
        version=version,
        resources=resources,
        resource_sets=resource_sets if resource_sets is not None else {None: set(resources.keys())},
        requires=requires if requires is not None else make_requires(resources),
        undefined=undefined if undefined is not None else set(),
        partial=partial,
    )


async def retry_limited_fast(
    fun: Callable[..., bool] | Callable[..., Awaitable[bool]],
    timeout: float = 0.1,
    interval: float = 0.005,
    *args: object,
    **kwargs: object,
) -> None:
    """
    Override defaults for the retry_limited function.

    The tests in this module have many invocations of it, where very fast resolution is expected, so we increase test
    performance by polling frequently and setting a low timeout.
    """
    await util.retry_limited(fun, timeout=timeout, interval=interval, *args, **kwargs)


async def wait_until_done(agent: TestAgent) -> None:
    await retry_limited_fast(
        lambda: (
            len(agent.scheduler._work._waiting) == 0
            and len(agent.scheduler._work.agent_queues.queued()) == 0
            and all(queue._unfinished_tasks == 0 for queue in agent.scheduler._work.agent_queues._agent_queues.values())
        )
    )


def state_manager_check(agent: "TestAgent"):
    agent.scheduler.state_update_manager.check_with_scheduler(agent.scheduler)


async def pass_method():
    """
    A dummy method that does nothing at all.
    """
    pass


@pytest.fixture
def environment() -> uuid.UUID:
    return uuid.UUID("83d604a0-691a-11ef-ae04-c8f750463317")


@pytest.fixture
async def config(inmanta_config, tmp_path):
    Config.set("config", "state-dir", str(tmp_path))
    Config.set("config", "log-dir", str(tmp_path / "logs"))
    Config.set("server", "agent-timeout", "2")
    Config.set("agent", "agent-repair-interval", "0")
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
    def make_resource_minimal(
        rid: ResourceIdStr,
        values: dict[str, object],
        requires: list[str],
    ) -> state.ResourceIntent:
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

        return state.ResourceIntent(resource_id=rid, attributes=attributes, attribute_hash=attribute_hash)

    return make_resource_minimal


def get_resources_for_agent(scheduler: ResourceScheduler, agent: str) -> Collection[ResourceIdStr]:
    return list(scheduler._state.resources_by_agent[agent])


async def test_basic_deploy(agent: TestAgent, make_resource_minimal):
    """
    Ensure the simples deploy scenario works: 2 dependant resources
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
        ResourceIdStr(rid2): make_resource_minimal(rid2, values={"value": "a"}, requires=[rid1]),
    }

    await agent.scheduler._new_version([model_version(version=1, resources=resources)])
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")

    assert agent.executor_manager.executors["agent1"].execute_count == 2


async def test_shutdown(agent: TestAgent, make_resource_minimal):
    """
    Ensure the simples deploy scenario works: 2 dependant resources
    """

    # basic tests once more

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
        ResourceIdStr(rid2): make_resource_minimal(rid2, values={"value": "a"}, requires=[rid1]),
    }

    await agent.scheduler._new_version([model_version(version=1, resources=resources)])
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")
    assert agent.executor_manager.executors["agent1"].execute_count == 2

    # Ensure proper shutdown

    # We are running
    assert len(agent.scheduler._workers) == 1
    assert agent.scheduler._workers["agent1"].is_running()

    # Make the agent active!
    await agent.scheduler.repair(reason="Test")

    # Shutdown
    await agent.scheduler.stop()
    assert len(agent.scheduler._workers) == 1
    assert not agent.scheduler._workers["agent1"].is_running()
    # This one can be used to validate the test case, but it is a race
    # So it is commented as it will cause flakes
    # assert not agent.scheduler._workers["agent1"]._task.done()

    # Join
    await agent.scheduler.join()
    assert not agent.scheduler._workers["agent1"].is_running()
    assert agent.scheduler._workers["agent1"]._task.done()

    # Reset
    await agent.scheduler._reset()
    assert len(agent.scheduler._workers) == 0


async def test_deploy_scheduled_set(agent: TestAgent, make_resource_minimal) -> None:
    """
    Verify the behavior of various scheduler intricacies relating to which resources are added to the scheduled work,
    depending on resource status and in-progress or already scheduled deploys.
    """
    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent2,name=2]")
    rid3 = ResourceIdStr("test::Resource[agent3,name=3]")

    # make agent1 and agent2's executors managed, leave the agent3 to execute without delay
    executor1: ManagedExecutor = agent.executor_manager.register_managed_executor("agent1")
    executor2: ManagedExecutor = agent.executor_manager.register_managed_executor("agent2")

    def make_resources(
        *,
        version: int,
        r1_value: Optional[int],
        r2_value: Optional[int],
        r3_value: Optional[int],
        requires: Optional[Mapping[ResourceIdStr, Sequence[ResourceIdStr]]] = None,
        r3_fail: bool = False,
    ) -> dict[ResourceIdStr, state.ResourceIntent]:
        """
        Returns three resources with a single attribute, whose value is set by the value parameters. The fail parameters
        control whether the executor should fail or deploy successfully.

        Setting a resource value to None strips it from the model.

        Unless explicitly overridden, the resources depend on one another like r1 -> r2 -> r3 (r1 provides r2 etc) and events
        are disabled.
        """
        requires = (
            requires
            if requires is not None
            else {
                rid2: [rid1] if r1_value is not None else [],
                rid3: [rid2] if r2_value is not None else [],
            }
        )
        return {
            ResourceIdStr(rid): make_resource_minimal(
                rid, values={"value": value, FAIL_DEPLOY: fail}, requires=requires.get(rid, [])
            )
            for rid, value, fail in [
                (rid1, r1_value, False),
                (rid2, r2_value, False),
                (rid3, r3_value, r3_fail),
            ]
            if value is not None
        }

    # first deploy
    resources: Mapping[ResourceIdStr, state.ResourceIntent]
    resources = make_resources(version=1, r1_value=0, r2_value=0, r3_value=0)
    await agent.scheduler._new_version([model_version(version=1, resources=resources)])

    def done():
        for agent_name in ("agent1", "agent2", "agent3"):
            queue = agent.scheduler._work.agent_queues._agent_queues.get(agent_name)
            if not queue or queue._unfinished_tasks != 0:
                return False
        return True

    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)

    await retry_limited_fast(done)

    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 1
    assert rid2 not in executor2.deploys, f"deploy for {rid2} should have finished"

    state_manager_check(agent)

    ###################################################################
    # Verify deploy behavior when everything is in a known good state #
    ###################################################################
    agent.executor_manager.reset_executor_counters()
    await agent.scheduler.deploy(reason="Test")
    # nothing new has run or is scheduled
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0
    state_manager_check(agent)

    ############################################################
    # Verify deploy behavior when a task is in known bad state #
    ############################################################
    agent.executor_manager.reset_executor_counters()
    # release a change to r2
    resources = make_resources(version=2, r1_value=0, r2_value=1, r3_value=0)
    await agent.scheduler._new_version([model_version(version=2, resources=resources)])
    # model handler failure
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.failed)
    # wait until r2 is done
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)

    # call deploy
    await agent.scheduler.deploy(reason="Test")
    # everything but r2 was in known good state => only r2 got another deploy
    await retry_limited_fast(lambda: rid2 in executor2.deploys)

    # finish up: set r2 result and wait until it's done
    executor2.deploys[rid2].set_result(const.HandlerResourceState.failed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 2)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0
    state_manager_check(agent)

    ######################################################################################################
    # Verify deploy behavior when a task is in known bad state but a deploy is already scheduled/running #
    ######################################################################################################
    agent.executor_manager.reset_executor_counters()
    # call deploy again => schedules r2
    await agent.scheduler.deploy(reason="Test")
    # wait until r2 is running, then call deploy once more
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    await agent.scheduler.deploy(reason="Test")
    # verify that r2 did not get scheduled again, since it is already running for the same intent
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 1

    # same principle, this time through new_version instead of deploy -> release change to r3
    resources = make_resources(version=3, r1_value=0, r2_value=1, r3_value=1)
    await agent.scheduler._new_version([model_version(version=3, resources=resources)])
    # verify that only r3 was newly scheduled
    await retry_limited_fast(lambda: agent.scheduler._work._waiting.keys() == {rid3})
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 1
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]
    state_manager_check(agent)

    # redeploy again, but r3 is already scheduled
    await agent.scheduler.deploy(reason="Test")
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 1
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]
    state_manager_check(agent)

    # release change for r2
    resources = make_resources(version=4, r1_value=0, r2_value=2, r3_value=1)
    await agent.scheduler._new_version([model_version(version=4, resources=resources)])
    # r2 got new intent => should be scheduled now even though it is already running
    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues.queued()) == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 1
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid2)}  # one task scheduled
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]  # and one running
    state_manager_check(agent)

    # finish up
    # finish r2 deploy, failing it once more, twice
    executor2.deploys[rid2].set_result(const.HandlerResourceState.failed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.failed)
    assert agent.scheduler._work._waiting.keys() == {rid3}, f"{rid3} should still be waiting for {rid2}"
    # wait until r3 is done (executed after r2)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent3"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.executor_manager.executors["agent3"].execute_count == 1
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0
    state_manager_check(agent)

    #####################################################################
    # Verify repair behavior when a deploy is already scheduled/running #
    #####################################################################
    agent.executor_manager.reset_executor_counters()
    # release a change to r2 and r3, drop r2->r1 requires to simplify wait conditions
    resources = make_resources(version=5, r1_value=0, r2_value=3, r3_value=2, requires={rid3: [rid2]})
    await agent.scheduler._new_version([model_version(version=5, resources=resources)])
    # wait until r2 is running
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    assert agent.scheduler._work._waiting.keys() == {rid3}
    assert agent.scheduler._work._waiting[rid3].blocked_on == {rid2}
    # call repair, verify that only r1 is scheduled because r2 and r3 are running or scheduled respectively
    await agent.scheduler.repair(reason="Test")
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._work._waiting.keys() == {rid3}
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]
    # finish deploy
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent3"].execute_count == 1)
    state_manager_check(agent)

    ################################################
    # Verify deferring when requires are scheduled #
    ################################################
    agent.executor_manager.reset_executor_counters()
    # set up initial state
    resources = make_resources(version=6, r1_value=0, r2_value=3, r3_value=2)
    await agent.scheduler._new_version([model_version(version=6, resources=resources)])
    await retry_limited_fast(done)
    # force r2 in the queue by releasing two changes for it
    resources = make_resources(version=7, r1_value=0, r2_value=4, r3_value=2)
    await agent.scheduler._new_version([model_version(version=7, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    resources = make_resources(version=8, r1_value=0, r2_value=5, r3_value=2)
    await agent.scheduler._new_version([model_version(version=8, resources=resources)])
    # reset counters and assert expected start state
    agent.executor_manager.reset_executor_counters()
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid2)}
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]
    state_manager_check(agent)

    # release a change to r1
    resources = make_resources(version=9, r1_value=1, r2_value=5, r3_value=2)
    await agent.scheduler._new_version([model_version(version=9, resources=resources)])
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # assert that queued r2 got moved out of the agent queues back to the waiting set
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert tasks.Deploy(resource=rid1) in agent.scheduler._work.agent_queues._in_progress

    # finish r1 and a single r2
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    assert len(agent.scheduler._work._waiting) == 0

    # release another change to r1
    resources = make_resources(version=10, r1_value=2, r2_value=5, r3_value=2)
    await agent.scheduler._new_version([model_version(version=10, resources=resources)])
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # assert that r2 got rescheduled because both it and its dependency have an update available while r2 is still running
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert tasks.Deploy(resource=rid1) in agent.scheduler._work.agent_queues._in_progress
    assert tasks.Deploy(resource=rid2) in agent.scheduler._work.agent_queues._in_progress

    # finish all deploys
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 2)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 3)
    # verify total number of deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 3
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0
    state_manager_check(agent)

    ################################################################
    # Verify scheduler behavior when requires are added or removed #
    ################################################################
    agent.executor_manager.reset_executor_counters()
    # set up initial state:
    # force r1 and r2 in the scheduled work and keep their respective agents occupied by releasing two changes for them
    # start with r2 only so its agent picks it up (no scheduled requires)
    resources = make_resources(version=11, r1_value=2, r2_value=6, r3_value=2)
    await agent.scheduler._new_version([model_version(version=11, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    # repeat for r1
    resources = make_resources(version=12, r1_value=3, r2_value=6, r3_value=2)
    await agent.scheduler._new_version([model_version(version=12, resources=resources)])
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # release one more change for both to force them in the scheduled work
    resources = make_resources(version=13, r1_value=4, r2_value=7, r3_value=2)
    await agent.scheduler._new_version([model_version(version=13, resources=resources)])
    # assert expected initial state
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid1)}
    assert tasks.Deploy(resource=rid1) in agent.scheduler._work.agent_queues._in_progress
    assert tasks.Deploy(resource=rid2) in agent.scheduler._work.agent_queues._in_progress

    # release new version: no changes to resources but drop requires
    resources = make_resources(version=14, r1_value=4, r2_value=7, r3_value=2, requires={})
    await agent.scheduler._new_version([model_version(version=14, resources=resources)])
    # assert that r2 is no longer blocked
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid) for rid in (rid1, rid2)}

    # release new version: no changes to resources but add requires in the other direction
    resources = make_resources(version=15, r1_value=4, r2_value=7, r3_value=2, requires={rid1: [rid2]})
    await agent.scheduler._new_version([model_version(version=15, resources=resources)])
    # assert that r1 has become blocked now
    assert agent.scheduler._work._waiting.keys() == {rid1}
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid2)}

    # advanced scenario: update resource + flip requires in one go
    resources = make_resources(version=16, r1_value=5, r2_value=8, r3_value=2)
    await agent.scheduler._new_version([model_version(version=16, resources=resources)])
    # assert that r2 has become blocked again
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid1)}
    state_manager_check(agent)

    # finish up: finish all waiting deploys
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 2)
    # verify total number of deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0
    state_manager_check(agent)

    ##########################################################
    # Verify scheduler behavior when a stale deploy finishes #
    ##########################################################
    agent.executor_manager.reset_executor_counters()

    # assert pre resource state
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        compliance=state.Compliance.COMPLIANT,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid1].last_deployed,  # ignore
        last_deploy_compliant=True,
    )
    assert rid1 not in agent.scheduler._state.dirty
    # set up initial state: release two changes for r1 -> the second makes the first stale
    resources = make_resources(version=17, r1_value=6, r2_value=8, r3_value=2)
    await agent.scheduler._new_version([model_version(version=17, resources=resources)])
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # additionally release a change for r2 so that it blocks on r1 finishing
    resources = make_resources(version=18, r1_value=7, r2_value=9, r3_value=2)
    await agent.scheduler._new_version([model_version(version=18, resources=resources)])
    # assert resource state after releasing changes
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        compliance=state.Compliance.HAS_UPDATE,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid1].last_deployed,  # ignore
        last_deploy_compliant=True,
    )
    assert rid1 in agent.scheduler._state.dirty

    # finish stale deploy
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    # verify that state remained the same
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        compliance=state.Compliance.HAS_UPDATE,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid1].last_deployed,  # ignore
        last_deploy_compliant=True,
    )
    assert rid1 in agent.scheduler._state.dirty
    # verify that r2 is still blocked on r1
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._work._waiting.keys() == {rid2}
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid1)]

    # finish all deploys
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    # assert final state and total deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        compliance=state.Compliance.COMPLIANT,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid1].last_deployed,  # ignore
        last_deploy_compliant=True,
    )
    assert rid1 not in agent.scheduler._state.dirty
    state_manager_check(agent)

    #######################################################################
    # Verify scheduler behavior when a resource is dropped from the model #
    #######################################################################
    agent.executor_manager.reset_executor_counters()

    # set up initial state: r1 running, second r1 queued, r2 blocked on r1, r3 blocked on r2
    resources = make_resources(version=19, r1_value=8, r2_value=9, r3_value=2)
    await agent.scheduler._new_version([model_version(version=19, resources=resources)])
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    resources = make_resources(version=20, r1_value=9, r2_value=10, r3_value=3)
    await agent.scheduler._new_version([model_version(version=20, resources=resources)])
    # assert initial state
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._work._waiting.keys() == {rid2, rid3}
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid1)}
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid1)]

    # release new model version without r1 or r2
    resources = make_resources(version=21, r1_value=None, r2_value=None, r3_value=3)
    await agent.scheduler._new_version([model_version(version=21, resources=resources)])
    # verify that running r1 is not affected but scheduled r1 and r2 are dropped (from queue and waiting respectively),
    # unblocking r3
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent3"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 1
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid1)]

    # finish last deploy
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 1
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    for r, tbr in agent.scheduler._work.agent_queues._tasks_by_resource.items():
        assert not tbr


async def test_deploy_single_agent(agent: TestAgent, make_resource_minimal) -> None:
    """
    Verify the behavior of deploy and repair for a single agent.
    """
    r1_success = ResourceIdStr("test::Resource[agent1,name=1]")
    r1_fail = ResourceIdStr("test::Resource[agent1,name=2]")
    r2_success = ResourceIdStr("test::Resource[agent2,name=1]")
    r2_fail = ResourceIdStr("test::Resource[agent2,name=2]")

    resources: Mapping[ResourceIdStr, state.ResourceDetails] = {
        r1_success: make_resource_minimal(r1_success, values={FAIL_DEPLOY: False}, requires=[]),
        r1_fail: make_resource_minimal(r1_fail, values={FAIL_DEPLOY: True}, requires=[]),
        r2_success: make_resource_minimal(r2_success, values={FAIL_DEPLOY: False}, requires=[]),
        r2_fail: make_resource_minimal(r2_fail, values={FAIL_DEPLOY: True}, requires=[]),
    }
    version: int = 1
    await agent.scheduler._new_version([model_version(version=version, resources=resources, requires={})])

    await wait_until_done(agent)
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.scheduler._state.resource_state[r1_success].compliance is Compliance.COMPLIANT
    assert agent.scheduler._state.resource_state[r1_fail].compliance is Compliance.NON_COMPLIANT
    assert agent.scheduler._state.resource_state[r2_success].compliance is Compliance.COMPLIANT
    assert agent.scheduler._state.resource_state[r2_fail].compliance is Compliance.NON_COMPLIANT

    before_trigger: datetime.datetime

    # call deploy for all agents
    agent.executor_manager.reset_executor_counters()
    before_trigger = datetime.datetime.now().astimezone()
    await agent.scheduler.deploy(reason="Test deploy")
    await wait_until_done(agent)

    # only non-compliant should redeploy
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.scheduler._state.resource_state[r1_success].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r1_fail].last_deployed > before_trigger
    assert agent.scheduler._state.resource_state[r2_success].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r2_fail].last_deployed > before_trigger

    # call repair for all agents
    agent.executor_manager.reset_executor_counters()
    before_trigger = datetime.datetime.now().astimezone()
    await agent.scheduler.repair(reason="Test repair")
    await wait_until_done(agent)

    # everything should redeploy
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.scheduler._state.resource_state[r1_success].last_deployed > before_trigger
    assert agent.scheduler._state.resource_state[r1_fail].last_deployed > before_trigger
    assert agent.scheduler._state.resource_state[r2_success].last_deployed > before_trigger
    assert agent.scheduler._state.resource_state[r2_fail].last_deployed > before_trigger

    # call deploy for agent1
    agent.executor_manager.reset_executor_counters()
    before_trigger = datetime.datetime.now().astimezone()
    await agent.scheduler.deploy(agent="agent1", reason="Test deploy for agent1")
    await wait_until_done(agent)

    # only non-compliant on agent1 should redeploy
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.scheduler._state.resource_state[r1_success].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r1_fail].last_deployed > before_trigger
    assert agent.scheduler._state.resource_state[r2_success].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r2_fail].last_deployed < before_trigger

    # call deploy for agent2
    agent.executor_manager.reset_executor_counters()
    before_trigger = datetime.datetime.now().astimezone()
    await agent.scheduler.deploy(agent="agent2", reason="Test deploy for agent2")
    await wait_until_done(agent)

    # only non-compliant on agent2 should redeploy
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.scheduler._state.resource_state[r1_success].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r1_fail].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r2_success].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r2_fail].last_deployed > before_trigger

    # call repair for agent1
    agent.executor_manager.reset_executor_counters()
    before_trigger = datetime.datetime.now().astimezone()
    await agent.scheduler.repair(agent="agent1", reason="Test repair for agent1")
    await wait_until_done(agent)

    # all resources on agent1 should redeploy
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.scheduler._state.resource_state[r1_success].last_deployed > before_trigger
    assert agent.scheduler._state.resource_state[r1_fail].last_deployed > before_trigger
    assert agent.scheduler._state.resource_state[r2_success].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r2_fail].last_deployed < before_trigger

    # call repair for agent2
    agent.executor_manager.reset_executor_counters()
    before_trigger = datetime.datetime.now().astimezone()
    await agent.scheduler.repair(agent="agent2", reason="Test repair for agent2")
    await wait_until_done(agent)

    # all resources on agent2 should redeploy
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.scheduler._state.resource_state[r1_success].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r1_fail].last_deployed < before_trigger
    assert agent.scheduler._state.resource_state[r2_success].last_deployed > before_trigger
    assert agent.scheduler._state.resource_state[r2_fail].last_deployed > before_trigger


async def test_deploy_event_propagation(agent: TestAgent, make_resource_minimal):
    """
    Ensure that events are propagated when a deploy finishes
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent2,name=2]"
    rid3 = "test::Resource[agent3,name=3]"

    # make agent2's executor managed, leave the others to execute without delay
    executor2: ManagedExecutor = agent.executor_manager.register_managed_executor("agent2")

    def make_resources(
        *,
        r1_value: Optional[int],
        r2_value: Optional[int],
        r3_value: Optional[int],
        requires: Optional[Mapping[ResourceIdStr, Sequence[ResourceIdStr]]] = None,
        r1_send_event: bool = True,
        r2_send_event: bool = False,
        r1_fail: bool = False,
    ) -> dict[ResourceIdStr, state.ResourceIntent]:
        """
        Returns three resources with a single attribute, whose value is set by the value parameters.
        Setting a resource value to None strips it from the model.

        The r1_fail parameter controls whether the r1 resource should fail or deploy successfully.

        Unless explicitly overridden, the resources depend on one another like r1 -> r2 -> r3 (r1 provides r2 etc), but only r1
        sends events.
        """
        requires = (
            requires
            if requires is not None
            else {
                rid2: [rid1] if r1_value is not None else [],
                rid3: [rid2] if r2_value is not None else [],
            }
        )
        return {
            ResourceIdStr(rid): make_resource_minimal(
                rid,
                values={"value": value, const.RESOURCE_ATTRIBUTE_SEND_EVENTS: send_event, FAIL_DEPLOY: fail},
                requires=requires.get(rid, []),
            )
            for rid, value, send_event, fail in [
                (rid1, r1_value, r1_send_event, r1_fail),
                (rid2, r2_value, r2_send_event, False),
                (rid3, r3_value, False, False),
            ]
            if value is not None
        }

    resources: Mapping[ResourceIdStr, state.ResourceIntent]
    resources = make_resources(r1_value=0, r2_value=0, r3_value=0)
    await agent.scheduler._new_version([model_version(version=5, resources=resources)])

    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent3")

    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 1

    ##################################
    # Verify basic event propagation #
    ##################################
    agent.executor_manager.reset_executor_counters()
    # make a change to r2 only -> verify that only r2 gets redeployed because it has send_event=False
    resources = make_resources(r1_value=0, r2_value=1, r3_value=0)
    await agent.scheduler._new_version([model_version(version=6, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0

    # make a change to r1 only -> verify that r2 gets deployed due to event propagation
    agent.executor_manager.reset_executor_counters()
    resources = make_resources(r1_value=1, r2_value=1, r3_value=0)
    await agent.scheduler._new_version([model_version(version=7, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    # verify that r3 didn't get an event, i.e. it did not deploy and it is not scheduled or executing
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    #########################
    # Verify failure events #
    #########################
    agent.executor_manager.reset_executor_counters()
    # release change to r1, and make its deploy fail
    resources = make_resources(r1_value=2, r2_value=1, r3_value=0, r1_fail=True)
    await agent.scheduler._new_version([model_version(version=8, resources=resources)])
    # assert that r2 got deployed through event propagation
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ################################################################
    # Verify event propagation when dependant is already deploying #
    ################################################################
    # this scenario is a rare race, but still important not to miss events
    agent.executor_manager.reset_executor_counters()

    # hang r2 in the running state by releasing an update for it
    resources = make_resources(r1_value=2, r2_value=2, r3_value=0)
    await agent.scheduler._new_version([model_version(version=9, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)

    # reset counters and assert start state
    agent.executor_manager.reset_executor_counters()
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert agent.scheduler._work.agent_queues._in_progress.keys() == {tasks.Deploy(resource=rid2)}

    # trigger an event by deploying r1
    await agent.scheduler.deploy_resource(
        rid1,
        reason="Test: deploying r1 to trigger an event for r2",
        # use same priority as running r2 deploy
        priority=TaskPriority.NEW_VERSION_DEPLOY,
    )
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    # assert that r2 was rescheduled due to the event, even though it is already deploying for its latest intent
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid2)}
    # Note: turns out this scenario is no longer really reachable in the way it was intended: the only way it's possible
    #   for both r1 and r2 to be deploying concurrently, is if r1 was triggered while r2 was already deploying (as set up
    #   above). However, in that case, r2 gets rescheduled when the r1 deploy is *requested*, rather than when it *finishes*
    #   (see assert on message below).
    #   The scenario is kept anyway, because the concept remains important. We don't want to fully rely on the
    #   reschedule-on-request behavior. If that would ever change, we want to make sure we retain this property. In which case
    #   this assert on the message is expected to break, but the rest of the scenario should remain valid.
    assert agent.scheduler._work.agent_queues.queued()[tasks.Deploy(resource=rid2)].reason == (
        "rescheduling because a dependency was scheduled while it was deploying"
    )
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]

    # verify that it suffices for r2 to be already scheduled (vs deploying above), i.e. it does not get scheduled twice
    # trigger an event by releasing a change for r1
    resources = make_resources(r1_value=4, r2_value=2, r3_value=0)
    await agent.scheduler._new_version([model_version(version=11, resources=resources)])
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid2)}
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]

    # finish up: deploy r2 twice
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.failed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 2)

    # verify total number of deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 2  # two changes
    assert agent.executor_manager.executors["agent2"].execute_count == 2  # two events
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
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
    resources = make_resources(r1_value=4, r2_value=3, r3_value=0, r2_send_event=True)
    await agent.scheduler._new_version([model_version(version=12, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    # release another change to r2, making the currently running deploy stale
    resources = make_resources(r1_value=4, r2_value=4, r3_value=0, r2_send_event=True)
    await agent.scheduler._new_version([model_version(version=13, resources=resources)])

    # verify expected intermediate state
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.scheduler._work.agent_queues.queued().keys() == {tasks.Deploy(resource=rid2)}
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]

    # finish stale r2 deploy and verify that it does not send out an event
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent2"].execute_count == 1)
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]

    # finish up: deploy r2 and r3 (this time it does get an event from non-stale r2)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent3"].execute_count == 1)

    # verify total number of deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 2  # two changes
    assert agent.executor_manager.executors["agent3"].execute_count == 1  # one non-stale event
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    ##################################################
    # Verify event propagation for dropped resources #
    ##################################################
    # A special case of a stale deploy: the resource that finished deploying does not exist at all anymore in the new version
    # => should not produce events
    agent.executor_manager.reset_executor_counters()
    # release a new version with an update to r2, where it sends events
    resources = make_resources(r1_value=4, r2_value=5, r3_value=0, r2_send_event=True)
    await agent.scheduler._new_version([model_version(version=14, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    # drop r2, making the currently running deploy stale
    resources = make_resources(r1_value=4, r2_value=None, r3_value=0)
    await agent.scheduler._new_version([model_version(version=15, resources=resources)])

    # verify expected intermediate state
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 0
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert [*agent.scheduler._work.agent_queues._in_progress.keys()] == [tasks.Deploy(resource=rid2)]

    # finish stale r2 deploy and verify that it doesn't send out an event
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    #################################################################################################
    # Verify resources are marked as dirty after event propagation causes success->failure transfer #
    #################################################################################################
    agent.executor_manager.reset_executor_counters()

    # set up initial state
    resources = make_resources(r1_value=4, r2_value=0, r3_value=0)
    await agent.scheduler._new_version([model_version(version=16, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    # verify initial state
    assert rid2 not in executor2.deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 0
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    assert agent.scheduler._state.resource_state[rid2] == state.ResourceState(
        compliance=state.Compliance.COMPLIANT,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=state.Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid2].last_deployed,  # ignore
        last_deploy_compliant=True,
    )
    assert len(agent.scheduler._state.dirty) == 0

    # release change for r1, sending event to r2 when it finishes
    resources = make_resources(r1_value=5, r2_value=0, r3_value=0)
    await agent.scheduler._new_version([model_version(version=17, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)

    # verify that r2 is still in an assumed good state, even though we're deploying it
    assert agent.scheduler._state.resource_state[rid2] == state.ResourceState(
        compliance=state.Compliance.COMPLIANT,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=state.Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid2].last_deployed,  # ignore
        last_deploy_compliant=True,
    )
    assert len(agent.scheduler._state.dirty) == 0

    # fail r2
    # failed works just as well but skipped is even more of an edge case
    executor2.deploys[rid2].set_result(const.HandlerResourceState.skipped)
    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    assert rid2 not in executor2.deploys
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.executor_manager.executors["agent3"].execute_count == 0
    # verify that r2 is considered dirty now, as it is skipped
    assert agent.scheduler._state.resource_state[rid2] == state.ResourceState(
        # We are skipped, so not compliant
        compliance=state.Compliance.NON_COMPLIANT,
        last_deploy_result=state.DeployResult.SKIPPED,
        blocked=state.Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid2].last_deployed,  # ignore
        last_deploy_compliant=False,
    )
    assert agent.scheduler._state.dirty == {rid2}

    # trigger a deploy, verify that r2 gets scheduled because it is dirty
    await agent.scheduler.deploy(reason="Test")
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 3
    assert agent.executor_manager.executors["agent3"].execute_count == 0

    ###########################################################################################
    # Verify resources wait for all dependencies to finish when they receive an event (#8514) #
    ###########################################################################################
    agent.executor_manager.reset_executor_counters()

    # set up initial state: have rid3 depend on both other resources
    resources = make_resources(
        r1_value=1,
        r2_value=1,
        r3_value=1,
        requires={
            rid3: [rid1, rid2],
        },
        r1_send_event=True,
        r2_send_event=False,
    )
    await agent.scheduler._new_version([model_version(version=18, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 1

    # release a change for rid2 to get it in a deploying state
    resources = make_resources(
        r1_value=1,
        r2_value=2,
        r3_value=1,
        requires={
            rid3: [rid1, rid2],
        },
        r1_send_event=True,
        r2_send_event=False,
    )
    await agent.scheduler._new_version([model_version(version=19, resources=resources)])
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    # leave it hanging in deploying state for now. Assert that all else is stable
    assert agent.scheduler._work.agent_queues._in_progress.keys() == {tasks.Deploy(resource=rid2)}
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert agent.executor_manager.executors["agent2"].execute_count == 1
    assert agent.executor_manager.executors["agent3"].execute_count == 1

    # release a change for rid1
    resources = make_resources(
        r1_value=2,
        r2_value=2,
        r3_value=1,
        requires={
            rid3: [rid1, rid2],
        },
        r1_send_event=True,
        r2_send_event=False,
    )
    await agent.scheduler._new_version([model_version(version=20, resources=resources)])
    # wait until rid1 is done
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)
    # verify that rid2 is still in a deploying state
    assert rid2 in executor2.deploys
    assert agent.scheduler._work.agent_queues._in_progress.keys() == {tasks.Deploy(resource=rid2)}
    # verify that rid3 got the event and is waiting for rid2
    assert agent.scheduler._work._waiting.keys() == {rid3}
    assert agent.scheduler._work._waiting[rid3].blocked_on == {rid2}
    assert agent.scheduler._work._waiting[rid3].reason == f"an event was received from {rid1}"

    # finish rid2 deploy, assert end condition
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent3"].execute_count == 2)
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert agent.executor_manager.executors["agent1"].execute_count == 2
    assert agent.executor_manager.executors["agent2"].execute_count == 2
    assert agent.executor_manager.executors["agent3"].execute_count == 2


async def test_skipped_for_dependencies_with_normal_event_propagation_disabled(agent: TestAgent, make_resource_minimal):
    """
    Ensure that a resource that was skipped for its dependencies gets scheduled when the
    dependency succeeds, even when normal event propagation is disabled.
    """

    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent2,name=2]")

    # make both agent's executors managed
    executor1: ManagedExecutor = agent.executor_manager.register_managed_executor("agent1")
    executor2: ManagedExecutor = agent.executor_manager.register_managed_executor("agent2")

    # Create resources and set send_event to False
    resources = {
        rid1: make_resource_minimal(
            rid=rid1, values={"value": "r1_value", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False}, requires=[]
        ),
        rid2: make_resource_minimal(
            rid=rid2, values={"value": "r2_value", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False}, requires=[rid1]
        ),
    }
    await agent.scheduler._new_version([model_version(version=1, resources=resources)])

    # Make both resources succeed
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)

    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)

    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0

    # Deploy rid1 and make sure that rid2 does not get scheduled because event propagation is disabled
    await agent.scheduler.deploy_resource(rid1, reason="Deploy rid1", priority=TaskPriority.USER_DEPLOY)
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.HandlerResourceState.failed)

    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert rid2 not in executor2.deploys

    # Deploy rid2 and make it skip for dependencies
    await agent.scheduler.deploy_resource(rid2, reason="Deploy rid2", priority=TaskPriority.USER_DEPLOY)

    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.skipped_for_dependency)
    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0

    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        compliance=state.Compliance.NON_COMPLIANT,
        last_deploy_result=state.DeployResult.FAILED,
        blocked=state.Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid1].last_deployed,  # ignore this one
        last_deploy_compliant=False,
    )

    assert agent.scheduler._state.resource_state[rid2] == state.ResourceState(
        # We are skipped, so not compliant
        compliance=state.Compliance.NON_COMPLIANT,
        last_deploy_result=state.DeployResult.SKIPPED,
        blocked=state.Blocked.TEMPORARILY_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid2].last_deployed,  # ignore this one
        last_deploy_compliant=False,
    )

    # Recover rid1 and verify that rid2 also gets scheduled
    await agent.scheduler.deploy_resource(rid1, reason="Recover rid1", priority=TaskPriority.USER_DEPLOY)
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)

    # rid2 gets scheduled when rid1 recovers despite send_event being set to False
    await retry_limited_fast(lambda: rid2 in executor2.deploys)
    executor2.deploys[rid2].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: len(agent.scheduler._work.agent_queues._in_progress) == 0)
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0

    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        compliance=state.Compliance.COMPLIANT,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=state.Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid1].last_deployed,  # ignore this one
        last_deploy_compliant=True,
    )

    assert agent.scheduler._state.resource_state[rid2] == state.ResourceState(
        compliance=state.Compliance.COMPLIANT,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=state.Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid2].last_deployed,  # ignore this one
        last_deploy_compliant=True,
    )


async def test_skipped_for_dependencies_recover_with_multiple_dependencies(agent: TestAgent, make_resource_minimal):
    """
    Verify that a resource is lifted out of the TEMPORARILY_BLOCKED state as soon as there are no known bad dependencies
    anymore. This in contrast to an faulty implementation where it would only be lifted when all dependencies are known good.
    """

    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent1,name=2]")
    rid3 = ResourceIdStr("test::Resource[agent1,name=3]")

    # Create resources and set send_event to False
    resources = {
        rid1: make_resource_minimal(
            rid=rid1, values={"value": "r1_value", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False}, requires=[]
        ),
        rid3: make_resource_minimal(
            rid=rid3, values={"value": "r3_value", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False}, requires=[rid1]
        ),
    }
    await agent.scheduler._new_version([model_version(version=1, resources=resources)])

    # finish first deploy, then replace the executor with a managed one
    await retry_limited_fast(
        lambda: (executor := agent.executor_manager.executors.get("agent1")) is not None and executor.execute_count == 2
    )

    # deploy rid1, and verify that rid3 does not get deployed through an event
    # (this test is only meaningful if normal event propagation is disabled)
    await agent.scheduler.deploy_resource(rid1, reason="Test deploy rid1", priority=TaskPriority.USER_DEPLOY)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 3)
    assert agent.scheduler._work.agent_queues._agent_queues["agent1"]._unfinished_tasks == 0

    # now replace the executor with a managed one for more fine-grained control over deploy behavior
    executor1: ManagedExecutor = agent.executor_manager.register_managed_executor("agent1")

    # fail rid1 and have rid3 skip for dependencies
    await agent.scheduler.deploy_resource(rid1, reason="Test deploy rid1", priority=TaskPriority.USER_DEPLOY)
    await agent.scheduler.deploy_resource(rid3, reason="Test deploy rid3", priority=TaskPriority.USER_DEPLOY)
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.HandlerResourceState.failed)
    await retry_limited_fast(lambda: rid3 in executor1.deploys)
    executor1.deploys[rid3].set_result(const.HandlerResourceState.skipped_for_dependency)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)

    # release a new version where rid3 no longer depends on the failed rid1, but on a new resource rid2
    agent.executor_manager.reset_executor_counters()
    resources = {
        rid1: make_resource_minimal(
            rid=rid1, values={"value": "r1_value", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False}, requires=[]
        ),
        rid2: make_resource_minimal(
            rid=rid2, values={"value": "r2_value", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False}, requires=[]
        ),
        rid3: make_resource_minimal(
            rid=rid3, values={"value": "r3_value", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False}, requires=[rid2]
        ),
    }
    await agent.scheduler._new_version([model_version(version=2, resources=resources)])
    # Verify that rid3 got unblocked now
    assert agent.scheduler._state.resource_state[rid3].blocked is Blocked.NOT_BLOCKED


async def test_receive_events(agent: TestAgent, make_resource_minimal):
    """
    Ensure that event propagation respects the receive_events attribute
    """

    rid_send = "test::Resource[root,name=send]"
    rid_nosend = "test::Resource[root,name=nosend]"
    rid_receive = "test::Resource[listen,name=receive]"
    rid_noreceive = "test::Resource[deaf,name=noreceive]"
    rid_defaultreceive = "test::Resource[listen,name=defaultreceive]"

    def make_resources(
        *,
        version: int,
        send_value: int,
        nosend_value: int,
        receive_value: int,
        noreceive_value: int,
        defaultreceive_value: int,
    ) -> dict[ResourceIdStr, state.ResourceIntent]:
        """
        Returns five resources with a single attribute, whose value is set by the value parameters.

        receive, noreceive and defaultreceive all require both send and nosend,
        but only send sets send_event=True and only receive sets receive_events=True
        """
        return {
            ResourceIdStr(rid): make_resource_minimal(
                rid,
                values={
                    "value": value,
                    const.RESOURCE_ATTRIBUTE_SEND_EVENTS: send_event,
                    **(
                        {
                            const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS: receive_event,
                        }
                        if receive_event is not None
                        else {}
                    ),
                },
                requires=requires,
            )
            for rid, value, send_event, receive_event, requires in [
                (rid_send, send_value, True, True, []),
                (rid_nosend, nosend_value, False, True, []),
                (rid_receive, receive_value, True, True, [rid_send, rid_nosend]),
                (rid_noreceive, noreceive_value, True, False, [rid_send, rid_nosend]),
                (rid_defaultreceive, noreceive_value, True, None, [rid_send, rid_nosend]),
            ]
        }

    # first release
    resources = make_resources(
        version=1, send_value=0, nosend_value=0, receive_value=0, noreceive_value=0, defaultreceive_value=0
    )
    await agent.scheduler._new_version([model_version(version=1, resources=resources)])

    def done():
        listen_queue = agent.scheduler._work.agent_queues._agent_queues.get("listen", None)
        deaf_queue = agent.scheduler._work.agent_queues._agent_queues.get("deaf", None)
        return all(queue is not None and queue._unfinished_tasks == 0 for queue in (listen_queue, deaf_queue))

    await retry_limited_fast(done)
    assert agent.executor_manager.executors["root"].execute_count == 2
    assert agent.executor_manager.executors["listen"].execute_count == 2
    assert agent.executor_manager.executors["deaf"].execute_count == 1
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    # reset counters
    agent.executor_manager.reset_executor_counters()
    # release change for send only
    resources = make_resources(
        version=2, send_value=1, nosend_value=0, receive_value=0, noreceive_value=0, defaultreceive_value=0
    )
    await agent.scheduler._new_version([model_version(version=2, resources=resources)])
    # verify that listeners got events and noreceive did not
    await retry_limited_fast(lambda: agent.executor_manager.executors["listen"].execute_count == 2)
    assert agent.executor_manager.executors["root"].execute_count == 1
    assert agent.executor_manager.executors["listen"].execute_count == 2
    assert agent.executor_manager.executors["deaf"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0

    # reset counters
    agent.executor_manager.reset_executor_counters()
    # release change for nosend only
    resources = make_resources(
        version=3, send_value=1, nosend_value=1, receive_value=0, noreceive_value=0, defaultreceive_value=0
    )
    await agent.scheduler._new_version([model_version(version=3, resources=resources)])
    # verify that no events were produced at all
    await retry_limited_fast(lambda: agent.executor_manager.executors["root"].execute_count == 1)
    assert agent.executor_manager.executors["root"].execute_count == 1
    assert agent.executor_manager.executors["listen"].execute_count == 0
    assert agent.executor_manager.executors["deaf"].execute_count == 0
    assert len(agent.scheduler._work._waiting) == 0
    assert len(agent.scheduler._work.agent_queues.queued()) == 0
    assert len(agent.scheduler._work.agent_queues._in_progress) == 0


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

    await agent.scheduler._new_version([model_version(version=5, resources=resources)])

    assert len(get_resources_for_agent(agent.scheduler, "agent1")) == 2

    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, {"value": "a"}, []),
    }

    await agent.scheduler._new_version([model_version(version=6, resources=resources)])

    assert len(get_resources_for_agent(agent.scheduler, "agent1")) == 1
    assert len(agent.scheduler._state.intent) == 1


async def test_dryrun(agent: TestAgent, make_resource_minimal):
    """
    Ensure the simples deploy scenario works: 2 dependant resources
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
        ResourceIdStr(rid2): make_resource_minimal(rid2, values={"value": "a"}, requires=[rid1]),
    }

    agent.scheduler.mock_versions[5] = resources

    dryrun = uuid.uuid4()
    await agent.scheduler.dryrun(dryrun, 5)
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")

    assert agent.executor_manager.executors["agent1"].dry_run_count == 2


async def test_get_facts(agent: TestAgent, make_resource_minimal):
    """
    Ensure the simples deploy scenario works: 2 dependant resources
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
        ResourceIdStr(rid2): make_resource_minimal(rid2, values={"value": "a"}, requires=[rid1]),
    }

    await agent.scheduler._new_version([model_version(version=5, resources=resources)])

    await agent.scheduler.get_facts(Id.parse_id(rid1))

    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")

    assert agent.executor_manager.executors["agent1"].facts_count == 1


async def test_unknowns(agent: TestAgent, make_resource_minimal) -> None:
    """
    Test whether unknowns are handled correctly by the scheduler.
    """
    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent1,name=2]")
    rid3 = ResourceIdStr("test::Resource[agent1,name=3]")
    rid4 = ResourceIdStr("test::Resource[agent1,name=4]")
    rid5 = ResourceIdStr("test::Resource[agent1,name=5]")
    rid6 = ResourceIdStr("test::Resource[agent1,name=6]")
    rid7 = ResourceIdStr("test::Resource[agent1,name=7]")

    def assert_resource_state(
        resource: ResourceIdStr,
        compliance: state.Compliance,
        deploy_result: state.DeployResult,
        blocked_status: state.Blocked,
        attribute_hash: str,
    ) -> None:
        """
        Assert that the given resource has the given Compliance, DeployResult and Blocked.
        If not, this method raises an AssertionError.

        :param resource: The resource of which the above-mentioned parameters have to be asserted.
        :param compliance: The Compliance to assert.
        :param deploy_result: The DeployResult to assert.
        :param blocked_status: The Blocked to assert.
        :param attribute_hash: The hash of the attributes of the resource.
        """
        assert agent.scheduler._state.resource_state[resource].compliance is compliance
        assert agent.scheduler._state.resource_state[resource].last_deploy_result is deploy_result
        assert agent.scheduler._state.resource_state[resource].blocked is blocked_status
        assert agent.scheduler._state.intent[resource].attribute_hash == attribute_hash

    # rid4 is undefined due to an unknown
    resources = {
        rid1: make_resource_minimal(
            rid=rid1,
            values={"value": "unknown"},
            requires=[rid2, rid3, rid4],
        ),
        rid2: make_resource_minimal(rid=rid2, values={"value": "a"}, requires=[rid5]),
        rid3: make_resource_minimal(rid=rid3, values={"value": "a"}, requires=[rid5, rid6]),
        rid4: make_resource_minimal(rid=rid4, values={"value": "unknown"}, requires=[]),
        rid5: make_resource_minimal(rid=rid5, values={"value": "a"}, requires=[]),
        rid6: make_resource_minimal(rid=rid6, values={"value": "a"}, requires=[rid7]),
        rid7: make_resource_minimal(rid=rid7, values={"value": "a"}, requires=[]),
    }

    #                             +-- rid2  <- rid5
    #                             |              |
    #      "Provides"      rid1 <-+-- rid3  <----+
    #        view                 |              |
    #                             +-- rid4     rid6 <- rid7

    await agent.scheduler._new_version(
        [
            model_version(
                version=1,
                resources=resources,
                undefined={rid4},
            )
        ]
    )
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")
    assert len(agent.scheduler._state.intent) == 7
    assert len(get_resources_for_agent(agent.scheduler, "agent1")) == 7

    # rid1: transitively blocked on rid4
    # rid2: deployed
    # rid3: deployed
    # rid4: blocked (unknown attribute)
    # rid5: deployed
    # rid6: deployed
    # rid7: deployed
    assert_resource_state(
        rid1,
        state.Compliance.HAS_UPDATE,
        state.DeployResult.NEW,
        state.Blocked.BLOCKED,
        resources[rid1].attribute_hash,
    )
    assert_resource_state(
        rid2,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid2].attribute_hash,
    )
    assert_resource_state(
        rid3,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid3].attribute_hash,
    )
    assert_resource_state(
        rid4,
        state.Compliance.UNDEFINED,
        state.DeployResult.NEW,
        state.Blocked.BLOCKED,
        resources[rid4].attribute_hash,
    )
    assert_resource_state(
        rid5,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid5].attribute_hash,
    )
    assert_resource_state(
        rid6,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid6].attribute_hash,
    )
    assert_resource_state(
        rid7,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid7].attribute_hash,
    )

    # rid4 becomes deployable
    # rid5 and rid6 are undefined
    # Change the desired state of rid2
    resources[rid4] = make_resource_minimal(rid=rid4, values={"value": "a"}, requires=[])
    resources[rid5] = make_resource_minimal(rid=rid5, values={"value": "unknown"}, requires=[])
    resources[rid6] = make_resource_minimal(rid=rid6, values={"value": "unknown"}, requires=[rid7])
    resources[rid2] = make_resource_minimal(rid=rid2, values={"value": "b"}, requires=[rid5])
    resources[rid3] = make_resource_minimal(rid=rid3, values={"value": "a"}, requires=[rid5, rid6])
    await agent.scheduler._new_version(
        [
            model_version(
                version=2,
                resources=resources,
                undefined={rid5, rid6},
            )
        ]
    )
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")
    assert len(agent.scheduler._state.intent) == 7

    # rid1: transitively blocked on rid5 and rid6
    # rid2: transitively blocked on rid5
    # rid3: transitively blocked on rid5 and rid6
    # rid4: deployed
    # rid5: blocked because it has an unknown attribute
    # rid6: blocked because it has an unknown attribute
    # rid7: deployed
    assert_resource_state(
        rid1,
        state.Compliance.HAS_UPDATE,
        state.DeployResult.NEW,
        state.Blocked.BLOCKED,
        resources[rid1].attribute_hash,
    )
    assert_resource_state(
        rid2,
        state.Compliance.HAS_UPDATE,
        state.DeployResult.DEPLOYED,
        state.Blocked.BLOCKED,
        resources[rid2].attribute_hash,
    )
    assert_resource_state(
        rid3,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.BLOCKED,
        resources[rid3].attribute_hash,
    )
    assert_resource_state(
        rid4,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid4].attribute_hash,
    )
    assert_resource_state(
        rid5,
        state.Compliance.UNDEFINED,
        state.DeployResult.DEPLOYED,
        state.Blocked.BLOCKED,
        resources[rid5].attribute_hash,
    )
    assert_resource_state(
        rid6,
        state.Compliance.UNDEFINED,
        state.DeployResult.DEPLOYED,
        state.Blocked.BLOCKED,
        resources[rid6].attribute_hash,
    )
    assert_resource_state(
        rid7,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid7].attribute_hash,
    )

    # rid5 no longer has an unknown attribute
    resources[rid5] = make_resource_minimal(rid=rid5, values={"value": "a"}, requires=[])
    resources[rid2] = make_resource_minimal(rid=rid2, values={"value": "b"}, requires=[rid5])
    await agent.scheduler._new_version(
        [
            model_version(
                version=3,
                resources=resources,
                undefined={rid6},
            )
        ]
    )
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")
    assert len(agent.scheduler._state.intent) == 7

    # rid1: transitively blocked on rid6
    # rid2: deployed
    # rid3: transitively blocked on rid6
    # rid4: deployed
    # rid5: deployed
    # rid6: blocked because it has an unknown attribute
    # rid7: deployed
    assert_resource_state(
        rid1,
        state.Compliance.HAS_UPDATE,
        state.DeployResult.NEW,
        state.Blocked.BLOCKED,
        resources[rid1].attribute_hash,
    )
    assert_resource_state(
        rid2,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid2].attribute_hash,
    )
    assert_resource_state(
        rid3,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.BLOCKED,
        resources[rid3].attribute_hash,
    )
    assert_resource_state(
        rid4,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid4].attribute_hash,
    )
    assert_resource_state(
        rid5,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid5].attribute_hash,
    )
    assert_resource_state(
        rid6,
        state.Compliance.UNDEFINED,
        state.DeployResult.DEPLOYED,
        state.Blocked.BLOCKED,
        resources[rid6].attribute_hash,
    )
    assert_resource_state(
        rid7,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid7].attribute_hash,
    )

    # rid8 and rid9 are both undefined
    rid8 = ResourceIdStr("test::Resource[agent1,name=8]")
    rid9 = ResourceIdStr("test::Resource[agent1,name=9]")
    resources = {
        rid8: make_resource_minimal(rid=rid8, values={"value": "unknown"}, requires=[]),
        rid9: make_resource_minimal(rid=rid9, values={"value": "unknown"}, requires=[rid8]),
    }
    await agent.scheduler._new_version(
        [
            model_version(
                version=4,
                resources=resources,
                undefined={rid8, rid9},
            )
        ]
    )
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")
    assert len(agent.scheduler._state.intent) == 2
    assert len(get_resources_for_agent(agent.scheduler, "agent1")) == 2

    assert_resource_state(
        rid8,
        state.Compliance.UNDEFINED,
        state.DeployResult.NEW,
        state.Blocked.BLOCKED,
        resources[rid8].attribute_hash,
    )
    assert_resource_state(
        rid9,
        state.Compliance.UNDEFINED,
        state.DeployResult.NEW,
        state.Blocked.BLOCKED,
        resources[rid9].attribute_hash,
    )

    # rid8 is no longer undefined
    resources[rid8] = make_resource_minimal(rid=rid8, values={"value": "a"}, requires=[])

    await agent.scheduler._new_version(
        [
            model_version(
                version=5,
                resources=resources,
                undefined={rid9},
            )
        ]
    )
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=agent.scheduler, agent_name="agent1")
    assert len(agent.scheduler._state.intent) == 2
    assert len(get_resources_for_agent(agent.scheduler, "agent1")) == 2

    assert_resource_state(
        rid8,
        state.Compliance.COMPLIANT,
        state.DeployResult.DEPLOYED,
        state.Blocked.NOT_BLOCKED,
        resources[rid8].attribute_hash,
    )
    assert_resource_state(
        rid9,
        state.Compliance.UNDEFINED,
        state.DeployResult.NEW,
        state.Blocked.BLOCKED,
        resources[rid9].attribute_hash,
    )


async def test_scheduler_priority(agent: TestAgent, environment, make_resource_minimal):
    """
    Ensure that the tasks are placed in the queue in the correct order
    and that existing tasks in the queue are replaced if a task that
    does the same thing with higher priority is added to the queue
    """

    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    resources = {
        rid1: make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
    }

    agent.executor_manager.register_managed_executor("agent1")

    # We add two different tasks and assert that they are consumed in the correct order
    # Add a new version deploy to the queue
    await agent.scheduler._new_version([model_version(version=1, resources=resources)])
    agent.scheduler.mock_versions[1] = resources

    # And then a dryrun
    dryrun = uuid.uuid4()
    await agent.scheduler.dryrun(dryrun, 1)

    # The tasks are consumed in the priority order
    first_task = await agent.scheduler._work.agent_queues.queue_get("agent1")
    assert isinstance(first_task.task, tasks.Deploy)
    second_task = await agent.scheduler._work.agent_queues.queue_get("agent1")
    assert isinstance(second_task.task, tasks.DryRun)

    # The same is true if a task with lesser priority is added first
    # Add a fact refresh task to the queue
    await agent.scheduler.get_facts(Id.parse_id(rid1))

    # Then add an interval deploy task to the queue
    agent.scheduler._state.dirty.add(rid1)
    await agent.scheduler.deploy(reason="Test", priority=TaskPriority.INTERVAL_DEPLOY)

    # The tasks are consumed in the priority order
    first_task = await agent.scheduler._work.agent_queues.queue_get("agent1")
    assert isinstance(first_task.task, tasks.Deploy)
    second_task = await agent.scheduler._work.agent_queues.queue_get("agent1")
    assert isinstance(second_task.task, tasks.RefreshFact)
    # Assert that all tasks were consumed
    queue = agent.scheduler._work.agent_queues._get_queue("agent1")._queue
    assert len(queue) == 0

    # Add an interval deploy task to the queue
    agent.scheduler._state.dirty.add(rid1)
    await agent.scheduler.deploy(reason="Test", priority=TaskPriority.INTERVAL_DEPLOY)

    # Add a dryrun to the queue (which has more priority)
    dryrun = uuid.uuid4()
    await agent.scheduler.dryrun(dryrun, 1)

    # Assert that we have both tasks in the queue
    queue = agent.scheduler._work.agent_queues._get_queue("agent1")._queue
    assert len(queue) == 2

    # Add a user deploy
    # It has more priority than interval deploy, so it will replace it in the queue
    # It also has more priority than dryrun, so it will be consumed first

    await agent.trigger_update(environment, "$__scheduler", incremental_deploy=True)

    first_task = await agent.scheduler._work.agent_queues.queue_get("agent1")
    assert isinstance(first_task.task, tasks.Deploy)
    second_task = await agent.scheduler._work.agent_queues.queue_get("agent1")
    assert isinstance(second_task.task, tasks.DryRun)

    # Interval deploy is still in the queue but marked as deleted
    queue = agent.scheduler._work.agent_queues._get_queue("agent1")._queue
    assert len(queue) == 1
    assert queue[0].deleted

    # Force clean queue
    agent.scheduler._work.agent_queues._get_queue("agent1")._queue = []

    # If a task to deploy a resource is added to the queue,
    # but a task to deploy that same resource is already present with higher priority,
    # it will be ignored and not added to the queue

    # Add a dryrun to the queue
    dryrun = uuid.uuid4()
    await agent.scheduler.dryrun(dryrun, 1)

    # Add a user deploy
    await agent.trigger_update(environment, "$__scheduler", incremental_deploy=True)

    # Try to add an interval deploy task to the queue
    agent.scheduler._state.dirty.add(rid1)
    await agent.scheduler.deploy(reason="Test", priority=TaskPriority.INTERVAL_DEPLOY)

    # Assert that we still have only 2 tasks in the queue
    queue = agent.scheduler._work.agent_queues._get_queue("agent1")._queue
    assert len(queue) == 2

    # The order is unaffected, the interval deploy was essentially ignored
    first_task = await agent.scheduler._work.agent_queues.queue_get("agent1")
    assert isinstance(first_task.task, tasks.Deploy)
    second_task = await agent.scheduler._work.agent_queues.queue_get("agent1")
    assert isinstance(second_task.task, tasks.DryRun)

    # All tasks were consumed
    queue = agent.scheduler._work.agent_queues._get_queue("agent1")._queue
    assert len(queue) == 0


async def test_scheduler_priority_rescheduling(agent: TestAgent, environment, make_resource_minimal):
    """
    Verify behavior of task rescheduling (e.g. because of new requires) with respect to priorities, both explicit and relative
    to other scheduled task (i.e. current queue position).
    """

    # General flow of the test: all deploy tasks, all on the same agent, different priorities. Tasks are never picked up,
    # only added or shifted around (due to changing priorities or requires edges).
    # This test interacts with scheduled work directly rather than to go through the scheduler for verbosity reasons.
    # For a basic priority test that does go via the scheduler see test_scheduler_priority.

    # define some resources
    rid1 = ResourceIdStr("test::Resource[agent,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent,name=2]")
    rid3 = ResourceIdStr("test::Resource[agent,name=3]")
    rid4 = ResourceIdStr("test::Resource[agent,name=4]")
    rid5 = ResourceIdStr("test::Resource[agent,name=5]")
    rid6 = ResourceIdStr("test::Resource[agent,name=6]")
    rid7 = ResourceIdStr("test::Resource[agent,name=7]")
    task1 = tasks.Deploy(resource=rid1)
    task2 = tasks.Deploy(resource=rid2)
    task3 = tasks.Deploy(resource=rid3)
    task4 = tasks.Deploy(resource=rid4)
    task5 = tasks.Deploy(resource=rid5)
    task6 = tasks.Deploy(resource=rid6)
    task7 = tasks.Deploy(resource=rid7)

    # set up the scheduled work
    requires: state.RequiresProvidesMapping = state.RequiresProvidesMapping()
    work: ScheduledWork = ScheduledWork(
        requires=requires, provides=requires.provides_view(), new_agent_notify=lambda *args, **kwargs: None
    )

    # three different deploy requests, each for a different resource. Verify that order ends up as expected
    work.deploy_with_context(
        resources={rid1},
        reason="First deploy",
        priority=TaskPriority(3),
    )
    work.deploy_with_context(
        resources={rid2},
        reason="Second deploy",
        priority=TaskPriority(1),
    )
    work.deploy_with_context(
        resources={rid3},
        reason="Third deploy",
        priority=TaskPriority(4),
    )

    assert [item.task for item in work.agent_queues.sorted("agent")] == [task2, task1, task3]

    # add some more tasks to the middle priority level
    work.deploy_with_context(
        resources={rid1, rid2, rid3, rid4, rid5},
        reason="Bulk deploy",
        priority=TaskPriority(3),
    )
    # add two more tasks to more urgent priority level for some relative ordering asserts later on
    work.deploy_with_context(
        resources={rid6},
        reason="deploy rid6",
        priority=TaskPriority(1),
    )
    work.deploy_with_context(
        resources={rid7},
        reason="deploy rid7",
        priority=TaskPriority(2),
    )

    def get_sorted_tasks() -> Sequence[tuple[tasks.Task, str]]:
        return [(item.task, item.reason) for item in work.agent_queues.sorted("agent")]

    # may be updated after each assertion
    original_sorted_tasks: Sequence[tuple[tasks.Task, str]] = get_sorted_tasks()

    # -> priority 1: rid2, rid6
    # -> priority 2: rid7
    # -> priority 3: rid1, rid3, rid4, rid5 (latter three in any order)
    assert original_sorted_tasks[:4] == [
        # rid2 already had a more urgent priority, it should remain first
        (task2, "Second deploy"),
        # rid6 was added later with a more urgent priority, it should move before the others but after rid2
        (task6, "deploy rid6"),
        # rid6 was added later with a more urgent priority, it should move before the others but after rid6
        (task7, "deploy rid7"),
        # rid1 was added first among those with this priority + it keeps its original reason
        (task1, "First deploy"),
    ]
    # other priorities are equal and non-deterministic
    assert set(original_sorted_tasks[4:]) == {
        (task3, "Bulk deploy"),
        (task4, "Bulk deploy"),
        (task5, "Bulk deploy"),
    }

    # add a requires edge, lifting a resource out of the agent queues because it becomes blocked
    rid_first_requires: ResourceIdStr = original_sorted_tasks[4][0].resource
    requires[rid_first_requires] = {rid1}
    work.deploy_with_context(
        {rid_first_requires},
        reason="add first requires",
        # less urgent priority
        priority=TaskPriority(5),
        added_requires={rid_first_requires: {rid1}},
    )
    # expect same order as before, minus the fourth element
    assert get_sorted_tasks() == original_sorted_tasks[:4] + original_sorted_tasks[5:]
    # drop the requires edge, unblocking the task again
    requires[rid_first_requires] = set()
    work.deploy_with_context(
        {rid_first_requires},
        reason="drop first requires",
        # less urgent priority
        priority=TaskPriority(5),
        dropped_requires={rid_first_requires: {rid1}},
    )
    # expect same order as original: because new priority is less urgent, the old priority, relative order and reason are kept
    assert get_sorted_tasks() == original_sorted_tasks

    # do the same for an equal priority task
    requires[rid_first_requires] = {rid1}
    work.deploy_with_context(
        {rid_first_requires},
        reason="add second requires",
        # equal priority
        priority=TaskPriority(3),
        added_requires={rid_first_requires: {rid1}},
    )
    # expect same order as before, minus the third element
    assert get_sorted_tasks() == original_sorted_tasks[:4] + original_sorted_tasks[5:]
    # drop the requires edge, unblocking the task again
    requires[rid_first_requires] = set()
    work.deploy_with_context(
        {rid_first_requires},
        reason="drop second requires",
        # equal priority
        priority=TaskPriority(3),
        dropped_requires={rid_first_requires: {rid1}},
    )
    # expect same order as original: even though new priority is lower, the old priority, relative order and reason are kept
    assert get_sorted_tasks() == original_sorted_tasks

    # same now for more urgent priority task in request that blocks it
    requires[rid_first_requires] = {rid1}
    work.deploy_with_context(
        {rid_first_requires},
        reason="add third requires",
        # more urgent priority
        priority=TaskPriority(1),
        added_requires={rid_first_requires: {rid1}},
    )
    # expect same order as before, minus the third element
    assert get_sorted_tasks() == original_sorted_tasks[:4] + original_sorted_tasks[5:]
    # drop the requires edge, unblocking the task again
    requires[rid_first_requires] = set()
    work.deploy_with_context(
        {rid_first_requires},
        reason="drop third requires",
        # equal priority as original
        priority=TaskPriority(3),
        dropped_requires={rid_first_requires: {rid1}},
    )
    # task is moved to new, more urgent priority, and receives the new message
    assert get_sorted_tasks() == [
        *original_sorted_tasks[:2],  # rid2, rid6
        # message from adding the requires
        (tasks.Deploy(resource=rid_first_requires), "add third requires"),
        original_sorted_tasks[2],  # rid7
        original_sorted_tasks[3],  # rid1
        *original_sorted_tasks[5:],
    ]

    # update original_sorted_tasks to reflect new order
    original_sorted_tasks = get_sorted_tasks()

    # same now but request the more urgent priority for the request that unblocks it
    rid_fourth_requires: ResourceIdStr = original_sorted_tasks[5][0].resource
    requires[rid_fourth_requires] = {rid1}
    work.deploy_with_context(
        {rid_fourth_requires},
        reason="add fourth requires",
        # equal priority as original
        priority=TaskPriority(3),
        added_requires={rid_fourth_requires: {rid1}},
    )
    # expect same order as before, minus the fourth element
    assert get_sorted_tasks() == original_sorted_tasks[:5] + original_sorted_tasks[6:]
    # drop the requires edge, unblocking the task again
    requires[rid_fourth_requires] = set()
    work.deploy_with_context(
        {rid_fourth_requires},
        reason="drop fourth requires",
        # most urgent priority
        priority=TaskPriority(0),
        dropped_requires={rid_fourth_requires: {rid1}},
    )
    # task is moved to new, more urgent priority, and receives the new message
    assert get_sorted_tasks() == [
        # message from dropping the requires
        (tasks.Deploy(resource=rid_fourth_requires), "drop fourth requires"),
        *original_sorted_tasks[:5],
        *original_sorted_tasks[6:],
    ]

    # update original_sorted_tasks to reflect new order
    original_sorted_tasks = get_sorted_tasks()

    # add a requires with an extremely urgent priority, but for a resource that's not in the to-deploy set
    # => priority should not affect this resource
    rid_fifth_requires: ResourceIdStr = original_sorted_tasks[2][0].resource
    requires[rid_fifth_requires] = {rid1}
    work.deploy_with_context(
        set(),
        reason="add fifth requires",
        # most urgent priority
        priority=TaskPriority(-1),
        added_requires={rid_fifth_requires: {rid1}},
    )
    # expect same order as before, minus the third element
    assert get_sorted_tasks() == original_sorted_tasks[:2] + original_sorted_tasks[3:]
    # drop the requires edge, unblocking the task again
    requires[rid_fifth_requires] = set()
    work.deploy_with_context(
        set(),
        reason="drop fifth requires",
        # most urgent priority
        priority=TaskPriority(-1),
        dropped_requires={rid_fifth_requires: {rid1}},
    )
    # no priority shifting took place: original is restored
    assert get_sorted_tasks() == original_sorted_tasks

    # get a single item from the queue, and while it's "deploying" add a dependency for it
    await work.agent_queues.queue_get("agent")
    assert work.agent_queues._in_progress == {tasks.Deploy(resource=rid_fourth_requires): TaskPriority(0)}
    # expect same order as before, minus the first element
    assert get_sorted_tasks() == original_sorted_tasks[1:]
    requires[rid_fourth_requires] = {rid1}
    work.deploy_with_context(
        set(),
        reason="add dependency while deploying",
        # most urgent priority
        priority=TaskPriority(-1),
        added_requires={rid_fourth_requires: {rid1}},
        deploying={rid_fourth_requires},
    )
    # no difference because new task is blocked
    assert get_sorted_tasks() == original_sorted_tasks[1:]
    assert rid_fourth_requires in work._waiting
    requires[rid_fourth_requires] = set()
    # unblock the task
    work.deploy_with_context(
        set(),
        reason="drop dependency again",
        # most urgent priority
        priority=TaskPriority(-1),
        dropped_requires={rid_fourth_requires: {rid1}},
        deploying={rid_fourth_requires},
    )
    # task got added again with original priority but a new message
    task_fourth_requires = tasks.Deploy(resource=rid_fourth_requires)
    assert get_sorted_tasks() == [
        (
            task_fourth_requires,
            "rescheduling because a dependency was scheduled while it was deploying",
        ),
        *original_sorted_tasks[1:],
    ]
    # assert it has the same priority as the in-progress task
    assert work.agent_queues.queued()[task_fourth_requires].priority == TaskPriority(0)

    # update original_sorted_tasks to reflect new order
    original_sorted_tasks = get_sorted_tasks()

    # while resource is still deploying, request a deploy for it with a more urgent priority
    work.deploy_with_context(
        {rid_fourth_requires},
        reason="deploy again while deploying",
        # most urgent priority
        priority=TaskPriority(-1),
        deploying={rid_fourth_requires},
    )
    # same order but different message
    assert get_sorted_tasks() == [
        (
            task_fourth_requires,
            "deploy again while deploying",
        ),
        *original_sorted_tasks[1:],
    ]
    # assert priorities
    # in-progress priority should have been shifted to increase priority of events that may be sent
    assert work.agent_queues.in_progress == {task_fourth_requires: TaskPriority(-1)}
    # queued priority should have been shifted as well, and requested_at refreshed
    assert work.agent_queues.queued()[task_fourth_requires].priority == TaskPriority(-1)
    assert work.agent_queues.queued()[task_fourth_requires].requested_at == work.agent_queues._entry_count - 1

    # update original_sorted_tasks to reflect new order
    original_sorted_tasks = get_sorted_tasks()

    # verify priority bumping on waiting task (not yet in queue)
    # add dependency to move task to waiting
    requires[rid2] = {rid1}
    work.deploy_with_context(
        {rid2},
        reason="add sixth requires",
        # low urgency priority
        priority=TaskPriority(5),
        added_requires={rid2: {rid1}},
    )
    assert get_sorted_tasks() == [original_sorted_tasks[0], *original_sorted_tasks[2:]]
    work.deploy_with_context(
        {rid2},
        reason="bump priority for rid2",
        # higher urgency priority
        priority=TaskPriority(0),
        # still waiting for rid1 => not queued
        added_requires={},
        dropped_requires={},
    )
    # unchanged versus previous check
    assert get_sorted_tasks() == [original_sorted_tasks[0], *original_sorted_tasks[2:]]
    assert rid2 in work._waiting
    # assert that waiting task's priority was bumped and its requested_at refreshed
    assert work._waiting[rid2].priority == TaskPriority(0)
    assert work._waiting[rid2].requested_at == work.agent_queues._entry_count - 1
    assert work._waiting[rid2].reason == "bump priority for rid2"


async def test_repair_does_not_trigger_for_blocked_resources(agent: TestAgent, make_resource_minimal):
    """
    Ensure that repair doesn't schedule known blocked resources
    """

    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent1,name=2]")

    resources = {
        rid1: make_resource_minimal(rid=rid1, values={"value": "r1_value"}, requires=[]),
        rid2: make_resource_minimal(rid=rid2, values={"value": "r2_value"}, requires=[]),
    }

    await agent.scheduler._new_version([model_version(version=1, resources=resources)])
    await retry_limited_fast(utils.is_agent_done, scheduler=agent.scheduler, agent_name="agent1")

    # Both resources were deployed
    assert agent.executor_manager.executors["agent1"].execute_count == 2

    agent.executor_manager.reset_executor_counters()

    # mark r1 as blocked and trigger a repair
    agent.scheduler._state.resource_state[rid1].blocked = Blocked.BLOCKED

    await agent.scheduler.repair(reason="Test triggered global repair")
    await retry_limited_fast(fun=utils.is_agent_done, scheduler=agent.scheduler, agent_name="agent1")

    # Only r2 was deployed
    assert agent.executor_manager.executors["agent1"].execute_count == 1


async def test_state_of_skipped_resources_for_dependencies(agent: TestAgent, make_resource_minimal):
    """
    Ensure that when a resource is skipped for its dependencies the scheduler marks it with Blocked.TEMPORARILY_BLOCKED
    """
    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent2,name=2]")

    # make agent2's executors managed, leave the agent1 auto fails
    executor2: ManagedExecutor = agent.executor_manager.register_managed_executor("agent2")

    resources = {
        rid1: make_resource_minimal(rid=rid1, values={"value": "r1_value", FAIL_DEPLOY: True}, requires=[]),
        rid2: make_resource_minimal(rid=rid2, values={"value": "r2_value"}, requires=[rid1]),
    }
    await agent.scheduler._new_version([model_version(version=1, resources=resources)])
    await retry_limited_fast(utils.is_agent_done, scheduler=agent.scheduler, agent_name="agent1")

    executor2.deploys[rid2].set_result(const.HandlerResourceState.skipped_for_dependency)
    await retry_limited_fast(utils.is_agent_done, scheduler=agent.scheduler, agent_name="agent2")

    assert agent.scheduler._state.resource_state[rid2] == state.ResourceState(
        # We are skipped, so not compliant
        compliance=state.Compliance.NON_COMPLIANT,
        last_deploy_result=state.DeployResult.SKIPPED,
        blocked=state.Blocked.TEMPORARILY_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid2].last_deployed,  # ignore
        last_deploy_compliant=False,
    )


async def test_remove_agent_venvs(environment, agent: TestAgent, make_resource_minimal, monkeypatch):
    """
    Verify that a request to remove the agent venvs waits until all executing agent tasks are finished.
    """
    # Track whether the remove_executor_venvs method of the agent was called
    # and block the call until the continue_remove_executor_venv_method future resolves.
    _remove_executor_venvs_method_was_called = False
    continue_remove_executor_venv_method = asyncio.get_running_loop().create_future()

    async def _remove_executor_venvs_dummy() -> None:
        nonlocal _remove_executor_venvs_method_was_called
        _remove_executor_venvs_method_was_called = True
        await continue_remove_executor_venv_method

    monkeypatch.setattr(agent, "_remove_executor_venvs", _remove_executor_venvs_dummy)

    # Mock the fact that we have no database and data.Notification().insert() would fail.
    async def insert_dummy(connection):
        pass

    monkeypatch.setattr(data.Notification, "insert", insert_dummy)

    # Push resources to the scheduler
    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent1,name=2]")

    executor1: ManagedExecutor = agent.executor_manager.register_managed_executor("agent1")

    resources = {
        rid1: make_resource_minimal(rid=rid1, values={"value": "r1_value"}, requires=[]),
        rid2: make_resource_minimal(rid=rid2, values={"value": "r2_value"}, requires=[rid1]),
    }
    await agent.scheduler._new_version(
        [
            ModelVersion(
                version=1,
                resources=resources,
                requires=make_requires(resources),
                undefined=set(),
                resource_sets={None: set(resources.keys())},
                partial=False,
            )
        ]
    )

    # Wait until rid1 is deploying
    await retry_limited_fast(lambda: rid1 in executor1.deploys, timeout=10)

    # Request removal of all agent venvs.
    # Assign task to a variable to prevent it from being garbage collected.
    remove_executor_venvs_task = asyncio.create_task(agent.remove_executor_venvs())  # noqa: F841
    await retry_limited_fast(lambda: agent.scheduler._deployment_suspended, timeout=10)

    # Verify that we are waiting for the ongoing deployment to finish, before removing the venvs.
    assert not _remove_executor_venvs_method_was_called

    # Finish the deployment of rid1
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)

    ## Now the venv removal should start
    await retry_limited_fast(lambda: _remove_executor_venvs_method_was_called, timeout=10)

    ## As long as the removal is in progress, no new deployments should be started
    assert not executor1.deploys

    # Finish the venv_removal
    continue_remove_executor_venv_method.set_result(None)

    # Now the deployment of rid2 should start
    await retry_limited_fast(lambda: rid2 in executor1.deploys, timeout=10)
    # Finish the deployment of rid2
    executor1.deploys[rid2].set_result(const.HandlerResourceState.deployed)


class BrokenDummyManager(executor.ExecutorManager[executor.Executor]):
    """
    A broken dummy ExecutorManager that fails on get_executor to test failure paths
    """

    async def get_executor(self, agent_name: str, agent_uri: str, code: typing.Collection[ModuleInstallSpec]) -> DummyExecutor:
        raise Exception()

    async def stop_for_agent(self, agent_name: str) -> list[DummyExecutor]:
        pass

    def get_environment_manager(self) -> None:
        return None

    async def stop_all_executors(self) -> list[DummyExecutor]:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor], timeout: float) -> None:
        pass


class BadTestAgent(Agent):
    """
    An agent (scheduler) that uses the broken dummy manager:
    """

    def __init__(
        self,
        environment: Optional[uuid.UUID] = None,
    ):
        super().__init__(environment)
        self.executor_manager = BrokenDummyManager()
        self.scheduler = TestScheduler(self.scheduler.environment, self.executor_manager, self.scheduler.client)


@pytest.fixture
async def bad_agent(environment, config):
    """
    Provide a new agent, with a scheduler that uses the broken dummy executor

    Allows testing without server, or executor
    """
    out = BadTestAgent(environment)
    await out.start_working()
    yield out
    await out.stop_working()


async def test_broken_executor_deploy(bad_agent: TestAgent, make_resource_minimal):
    """
    Ensure the simple deploy scenario works: 2 dependant resources
    """

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent1,name=2]"
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(rid1, values={"value": "a"}, requires=[]),
        ResourceIdStr(rid2): make_resource_minimal(rid2, values={"value": "a"}, requires=[rid1]),
    }

    await bad_agent.scheduler._new_version([model_version(version=1, resources=resources)])
    await retry_limited(utils.is_agent_done, timeout=5, scheduler=bad_agent.scheduler, agent_name="agent1")


async def test_deploy_blocked_state(agent: TestAgent, make_resource_minimal) -> None:
    """
    Verify topology changes that update recursive properties
    """

    # Shorthand variables for specific resources
    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent1,name=2]")
    rid3 = ResourceIdStr("test::Resource[agent1,name=3]")
    rid4 = ResourceIdStr("test::Resource[agent1,name=4]")
    rid5 = ResourceIdStr("test::Resource[agent1,name=5]")
    rid6 = ResourceIdStr("test::Resource[agent1,name=6]")
    rid7 = ResourceIdStr("test::Resource[agent1,name=7]")
    rid8 = ResourceIdStr("test::Resource[agent1,name=8]")
    rid9 = ResourceIdStr("test::Resource[agent1,name=9]")

    version = 1

    async def make_resources(rx_requires: list[list[ResourceIdStr]], undef: list[ResourceIdStr] = [rid1]) -> None:
        """
        Build as many resources as required, with subsequent ids

        :param rx_requires: the requires relation for each resources
        :param undef: rids of undefined resources

        hashes change every time
        """
        nonlocal version
        rids = (ResourceIdStr(f"test::Resource[agent1,name={i + 1}]") for i in itertools.count())
        resources = {
            rid: make_resource_minimal(
                rid,
                values={"value": version},
                requires=requires,
            )
            for rid, requires in zip(rids, rx_requires)
        }
        await agent.scheduler._new_version(
            [
                model_version(
                    version=version,
                    resources=resources,
                    undefined=undef,
                )
            ]
        )
        version += 1
        await retry_limited_fast(utils.is_agent_done, scheduler=agent.scheduler, agent_name="agent1")

    def is_deployed(rid: ResourceIdStr):
        assert agent.scheduler._state.resource_state[rid].last_deploy_result == DeployResult.DEPLOYED
        assert agent.scheduler._state.resource_state[rid].compliance == Compliance.COMPLIANT
        assert agent.scheduler._state.resource_state[rid].blocked == Blocked.NOT_BLOCKED

    def is_blocked(rid: ResourceIdStr):
        assert agent.scheduler._state.resource_state[rid].last_deploy_result == DeployResult.DEPLOYED, rid
        assert agent.scheduler._state.resource_state[rid].compliance == Compliance.HAS_UPDATE, rid
        assert agent.scheduler._state.resource_state[rid].blocked == Blocked.BLOCKED, rid

    def is_undefined(rid: ResourceIdStr):
        assert agent.scheduler._state.resource_state[rid].last_deploy_result == DeployResult.DEPLOYED
        assert agent.scheduler._state.resource_state[rid].compliance == Compliance.UNDEFINED
        assert agent.scheduler._state.resource_state[rid].blocked == Blocked.BLOCKED

    def is_new_undefined(rid: ResourceIdStr):
        assert agent.scheduler._state.resource_state[rid].last_deploy_result == DeployResult.NEW
        assert agent.scheduler._state.resource_state[rid].compliance == Compliance.UNDEFINED
        assert agent.scheduler._state.resource_state[rid].blocked == Blocked.BLOCKED

    def is_new_blocked(rid: ResourceIdStr):
        assert agent.scheduler._state.resource_state[rid].last_deploy_result == DeployResult.NEW
        assert agent.scheduler._state.resource_state[rid].compliance == Compliance.HAS_UPDATE
        assert agent.scheduler._state.resource_state[rid].blocked == Blocked.BLOCKED

    # Chain of 3
    # 3 -> 1 -> 2
    # 1 is undefined
    # 2 is free to deploy
    # 3 is blocked
    await make_resources(
        [
            [rid2],
            [],
            [rid1],
        ],
        undef=[rid1],
    )
    is_new_undefined(rid1)
    is_deployed(rid2)
    is_new_blocked(rid3)

    # reverse order
    # 3 <- 1 <- 2
    # 1 is undefined
    # 3 is free to deploy
    # 2 is blocked
    await make_resources(
        [[rid3], [rid1], []],
        undef=[rid1],
    )

    is_new_undefined(rid1)
    is_blocked(rid2)
    is_deployed(rid3)

    # diamond 1 < 2,3,4 < 5
    diamond = [[rid2, rid3, rid4], [rid5], [rid5], [rid5], [], []]
    # 1 is undefined
    # rest is free
    await make_resources(diamond, [rid1])
    is_deployed(rid2)
    is_deployed(rid3)
    is_deployed(rid4)
    is_deployed(rid5)
    is_deployed(rid6)
    is_new_undefined(rid1)

    # 5 is undefined
    # rest is blocked
    await make_resources(diamond, [rid5])

    is_blocked(rid2)
    is_blocked(rid3)
    is_blocked(rid4)
    is_undefined(rid5)
    is_deployed(rid6)
    is_new_blocked(rid1)

    # Unblock it all
    await make_resources(diamond, [])

    is_deployed(rid2)
    is_deployed(rid3)
    is_deployed(rid4)
    is_deployed(rid5)
    is_deployed(rid6)
    is_deployed(rid1)

    # Mixed graph
    # graph of 4 levels high, with 2 tops, where every node requires the two nodes below
    # layer 1: 1 -> 3,4  2->4,5
    # layer 2: 3 -> 6,7  4->7,8 ....
    # Layer n has n+1 nodes
    # Each node i in layer n requires i+n and i+n+1

    def make_node_layer(n):
        offset_row_below = int((n + 1) * (n + 2) / 2)
        nr_of_nodes = n + 1
        return [
            [
                ResourceIdStr(f"test::Resource[agent1,name={offset_row_below + i}]"),
                ResourceIdStr(f"test::Resource[agent1,name={offset_row_below + i + 1}]"),
            ]
            for i in range(nr_of_nodes)
        ]

    graph = [*make_node_layer(1), *make_node_layer(2), *make_node_layer(3), *[[]] * 5]

    # Deploy all
    await make_resources(graph, [])
    for rid in range(14):
        is_deployed(f"test::Resource[agent1,name={rid + 1}]")

    # Block 6,7 and 5, causing 1,2,3,4 to be blocked
    await make_resources(graph, [rid6, rid7, rid5])
    for rid in range(4):
        is_blocked(f"test::Resource[agent1,name={rid + 1}]")
    for rid in range(4, 7):
        is_undefined(f"test::Resource[agent1,name={rid + 1}]")
    for rid in range(7, 14):
        is_deployed(f"test::Resource[agent1,name={rid + 1}]")

    # Unblock 5 and 7
    # Block 9
    # 1,3 blocked due to 6
    # 2,5 blocked due to nine
    # 4,7,8 unblocked
    await make_resources(graph, [rid6, rid9])
    is_undefined(rid6)
    is_undefined(rid9)
    is_blocked(rid1)
    is_blocked(rid2)
    is_blocked(rid3)
    is_blocked(rid5)
    is_deployed(rid4)
    is_deployed(rid7)
    is_deployed(rid8)
    for rid in range(9, 14):
        is_deployed(f"test::Resource[agent1,name={rid + 1}]")

    # Also unblock 9
    # 1,3 blocked due to 6
    # 2,4,5,7,8 unblocked
    await make_resources(graph, [rid6])
    is_undefined(rid6)
    is_blocked(rid1)
    is_blocked(rid3)
    is_deployed(rid2)
    is_deployed(rid4)
    is_deployed(rid5)
    for rid in range(6, 14):
        is_deployed(f"test::Resource[agent1,name={rid + 1}]")

    # Drop half of it, deploy all
    graph = [*make_node_layer(1), *[[]] * 3]
    await make_resources(graph, [])
    for rid in range(5):
        is_deployed(f"test::Resource[agent1,name={rid + 1}]")
    for rid in range(5, 14):
        assert f"test::Resource[agent1,name={rid + 1}]" not in agent.scheduler._state.resource_state


async def test_deploy_orphaned(agent: TestAgent, make_resource_minimal) -> None:
    """
    Verify behavior when a deploy finishes for a since-orphaned resource.
    """
    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    executor1: ManagedExecutor = agent.executor_manager.register_managed_executor("agent1")

    resources: Mapping[ResourceIdStr, state.ResourceIntent] = {
        rid1: make_resource_minimal(rid1, values={"hello": "world"}, requires=[])
    }
    await agent.scheduler._new_version([model_version(version=1, resources=resources, requires={})])

    # wait until deploy starts, then hang it there
    await retry_limited_fast(lambda: rid1 in executor1.deploys)

    # now release a new version orphaning the resource, and another one putting it back right after
    await agent.scheduler._new_version(
        [
            model_version(version=2, resources={}, requires={}),
            model_version(version=3, resources=resources, requires={}),
        ]
    )

    # finish the deploy
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)

    # verify that the the resource is still considered undeployed, because it is considered new, i.e.
    # not the same as the one that just finished deploying
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        compliance=state.Compliance.HAS_UPDATE,
        last_deploy_result=state.DeployResult.NEW,
        blocked=state.Blocked.NOT_BLOCKED,
        last_deployed=None,
        last_deploy_compliant=None,
    )

    # wait for and finish the second deploy
    await retry_limited_fast(lambda: rid1 in executor1.deploys)
    executor1.deploys[rid1].set_result(const.HandlerResourceState.deployed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)
    assert agent.scheduler._state.resource_state[rid1] == state.ResourceState(
        compliance=state.Compliance.COMPLIANT,
        last_deploy_result=state.DeployResult.DEPLOYED,
        blocked=state.Blocked.NOT_BLOCKED,
        last_deployed=agent.scheduler._state.resource_state[rid1].last_deployed,  # ignore
        last_deploy_compliant=True,
    )


async def test_multiple_versions_intent_changes(agent: TestAgent, make_resource_minimal) -> None:
    """
    Verify the behavior of _new_version (without inspecting task behavior) when multiple versions are processed
    in one go (e.g. when the scheduler has been paused or when versions come in fast after one another).
    """

    all_models: list[ModelVersion] = []

    def model(
        resources: Mapping[ResourceIdStr, ResourceDetails],
        *,
        requires: Optional[Mapping[ResourceIdStr, Set[ResourceIdStr]]] = None,
        undefined: Optional[Set[ResourceIdStr]] = None,
    ) -> ModelVersion:
        requires = requires if requires is not None else {}
        undefined = undefined if undefined is not None else set()
        result: ModelVersion = model_version(
            version=len(all_models) + 1,
            resources=resources,
            requires=requires,
            undefined=undefined,
        )
        all_models.append(result)
        return result

    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent1,name=2]")
    rid3 = ResourceIdStr("test::Resource[agent1,name=3]")
    rid4 = ResourceIdStr("test::Resource[agent1,name=4]")
    rid5 = ResourceIdStr("test::Resource[agent1,name=5]")
    rid6 = ResourceIdStr("test::Resource[agent1,name=6]")

    baseline_resources: Mapping[ResourceIdStr, state.ResourceIntent] = {
        rid: make_resource_minimal(rid, values={"hello": "world"}, requires=[]) for rid in (rid1, rid2, rid3)
    }

    scheduler: ResourceScheduler = agent.scheduler

    async def restore_baseline_state() -> None:
        """
        Re-release baseline model, wait for stable state (all executions done, all resources compliant),
        then assert expected baseline state.
        """
        await agent.start_working()
        await scheduler._new_version([model(baseline_resources)])
        await retry_limited_fast(lambda: scheduler._work.agent_queues._agent_queues["agent1"]._unfinished_tasks == 0)
        assert scheduler._state.intent == baseline_resources
        assert len(scheduler._state.resource_state) == 3
        for rid in (rid1, rid2, rid3):
            assert len(scheduler._state.requires[rid]) == 0
            assert len(scheduler._state.requires.provides_view().get(rid, set())) == 0
            assert scheduler._state.resource_state[rid].compliance is Compliance.COMPLIANT
            assert scheduler._state.resource_state[rid].last_deploy_result is DeployResult.DEPLOYED
            assert scheduler._state.resource_state[rid].blocked is Blocked.NOT_BLOCKED
        assert len(scheduler._state.dirty) == 0
        # Make sure that _new_version() calls done by the test case do not get deployed to prevent races on state assertions.
        await agent.stop_working()

    await restore_baseline_state()

    # release three new versions, each updating a different resource
    # also add some new resources, one in each version
    await scheduler._new_version(
        [
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "values"}, requires=[]),
                    rid2: all_models[-1].resources[rid2],
                    rid3: all_models[-1].resources[rid3],
                    rid4: make_resource_minimal(rid4, values={"new": "values"}, requires=[]),
                }
            ),
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                    rid2: make_resource_minimal(rid2, values={"changed": "values"}, requires=[]),
                    rid3: all_models[-1].resources[rid3],
                    rid4: all_models[-1].resources[rid4],
                    rid5: make_resource_minimal(rid5, values={"new": "values"}, requires=[]),
                }
            ),
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                    rid2: all_models[-1].resources[rid2],
                    rid3: make_resource_minimal(rid3, values={"changed": "values"}, requires=[]),
                    rid4: all_models[-1].resources[rid4],
                    rid5: make_resource_minimal(rid5, values={"update after new": "values"}, requires=[]),
                    rid6: make_resource_minimal(rid6, values={"new": "values"}, requires=[]),
                }
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    for rid in (rid1, rid2, rid3):
        assert scheduler._state.resource_state[rid].compliance is Compliance.HAS_UPDATE
        assert scheduler._state.resource_state[rid].last_deploy_result is DeployResult.DEPLOYED
        assert scheduler._state.resource_state[rid].blocked is Blocked.NOT_BLOCKED
    for rid in (rid4, rid5, rid6):
        assert scheduler._state.resource_state[rid].compliance is Compliance.HAS_UPDATE
        assert scheduler._state.resource_state[rid].last_deploy_result is DeployResult.NEW
        assert scheduler._state.resource_state[rid].blocked is Blocked.NOT_BLOCKED

    await restore_baseline_state()

    # release three new versions, each deleting a resource, including one that was added in an earlier version
    await scheduler._new_version(
        [
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                    rid2: all_models[-1].resources[rid2],
                    # no rid3
                    rid4: make_resource_minimal(rid4, values={"new": "values"}, requires=[]),
                    rid5: make_resource_minimal(rid5, values={"new": "values"}, requires=[]),
                }
            ),
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                    # no rid2
                    # no rid4
                    rid5: all_models[-1].resources[rid5],
                }
            ),
            model(
                {
                    # no rid1
                    rid5: all_models[-1].resources[rid5],
                }
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    assert scheduler._state.resource_state[rid5].compliance is Compliance.HAS_UPDATE
    assert scheduler._state.resource_state[rid5].last_deploy_result is DeployResult.NEW
    assert scheduler._state.resource_state[rid5].blocked is Blocked.NOT_BLOCKED

    await restore_baseline_state()

    # Resource becomes undefined
    await scheduler._new_version(
        [
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                    rid2: all_models[-1].resources[rid2],
                    rid4: make_resource_minimal(rid4, values={"new": "unknown"}, requires=[]),
                },
                undefined={rid4},
            ),
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "unknown"}, requires=[]),
                    rid2: all_models[-1].resources[rid2],
                    rid4: make_resource_minimal(rid4, values={"new": "unknown"}, requires=[]),
                },
                undefined={rid1, rid4},
            ),
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "unknown"}, requires=[]),
                    rid2: make_resource_minimal(rid2, values={"changed": "unknown"}, requires=[]),
                    rid4: make_resource_minimal(rid4, values={"new": "unknown"}, requires=[]),
                },
                undefined={rid1, rid2, rid4},
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    for rid in (rid1, rid2, rid4):
        assert scheduler._state.resource_state[rid].compliance is Compliance.UNDEFINED
        assert (
            scheduler._state.resource_state[rid].last_deploy_result is DeployResult.DEPLOYED
            if rid != rid4
            else DeployResult.NEW
        )
        assert scheduler._state.resource_state[rid].blocked is Blocked.BLOCKED

    await restore_baseline_state()

    # Resource becomes defined

    # Make sure resources are initialized as undefined
    await scheduler._new_version(
        [
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "unknown"}, requires=[]),
                    rid2: make_resource_minimal(rid2, values={"changed": "unknown"}, requires=[]),
                    rid3: make_resource_minimal(rid3, values={"changed": "unknown"}, requires=[]),
                },
                undefined={rid1, rid2, rid3},
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    for rid in (rid1, rid2, rid3):
        assert scheduler._state.resource_state[rid].compliance is Compliance.UNDEFINED
        assert scheduler._state.resource_state[rid].last_deploy_result is DeployResult.DEPLOYED
        assert scheduler._state.resource_state[rid].blocked is Blocked.BLOCKED

    await scheduler._new_version(
        [
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                    rid2: make_resource_minimal(rid2, values={"changed": "unknown"}, requires=[]),
                    rid3: make_resource_minimal(rid3, values={"changed": "unknown"}, requires=[]),
                },
                undefined={rid2, rid3},
            ),
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                    rid2: all_models[-1].resources[rid2],
                    rid3: make_resource_minimal(rid3, values={"changed": "unknown"}, requires=[]),
                },
                undefined={rid3},
            ),
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                    rid2: all_models[-1].resources[rid2],
                    rid3: all_models[-1].resources[rid3],
                },
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    for rid in (rid1, rid2, rid3):
        assert scheduler._state.resource_state[rid].compliance is Compliance.HAS_UPDATE
        assert scheduler._state.resource_state[rid].last_deploy_result is DeployResult.DEPLOYED
        assert scheduler._state.resource_state[rid].blocked is Blocked.NOT_BLOCKED

    await restore_baseline_state()

    # Resource becomes undefined, defined and then undefined again
    await scheduler._new_version(
        [
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "unknown"}, requires=[]),
                },
                undefined={rid1},
            ),
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                },
            ),
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "unknown"}, requires=[]),
                },
                undefined={rid1},
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    assert scheduler._state.resource_state[rid1].compliance is Compliance.UNDEFINED
    assert scheduler._state.resource_state[rid1].last_deploy_result is DeployResult.DEPLOYED
    assert scheduler._state.resource_state[rid1].blocked is Blocked.BLOCKED

    await restore_baseline_state()

    # Resource becomes defined, undefined and then defined again

    # Make sure resources are initialized as undefined
    await scheduler._new_version(
        [
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "unknown"}, requires=[]),
                },
                undefined={rid1},
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    assert scheduler._state.resource_state[rid1].compliance is Compliance.UNDEFINED
    assert scheduler._state.resource_state[rid1].last_deploy_result is DeployResult.DEPLOYED
    assert scheduler._state.resource_state[rid1].blocked is Blocked.BLOCKED

    await scheduler._new_version(
        [
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                },
            ),
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "unknown"}, requires=[]),
                },
                undefined={rid1},
            ),
            model(
                {
                    rid1: all_models[-1].resources[rid1],
                },
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    assert scheduler._state.resource_state[rid1].compliance is Compliance.HAS_UPDATE
    assert scheduler._state.resource_state[rid1].last_deploy_result is DeployResult.DEPLOYED
    assert scheduler._state.resource_state[rid1].blocked is Blocked.NOT_BLOCKED

    await restore_baseline_state()

    # Verify updates of requires
    await scheduler._new_version(
        [
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "value"}, requires=[rid2]),
                    rid2: make_resource_minimal(rid2, values={"changed": "value"}, requires=[rid3]),
                    rid3: make_resource_minimal(rid3, values={"changed": "value"}, requires=[]),
                },
                requires={
                    rid1: {rid2},
                    rid2: {rid3},
                    rid3: set(),
                },
            ),
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "value"}, requires=[rid2]),
                    rid2: make_resource_minimal(rid2, values={"changed": "value"}, requires=[]),
                    rid3: make_resource_minimal(rid3, values={"changed": "value"}, requires=[rid2]),
                },
                requires={
                    rid1: {rid2},
                    rid2: set(),
                    rid3: {rid2},
                },
            ),
            model(
                {
                    rid1: make_resource_minimal(rid1, values={"changed": "value"}, requires=[]),
                    rid2: make_resource_minimal(rid2, values={"changed": "value"}, requires=[rid1]),
                    rid3: make_resource_minimal(rid3, values={"changed": "value"}, requires=[rid2]),
                },
                requires={
                    rid1: set(),
                    rid2: {rid1},
                    rid3: {rid2},
                },
            ),
        ]
    )
    assert scheduler._state.intent == all_models[-1].resources
    for rid in (rid1, rid2, rid3):
        assert scheduler._state.resource_state[rid].compliance is Compliance.HAS_UPDATE
        assert scheduler._state.resource_state[rid].last_deploy_result is DeployResult.DEPLOYED
        assert scheduler._state.resource_state[rid].blocked is Blocked.NOT_BLOCKED
    assert scheduler._state.requires[rid1] == set()
    assert scheduler._state.requires[rid2] == {rid1}
    assert scheduler._state.requires[rid3] == {rid2}


async def test_transient_deploy(agent: TestAgent, make_resource_minimal, caplog) -> None:
    """
    Verify the behavior of TEMPORARILY_BLOCKED resources when it comes to deploys:
    1. should not be included in normal deploys
    2. should be included in repairs (#8423, until #8580 is implemented)
    3. should be included when explicitly requested by deploy_resource()
    4. should produce appropriate warning when the newly triggered (by 2/3) deploy behaves unexpectedly
    """
    rid1 = ResourceIdStr("test::Resource[agent1,name=1]")
    rid2 = ResourceIdStr("test::Resource[agent1,name=2]")
    executor: ManagedExecutor = agent.executor_manager.register_managed_executor("agent1")

    # set up rid1 to depend on rid2
    resources: Mapping[ResourceIdStr, state.ResourceIntent] = {
        rid1: make_resource_minimal(rid1, values={"hello": "world 1"}, requires=[rid2]),
        rid2: make_resource_minimal(rid2, values={"hello": "world 2"}, requires=[]),
    }
    version: int = 42
    await agent.scheduler._new_version([model_version(version=version, resources=resources, requires={rid1: {rid2}})])

    # wait until deploy starts, then fail r2 and make r1 skip for dependencies
    await retry_limited_fast(lambda: rid2 in executor.deploys)
    executor.deploys[rid2].set_result(const.HandlerResourceState.failed)
    await retry_limited_fast(lambda: rid1 in executor.deploys)
    executor.deploys[rid1].set_result(const.HandlerResourceState.skipped_for_dependency)

    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)

    scheduler: ResourceScheduler = agent.scheduler

    assert scheduler._state.resource_state[rid2].compliance is Compliance.NON_COMPLIANT
    assert scheduler._state.resource_state[rid1].compliance is Compliance.NON_COMPLIANT
    assert scheduler._state.resource_state[rid2].blocked is Blocked.NOT_BLOCKED
    assert scheduler._state.resource_state[rid1].blocked is Blocked.TEMPORARILY_BLOCKED

    # trigger deploy: verify only r2 gets scheduled, make it return the same result as before
    agent.executor_manager.reset_executor_counters()
    await scheduler.deploy(reason="Test: triggering full deploy")
    await retry_limited_fast(lambda: rid2 in executor.deploys)
    executor.deploys[rid2].set_result(const.HandlerResourceState.failed)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)
    assert agent.executor_manager.executors["agent1"].execute_count == 1
    assert len(scheduler._work._waiting) == 0
    assert len(scheduler._work.agent_queues.queued()) == 0
    assert len(scheduler._work.agent_queues._in_progress) == 0

    agent.executor_manager.reset_executor_counters()
    await scheduler.repair(reason="Test: triggering repair")
    # trigger repair: verify both resources get scheduled, make them return the same result as before
    await retry_limited_fast(lambda: rid2 in executor.deploys)
    executor.deploys[rid2].set_result(const.HandlerResourceState.failed)
    await retry_limited_fast(lambda: rid1 in executor.deploys)
    executor.deploys[rid1].set_result(const.HandlerResourceState.skipped_for_dependency)
    await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)

    def get_resource_action_logs(caplog) -> list[logging.LogRecord]:
        return [record for record in caplog.records if record.name.startswith("inmanta.resource_action")]

    # verify no log is emitted if it skips again as expected
    agent.executor_manager.reset_executor_counters()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        await scheduler.deploy_resource(
            rid1,
            reason="Test: deploying r1, skipping for dependencies",
            priority=TaskPriority.USER_DEPLOY,
        )
        await retry_limited_fast(lambda: rid1 in executor.deploys)
        executor.deploys[rid1].set_result(const.HandlerResourceState.skipped_for_dependency)
        await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)

        assert len(get_resource_action_logs(caplog)) == 0
        assert len(scheduler.state_update_manager.deploys[rid1].messages) == 0

    # verify log message is as expected if rid1 suddenly succeeds
    agent.executor_manager.reset_executor_counters()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        # trigger another deploy for rid1, this time make it succeed
        await scheduler.deploy_resource(
            rid1,
            reason="Test: deploying r1",
            priority=TaskPriority.USER_DEPLOY,
        )
        await retry_limited_fast(lambda: rid1 in executor.deploys)
        executor.deploys[rid1].set_result(const.HandlerResourceState.deployed)

        await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)

        # verify that it is logged to the scheduler log under a resource action logger
        resource_action_logs = get_resource_action_logs(caplog)
        assert len(resource_action_logs) == 1
        record: logging.LogRecord = resource_action_logs[0]
        assert record.levelno == logging.WARNING
        assert record.name == "inmanta.resource_action.agent1"
        expected_message: str = (
            f"Resource {rid1} was expected to skip for dependencies but it deployed successfully."
            " The handler for this resource raised a SkipResourceForDependencies exception in a previous execution, indicating"
            " that it would only be able to progress once all requires reached a deployed state. Some requires"
            f" ({rid2}: failed) are still in a non-deployed state, therefore it was assumed that a new deploy attempt would"
            " have no effect. This indicates incorrect usage of the exception, and it will lead to resources getting stuck in"
            " the skipped state. While this can be worked around by triggering a repair for now, that may not work in the"
            " future. Please check your handler implementation, and make sure to raise the generic SkipResource rather than"
            " SkipResourceForDependencies if you wish to skip a deploy for any other reason than to wait until all requires"
            " are in a good state. Please contact support if you believe your handler implementation is correct after all."
        )
        assert record.message == f"resource {rid1},v={version}: {expected_message}"
        # verify that it is also sent to the database
        assert len(scheduler.state_update_manager.deploys[rid1].messages) == 1
        assert scheduler.state_update_manager.deploys[rid1].messages[0].msg == expected_message

    assert scheduler._state.resource_state[rid2].compliance is Compliance.NON_COMPLIANT
    assert scheduler._state.resource_state[rid1].compliance is Compliance.COMPLIANT
    assert scheduler._state.resource_state[rid2].blocked is Blocked.NOT_BLOCKED
    # verify that scheduler recognized that it is no longer blocked
    assert scheduler._state.resource_state[rid1].blocked is Blocked.NOT_BLOCKED

    # verify no log is emitted if it succeeds again, or for other transitions, e.g. success -> failed -> success
    agent.executor_manager.reset_executor_counters()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        await scheduler.deploy_resource(
            rid1,
            reason="Test: deploying r1 for success",
            priority=TaskPriority.USER_DEPLOY,
        )
        await retry_limited_fast(lambda: rid1 in executor.deploys)
        executor.deploys[rid1].set_result(const.HandlerResourceState.deployed)
        await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)

        await scheduler.deploy_resource(
            rid1,
            reason="Test: deploying r1 for failure",
            priority=TaskPriority.USER_DEPLOY,
        )
        await retry_limited_fast(lambda: rid1 in executor.deploys)
        executor.deploys[rid1].set_result(const.HandlerResourceState.failed)
        await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 2)

        await scheduler.deploy_resource(
            rid1,
            reason="Test: deploying r1 for success",
            priority=TaskPriority.USER_DEPLOY,
        )
        await retry_limited_fast(lambda: rid1 in executor.deploys)
        executor.deploys[rid1].set_result(const.HandlerResourceState.deployed)
        await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 3)

        assert len(get_resource_action_logs(caplog)) == 0
        assert len(scheduler.state_update_manager.deploys[rid1].messages) == 0

    # verify no log message is emitted for a valid recovery
    agent.executor_manager.reset_executor_counters()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        # set up initial state: make r1 skip for dependencies again
        await scheduler.deploy_resource(
            rid1,
            reason="Test: deploying r1 for success",
            priority=TaskPriority.USER_DEPLOY,
        )
        await retry_limited_fast(lambda: rid1 in executor.deploys)
        executor.deploys[rid1].set_result(const.HandlerResourceState.skipped_for_dependency)

        await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)

        # verify initial state
        assert scheduler._state.resource_state[rid2].compliance is Compliance.NON_COMPLIANT
        assert scheduler._state.resource_state[rid1].compliance is Compliance.NON_COMPLIANT
        assert scheduler._state.resource_state[rid2].blocked is Blocked.NOT_BLOCKED
        assert scheduler._state.resource_state[rid1].blocked is Blocked.TEMPORARILY_BLOCKED

        # deploy r2 successfully
        await scheduler.deploy_resource(
            rid2,
            reason="Test: deploying r2 for success",
            priority=TaskPriority.USER_DEPLOY,
        )
        await retry_limited_fast(lambda: rid2 in executor.deploys)
        executor.deploys[rid2].set_result(const.HandlerResourceState.deployed)

        # r1 will get a recovery event, make it succeed
        await retry_limited_fast(lambda: rid1 in executor.deploys)
        executor.deploys[rid1].set_result(const.HandlerResourceState.deployed)

        await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 3)

        # verify new state
        assert scheduler._state.resource_state[rid2].compliance is Compliance.COMPLIANT
        assert scheduler._state.resource_state[rid1].compliance is Compliance.COMPLIANT
        assert scheduler._state.resource_state[rid2].blocked is Blocked.NOT_BLOCKED
        assert scheduler._state.resource_state[rid1].blocked is Blocked.NOT_BLOCKED

        # this is a valid recovery, verify that no log message was emitted
        assert len(get_resource_action_logs(caplog)) == 0
        assert len(scheduler.state_update_manager.deploys[rid1].messages) == 0
        assert len(scheduler.state_update_manager.deploys[rid2].messages) == 0

    # verify log message is as expected if r1 succeeds while in TEMPORARILY_BLOCKED state but all resources are in a good state
    # (scheduler bug)
    agent.executor_manager.reset_executor_counters()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert scheduler._state.resource_state[rid2].compliance is Compliance.COMPLIANT
        scheduler._state.resource_state[rid1].blocked = Blocked.TEMPORARILY_BLOCKED

        # deploy r1 successfully
        await scheduler.deploy_resource(
            rid1,
            reason="Test: deploying r1",
            priority=TaskPriority.USER_DEPLOY,
        )
        await retry_limited_fast(lambda: rid1 in executor.deploys)
        executor.deploys[rid1].set_result(const.HandlerResourceState.deployed)

        await retry_limited_fast(lambda: agent.executor_manager.executors["agent1"].execute_count == 1)

        # verify that the warning message now implies a scheduler bug rather than a handler bug
        resource_action_logs = get_resource_action_logs(caplog)
        assert len(resource_action_logs) == 1
        record: logging.LogRecord = resource_action_logs[0]
        assert record.levelno == logging.WARNING
        assert record.name == "inmanta.resource_action.agent1"
        expected_message: str = (
            f"Inconsistent internal state for resource {rid1}. The inmanta resource scheduler assumed it was still blocked,"
            " pending a successful deploy of at least one of its requires. However, all dependencies are already in a deployed"
            " state. This was expected to be impossible and it indicates a (non-critical) bug in the inmanta resource"
            " scheduler. Please report this bug. In the meantime, if you encounter any resources stuck in the skipped"
            " state, trigger a repair as a workaround to force a deploy."
        )
        assert record.message == f"resource {rid1},v={version}: {expected_message}"
        assert len(scheduler.state_update_manager.deploys[rid1].messages) == 1
        assert scheduler.state_update_manager.deploys[rid1].messages[0].msg == expected_message

    assert scheduler._state.resource_state[rid2].compliance is Compliance.COMPLIANT
    assert scheduler._state.resource_state[rid1].compliance is Compliance.COMPLIANT
    assert scheduler._state.resource_state[rid2].blocked is Blocked.NOT_BLOCKED
    # verify that scheduler recognized that it is no longer blocked
    assert scheduler._state.resource_state[rid1].blocked is Blocked.NOT_BLOCKED
