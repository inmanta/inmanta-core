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

import datetime
import uuid

import utils
from inmanta import const, data


async def test_consistent_resource_state_reporting(
    server, agent, environment, resource_container, clienthelper, client
) -> None:
    """Doesn't work for new scheduler, as every release is a deploy"""
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTO_DEPLOY, False)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_INTERVAL, 0)
    await env.set(data.AUTOSTART_AGENT_REPAIR_INTERVAL, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    rid = "test::Resource[agent1,key=key1]"
    rid2 = "test::Resource[agent1,key=key2]"

    async def _put_version(version: int) -> None:
        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": f"{rid},v={version}",
                "change": False,
                "send_event": True,
                "purged": False,
                "requires": [],
                "purge_on_delete": False,
            },
            {
                "key": "key2",
                "value": "value1",
                "id": f"{rid2},v={version}",
                "change": False,
                "send_event": True,
                "purged": False,
                "requires": [rid],
                "purge_on_delete": False,
            },
        ]
        await clienthelper.put_version_simple(resources, version)

    version1 = await clienthelper.get_version()
    await _put_version(version1)

    version2 = await clienthelper.get_version()
    await _put_version(version2)

    result = await client.release_version(environment, version1, push=True)
    assert result.code == 200
    await utils.wait_until_deployment_finishes(client, environment)

    result = await client.release_version(environment, version2, push=False)
    assert result.code == 200

    result = await agent._client.resource_action_update(
        tid=environment,
        resource_ids=[f"{rid},v={version1}"],
        action_id=uuid.uuid4(),
        action=const.ResourceAction.deploy,
        started=datetime.datetime.now(),
        finished=datetime.datetime.now(),
        messages=[],
        status=const.ResourceState.failed,
    )
    assert result.code == 200

    result = await client.resource_list(tid=environment)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    by_id = {r["resource_id"]: r for r in result.result["data"]}
    assert by_id[rid]["status"] == const.ResourceState.failed.value

    # V2 endpoint to get resource details
    result = await client.resource_details(tid=environment, rid=rid)
    assert result.code == 200
    assert result.result["data"]["status"] == const.ResourceState.failed.value
    assert result.result["data"]["requires_status"] == {}

    result = await client.resource_details(tid=environment, rid=rid2)
    assert result.code == 200
    assert result.result["data"]["status"] == const.ResourceState.deployed.value
    assert result.result["data"]["requires_status"] == {rid: const.ResourceState.failed}
