"""
    Copyright 2023 Inmanta

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

from inmanta.agent import Agent
from inmanta.const import AgentTriggerMethod

LOGGER = logging.getLogger("test")


async def test_6475_deploy_with_failure_masking(server, agent: Agent, environment, resource_container, clienthelper, client):
    """
    Consider:

    a version v1 is deploying
    a new version v2 is released
    resource a[k=x],v=2 is marked as deployed for known good state
    resource a[k=x],v=1 fails

    Now, the good state of v2 has masked the bad state of v1.
    """

    async def make_version() -> int:
        version = await clienthelper.get_version()
        rvid = f"test::Wait[agent1,key=key1],v={version}"
        rvid2 = f"test::Resource[agent1,key=key2],v={version}"

        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": rvid,
                "send_event": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value1",
                "id": rvid2,
                "send_event": False,
                "purged": False,
                "requires": [rvid],
            },
        ]
        await clienthelper.put_version_simple(resources, version)
        return version

    v1 = await make_version()

    assert resource_container.Provider.readcount("agent1", "key2") == 0
    # deploy resource: success
    result = await client.release_version(environment, v1, True)
    assert result.code == 200
    await resource_container.wait_for_done_with_waiters(client, environment, v1, 2)

    # start deploy but hang
    # Make it fail
    assert resource_container.Provider.readcount("agent1", "key2") == 1
    resource_container.Provider.set_fail("agent1", "key2", 1)
    result = await client.deploy(environment)
    assert result.code == 200

    # add new version
    v2 = await make_version()
    result = await client.release_version(environment, v2, False)
    assert result.code == 200

    # fail deploy
    def make_waiter(nr_of_deploys):
        async def wait_condition():
            result = await client.resource_logs(environment, "test::Resource[agent1,key=key2]", filter={"action": ["deploy"]})
            assert result.code == 200
            end_lines = [line for line in result.result["data"] if "End run" in line.get("msg", "")]
            LOGGER.info("Deploys done: %s", end_lines)
            return len(end_lines) < nr_of_deploys

        return wait_condition

    await resource_container.wait_for_condition_with_waiters(make_waiter(2))
    assert resource_container.Provider.readcount("agent1", "key2") == 2

    # increment should contain the failed resource
    sid = agent.sessionid
    result = await agent._client.get_resources_for_agent(environment, "agent1", incremental_deploy=True, sid=sid)
    assert result.code == 200, result.result
    assert len(result.result["resources"]) == 1
    assert result.result["resources"][0]["resource_id"] == "test::Resource[agent1,key=key2]"

    result = await client.deploy(environment, agent_trigger_method=AgentTriggerMethod.push_incremental_deploy)
    assert result.code == 200
    await resource_container.wait_for_condition_with_waiters(make_waiter(3))

    result = await client.resource_logs(environment, "test::Resource[agent1,key=key2]", filter={"action": ["deploy"]})
    assert result.code == 200
    for line in result.result["data"]:
        LOGGER.info("Final logs: %s", line["msg"])

    # 2 times for v1
    # 1 time for v2
    assert resource_container.Provider.readcount("agent1", "key2") == 3
