"""
    Copyright 2021 Inmanta

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
import uuid

import pytest

from inmanta import const, data
from inmanta.data.model import ResourceIdStr, ResourceVersionIdStr


@pytest.fixture
def resource_deployer(environment, agent):
    class ResourceDeploymentHelperFunctions:
        @classmethod
        async def start_deployment(cls, rvid: ResourceVersionIdStr) -> uuid.UUID:
            action_id = uuid.uuid4()
            result = await agent._client.resource_deploy_start(tid=environment, resource_id=rvid, action_id=action_id)
            assert result.code == 200
            return action_id

        @classmethod
        async def deployment_finished(
            cls,
            rvid: ResourceVersionIdStr,
            action_id: uuid.UUID,
            change: const.Change = const.Change.created,
            status: const.ResourceState = const.ResourceState.deployed,
        ) -> None:
            result = await agent._client.resource_deploy_done(
                tid=environment,
                resource_id=rvid,
                action_id=action_id,
                status=status,
                change=change,
            )
            assert result.code == 200

        @classmethod
        async def deploy_resource(
            cls,
            rvid: ResourceVersionIdStr,
            change: const.Change = const.Change.created,
            status: const.ResourceState = const.ResourceState.deployed,
        ) -> None:
            action_id = await cls.start_deployment(rvid)
            await cls.deployment_finished(rvid, action_id, change, status)

    yield ResourceDeploymentHelperFunctions


@pytest.mark.asyncio
async def test_events_api_endpoints_basic_case(server, client, environment, clienthelper, agent, resource_deployer):
    """
    Test whether the `get_resource_events` and the `resource_did_dependency_change`
    endpoints behave as expected
    """
    result = await client.environment_settings_set(tid=environment, id=data.AUTO_DEPLOY, value=False)
    assert result.code == 200

    version = await clienthelper.get_version()

    rid_r1_v1 = ResourceIdStr("std::File[agent1,path=/etc/file1]")
    rvid_r1_v1 = ResourceVersionIdStr(f"{rid_r1_v1},v={version}")
    rid_r2_v1 = ResourceIdStr("std::File[agent1,path=/etc/file2]")
    rvid_r2_v1 = ResourceVersionIdStr(f"{rid_r2_v1},v={version}")
    rid_r3_v1 = ResourceIdStr("std::File[agent1,path=/etc/file3]")
    rvid_r3_v1 = ResourceVersionIdStr(f"{rid_r3_v1},v={version}")
    resources = [
        {"path": "/etc/file1", "id": rvid_r1_v1, "requires": [rvid_r2_v1, rvid_r3_v1], "purged": False, "send_event": False},
        {"path": "/etc/file2", "id": rvid_r2_v1, "requires": [], "purged": False, "send_event": False},
        {"path": "/etc/file3", "id": rvid_r3_v1, "requires": [], "purged": False, "send_event": False},
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await agent._client.get_resource_events(tid=environment, id=rvid_r1_v1)
    assert result.code == 400
    assert "Fetching resource events only makes sense when the resource is currently deploying" in result.result["message"]
    result = await agent._client.resource_did_dependency_change(tid=environment, id=rvid_r1_v1)
    assert result.code == 400
    assert "Fetching resource events only makes sense when the resource is currently deploying" in result.result["message"]

    # Perform deployment
    await resource_deployer.deploy_resource(rvid=rvid_r2_v1)
    await resource_deployer.deploy_resource(rvid=rvid_r3_v1, status=const.ResourceState.failed)
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    # Verify that events exist
    result = await agent._client.get_resource_events(tid=environment, id=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert len(result.result["data"][rid_r2_v1]) == 1
    assert result.result["data"][rid_r2_v1][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r2_v1][0]["status"] == const.ResourceState.deployed
    assert len(result.result["data"][rid_r3_v1]) == 1
    assert result.result["data"][rid_r3_v1][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r3_v1][0]["status"] == const.ResourceState.failed
    result = await agent._client.resource_did_dependency_change(tid=environment, id=rvid_r1_v1)
    assert result.code == 200
    assert result.result["data"]

    # Finish first deployment
    await resource_deployer.deployment_finished(rvid=rvid_r1_v1, action_id=action_id)

    # Start new deployment r1
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    # Assert no events anymore
    result = await agent._client.get_resource_events(tid=environment, id=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert len(result.result["data"][rid_r2_v1]) == 0
    assert len(result.result["data"][rid_r3_v1]) == 0
    result = await agent._client.resource_did_dependency_change(tid=environment, id=rvid_r1_v1)
    assert result.code == 200
    assert not result.result["data"]

    # Finish deployment r1
    await resource_deployer.deployment_finished(rvid=rvid_r1_v1, action_id=action_id)

    # Deploy r2 and r3, but no changes occurred.
    await resource_deployer.deploy_resource(rvid=rvid_r2_v1, change=const.Change.nochange)
    await resource_deployer.deploy_resource(rvid=rvid_r3_v1, change=const.Change.nochange)

    # Start new deployment r1
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    # Ensure events, but no reload deployment required
    result = await agent._client.get_resource_events(tid=environment, id=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert len(result.result["data"][rid_r2_v1]) == 1
    assert result.result["data"][rid_r2_v1][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r2_v1][0]["status"] == const.ResourceState.deployed
    assert len(result.result["data"][rid_r3_v1]) == 1
    assert result.result["data"][rid_r3_v1][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r3_v1][0]["status"] == const.ResourceState.deployed
    result = await agent._client.resource_did_dependency_change(tid=environment, id=rvid_r1_v1)
    assert result.code == 200
    assert not result.result["data"]

    # Finish deployment r1
    await resource_deployer.deployment_finished(rvid=rvid_r1_v1, action_id=action_id)


@pytest.mark.asyncio
async def test_events_api_endpoints_events_across_versions(server, client, environment, clienthelper, agent, resource_deployer):
    """
    Ensure that events are captured across versions.
    """
    result = await client.environment_settings_set(tid=environment, id=data.AUTO_DEPLOY, value=False)
    assert result.code == 200

    # Version 1
    version = await clienthelper.get_version()
    rvid_r1_v1 = ResourceVersionIdStr(f"std::File[agent1,path=/etc/file1],v={version}")
    rvid_r2_v1 = ResourceVersionIdStr(f"std::File[agent1,path=/etc/file2],v={version}")
    resources = [
        {"path": "/etc/file1", "id": rvid_r1_v1, "requires": [rvid_r2_v1], "purged": False, "send_event": False},
        {"path": "/etc/file2", "id": rvid_r2_v1, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    # Deploy
    await resource_deployer.deploy_resource(rvid=rvid_r2_v1)

    # Version 2
    version = await clienthelper.get_version()
    rvid_r1_v2 = ResourceVersionIdStr(f"std::File[agent1,path=/etc/file1],v={version}")
    rvid_r2_v2 = ResourceVersionIdStr(f"std::File[agent1,path=/etc/file2],v={version}")
    rvid_r3_v2 = ResourceVersionIdStr(f"std::File[agent1,path=/etc/file3],v={version}")
    resources = [
        {"path": "/etc/file1", "id": rvid_r1_v2, "requires": [rvid_r2_v2, rvid_r3_v2], "purged": False, "send_event": False},
        {"path": "/etc/file2", "id": rvid_r2_v2, "requires": [], "purged": False, "send_event": False},
        {"path": "/etc/file3", "id": rvid_r3_v2, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    # Deploy
    await resource_deployer.deploy_resource(rvid=rvid_r2_v2)
    await resource_deployer.deploy_resource(rvid=rvid_r3_v2)

    # Version 3
    version = await clienthelper.get_version()
    rvid_r1_v3 = ResourceVersionIdStr(f"std::File[agent1,path=/etc/file1],v={version}")
    rid_v3_v3 = ResourceIdStr("std::File[agent1,path=/etc/file3]")
    rvid_r3_v3 = ResourceVersionIdStr(f"{rid_v3_v3},v={version}")
    resources = [
        {"path": "/etc/file1", "id": rvid_r1_v3, "requires": [rvid_r3_v3], "purged": False, "send_event": False},
        {"path": "/etc/file3", "id": rvid_r3_v3, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    # Deploy
    await resource_deployer.deploy_resource(rvid=rvid_r3_v3, status=const.ResourceState.failed)
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v3)

    # Assert events
    result = await agent._client.get_resource_events(tid=environment, id=rvid_r1_v3)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert len(result.result["data"][rid_v3_v3]) == 2
    assert result.result["data"][rid_v3_v3][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_v3_v3][0]["status"] == const.ResourceState.failed
    assert result.result["data"][rid_v3_v3][1]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_v3_v3][1]["status"] == const.ResourceState.deployed
    result = await agent._client.resource_did_dependency_change(tid=environment, id=rvid_r1_v3)
    assert result.code == 200
    assert result.result["data"]

    # Mark deployment r1 as done
    await resource_deployer.deployment_finished(rvid=rvid_r1_v3, action_id=action_id)

    # Start new deployment for r1
    await resource_deployer.start_deployment(rvid=rvid_r1_v3)

    # Assert no move events
    result = await agent._client.get_resource_events(tid=environment, id=rvid_r1_v3)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert len(result.result["data"][rid_v3_v3]) == 0
    result = await agent._client.resource_did_dependency_change(tid=environment, id=rvid_r1_v3)
    assert result.code == 200
    assert not result.result["data"]


@pytest.mark.asyncio
async def test_events_resource_without_dependencies(server, client, environment, clienthelper, agent, resource_deployer):
    """
    Ensure that events are captured across versions.
    """
    result = await client.environment_settings_set(tid=environment, id=data.AUTO_DEPLOY, value=False)
    assert result.code == 200

    # Version 1
    version = await clienthelper.get_version()
    rvid_r1_v1 = ResourceVersionIdStr(f"std::File[agent1,path=/etc/file1],v={version}")
    resources = [
        {"path": "/etc/file1", "id": rvid_r1_v1, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    # Start new deployment for r1
    await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    result = await agent._client.get_resource_events(tid=environment, id=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 0
    result = await agent._client.resource_did_dependency_change(tid=environment, id=rvid_r1_v1)
    assert result.code == 200
    assert not result.result["data"]
