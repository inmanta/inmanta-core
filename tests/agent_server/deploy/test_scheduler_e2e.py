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

import asyncio
import logging

import pytest

import utils
from agent_server.deploy.scheduler_test_util import DummyCodeManager
from inmanta import config
from inmanta.agent.agent_new import Agent
from inmanta.agent.in_process_executor import InProcessExecutorManager
from inmanta.config import Config
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.util import get_compiler_version, groupby
from utils import resource_action_consistency_check, retry_limited

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
async def agent(server, environment):
    """Construct an agent that can execute using the resource container"""
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    a = Agent(environment)

    a.scheduler._executor_manager = InProcessExecutorManager(
        environment, a._client, asyncio.get_event_loop(), logger, a.thread_pool, a._storage["code"], a._storage["env"], False
    )
    a.scheduler._code_manager = DummyCodeManager(a._client)

    await a.start()
    # Server doesn
    await a.start_working()

    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


async def test_basics(agent, resource_container, clienthelper, client, environment):
    """
    This tests make sure the resource scheduler is working as expected for these parts:
        - Construction of initial model state
        - Retrieval of data when a new version is released
    """

    env_id = environment

    # First part - test the ResourceScheduler (retrieval of data from DB)
    Config.set("config", "agent-deploy-interval", "100")
    Config.set("server", "new-resource-scheduler", "True")

    resource_container.Provider.reset()
    # set the deploy environment
    resource_container.Provider.set("agent1", "key", "value")
    resource_container.Provider.set("agent2", "key", "value")
    resource_container.Provider.set("agent3", "key", "value")

    async def make_version():
        version = await clienthelper.get_version()
        resources = []
        for agent in ["agent1", "agent2", "agent3"]:
            resources.extend(
                [
                    {
                        "key": "key",
                        "value": "value",
                        "id": "test::Wait[%s,key=key],v=%d" % (agent, version),
                        "requires": ["test::Resource[%s,key=key3],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                    },
                    {
                        "key": "key2",
                        "value": "value",
                        "id": "test::Resource[%s,key=key2],v=%d" % (agent, version),
                        "requires": ["test::Wait[%s,key=key],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                    },
                    {
                        "key": "key3",
                        "value": "value",
                        "id": "test::Resource[%s,key=key3],v=%d" % (agent, version),
                        "requires": [],
                        "purged": False,
                        "send_event": False,
                    },
                    {
                        "key": "key4",
                        "value": "value",
                        "id": "test::Resource[%s,key=key4],v=%d" % (agent, version),
                        "requires": ["test::Resource[%s,key=key3],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                    },
                    {
                        "key": "key5",
                        "value": "value",
                        "id": "test::Resource[%s,key=key5],v=%d" % (agent, version),
                        "requires": [
                            "test::Resource[%s,key=key4],v=%d" % (agent, version),
                            "test::Wait[%s,key=key],v=%d" % (agent, version),
                        ],
                        "purged": False,
                        "send_event": False,
                    },
                ]
            )
        return version, resources

    async def wait_for_resources(version: int, n: int) -> None:
        result = await client.get_version(env_id, version)
        assert result.code == 200

        def done_per_agent(result):
            done = [x for x in result.result["resources"] if x["status"] == "deployed"]
            peragent = groupby(done, lambda x: x["agent"])
            return {agent: len([x for x in grp]) for agent, grp in peragent}

        def mindone(result):
            alllist = done_per_agent(result).values()
            if len(alllist) == 0:
                return 0
            return min(alllist)

        async def done():
            result = await client.get_version(env_id, version)
            return mindone(result) < n

        await retry_limited(done, 10)

    logger.info("setup done")

    version1, resources = await make_version()
    result = await client.put_version(
        tid=env_id, version=version1, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = await client.release_version(env_id, version1, push=False)
    assert result.code == 200

    logger.info("first version released")
    # timeout on single thread!
    await wait_for_resources(version1, n=1)

    await resource_container.wait_for_done_with_waiters(client, env_id, version1)

    await resource_action_consistency_check()
