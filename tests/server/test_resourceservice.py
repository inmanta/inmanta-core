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

import datetime
import uuid
from datetime import timezone

import pytest

from inmanta import const, data, util
from inmanta.agent import executor
from inmanta.data.model import ResourceIdStr, ResourceVersionIdStr
from inmanta.deploy import persistence, state


@pytest.fixture
async def resource_deployer(client, environment, null_agent):
    env_id = uuid.UUID(environment)
    update_manager = persistence.ToDbUpdateManager(client, env_id)

    class ResourceDeploymentHelperFunctions:
        @classmethod
        async def start_deployment(cls, rvid: ResourceVersionIdStr) -> uuid.UUID:
            action_id = uuid.uuid4()
            await update_manager.send_in_progress(action_id, rvid)
            return action_id

        @classmethod
        async def deployment_finished(
            cls,
            rvid: ResourceVersionIdStr,
            action_id: uuid.UUID,
            attribute_hash: str,
            change: const.Change = const.Change.created,
            status: const.ResourceState = const.ResourceState.deployed,
            deployment_result: state.DeploymentResult = state.DeploymentResult.DEPLOYED,
        ) -> None:
            await update_manager.send_deploy_done(
                attribute_hash=attribute_hash,
                result=executor.DeployResult(
                    rvid=rvid,
                    action_id=action_id,
                    status=status,
                    messages=[],
                    changes={},
                    change=change,
                    deployment_result=deployment_result,
                ),
            )

        @classmethod
        async def deploy_resource(
            cls,
            rvid: ResourceVersionIdStr,
            attribute_hash: str,
            change: const.Change = const.Change.created,
            status: const.ResourceState = const.ResourceState.deployed,
            deployment_result: state.DeploymentResult = state.DeploymentResult.DEPLOYED,
        ) -> None:
            action_id = await cls.start_deployment(rvid)
            await cls.deployment_finished(rvid, action_id, attribute_hash, change, status, deployment_result)

    # Disable AUTO_DEPLOY
    result = await client.environment_settings_set(tid=environment, id=data.AUTO_DEPLOY, value=False)
    assert result.code == 200

    yield ResourceDeploymentHelperFunctions


async def test_events_api_endpoints_basic_case(server, client, environment, clienthelper, null_agent, resource_deployer):
    """
    Test whether the `get_resource_events` and the `resource_did_dependency_change`
    endpoints behave as expected
    """
    await clienthelper.set_auto_deploy(auto=True)
    version = await clienthelper.get_version()

    # a name that is hard to parse
    rid = r"""exec::Run[agent1,command=sh -c "git _%\/ clone \"https://codis.git\"  && chown -R centos:centos "]"""
    rid_r1_v1 = ResourceIdStr(rid)
    rvid_r1_v1 = ResourceVersionIdStr(f"{rid_r1_v1},v={version}")
    rid_r2_v1 = ResourceIdStr("std::testing::NullResource[agent1,name=file2]")
    rvid_r2_v1 = ResourceVersionIdStr(f"{rid_r2_v1},v={version}")
    rid_r3_v1 = ResourceIdStr("std::testing::NullResource[agent1,name=file3]")
    rvid_r3_v1 = ResourceVersionIdStr(f"{rid_r3_v1},v={version}")
    resources = [
        {"name": "file1", "id": rvid_r1_v1, "requires": [rvid_r2_v1, rvid_r3_v1], "purged": False, "send_event": False},
        {"name": "file2", "id": rvid_r2_v1, "requires": [], "purged": False, "send_event": False},
        {"name": "file3", "id": rvid_r3_v1, "requires": [], "purged": False, "send_event": False},
    ]
    attribute_has_r1 = util.make_attribute_hash(rid_r1_v1, resources[0])
    attribute_has_r2 = util.make_attribute_hash(rid_r2_v1, resources[1])
    attribute_has_r3 = util.make_attribute_hash(rid_r3_v1, resources[2])

    await clienthelper.put_version_simple(resources, version, wait_for_released=True)

    result = await null_agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 400, result.result
    assert "Fetching resource events only makes sense when the resource is currently deploying" in result.result["message"]
    result = await null_agent._client.resource_did_dependency_change(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 400
    assert "Fetching resource events only makes sense when the resource is currently deploying" in result.result["message"]

    # Perform deployment
    await resource_deployer.deploy_resource(rvid=rvid_r2_v1, attribute_hash=attribute_has_r2)
    await resource_deployer.deploy_resource(rvid=rvid_r3_v1, attribute_hash=attribute_has_r3, status=const.ResourceState.failed)
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    # Verify that events exist
    result = await null_agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert len(result.result["data"][rid_r2_v1]) == 1
    assert result.result["data"][rid_r2_v1][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r2_v1][0]["status"] == const.ResourceState.deployed
    assert len(result.result["data"][rid_r3_v1]) == 1
    assert result.result["data"][rid_r3_v1][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r3_v1][0]["status"] == const.ResourceState.failed
    result = await null_agent._client.resource_did_dependency_change(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert result.result["data"]

    # Finish first deployment
    await resource_deployer.deployment_finished(rvid=rvid_r1_v1, attribute_hash=attribute_has_r1, action_id=action_id)

    # Start new deployment r1
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    # Assert no events anymore
    result = await null_agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert len(result.result["data"][rid_r2_v1]) == 0
    assert len(result.result["data"][rid_r3_v1]) == 0
    result = await null_agent._client.resource_did_dependency_change(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert not result.result["data"]

    # Finish deployment r1
    await resource_deployer.deployment_finished(rvid=rvid_r1_v1, attribute_hash=attribute_has_r1, action_id=action_id)

    # Deploy r2 and r3, but no changes occurred.
    await resource_deployer.deploy_resource(rvid=rvid_r2_v1, attribute_hash=attribute_has_r2, change=const.Change.nochange)
    await resource_deployer.deploy_resource(rvid=rvid_r3_v1, attribute_hash=attribute_has_r3, change=const.Change.nochange)

    # Start new deployment r1
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    # Ensure events, but no reload deployment required
    result = await null_agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert len(result.result["data"][rid_r2_v1]) == 1
    assert result.result["data"][rid_r2_v1][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r2_v1][0]["status"] == const.ResourceState.deployed
    assert len(result.result["data"][rid_r3_v1]) == 1
    assert result.result["data"][rid_r3_v1][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r3_v1][0]["status"] == const.ResourceState.deployed
    result = await null_agent._client.resource_did_dependency_change(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert not result.result["data"]

    # Finish deployment r1
    await resource_deployer.deployment_finished(rvid=rvid_r1_v1, attribute_hash=attribute_has_r1, action_id=action_id)


async def test_events_api_endpoints_increment(server, client, environment, clienthelper, null_agent, resource_deployer):
    """
    Test whether the `get_resource_events` and the `resource_did_dependency_change`
    endpoints behave as expected. Also test the exclude_change parameter for get_resource_events
    """
    agent = null_agent

    rid = r"""exec::Run[agent1,command=sh -c "git _%\/ clone \"https://codis.git\"  && chown -R centos:centos "]"""
    rid_r1 = ResourceIdStr(rid)
    rid_r2 = ResourceIdStr("std::testing::NullResource[agent1,name=file2]")
    rid_r3 = ResourceIdStr("std::testing::NullResource[agent1,name=file3]")

    async def put_version() -> tuple[
        tuple[ResourceVersionIdStr, str],
        tuple[ResourceVersionIdStr, str],
        tuple[ResourceVersionIdStr, str],
    ]:
        version = await clienthelper.get_version()
        # a name that is hard to parse
        rvid_r1_v1 = ResourceVersionIdStr(f"{rid_r1},v={version}")
        rvid_r2_v1 = ResourceVersionIdStr(f"{rid_r2},v={version}")
        rvid_r3_v1 = ResourceVersionIdStr(f"{rid_r3},v={version}")
        resources = [
            {"name": "file1", "id": rvid_r1_v1, "requires": [rvid_r2_v1, rvid_r3_v1], "purged": False, "send_event": True},
            {"name": "file2", "id": rvid_r2_v1, "requires": [], "purged": False, "send_event": True},
            {"name": "file3", "id": rvid_r3_v1, "requires": [], "purged": False, "send_event": True},
        ]
        rid_r1_attribute_hash = util.make_attribute_hash(resource_id=rid_r1, attributes=resources[0])
        rid_r2_attribute_hash = util.make_attribute_hash(resource_id=rid_r2, attributes=resources[1])
        rid_r3_attribute_hash = util.make_attribute_hash(resource_id=rid_r3, attributes=resources[2])

        await clienthelper.put_version_simple(resources, version)
        result = await client.release_version(
            environment,
            version,
            push=False,
        )
        assert result.code == 200

        result = await client.release_version(
            environment,
            version,
            push=False,
        )
        # ensure we can only do it once
        assert result.code == 409

        return (rvid_r1_v1, rid_r1_attribute_hash), (rvid_r2_v1, rid_r2_attribute_hash), (rvid_r3_v1, rid_r3_attribute_hash)

    (
        (rvid_r1_v1, rvid_r1_v1_attribute_hash),
        (rvid_r2_v1, rvid_r2_v1_attribute_hash),
        (rvid_r3_v1, rvid_r3_v1_attribute_hash),
    ) = await put_version()

    # Perform deployment
    await resource_deployer.deploy_resource(rvid=rvid_r2_v1, attribute_hash=rvid_r2_v1_attribute_hash)
    await resource_deployer.deploy_resource(
        rvid=rvid_r3_v1, attribute_hash=rvid_r3_v1_attribute_hash, status=const.ResourceState.failed
    )
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    # Verify that events exist
    result = await agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 2

    # Finish first deployment
    await resource_deployer.deployment_finished(rvid=rvid_r1_v1, attribute_hash=rvid_r1_v1_attribute_hash, action_id=action_id)

    print("pre event", datetime.datetime.now(timezone.utc))
    # Make events: deploy r2 and r3
    await resource_deployer.deploy_resource(
        rvid=rvid_r2_v1, attribute_hash=rvid_r2_v1_attribute_hash, change=const.Change.updated
    )
    await resource_deployer.deploy_resource(
        rvid=rvid_r3_v1, attribute_hash=rvid_r3_v1_attribute_hash, change=const.Change.updated
    )
    print("post event", datetime.datetime.now(timezone.utc))

    (
        (rvid_r1_v2, rvid_r1_v2_attribute_hash),
        (rvid_r2_v2, rvid_r2_v2_attribute_hash),
        (rvid_r3_v2, rvid_r3_v2_attribute_hash),
    ) = await put_version()

    # Start new deployment r1
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v2)

    # Assert we find the events
    result = await agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v2)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert len(result.result["data"][rid_r2]) == 2
    # incremental deploy
    assert result.result["data"][rid_r2][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r2][0]["status"] == const.ResourceState.deployed
    assert result.result["data"][rid_r2][0]["change"] == const.Change.nochange
    # actual deploy
    assert result.result["data"][rid_r2][1]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r2][1]["status"] == const.ResourceState.deployed
    assert result.result["data"][rid_r2][1]["change"] == const.Change.updated
    assert len(result.result["data"][rid_r3]) == 2
    # incremental deploy
    assert result.result["data"][rid_r3][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r3][0]["status"] == const.ResourceState.deployed
    assert result.result["data"][rid_r3][0]["change"] == const.Change.nochange
    # actual deploy
    assert result.result["data"][rid_r3][1]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r3][1]["status"] == const.ResourceState.deployed
    assert result.result["data"][rid_r3][1]["change"] == const.Change.updated

    # Assert we find the events excluding the nochange changes
    result = await agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v2, exclude_change=const.Change.nochange)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert len(result.result["data"][rid_r2]) == 1

    assert result.result["data"][rid_r2][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r2][0]["status"] == const.ResourceState.deployed
    assert result.result["data"][rid_r2][0]["change"] == const.Change.updated

    assert len(result.result["data"][rid_r3]) == 1

    assert result.result["data"][rid_r3][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_r3][0]["status"] == const.ResourceState.deployed
    assert result.result["data"][rid_r3][0]["change"] == const.Change.updated

    # Finish deployment r1
    await resource_deployer.deployment_finished(rvid=rvid_r1_v2, attribute_hash=rvid_r1_v2_attribute_hash, action_id=action_id)


async def test_events_api_endpoints_events_across_versions(server, client, environment, clienthelper, agent, resource_deployer):
    """
    Ensure that events are captured across versions.
    """
    # Version 1
    version = await clienthelper.get_version()
    rvid_r1_v1 = ResourceVersionIdStr(f"std::testing::NullResource[agent1,name=file1],v={version}")
    rid_r2 = ResourceIdStr("std::testing::NullResource[agent1,name=file2]")
    rvid_r2_v1 = ResourceVersionIdStr(f"{rid_r2},v={version}")
    resources = [
        {"name": "file1", "id": rvid_r1_v1, "requires": [rvid_r2_v1], "purged": False, "send_event": False},
        {"name": "file2", "id": rvid_r2_v1, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    # Deploy
    await resource_deployer.deploy_resource(
        rvid=rvid_r2_v1, attribute_hash=util.make_attribute_hash(rid_r2, attributes=resources[1])
    )

    # Version 2
    version = await clienthelper.get_version()
    rid_r1 = ResourceIdStr("std::testing::NullResource[agent1,name=file1]")
    rvid_r1_v2 = ResourceVersionIdStr(f"{rid_r1},v={version}")
    rid_r2 = ResourceIdStr("std::testing::NullResource[agent1,name=file2]")
    rvid_r2_v2 = ResourceVersionIdStr(f"{rid_r2},v={version}")
    rid_r3 = ResourceIdStr("std::testing::NullResource[agent1,name=file3]")
    rvid_r3_v2 = ResourceVersionIdStr(f"{rid_r3},v={version}")

    resources = [
        {"name": "file1", "id": rvid_r1_v2, "requires": [rvid_r2_v2, rvid_r3_v2], "purged": False, "send_event": False},
        {"name": "file2", "id": rvid_r2_v2, "requires": [], "purged": False, "send_event": False},
        {"name": "file3", "id": rvid_r3_v2, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    # Deploy
    await resource_deployer.deploy_resource(
        rvid=rvid_r2_v2, attribute_hash=util.make_attribute_hash(resource_id=rid_r2, attributes=resources[1])
    )
    await resource_deployer.deploy_resource(
        rvid=rvid_r3_v2, attribute_hash=util.make_attribute_hash(resource_id=rid_r3, attributes=resources[2])
    )

    # Version 3
    version = await clienthelper.get_version()
    rid_r1_v3 = ResourceIdStr("std::testing::NullResource[agent1,name=file1]")
    rvid_r1_v3 = ResourceVersionIdStr(f"{rid_r1_v3},v={version}")
    rid_v3_v3 = ResourceIdStr("std::testing::NullResource[agent1,name=file3]")
    rvid_r3_v3 = ResourceVersionIdStr(f"{rid_v3_v3},v={version}")
    resources = [
        {"name": "file1", "id": rvid_r1_v3, "requires": [rvid_r3_v3], "purged": False, "send_event": False},
        {"name": "file3", "id": rvid_r3_v3, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    # Deploy
    await resource_deployer.deploy_resource(
        rvid=rvid_r3_v3,
        attribute_hash=util.make_attribute_hash(resource_id=rid_v3_v3, attributes=resources[1]),
        status=const.ResourceState.failed,
    )
    action_id = await resource_deployer.start_deployment(rvid=rvid_r1_v3)

    # Assert events
    result = await agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v3)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert len(result.result["data"][rid_v3_v3]) == 2
    assert result.result["data"][rid_v3_v3][0]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_v3_v3][0]["status"] == const.ResourceState.failed
    assert result.result["data"][rid_v3_v3][1]["action"] == const.ResourceAction.deploy
    assert result.result["data"][rid_v3_v3][1]["status"] == const.ResourceState.deployed
    result = await agent._client.resource_did_dependency_change(tid=environment, rvid=rvid_r1_v3)
    assert result.code == 200
    assert result.result["data"]

    # Mark deployment r1 as done
    await resource_deployer.deployment_finished(
        rvid=rvid_r1_v3,
        attribute_hash=util.make_attribute_hash(resource_id=rid_r1_v3, attributes=resources[0]),
        action_id=action_id,
    )

    # Start new deployment for r1
    await resource_deployer.start_deployment(rvid=rvid_r1_v3)

    # Assert no move events
    result = await agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v3)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert len(result.result["data"][rid_v3_v3]) == 0
    result = await agent._client.resource_did_dependency_change(tid=environment, rvid=rvid_r1_v3)
    assert result.code == 200
    assert not result.result["data"]


async def test_events_resource_without_dependencies(
    server, client, environment, clienthelper, null_agent, resource_deployer
) -> None:
    """
    Ensure that events are captured across versions.
    """
    # Version 1
    version = await clienthelper.get_version()
    rvid_r1_v1 = ResourceVersionIdStr(f"std::testing::NullResource[agent1,name=file1],v={version}")
    resources = [
        {"name": "file1", "id": rvid_r1_v1, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200

    # Start new deployment for r1
    await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    result = await null_agent._client.get_resource_events(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert len(result.result["data"]) == 0
    result = await null_agent._client.resource_did_dependency_change(tid=environment, rvid=rvid_r1_v1)
    assert result.code == 200
    assert not result.result["data"]


@pytest.mark.parametrize("endpoint_to_use", ["deployment_endpoint", "resource_action_update"])
async def test_last_non_deploying_status_field_on_resource(
    client, environment, clienthelper, resource_deployer, null_agent, endpoint_to_use: str
) -> None:
    """
    Test whether the `last_non_deploying_status` field is updated correctly when a deployment of a resource is done.

    :param endpoint_to_use: Indicates which code path should be used to report a resource action updates.
                            The old one (resource_action_update) or the new one (deployment_endpoint).
    """
    version = await clienthelper.get_version()
    rid_r1 = ResourceIdStr("std::testing::NullResource[agent1,name=file1]")
    rvid_r1_v1 = ResourceVersionIdStr(f"{rid_r1},v={version}")
    rid_r2 = ResourceIdStr("std::testing::NullResource[agent1,name=file2]")
    rvid_r2_v1 = ResourceVersionIdStr(f"{rid_r2},v={version}")
    resources = [
        {"name": "file1", "id": rvid_r1_v1, "requires": [], "purged": False, "send_event": False},
        {"name": "file2", "id": rvid_r2_v1, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200

    async def assert_status_fields(
        r1_status: const.ResourceState,
        r1_last_non_deploying_status: const.NonDeployingResourceState,
        r2_status: const.ResourceState,
        r2_last_non_deploying_status: const.NonDeployingResourceState,
    ) -> None:
        db_resources = await data.Resource.get_list(environment=environment)
        rvid_to_resources = {res.resource_version_id: res for res in db_resources}

        db_resource_state = await data.ResourcePersistentState.get_list(environment=environment)
        rid_to_resource_state = {res.resource_id: res for res in db_resource_state}

        assert rvid_to_resources[rvid_r1_v1].status is r1_status
        assert rid_to_resource_state[rid_r1].last_non_deploying_status is r1_last_non_deploying_status
        assert rvid_to_resources[rvid_r2_v1].status is r2_status
        assert rid_to_resource_state[rid_r2].last_non_deploying_status is r2_last_non_deploying_status

    async def start_deployment(rvid: ResourceVersionIdStr) -> uuid.UUID:
        if endpoint_to_use == "deployment_endpoint":
            return await resource_deployer.start_deployment(rvid=rvid)
        else:
            action_id = uuid.uuid4()
            result = await null_agent._client.resource_action_update(
                tid=environment,
                resource_ids=[rvid],
                action_id=action_id,
                action=const.ResourceAction.deploy,
                started=datetime.datetime.now().astimezone(),
                status=const.ResourceState.deploying,
            )
            assert result.code == 200
            return action_id

    async def deployment_finished(
        rvid: ResourceVersionIdStr,
        action_id: uuid.UUID,
        status: const.ResourceState,
        attribute_hash: str,
        deployment_result: state.DeploymentResult,
    ) -> None:
        if endpoint_to_use == "deployment_endpoint":
            await resource_deployer.deployment_finished(
                rvid=rvid,
                action_id=action_id,
                attribute_hash=attribute_hash,
                status=status,
                deployment_result=deployment_result,
            )
        else:
            now = datetime.datetime.now().astimezone()
            result = await null_agent._client.resource_action_update(
                tid=environment,
                resource_ids=[rvid],
                action_id=action_id,
                action=const.ResourceAction.deploy,
                started=now,
                finished=now,
                status=status,
            )
            assert result.code == 200

    # All resources in available state
    await assert_status_fields(
        r1_status=const.ResourceState.available,
        r1_last_non_deploying_status=const.NonDeployingResourceState.available,
        r2_status=const.ResourceState.available,
        r2_last_non_deploying_status=const.NonDeployingResourceState.available,
    )

    # Put R1 in deploying state
    action_id_r1 = await start_deployment(rvid=rvid_r1_v1)
    await assert_status_fields(
        r1_status=const.ResourceState.deploying,
        r1_last_non_deploying_status=const.NonDeployingResourceState.available,
        r2_status=const.ResourceState.available,
        r2_last_non_deploying_status=const.NonDeployingResourceState.available,
    )

    # R1 finished deployment + R2 start deployment
    await deployment_finished(
        rvid=rvid_r1_v1,
        action_id=action_id_r1,
        status=const.ResourceState.deployed,
        attribute_hash=util.make_attribute_hash(resource_id=rid_r1, attributes=resources[0]),
        deployment_result=state.DeploymentResult.DEPLOYED,
    )
    action_id_r2 = await start_deployment(rvid=rvid_r2_v1)
    await assert_status_fields(
        r1_status=const.ResourceState.deployed,
        r1_last_non_deploying_status=const.NonDeployingResourceState.deployed,
        r2_status=const.ResourceState.deploying,
        r2_last_non_deploying_status=const.NonDeployingResourceState.available,
    )

    # R1 start deployment + R2 skipped
    action_id_r1 = await start_deployment(rvid=rvid_r1_v1)
    await deployment_finished(
        rvid=rvid_r2_v1,
        action_id=action_id_r2,
        status=const.ResourceState.skipped,
        attribute_hash=util.make_attribute_hash(resource_id=rid_r2, attributes=resources[1]),
        deployment_result=state.DeploymentResult.SKIPPED,
    )
    await assert_status_fields(
        r1_status=const.ResourceState.deploying,
        r1_last_non_deploying_status=const.NonDeployingResourceState.deployed,
        r2_status=const.ResourceState.skipped,
        r2_last_non_deploying_status=const.NonDeployingResourceState.skipped,
    )

    # R1 failed + R2 start deployment
    await deployment_finished(
        rvid=rvid_r1_v1,
        action_id=action_id_r1,
        status=const.ResourceState.failed,
        attribute_hash=util.make_attribute_hash(resource_id=rid_r1, attributes=resources[0]),
        deployment_result=state.DeploymentResult.FAILED,
    )
    await start_deployment(rvid=rvid_r2_v1)
    await assert_status_fields(
        r1_status=const.ResourceState.failed,
        r1_last_non_deploying_status=const.NonDeployingResourceState.failed,
        r2_status=const.ResourceState.deploying,
        r2_last_non_deploying_status=const.NonDeployingResourceState.skipped,
    )


async def test_log_deploy_start(server, client, environment, clienthelper, agent, resource_deployer):
    """
    Ensure that a message is logged when starting a deploy.
    """
    # Version 1
    version = await clienthelper.get_version()
    rid_r1 = ResourceIdStr("std::testing::NullResource[agent1,name=file1]")
    rvid_r1_v1 = ResourceVersionIdStr(f"{rid_r1},v={version}")
    resources = [
        {"name": "file1", "id": rvid_r1_v1, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    # Start new deployment for r1
    await resource_deployer.start_deployment(rvid=rvid_r1_v1)

    result = await client.resource_logs(environment, rid_r1)
    assert result.code == 200
    deploy_started_message = next(
        (log_message for log_message in result.result["data"] if "Resource deploy started on agent" in log_message["msg"]), None
    )
    assert deploy_started_message
