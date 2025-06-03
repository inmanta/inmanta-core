"""
Copyright 2016 Inmanta

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
import uuid
from datetime import datetime
from re import sub
from uuid import UUID

import pytest

from inmanta import const, data, util
from inmanta.agent.executor import DeployReport
from inmanta.const import Change
from inmanta.deploy import persistence, state
from inmanta.resources import Id
from inmanta.server import SLICE_ORCHESTRATION
from inmanta.types import ResourceVersionIdStr
from inmanta.util import get_compiler_version
from utils import assert_no_warning


async def test_deploy(server, client, null_agent, environment, caplog, clienthelper):
    """
    Test basic deploy mechanism mocking
    """
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        version = await env.get_next_version()

        def make_resources(version: int):
            return [
                {
                    "key": "key1",
                    "id": "test::Resource[agent1,key=key1],v=%d" % version,
                    "send_event": False,
                    "purged": False,
                    "requires": [],
                },
                {
                    "key": "key2",
                    "id": "test::Resource[agent1,key=key2],v=%d" % version,
                    "send_event": False,
                    "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
                    "purged": False,
                },
                {
                    "key": "key3",
                    "id": "test::Resource[agent1,key=key3],v=%d" % version,
                    "send_event": False,
                    "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
                    "purged": True,
                },
                {"key": "key4", "id": "test::Resource[agent2,key=key4],v=%d" % version, "send_event": False, "requires": []},
            ]

        resources = make_resources(version)
        res = await orchestration_service.put_version(
            env=env,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            resource_state={},
            compiler_version=get_compiler_version(),
            module_version_info={},
        )
        assert res == 200

        result, _ = await orchestration_service.release_version(env, version, False)
        assert result == 200

        # Deploy each resource
        update_manager = persistence.ToDbUpdateManager(client, env.id)
        for resource in resources:
            action_id = uuid.uuid4()
            now = datetime.now()
            rid = Id.parse_id(resource["id"])
            await update_manager.send_in_progress(action_id, rid)

            await update_manager.send_deploy_done(
                attribute_hash=util.make_attribute_hash(resource_id=rid.resource_str(), attributes=resource),
                result=DeployReport(
                    rvid=rid.resource_version_str(),
                    action_id=action_id,
                    resource_state=const.HandlerResourceState.deployed,
                    messages=[],
                    changes={},
                    change=const.Change.updated,
                ),
                state=state.ResourceState(
                    compliance=state.Compliance.COMPLIANT,
                    last_deploy_result=state.DeployResult.DEPLOYED,
                    blocked=state.Blocked.NOT_BLOCKED,
                    last_deployed=now,
                ),
                started=now,
                finished=now,
            )

        result, payload = await orchestration_service.get_version(env, version)
        assert result == 200
        assert await clienthelper.done_count() == len(resources)

        # second, identical check_version
        v2 = await env.get_next_version()
        resources = make_resources(v2)
        res = await orchestration_service.put_version(
            env=env,
            version=v2,
            resources=resources,
            unknowns=[],
            version_info={},
            resource_state={},
            compiler_version=get_compiler_version(),
            module_version_info={},
        )
        assert res == 200

        increment, _ = await data.ConfigurationModel.get_increment(environment, version=v2)
        assert len(increment) == 0

    assert_no_warning(caplog)


def strip_version(v):
    return sub(",v=[0-9]+", "", v)


async def test_deploy_cad_double(server, null_agent, environment, caplog, client, clienthelper):
    version = await clienthelper.get_version()
    rvid = ResourceVersionIdStr(f"test::Resource[agent1,key=key1],v={version}")
    rvid2 = ResourceVersionIdStr(f"test::Resource[agent2,key=key2],v={version}")

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": rvid,
            "send_event": True,
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
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    async def deploy(rvid: ResourceVersionIdStr, change: Change = Change.nochange):
        update_manager = persistence.ToDbUpdateManager(client, uuid.UUID(environment))
        action_id = uuid.uuid4()
        start_time: datetime = datetime.now().astimezone()
        rid = Id.parse_id(rvid)
        await update_manager.send_in_progress(action_id, rid)
        await update_manager.send_deploy_done(
            attribute_hash=util.make_attribute_hash(resource_id=rid.resource_str(), attributes=resources[0]),
            result=DeployReport(
                rvid=rvid,
                action_id=action_id,
                resource_state=const.HandlerResourceState.deployed,
                messages=[],
                changes={},
                change=change,
            ),
            state=state.ResourceState(
                compliance=state.Compliance.COMPLIANT,
                last_deploy_result=state.DeployResult.DEPLOYED,
                blocked=state.Blocked.NOT_BLOCKED,
                last_deployed=datetime.now().astimezone(),
            ),
            started=start_time,
            finished=datetime.now().astimezone(),
        )

    async def assert_resources_to_deploy(
        environment: uuid.UUID, agent: str, version: int, expected_nr_of_resources: int
    ) -> None:
        increment, _ = await data.ConfigurationModel.get_increment(environment, version=version)
        resource_for_agent = [rid for rid in increment if Id.parse_id(rid).agent_name == agent]
        assert len(resource_for_agent) == expected_nr_of_resources

    await assert_resources_to_deploy(UUID(environment), agent="agent2", version=version, expected_nr_of_resources=1)

    await deploy(rvid)
    await deploy(rvid2)

    await assert_resources_to_deploy(UUID(environment), agent="agent2", version=version, expected_nr_of_resources=0)

    await deploy(rvid, change=Change.updated)

    await assert_resources_to_deploy(UUID(environment), agent="agent2", version=version, expected_nr_of_resources=1)


@pytest.mark.slowtest
async def test_release_stuck(
    server,
    environment,
    clienthelper,
    client,
    project_default,
):
    async def make_version() -> int:
        version = await clienthelper.get_version()
        rvid = f"test::Resource[agent1,key=key1],v={version}"
        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": rvid,
                "change": False,
                "send_event": True,
                "purged": False,
                "requires": [],
                "purge_on_delete": False,
            },
        ]
        await clienthelper.put_version_simple(resources, version, wait_for_released=True)
        return version

        # set auto deploy and push

    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    #  a version v1 is deploying
    await make_version()

    #  a version v2 is deploying
    await make_version()

    # Delete environment
    result = await client.environment_delete(environment)
    assert result.code == 200

    # Re-create
    result = await client.create_environment(project_id=project_default, name="env", environment_id=environment)
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    await make_version()
    # This will time-out when there is a run_ahead_lock still in place
    await make_version()
