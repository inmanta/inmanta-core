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
async def auto_start_agent(server_config):
    return False

async def test_basics(agent, resource_container, clienthelper, client, environment):
    """
    This tests make sure the resource scheduler is working as expected for these parts:
        - Construction of initial model state
        - Retrieval of data when a new version is released
    """

    env_id = environment
    scheduler = agent.scheduler

    resource_container.Provider.reset()
    # set the deploy environment
    resource_container.Provider.set("agent1", "key", "value")
    resource_container.Provider.set("agent2", "key", "value")
    resource_container.Provider.set("agent3", "key", "value")

    async def make_version(is_different=False):
        """

        :param is_different: make the standard version or one with a change
        :return:
        """
        version = await clienthelper.get_version()
        resources = []
        for agent in ["agent1", "agent2", "agent3"]:
            resources.extend(
                [
                    {
                        "key": "key",
                        "value": "value",
                        "id": "test::Resource[%s,key=key],v=%d" % (agent, version),
                        "requires": ["test::Resource[%s,key=key3],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                    },
                    {
                        "key": "key2",
                        "value": "value",
                        "id": "test::Resource[%s,key=key2],v=%d" % (agent, version),
                        "requires": ["test::Resource[%s,key=key],v=%d" % (agent, version)],
                        "purged": not is_different,
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
                            "test::Resource[%s,key=key],v=%d" % (agent, version),
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

    await check_scheduler_state(resources, scheduler)

    await clienthelper.wait_for_deployed(version1)

    await resource_action_consistency_check()

    version1, resources = await make_version(True)
    result = await client.put_version(
        tid=env_id, version=version1, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    # deploy and wait until one is ready
    result = await client.release_version(env_id, version1, push=False)
    assert result.code == 200

    # all deployed!
    async def done():
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        # {'by_state': {'available': 3, 'cancelled': 0, 'deployed': 12, 'deploying': 0, 'failed': 0, 'skipped': 0,
        #               'skipped_for_undefined': 0, 'unavailable': 0, 'undefined': 0}, 'total': 15}
        total = summary["total"]
        deployed = summary["by_state"]["deployed"]
        return total == deployed

    await retry_limited(done, 10)

    await check_scheduler_state(resources, scheduler)

    await resource_action_consistency_check()


async def check_scheduler_state(resources, scheduler):
    # State consistency check
    for resource in resources:
        id_without_version, _, _ = resource["id"].partition(",v=")
        assert id_without_version in scheduler._state.resources
        expected_resource_attributes = dict(resource)
        current_attributes = dict(scheduler._state.resources[id_without_version].attributes)
        # Id's have different versions
        del expected_resource_attributes["id"]
        del current_attributes["id"]
        new_requires = []
        for require in expected_resource_attributes["requires"]:
            require_without_version, _, _ = require.partition(",v=")
            new_requires.append(require_without_version)
        expected_resource_attributes["requires"] = new_requires
        assert current_attributes == expected_resource_attributes
        # This resource has no requirements
        if id_without_version not in scheduler._state.requires._primary:
            assert expected_resource_attributes["requires"] == []
        else:
            assert scheduler._state.requires._primary[id_without_version] == set(expected_resource_attributes["requires"])

