"""
    Copyright 2019 Inmanta

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
import uuid

import pytest

from inmanta import const, data, execute
from inmanta.agent.agent import Agent
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.util import get_compiler_version
from utils import ClientHelper, _wait_until_deployment_finishes, retry_limited

logger = logging.getLogger("inmanta.test.dryrun")


@pytest.mark.asyncio(timeout=150)
async def test_dryrun_and_deploy(server, client, resource_container, environment):
    """
    dryrun and deploy a configuration model

    There is a second agent with an undefined resource. The server will shortcut the dryrun and deploy for this resource
    without an agent being present.
    """

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
    await agent.start()

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    clienthelper = ClientHelper(client, environment)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": True,
        },
        {
            "key": "key4",
            "value": execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key5",
            "value": "val",
            "id": "test::Resource[agent2,key=key5],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
            "purged": False,
        },
        {
            "key": "key6",
            "value": "val",
            "id": "test::Resource[agent2,key=key6],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key5],v=%d" % version],
            "purged": False,
        },
    ]

    status = {"test::Resource[agent2,key=key4]": const.ResourceState.undefined}
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=status,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    mod_db = await data.ConfigurationModel.get_version(uuid.UUID(environment), version)
    undep = await mod_db.get_undeployable()
    assert undep == ["test::Resource[agent2,key=key4]"]

    undep = await mod_db.get_skipped_for_undeployable()
    assert undep == ["test::Resource[agent2,key=key5]", "test::Resource[agent2,key=key6]"]

    # request a dryrun
    result = await client.dryrun_request(environment, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = await client.dryrun_list(environment, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = await client.dryrun_list(environment, version)
        await asyncio.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = await client.dryrun_report(environment, dry_run_id)
    assert result.code == 200

    changes = result.result["dryrun"]["resources"]

    assert changes[resources[0]["id"]]["changes"]["purged"]["current"]
    assert not changes[resources[0]["id"]]["changes"]["purged"]["desired"]
    assert changes[resources[0]["id"]]["changes"]["value"]["current"] is None
    assert changes[resources[0]["id"]]["changes"]["value"]["desired"] == resources[0]["value"]

    assert changes[resources[1]["id"]]["changes"]["value"]["current"] == "incorrect_value"
    assert changes[resources[1]["id"]]["changes"]["value"]["desired"] == resources[1]["value"]

    assert not changes[resources[2]["id"]]["changes"]["purged"]["current"]
    assert changes[resources[2]["id"]]["changes"]["purged"]["desired"]

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 6
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    result = await client.get_version(environment, version)
    assert result.result["model"]["done"] == len(resources)

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")

    actions = await data.ResourceAction.get_list()
    assert sum([len(x.resource_version_ids) for x in actions if x.status == const.ResourceState.undefined]) == 1
    assert sum([len(x.resource_version_ids) for x in actions if x.status == const.ResourceState.skipped_for_undefined]) == 2

    await agent.stop()


@pytest.mark.asyncio(timeout=30)
async def test_dryrun_failures(resource_container, server, agent, client, environment, clienthelper):
    """
    test dryrun scaling
    """
    env_id = environment

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Noprov[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::FailFast[agent1,key=key2],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::DoesNotExist[agent1,key=key2],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # request a dryrun
    result = await client.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = await client.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = await client.dryrun_list(env_id, version)
        await asyncio.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = await client.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    resources = result.result["dryrun"]["resources"]

    def assert_handler_failed(resource, msg):
        changes = resources[resource]
        assert "changes" in changes
        changes = changes["changes"]
        assert "handler" in changes
        change = changes["handler"]
        assert change["current"] == "FAILED"
        assert change["desired"] == msg

    assert_handler_failed("test::Noprov[agent1,key=key1],v=%d" % version, "Unable to find a handler")
    assert_handler_failed("test::FailFast[agent1,key=key2],v=%d" % version, "Handler failed")

    # check if this resource was marked as unavailable
    response = await client.get_resource(environment, "test::DoesNotExist[agent1,key=key2],v=%d" % version, logs=True)
    assert response.code == 200

    # resource stays available but an unavailable state is logged because of the failed dryrun
    result = response.result
    assert result["resource"]["status"] == "available"
    log_entry = result["logs"][0]
    assert log_entry["action"] == "dryrun"
    assert log_entry["status"] == "unavailable"
    assert "Failed to load" in log_entry["messages"][0]["msg"]

    await agent.stop()


@pytest.mark.asyncio(timeout=30)
async def test_dryrun_scale(resource_container, server, client, environment, agent, clienthelper):
    """
    test dryrun scaling
    """
    version = await clienthelper.get_version()
    env_id = environment

    resources = []
    for i in range(1, 100):
        resources.append(
            {
                "key": "key%d" % i,
                "value": "value%d" % i,
                "id": "test::Resource[agent1,key=key%d],v=%d" % (i, version),
                "purged": False,
                "send_event": False,
                "requires": [],
            }
        )

    await clienthelper.put_version_simple(resources, version)

    # request a dryrun
    result = await client.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = await client.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = await client.dryrun_list(env_id, version)
        await asyncio.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = await client.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    await agent.stop()
