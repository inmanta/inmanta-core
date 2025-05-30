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

# Copied over from old tests

import json
import logging
import uuid

import pytest

from inmanta import const, data, execute
from inmanta.const import AgentAction
from inmanta.util import get_compiler_version
from utils import ClientHelper, retry_limited, wait_until_deployment_finishes

logger = logging.getLogger("inmanta.test.dryrun")


async def test_dryrun_and_deploy(server, client, resource_container, environment, agent):
    """
    dryrun and deploy a configuration model

    There is a second agent with an undefined resource. The server will shortcut the dryrun and deploy for this resource
    without an agent being present.
    """
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
        module_version_info={},
    )
    assert result.code == 200

    mod_db = await data.ConfigurationModel.get_version(uuid.UUID(environment), version)
    undep = mod_db.get_undeployable()
    assert undep == ["test::Resource[agent2,key=key4]"]

    undep = mod_db.get_skipped_for_undeployable()
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

    async def dryrun_finished():
        result = await client.dryrun_list(environment, version)
        return result.result["dryruns"][0]["todo"] == 0

    await retry_limited(dryrun_finished, 10)

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
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 6

    result = await client.get_version(environment, version)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment)

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")


async def test_dryrun_failures(resource_container, server, agent, client, environment, clienthelper):
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

    async def dryrun_finished():
        result = await client.dryrun_list(env_id, version)
        return result.result["dryruns"][0]["todo"] == 0

    await retry_limited(dryrun_finished, 10)

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
    log_entry = result["logs"][0]
    assert log_entry["action"] == "dryrun"
    assert log_entry["status"] == "unavailable"
    assert "Unable to deserialize" in log_entry["messages"][0]["msg"]

    await agent.stop()


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

    async def dryrun_finished():
        result = await client.dryrun_list(env_id, version)
        return result.result["dryruns"][0]["todo"] == 0

    await retry_limited(dryrun_finished, 10)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = await client.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    await agent.stop()


@pytest.mark.parametrize("auto_start_agent", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_dryrun_code_loading_failure(server, client, resource_container, environment, clienthelper):
    """
    Test running a dryrun when there is no handler code available. We use an autostarted agent, these
    do not have access to the handler code for the resource_container.
    """
    resource_container.Provider.reset()
    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}]

    await clienthelper.put_version_simple(resources, version)

    await wait_until_deployment_finishes(client, environment, timeout=10)

    result = await client.dryrun_trigger(environment, version)
    assert result.code == 200
    dry_run_id = result.result["data"]

    result = await client.list_dryruns(environment, version)
    assert result.code == 200
    assert len(result.result["data"]) == 1

    async def dryrun_finished():
        result = await client.list_dryruns(environment, version)
        logger.info("%s", result.result)
        return result.result["data"][0]["todo"] == 0

    await retry_limited(dryrun_finished, 10)

    result = await client.get_dryrun_diff(environment, version, dry_run_id)
    assert result.code == 200
    assert len(result.result["data"]["diff"]) == len(resources)
    changes = result.result["data"]["diff"]

    assert changes[0]["attributes"]["handler"] == {
        "from_value": "FAILED",
        "from_value_compare": "FAILED",
        "to_value": "Unable to construct an executor for this resource",
        "to_value_compare": "Unable to construct an executor for this resource",
    }


async def test_dryrun_v2(server, client, resource_container, environment, agent):
    """
    Dryrun a configuration model with the v2 api, where applicable
    """

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key_mod", {"first_level": {"nested": [5, 3, 2, 1, 1]}})
    resource_container.Provider.set("agent1", "key3", "value")
    resource_container.Provider.set("agent1", "key_unmodified", "the_same")

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
            "key": "key_mod",
            "value": {"first_level": {"nested": {"one_more_level": [5, 3, 2, 1, 1]}}},
            "id": "test::Resource[agent1,key=key_mod],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key_unmodified",
            "value": "the_same",
            "id": "test::Resource[agent1,key=key_unmodified],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
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
        {
            "key": "key7",
            "value": "val",
            "id": "test::Resource[agent3,key=key7],v=%d" % version,
            "send_event": False,
            "requires": [],
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
        module_version_info={},
    )
    assert result.code == 200
    # Pause agent3
    result = await client.agent_action(tid=environment, name="agent3", action=AgentAction.pause.name)
    assert result.code == 200
    a = await data.Agent.get_one(environment=environment, name="agent3")
    assert a.paused

    mod_db = await data.ConfigurationModel.get_version(uuid.UUID(environment), version)
    assert mod_db is not None
    undep = mod_db.get_undeployable()
    assert undep == ["test::Resource[agent2,key=key4]"]

    undep = mod_db.get_skipped_for_undeployable()
    assert undep == ["test::Resource[agent2,key=key5]", "test::Resource[agent2,key=key6]"]

    result = await client.dryrun_trigger(uuid.uuid4(), version)
    assert result.code == 404
    result = await client.dryrun_trigger(environment, 123456789)
    assert result.code == 404

    result = await client.list_dryruns(uuid.uuid4(), version)
    assert result.code == 404

    result = await client.list_dryruns(environment, 123456789)
    assert result.code == 404

    result = await client.list_dryruns(environment, version)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    # request a dryrun with correct parameters
    result = await client.dryrun_trigger(environment, version)
    assert result.code == 200
    dry_run_id = result.result["data"]

    # get the dryrun results
    result = await client.list_dryruns(environment, version)
    assert result.code == 200
    assert len(result.result["data"]) == 1

    async def dryrun_finished():
        result = await client.list_dryruns(environment, version)
        logger.info("%s", result.result)
        return result.result["data"][0]["todo"] == 0

    await retry_limited(dryrun_finished, 10)

    result = await client.get_dryrun_diff(uuid.uuid4(), version, dry_run_id)
    assert result.code == 404
    result = await client.get_dryrun_diff(environment, version, uuid.uuid4())
    assert result.code == 404
    result = await client.get_dryrun_diff(environment, version, dry_run_id)
    assert result.code == 200
    assert len(result.result["data"]["diff"]) == len(resources)
    changes = result.result["data"]["diff"]

    assert changes[0]["status"] == "added"
    assert changes[0]["attributes"]["value"] == {
        "from_value": None,
        "from_value_compare": "",
        "to_value": resources[0]["value"],
        "to_value_compare": resources[0]["value"],
    }

    assert changes[1]["status"] == "modified"
    assert changes[1]["attributes"]["value"] == {
        "from_value": "incorrect_value",
        "from_value_compare": "incorrect_value",
        "to_value": resources[1]["value"],
        "to_value_compare": resources[1]["value"],
    }
    assert changes[2]["status"] == "deleted"
    assert changes[3]["status"] == "modified"
    assert changes[3]["attributes"]["value"] == {
        "from_value": {"first_level": {"nested": [5, 3, 2, 1, 1]}},
        "from_value_compare": json.dumps({"first_level": {"nested": [5, 3, 2, 1, 1]}}, indent=4, sort_keys=True),
        "to_value": resources[3]["value"],
        "to_value_compare": json.dumps(resources[3]["value"], indent=4, sort_keys=True),
    }
    assert changes[4]["status"] == "unmodified"
    assert changes[5]["status"] == "undefined"
    assert changes[6]["status"] == "skipped_for_undefined"
    assert changes[7]["status"] == "skipped_for_undefined"

    assert changes[8]["status"] == "agent_down"
    # Changes for undeployable resources are empty
    for i in range(4, 9):
        assert changes[i]["attributes"] == {}

    # Change a value for a new dryrun
    res = await data.Resource.get(environment, "test::Resource[agent1,key=key1],v=%d" % version)
    await res.update(attributes={**res.attributes, "value": "updated_value"})

    result = await client.dryrun_trigger(environment, version)
    assert result.code == 200
    new_dry_run_id = result.result["data"]
    result = await client.list_dryruns(environment, version)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    # Check if the dryruns are ordered correctly
    assert result.result["data"][0]["id"] == new_dry_run_id
    assert result.result["data"][0]["date"] > result.result["data"][1]["date"]

    await retry_limited(dryrun_finished, 10)

    # The new dryrun should have the updated value
    result = await client.get_dryrun_diff(environment, version, new_dry_run_id)
    assert result.code == 200
    assert result.result["data"]["diff"][0]["attributes"]["value"]["to_value"] == "updated_value"
