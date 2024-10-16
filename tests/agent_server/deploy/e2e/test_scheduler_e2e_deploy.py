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

import logging

from agent_server.deploy.scheduler_test_util import wait_full_success
from inmanta import const
from inmanta.const import AgentAction
from inmanta.deploy.state import DeploymentResult
from utils import resource_action_consistency_check

logger = logging.getLogger(__name__)


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
    resource_container.Provider.set_fail("agent1", "key3", 2)

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

    async def make_marker_version() -> int:
        version = await clienthelper.get_version()
        resources = [
            {
                "key": "key",
                "value": "value",
                "id": "test::Resource[agentx,key=key],v=%d" % version,
                "requires": [],
                "purged": False,
                "send_event": False,
            },
        ]
        await clienthelper.put_version_simple(version=version, resources=resources)
        return version

    logger.info("setup done")

    version1, resources = await make_version()
    await clienthelper.put_version_simple(version=version1, resources=resources)

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = await client.release_version(env_id, version1)
    assert result.code == 200

    await clienthelper.wait_for_released(version1)

    logger.info("first version released")

    await clienthelper.wait_for_deployed()

    await check_scheduler_state(resources, scheduler)
    await resource_action_consistency_check()
    await check_server_state_vs_scheduler_state(client, environment, scheduler)

    # check states
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    # {'by_state': {'available': 3, 'cancelled': 0, 'deployed': 12, 'deploying': 0, 'failed': 0, 'skipped': 0,
    #               'skipped_for_undefined': 0, 'unavailable': 0, 'undefined': 0}, 'total': 15}
    print(summary)
    assert 10 == summary["by_state"]["deployed"]
    assert 1 == summary["by_state"]["failed"]
    assert 4 == summary["by_state"]["skipped"]

    version1, resources = await make_version(True)
    await clienthelper.put_version_simple(version=version1, resources=resources)
    await make_marker_version()

    # deploy and wait until one is ready
    result = await client.release_version(env_id, version1, push=False)
    await clienthelper.wait_for_released(version1)

    await clienthelper.wait_for_deployed()

    await check_scheduler_state(resources, scheduler)

    await resource_action_consistency_check()
    assert resource_container.Provider.readcount("agentx", "key") == 0

    # deploy trigger
    await client.deploy(environment, agent_trigger_method=const.AgentTriggerMethod.push_incremental_deploy)

    await wait_full_success(client, environment)

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200
    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.unpause.value)
    assert result.code == 200


async def check_server_state_vs_scheduler_state(client, environment, scheduler):
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    for item in result.result["data"]:
        the_id = item["resource_id"]
        status = item["status"]
        state = scheduler._state.resource_state[the_id]

        state_correspondence = {
            "deployed": DeploymentResult.DEPLOYED,
            "skipped": DeploymentResult.FAILED,
            "failed": DeploymentResult.FAILED,
        }

        assert state_correspondence[status] == state.deployment_result


async def check_scheduler_state(resources, scheduler):
    # State consistency check
    for resource in resources:
        id_without_version, _, _ = resource["id"].partition(",v=")
        assert id_without_version in scheduler._state.resources
        expected_resource_attributes = dict(resource)
        current_attributes = dict(scheduler._state.resources[id_without_version].attributes)
        # scheduler's attributes does not have the injected id
        del expected_resource_attributes["id"]
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
