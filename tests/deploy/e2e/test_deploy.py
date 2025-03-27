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
import pathlib
import uuid
from collections.abc import Sequence
from typing import Callable, Mapping, NamedTuple, Optional

import pytest

from inmanta import config, const, data, execute
from inmanta.config import Config
from inmanta.data import SERVER_COMPILE
from inmanta.data.model import SchedulerStatusReport
from inmanta.deploy.state import Blocked, Compliance, DeployResult, ResourceState
from inmanta.deploy.work import TaskPriority
from inmanta.resources import Id
from inmanta.server import SLICE_PARAM, SLICE_SERVER
from inmanta.types import ResourceIdStr
from inmanta.util import get_compiler_version
from utils import (
    assert_resource_persistent_state,
    log_contains,
    resource_action_consistency_check,
    retry_limited,
    wait_full_success,
    wait_until_deployment_finishes,
)

logger = logging.getLogger(__name__)


async def test_on_disk_layout(server, agent, environment):
    """
    Check that the storage is configured correctly:
          <state-dir>
              ├─ server/
                 ├─ env_uuid_1/
                 │   ├─ executors/
                 │   │   ├─ venvs/
                 │   │   │  ├─ venv_blueprint_hash_1/
                 │   │   │  ├─ venv_blueprint_hash_2/
                 │   │   │  ├─ ...
                 │   │   ├─ code/
                 │   │      ├─ executor_blueprint_hash_1/
                 │   │      ├─ executor_blueprint_hash_2/
                 │   │      ├─ ...
                 │   ├─ scheduler.cfg
                 │   ├─ compiler/
                 │
                 ├─ env_uuid_2/
                 │  ├─ ( ... )
          <log-dir>
              ├─ logs/
    """
    state_dir = pathlib.Path(config.Config.get("config", "state-dir"))
    log_dir = pathlib.Path(config.Config.get("config", "log-dir"))

    server_storage = server.get_slice(SLICE_SERVER)._server_storage
    agent_storage = agent._storage

    expected_server_storage = {
        "server": str(state_dir / "server"),
        "logs": str(log_dir),
    }
    scheduler_state_dir = pathlib.Path(state_dir / "server" / str(environment))
    executors_dir = scheduler_state_dir / "executors"
    expected_agent_storage = {"executors": str(executors_dir)}

    def check_on_disk_structure(expected_structure: Mapping[str, str], actual_structure: Mapping[str, str]):
        """
        Expects 2 mappings representing expected and actual on-disk file structure.
        Checks for equality between the 2 and checks that the underlying structure is present.
        """
        # Check structure is as expected
        assert expected_structure == actual_structure
        # Check existence
        for path in actual_structure.values():
            assert pathlib.Path(path).exists()

    check_on_disk_structure(expected_server_storage, server_storage)
    check_on_disk_structure(expected_agent_storage, agent_storage)

    # Also check that "venvs" and "code" directories are properly created:
    for sub_dir in [
        executors_dir / "venvs",
        executors_dir / "code",
    ]:
        assert sub_dir.exists()

    # Check for presence of the new disk layout marker file
    marker_file_path = state_dir / const.INMANTA_DISK_LAYOUT_VERSION
    assert pathlib.Path(marker_file_path).exists()

    # Check that the version matches the established default version
    with open(marker_file_path, "r") as file:
        assert file.read() == str(const.DEFAULT_INMANTA_DISK_LAYOUT_VERSION)


async def test_basics(agent, resource_container, clienthelper, client, environment):
    """
    This tests make sure the resource scheduler is working as expected for these parts:
        - Construction of initial model state
        - Retrieval of data when a new version is released
        - Use test::Resourcex to ensure the executor doesn't mutate the input
        - Test the endpoint to check scheduler internal state against the DB.
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
                        "key": "key1",
                        "value": "value",
                        "id": "test::Resourcex[%s,key=key1],v=%d" % (agent, version),
                        "requires": ["test::Resourcex[%s,key=key3],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                        "attributes": {"A": "B"},
                    },
                    {
                        "key": "key2",
                        "value": "value",
                        "id": "test::Resourcex[%s,key=key2],v=%d" % (agent, version),
                        "requires": ["test::Resourcex[%s,key=key1],v=%d" % (agent, version)],
                        "purged": not is_different,
                        "send_event": False,
                        "attributes": {"A": "B"},
                    },
                    {
                        "key": "key3",
                        "value": "value",
                        "id": "test::Resourcex[%s,key=key3],v=%d" % (agent, version),
                        "requires": [],
                        "purged": False,
                        "send_event": False,
                        "attributes": {"A": "B"},
                    },
                    {
                        "key": "key4",
                        "value": "value",
                        "id": "test::Resourcex[%s,key=key4],v=%d" % (agent, version),
                        "requires": ["test::Resourcex[%s,key=key3],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                        "attributes": {"A": "B"},
                    },
                    {
                        "key": "key5",
                        "value": "value",
                        "id": "test::Resourcex[%s,key=key5],v=%d" % (agent, version),
                        "requires": [
                            "test::Resourcex[%s,key=key4],v=%d" % (agent, version),
                            "test::Resourcex[%s,key=key1],v=%d" % (agent, version),
                        ],
                        "purged": False,
                        "send_event": False,
                        "attributes": {"A": "B"},
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
                "id": "test::Resourcex[agentx,key=key],v=%d" % version,
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

    result = await client.get_scheduler_status(env_id)
    assert result.code == 200

    expected_state = {"scheduler_state": {}, "db_state": {}, "discrepancies": {}, "resource_states": {}}
    assert result.result["data"] == expected_state

    # deploy and wait until one is ready
    result = await client.release_version(env_id, version1)
    assert result.code == 200

    await clienthelper.wait_for_released(version1)

    logger.info("first version released")

    await clienthelper.wait_for_deployed(version=1)

    deployed_resource_expected_status = {"blocked": "not_blocked", "last_deploy_result": "deployed", "compliance": "compliant"}
    failed_resource_expected_status = {"blocked": "not_blocked", "last_deploy_result": "failed", "compliance": "non_compliant"}
    skipped_resource_expected_status = {
        "blocked": "temporarily_blocked",
        "last_deploy_result": "skipped",
        "compliance": "non_compliant",
    }

    class ExpectedResourceStatus(NamedTuple):
        rid: str
        expected_status: dict[str, str]

    def selective_comparison(left_dict, right_dict):
        for field in ["discrepancies"]:
            left_value = left_dict.get(field)
            right_value = right_dict.get(field)
            assert left_value is not None and right_value is not None
            assert left_value == right_value

        left_state = left_dict.get("scheduler_state")
        right_state = right_dict.get("scheduler_state")

        assert left_state.keys() == right_state.keys()

        for k, left_r_state in left_state.items():
            right_r_state = right_state[k]
            left_r_state.pop("last_deployed")
            assert left_r_state == right_r_state

        return True

    def build_expected_state(
        all_resources: Sequence[str], specific_resources: Sequence[ExpectedResourceStatus]
    ) -> SchedulerStatusReport:
        """
        helper method to build a custom SchedulerStatusReport
        """
        expected_state = {
            "scheduler_state": {
                Id.parse_id(resource["id"]).resource_str(): deployed_resource_expected_status for resource in all_resources
            },
            "discrepancies": {},
            "db_state": {},
            "resource_states": {},
        }
        for resource_status in specific_resources:
            expected_state["scheduler_state"][resource_status.rid] = resource_status.expected_status

        return SchedulerStatusReport.model_validate(expected_state)

    v1_expected_result = []
    for i in range(1, 6):
        rid = f"test::Resourcex[agent1,key=key{i}]"
        result = failed_resource_expected_status if i == 3 else skipped_resource_expected_status
        v1_expected_result.append(ExpectedResourceStatus(rid=rid, expected_status=result))

    result = await client.get_scheduler_status(env_id)
    assert result.code == 200
    selective_comparison(result.result["data"], build_expected_state(resources, v1_expected_result).model_dump())

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

    # Assert that the resource_persistent_state table is consistent.
    result = await data.ResourcePersistentState.get_list(environment=environment)
    rid_to_rps = {r.resource_id: r for r in result}
    for agent in ["agent1", "agent2", "agent3"]:
        for key in ["key1", "key2", "key3", "key4", "key5"]:
            match (agent, key):
                case ("agent1", "key3"):
                    last_deploy_result = DeployResult.FAILED
                    compliance = Compliance.NON_COMPLIANT
                    blocked = Blocked.NOT_BLOCKED
                case ("agent1", _):
                    last_deploy_result = DeployResult.SKIPPED
                    compliance = Compliance.NON_COMPLIANT
                    blocked = Blocked.TEMPORARILY_BLOCKED
                case _:
                    last_deploy_result = DeployResult.DEPLOYED
                    compliance = Compliance.COMPLIANT
                    blocked = Blocked.NOT_BLOCKED
            assert_resource_persistent_state(
                resource_persistent_state=rid_to_rps[ResourceIdStr(f"test::Resourcex[{agent},key={key}]")],
                is_undefined=False,
                is_orphan=False,
                last_deploy_result=last_deploy_result,
                blocked=blocked.db_value(),
                expected_compliance=compliance,
            )

    version1, resources = await make_version(True)
    await clienthelper.put_version_simple(version=version1, resources=resources)
    await make_marker_version()
    introspect_state = await client.get_scheduler_status(env_id)
    assert introspect_state.code == 200, introspect_state
    # deploy and wait until one is ready
    result = await client.release_version(env_id, version1, push=False)
    assert result.code == 200
    await clienthelper.wait_for_released(version1)

    await clienthelper.wait_for_deployed(version=version1)

    await check_scheduler_state(resources, scheduler)

    await resource_action_consistency_check()
    assert resource_container.Provider.readcount("agentx", "key") == 0
    introspect_state = await client.get_scheduler_status(env_id)
    assert introspect_state.code == 200, introspect_state

    # Assert that the resource_persistent_state table is consistent.
    result = await data.ResourcePersistentState.get_list(environment=environment)
    rid_to_rps = {r.resource_id: r for r in result}
    for agent in ["agent1", "agent2", "agent3"]:
        for key in ["key1", "key2", "key3", "key4", "key5"]:
            match (agent, key):
                case ("agent1", "key3"):
                    last_deploy_result = DeployResult.FAILED
                    compliance = Compliance.NON_COMPLIANT
                    blocked = Blocked.NOT_BLOCKED
                case ("agent1", _):
                    last_deploy_result = DeployResult.SKIPPED
                    compliance = Compliance.NON_COMPLIANT
                    blocked = Blocked.TEMPORARILY_BLOCKED
                case _:
                    last_deploy_result = DeployResult.DEPLOYED
                    compliance = Compliance.COMPLIANT
                    blocked = Blocked.NOT_BLOCKED
            assert_resource_persistent_state(
                resource_persistent_state=rid_to_rps[ResourceIdStr(f"test::Resourcex[{agent},key={key}]")],
                is_undefined=False,
                is_orphan=False,
                last_deploy_result=last_deploy_result,
                blocked=blocked.db_value(),
                expected_compliance=compliance,
            )
    # Unreleased resources are not present in the resource_persistent_state table.
    assert ResourceIdStr("test::Resourcex[agentx,key=key]") not in rid_to_rps

    # deploy trigger
    await client.deploy(environment, agent_trigger_method=const.AgentTriggerMethod.push_incremental_deploy)

    await wait_full_success(client, environment)

    # Assert that the resource_persistent_state table is consistent.
    result = await data.ResourcePersistentState.get_list(environment=environment)
    rid_to_rps = {r.resource_id: r for r in result}
    for agent in ["agent1", "agent2", "agent3"]:
        for key in ["key1", "key2", "key3", "key4", "key5"]:
            assert_resource_persistent_state(
                resource_persistent_state=rid_to_rps[ResourceIdStr(f"test::Resourcex[{agent},key={key}]")],
                is_undefined=False,
                is_orphan=False,
                last_deploy_result=DeployResult.DEPLOYED,
                blocked=Blocked.NOT_BLOCKED,
                expected_compliance=Compliance.COMPLIANT,
            )
    # Unreleased resources are not present in the resource_persistent_state table.
    assert ResourceIdStr("test::Resourcex[agentx,key=key]") not in rid_to_rps

    result = await client.get_scheduler_status(env_id)
    assert result.code == 200
    selective_comparison(result.result["data"], build_expected_state(resources, []).model_dump())


async def check_server_state_vs_scheduler_state(client, environment, scheduler):
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    for item in result.result["data"]:
        the_id = item["resource_id"]
        status = item["status"]
        state = scheduler._state.resource_state[the_id]

        state_correspondence = {
            "deployed": DeployResult.DEPLOYED,
            "skipped": DeployResult.SKIPPED,
            "failed": DeployResult.FAILED,
        }

        assert state_correspondence[status] == state.last_deploy_result


async def check_scheduler_state(resources, scheduler):
    # State consistency check
    for resource in resources:
        id_without_version, _, _ = resource["id"].partition(",v=")
        assert id_without_version in scheduler._state.intent
        expected_resource_attributes = dict(resource)
        current_attributes = dict(scheduler._state.intent[id_without_version].attributes)
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


async def test_deploy_empty(server, client, clienthelper, environment, agent):
    """
    Test deployment of empty model
    """

    version = await clienthelper.get_version()

    resources = []

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["released"]

    async def is_active():
        r_versions = await client.list_desired_state_versions(environment)
        assert r_versions.code == 200
        versions = r_versions.result["data"]
        assert len(versions) == 1
        return versions[0]["status"] == "active"

    await retry_limited(is_active, 1)


async def test_deploy_to_empty(server, client, clienthelper, environment, agent, resource_container):
    """
    Test deployment of empty model after a not-empty model

    Ensure we unload all resources
    """
    env_id = environment
    scheduler = agent.scheduler

    async def make_version(is_different=False):
        """

        :param is_different: make the standard version or one with a change
        :return:
        """
        version = await clienthelper.get_version()
        agent = "agent1"
        resources = [
                    {
                        "key": "key1",
                        "value": "value",
                        "id": "test::Resourcex[%s,key=key1],v=%d" % (agent, version),
                        "requires": [],
                        "purged": False,
                        "send_event": False,
                        "attributes": {"A": "B"},
                    }

            ]
        return version, resources

    logger.info("setup done")
    version1, resources = await make_version()
    await clienthelper.put_version_simple(version=version1, resources=resources)

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = await client.release_version(env_id, version1)
    assert result.code == 200

    await clienthelper.wait_for_released(version1)

    logger.info("first version released")

    await clienthelper.wait_for_deployed(version=1)

    assert len(scheduler._state.resource_state) == 1

    version = await clienthelper.get_version()
    resources = []
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]

    async def is_active():
        r_versions = await client.list_desired_state_versions(environment)
        assert r_versions.code == 200
        versions = r_versions.result["data"]
        assert len(versions) == 2
        return versions[0]["status"] == "active"

    await retry_limited(is_active, 1)
    assert len(scheduler._state.resource_state) == 0


async def test_deploy_with_undefined(server, client, resource_container, agent, environment, clienthelper):
    """
    Test deploy of resource with undefined
    """
    Config.set("config", "agent-deploy-interval", "100")

    resource_container.Provider.reset()
    resource_container.Provider.set_skip("agent2", "key1", 1)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent2,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key2],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "value": execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Resource[agent2,key=key1],v=%d" % version, "test::Resource[agent2,key=key2],v=%d" % version],
            "purged": False,
        },
        {
            "key": "key5",
            "value": "val",
            "id": "test::Resource[agent2,key=key5],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
            "purged": False,
        },
    ]

    status = {
        "test::Resource[agent2,key=key4]": const.ResourceState.undefined,
        "test::Resource[agent2,key=key2]": const.ResourceState.undefined,
    }
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

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["released"]

    # The server will mark the full version as deployed even though the agent has not done anything yet.
    result = await client.get_version(environment, version)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment)

    actions = await data.ResourceAction.get_list()
    assert len([x for x in actions if x.status == const.ResourceState.undefined]) >= 1

    result = await client.get_version(environment, version)
    assert result.code == 200

    assert resource_container.Provider.changecount("agent2", "key4") == 0
    assert resource_container.Provider.changecount("agent2", "key5") == 0
    assert resource_container.Provider.changecount("agent2", "key1") == 0

    assert resource_container.Provider.readcount("agent2", "key4") == 0
    assert resource_container.Provider.readcount("agent2", "key5") == 0
    assert resource_container.Provider.readcount("agent2", "key1") == 1

    # Do a second deploy of the same model on agent2 with undefined resources
    result = await client.deploy(
        tid=environment, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy, agents=["agent2"]
    )
    assert result.code == 200

    def done():
        return (
            resource_container.Provider.changecount("agent2", "key4") == 0
            and resource_container.Provider.changecount("agent2", "key5") == 0
            and resource_container.Provider.changecount("agent2", "key1") == 1
            and resource_container.Provider.readcount("agent2", "key4") == 0
            and resource_container.Provider.readcount("agent2", "key5") == 0
            and resource_container.Provider.readcount("agent2", "key1") == 2
        )

    await retry_limited(done, 100)
    await resource_action_consistency_check()


async def test_failing_deploy_no_handler(resource_container, agent, environment, client, clienthelper, async_finalizer):
    """
    dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Noprov[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": [],
        }
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["total"] == 1

    result = await client.get_version(environment, version)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment)

    result = await client.get_version(environment, version, include_logs=True)

    logs = result.result["resources"][0]["actions"][0]["messages"]
    assert any("traceback" in log["kwargs"] for log in logs), "\n".join(result.result["resources"][0]["actions"][0]["messages"])

    resource_persistent_state = await data.ResourcePersistentState.get_one(
        environment=environment, resource_id="test::Noprov[agent1,key=key1]"
    )
    assert_resource_persistent_state(
        resource_persistent_state=resource_persistent_state,
        is_undefined=False,
        is_orphan=False,
        last_deploy_result=DeployResult.FAILED,
        blocked=Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.NON_COMPLIANT,
    )


@pytest.mark.parametrize("halted", [True, False])
async def test_unknown_parameters(
    resource_container, environment, client, server, clienthelper, agent_no_state_check, halted, caplog
):
    """
    Test retrieving facts from the agent
    """

    caplog.set_level(logging.DEBUG)
    resource_container.Provider.reset()
    await client.set_setting(environment, SERVER_COMPILE, False)

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        }
    ]

    unknowns = [{"resource": resource_id_wov, "parameter": "length", "source": "fact"}]

    if halted:
        result = await client.halt_environment(environment)
        assert result.code == 200

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=unknowns,
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await server.get_slice(SLICE_PARAM).renew_facts()

    env_id = uuid.UUID(environment)
    if not halted:
        params = await data.Parameter.get_list(environment=env_id, resource_id=resource_id_wov)
        while len(params) < 3:
            params = await data.Parameter.get_list(environment=env_id, resource_id=resource_id_wov)
            await asyncio.sleep(0.1)

        result = await client.get_param(env_id, "length", resource_id_wov)
        assert result.code == 200
        msg = f"Requesting value for unknown parameter length of resource test::Resource[agent1,key=key] in env {environment}"
        log_contains(caplog, "inmanta.server.services.paramservice", logging.DEBUG, msg)

    else:
        msg = "Requesting value for 0 unknowns"
        log_contains(caplog, "inmanta.server.services.paramservice", logging.DEBUG, msg)


async def test_fail(resource_container, client, agent, environment, clienthelper, async_finalizer):
    """
    Test results when a step fails
    """
    resource_container.Provider.reset()

    resource_container.Provider.set("agent1", "key", "value")

    env_id = environment

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": "test::Fail[agent1,key=key],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": ["test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key3",
            "value": "value",
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "requires": ["test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key4",
            "value": "value",
            "id": "test::Resource[agent1,key=key4],v=%d" % version,
            "requires": ["test::Resource[agent1,key=key3],v=%d" % version],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key5",
            "value": "value",
            "id": "test::Resource[agent1,key=key5],v=%d" % version,
            "requires": ["test::Resource[agent1,key=key4],v=%d" % version, "test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # deploy and wait until done
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await wait_until_deployment_finishes(client, env_id)

    result = await client.resource_list(env_id)

    states = {x["resource_id"]: x["status"] for x in result.result["data"]}

    assert states["test::Fail[agent1,key=key]"] == "failed"
    assert states["test::Resource[agent1,key=key2]"] == "skipped"
    assert states["test::Resource[agent1,key=key3]"] == "skipped"
    assert states["test::Resource[agent1,key=key4]"] == "skipped"
    assert states["test::Resource[agent1,key=key5]"] == "skipped"

    for rid, status in states.items():
        resource_persistent_state = await data.ResourcePersistentState.get_one(
            environment=environment, resource_id=ResourceIdStr(rid)
        )
        assert_resource_persistent_state(
            resource_persistent_state=resource_persistent_state,
            is_undefined=False,
            is_orphan=False,
            last_deploy_result=DeployResult.FAILED if status == "failed" else DeployResult.SKIPPED,
            blocked=Blocked.NOT_BLOCKED if status == "failed" else Blocked.TEMPORARILY_BLOCKED.db_value(),
            expected_compliance=Compliance.NON_COMPLIANT,
        )


class ResourceProvider:
    def __init__(self, index, name, producer, state=None):
        self.name = name
        self.producer = producer
        self.state = state
        self.index = index

    def get_resource(
        self, resource_container, agent: str, key: str, version: str, requires: list[str]
    ) -> tuple[dict[str, str], Optional[const.ResourceState]]:
        base = {
            "key": key,
            "value": "value1",
            "id": "test::Resource[%s,key=%s],v=%d" % (agent, key, version),
            "send_event": True,
            "receive_events": False,
            "purged": False,
            "requires": requires,
        }

        self.producer(resource_container.Provider, agent, key)

        state = None
        if self.state is not None:
            state = (f"test::Resource[{agent},key={key}]", self.state)

        return base, state

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


# for events, self is the consuming node
# dep is the producer/required node
self_states = [
    ResourceProvider(0, "skip", lambda p, a, k: p.set_skip(a, k, 1)),
    ResourceProvider(1, "fail", lambda p, a, k: p.set_fail(a, k, 1)),
    ResourceProvider(2, "success", lambda p, a, k: None),
    ResourceProvider(3, "undefined", lambda p, a, k: None, const.ResourceState.undefined),
]

dep_states = [
    ResourceProvider(0, "skip", lambda p, a, k: p.set_skip(a, k, 1)),
    ResourceProvider(1, "fail", lambda p, a, k: p.set_fail(a, k, 1)),
    ResourceProvider(2, "success", lambda p, a, k: None),
]


def make_matrix(matrix: str, valueparser: Callable[[str], bool]) -> list[list[bool]]:
    """
    Expect matrix of the form

        header1    header2     header3
    row1    y    y    n
    """
    unparsed = [[v for v in row.split()][1:] for row in matrix.strip().split("\n")][1:]

    return [[valueparser(nsv) for nsv in nv] for nv in unparsed]


# self state on X axis
# dep state on the Y axis
dorun = make_matrix(
    """
        skip    fail    success    undef
skip    n    n    n    n
fail    n    n    n    n
succ    y    y    y    n
""",
    lambda x: x == "y",
)

dochange = make_matrix(
    """
        skip    fail    success    undef
skip    n    n    n    n
fail    n    n    n    n
succ    n    n    y    n
""",
    lambda x: x == "y",
)


@pytest.mark.parametrize("self_state", self_states, ids=lambda x: x.name)
@pytest.mark.parametrize("dep_state", dep_states, ids=lambda x: x.name)
async def test_deploy_and_events(
    client, agent, clienthelper, environment, resource_container, self_state, dep_state, async_finalizer
):
    resource_container.Provider.reset()

    version = await clienthelper.get_version()

    (dep, dep_status) = dep_state.get_resource(resource_container, "agent1", "key2", version, [])
    (own, own_status) = self_state.get_resource(
        resource_container,
        "agent1",
        "key3",
        version,
        ["test::Resource[agent1,key=key2],v=%d" % version, "test::Resource[agent1,key=key1],v=%d" % version],
    )

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": True,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        dep,
        own,
    ]

    status = {x[0]: x[1] for x in [dep_status, own_status] if x is not None}
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

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3

    result = await client.get_version(environment, version)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment)

    # verify against result matrices
    assert dorun[dep_state.index][self_state.index] == (resource_container.Provider.readcount("agent1", "key3") > 0)
    assert dochange[dep_state.index][self_state.index] == (resource_container.Provider.changecount("agent1", "key3") > 0)


dep_states_reload = [
    ResourceProvider(0, "skip", lambda p, a, k: p.set_skip(a, k, 1)),
    ResourceProvider(0, "fail", lambda p, a, k: p.set_fail(a, k, 1)),
    ResourceProvider(0, "nochange", lambda p, a, k: p.set(a, k, "value1")),
    ResourceProvider(1, "changed", lambda p, a, k: None),
]


@pytest.mark.parametrize("dep_state", dep_states_reload, ids=lambda x: x.name)
async def test_reload(server, client, clienthelper, environment, resource_container, dep_state, agent):

    resource_container.Provider.reset()

    version = await clienthelper.get_version()

    (dep, dep_status) = dep_state.get_resource(resource_container, "agent1", "key1", version, [])

    resources = [
        {
            "key": "key2",
            "value": "value1",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": True,
            "receive_events": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
        },
        dep,
    ]

    status = {x[0]: x[1] for x in [dep_status] if x is not None}
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

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["total"] == 2

    result = await client.get_version(environment, version)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment)

    assert dep_state.index == resource_container.Provider.reloadcount("agent1", "key2")

    result = await data.ResourcePersistentState.get_list(environment=environment)
    result_per_resource_id = {r.resource_id: r for r in result}
    assert_resource_persistent_state(
        resource_persistent_state=result_per_resource_id[ResourceIdStr("test::Resource[agent1,key=key2]")],
        is_undefined=False,
        is_orphan=False,
        last_deploy_result=DeployResult.SKIPPED if dep_state.name in {"skip", "fail"} else DeployResult.DEPLOYED,
        blocked=Blocked.TEMPORARILY_BLOCKED.db_value() if dep_state.name in {"skip", "fail"} else Blocked.NOT_BLOCKED,
        expected_compliance=(Compliance.NON_COMPLIANT if dep_state.name in {"skip", "fail"} else Compliance.COMPLIANT),
    )


async def test_inprogress(resource_container, server, client, clienthelper, environment, agent):
    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Wait[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        }
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    async def in_progress():
        result = await client.resource_list(environment, version)
        assert result.code == 200
        res = result.result["data"][0]
        status = res["status"]
        return status == "deploying"

    await retry_limited(in_progress, 30)

    result = await data.ResourcePersistentState.get_list(environment=environment)
    assert len(result) == 1
    assert_resource_persistent_state(
        resource_persistent_state=result[0],
        is_undefined=False,
        is_orphan=False,
        last_deploy_result=DeployResult.NEW,
        blocked=Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.HAS_UPDATE,
    )

    await resource_container.wait_for_done_with_waiters(client, environment, version)


async def test_resource_status(resource_container, server, client, clienthelper, environment, agent):
    """
    Verify that the resource_status column in the resource_persistent_state table contains correct data.
    """
    resource_container.Provider.reset()
    env_id = environment

    result = await client.set_setting(environment, "auto_deploy", False)
    assert result.code == 200

    def get_resources(version: int) -> list[dict[str, object]]:
        return [
            {
                "key": "key1",
                "value": "value",
                "id": f"test::Resource[agent1,key=key1],v={version}",
                "requires": [],
                "purged": False,
                "send_event": False,
                "receive_events": False,
            },
            {
                "key": "key2",
                "value": "value",
                "id": f"test::Resource[agent1,key=key2],v={version}",
                "requires": [],
                "purged": False,
                "send_event": False,
                "receive_events": False,
            },
            {
                "key": "key3",
                "value": "value",
                "id": f"test::Resource[agent1,key=key3],v={version}",
                "requires": [f"test::Resource[agent1,key=key2],v={version}"],
                "purged": False,
                "send_event": False,
                "receive_events": False,
            },
            {
                "key": "key4",
                "value": f"value-{version}",  # Make sure the attribute_hash changes on each version
                "id": f"test::Resource[agent1,key=key4],v={version}",
                "requires": [],
                "purged": False,
                "send_event": False,
                "receive_events": False,
            },
            {
                "key": "key5",
                "value": "value",
                "id": f"test::Resource[agent1,key=key5],v={version}",
                "requires": [f"test::Resource[agent1,key=key4],v={version}"],
                "purged": False,
                "send_event": False,
                "receive_events": False,
            },
        ]

    async def deploy_resources(
        version: int, resources: list[dict[str, object]], resource_state: dict[ResourceIdStr, const.ResourceState]
    ) -> None:
        result = await client.put_version(
            tid=env_id,
            version=version,
            resources=resources,
            resource_state=resource_state,
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert result.code == 200, result.result

        # deploy and wait until done
        result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
        assert result.code == 200

        result = await client.get_version(env_id, version)
        assert result.code == 200

        await wait_until_deployment_finishes(client, env_id, version=version)

    resource_container.Provider.set_fail("agent1", "key2", 1)
    version = await clienthelper.get_version()
    await deploy_resources(
        version=version,
        resources=get_resources(version),
        resource_state={
            ResourceIdStr("test::Resource[agent1,key=key1]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key2]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key3]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key4]"): const.ResourceState.undefined,
            ResourceIdStr("test::Resource[agent1,key=key5]"): const.ResourceState.available,
        },
    )
    result = await data.ResourcePersistentState.get_list(environment=environment)
    result_per_resource_id = {r.resource_id: r for r in result}
    assert_resource_persistent_state(
        resource_persistent_state=result_per_resource_id[ResourceIdStr("test::Resource[agent1,key=key1]")],
        is_undefined=False,
        is_orphan=False,
        last_deploy_result=DeployResult.DEPLOYED,
        blocked=Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.COMPLIANT,
    )
    assert_resource_persistent_state(
        resource_persistent_state=result_per_resource_id[ResourceIdStr("test::Resource[agent1,key=key2]")],
        is_undefined=False,
        is_orphan=False,
        last_deploy_result=DeployResult.FAILED,
        blocked=Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.NON_COMPLIANT,
    )
    assert_resource_persistent_state(
        resource_persistent_state=result_per_resource_id[ResourceIdStr("test::Resource[agent1,key=key3]")],
        is_undefined=False,
        is_orphan=False,
        last_deploy_result=DeployResult.SKIPPED,
        blocked=Blocked.TEMPORARILY_BLOCKED.db_value(),
        expected_compliance=Compliance.NON_COMPLIANT,
    )
    assert_resource_persistent_state(
        resource_persistent_state=result_per_resource_id[ResourceIdStr("test::Resource[agent1,key=key4]")],
        is_undefined=True,
        is_orphan=False,
        last_deploy_result=DeployResult.NEW,
        blocked=Blocked.BLOCKED,
        expected_compliance=Compliance.UNDEFINED,
    )
    assert_resource_persistent_state(
        resource_persistent_state=result_per_resource_id[ResourceIdStr("test::Resource[agent1,key=key5]")],
        is_undefined=False,
        is_orphan=False,
        last_deploy_result=DeployResult.NEW,
        blocked=Blocked.BLOCKED,
        expected_compliance=Compliance.HAS_UPDATE,
    )

    # * Remove key1, so that it becomes orphan
    # * Make key2 no longer fail
    # * Make key4 no longer undefined
    version = await clienthelper.get_version()
    await deploy_resources(
        version=version,
        resources=get_resources(version)[1:],  # key1 becomes orphan
        resource_state={
            ResourceIdStr("test::Resource[agent1,key=key2]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key3]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key4]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key5]"): const.ResourceState.available,
        },
    )
    result = await data.ResourcePersistentState.get_list(environment=environment)
    result_per_resource_id = {r.resource_id: r for r in result}
    for i in range(1, 6):
        assert_resource_persistent_state(
            resource_persistent_state=result_per_resource_id[ResourceIdStr(f"test::Resource[agent1,key=key{i}]")],
            is_undefined=False,
            is_orphan=(i == 1),
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            expected_compliance=None if i == 1 else Compliance.COMPLIANT,
        )

    # Make key4 undefined again
    version = await clienthelper.get_version()
    await deploy_resources(
        version=version,
        resources=get_resources(version),
        resource_state={
            ResourceIdStr("test::Resource[agent1,key=key1]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key2]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key3]"): const.ResourceState.available,
            ResourceIdStr("test::Resource[agent1,key=key4]"): const.ResourceState.undefined,
            ResourceIdStr("test::Resource[agent1,key=key5]"): const.ResourceState.available,
        },
    )
    result = await data.ResourcePersistentState.get_list(environment=environment)
    result_per_resource_id = {r.resource_id: r for r in result}
    for i in range(1, 4):
        assert_resource_persistent_state(
            resource_persistent_state=result_per_resource_id[ResourceIdStr(f"test::Resource[agent1,key=key{i}]")],
            is_undefined=False,
            is_orphan=False,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            expected_compliance=Compliance.COMPLIANT,
        )
    assert_resource_persistent_state(
        resource_persistent_state=result_per_resource_id[ResourceIdStr("test::Resource[agent1,key=key4]")],
        is_undefined=True,
        is_orphan=False,
        last_deploy_result=DeployResult.DEPLOYED,
        blocked=Blocked.BLOCKED,
        expected_compliance=Compliance.UNDEFINED,
    )
    assert_resource_persistent_state(
        resource_persistent_state=result_per_resource_id[ResourceIdStr("test::Resource[agent1,key=key5]")],
        is_undefined=False,
        is_orphan=False,
        last_deploy_result=DeployResult.DEPLOYED,
        blocked=Blocked.BLOCKED,
        expected_compliance=Compliance.COMPLIANT,
    )


async def test_lsm_states(resource_container, server, client, clienthelper, environment, agent):
    version = await clienthelper.get_version()

    resource_container.Provider.set_fail("agent1", "key", 1)

    rid1 = "test::Resource[agent1,key=key]"
    rid2 = "test::Resource[agent1,key=key2]"
    lsmrid = "test::LSMLike[agent1,key=key3]"

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": f"{rid1},v={version}",
            "requires": [],
            "purged": False,
            "send_event": True,
            "receive_events": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": f"{rid2},v={version}",
            "requires": [rid1],
            "purged": False,
            "send_event": True,
            "receive_events": False,
        },
        {
            "key": "key3",
            "value": "value",
            "id": f"{lsmrid},v={version}",
            "requires": [rid1, rid2],
            "purged": False,
            "send_event": True,
            "receive_events": False,
        },
    ]
    await clienthelper.set_auto_deploy(True)
    await clienthelper.put_version_simple(resources, version, wait_for_released=True)
    await clienthelper.wait_for_deployed()

    result = await client.resource_list(environment)
    assert result.code == 200
    state_map = {r["resource_id"]: r["status"] for r in result.result["data"]}
    # One failure, one skip, in the depdencies
    # response is failure
    assert state_map == {rid1: "failed", rid2: "skipped", lsmrid: "failed"}


async def test_skipped_for_dependency(resource_container, server, client, clienthelper, environment, agent):
    """
    Asserts the state of a resource, on the scheduler, whose dependency has been skipped
    """
    version = await clienthelper.get_version()

    resource_container.Provider.set_skip("agent1", "key", 2)

    rid1 = "test::Resource[agent1,key=key]"
    rid2 = "test::Resource[agent1,key=key2]"

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": f"{rid1},v={version}",
            "requires": [],
            "purged": False,
            "send_event": True,
            "receive_events": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": f"{rid2},v={version}",
            "requires": [rid1],
            "purged": False,
            "send_event": True,
            "receive_events": False,
        },
    ]
    await clienthelper.set_auto_deploy(True)
    await clienthelper.put_version_simple(resources, version, wait_for_released=True)
    await clienthelper.wait_for_deployed(version=version)
    scheduler = agent.scheduler
    assert scheduler._state.resource_state[rid2] == ResourceState(
        compliance=Compliance.NON_COMPLIANT,
        last_deploy_result=DeployResult.SKIPPED,
        blocked=Blocked.TEMPORARILY_BLOCKED,
        last_deployed=scheduler._state.resource_state[rid2].last_deployed,  # ignore
    )
    assert scheduler._state.resource_state[rid1] == ResourceState(
        compliance=Compliance.NON_COMPLIANT,
        last_deploy_result=DeployResult.SKIPPED,
        blocked=Blocked.NOT_BLOCKED,
        last_deployed=scheduler._state.resource_state[rid1].last_deployed,  # ignore
    )

    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key",
            "value": "value",
            "id": f"{rid1},v={version}",
            "requires": [],
            "purged": False,
            "send_event": True,
            "receive_events": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": f"{rid2},v={version}",
            "requires": [],
            "purged": False,
            "send_event": True,
            "receive_events": False,
        },
    ]
    await clienthelper.set_auto_deploy(True)
    await clienthelper.put_version_simple(resources, version, wait_for_released=True)

    async def wait_for_resource_state() -> bool:
        if scheduler._state.resource_state[rid1] != ResourceState(
            compliance=Compliance.NON_COMPLIANT,
            last_deploy_result=DeployResult.SKIPPED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=scheduler._state.resource_state[rid1].last_deployed,  # ignore
        ):
            return False
        if scheduler._state.resource_state[rid2] != ResourceState(
            compliance=Compliance.COMPLIANT,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=scheduler._state.resource_state[rid2].last_deployed,  # ignore
        ):
            return False
        return True

    # We can't rely on clienthelper.wait_for_deployed() here to wait until the re-deployment has finished,
    # because that method waits only until all resources reach a deployed state, not necessarily until the scheduler is stable
    await retry_limited(wait_for_resource_state, timeout=10)


async def test_redeploy_after_dependency_recovered(resource_container, server, client, clienthelper, environment, agent):
    """
    Asserts that a transiently skipped resource recovers when its dependencies succeed
    """
    version = await clienthelper.get_version()

    # Disable auto deploys and repairs
    Config.set("config", "agent-repair-interval", "0")
    Config.set("config", "agent-deploy-interval", "0")

    resource_container.Provider.set_fail("agent1", "key", 1)

    rid1 = "test::Resource[agent1,key=key]"
    rid2 = "test::Resource[agent1,key=key2]"

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": f"{rid1},v={version}",
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": f"{rid2},v={version}",
            "requires": [rid1],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
    ]
    await clienthelper.set_auto_deploy(True)
    await clienthelper.put_version_simple(resources, version, wait_for_released=True)

    await clienthelper.wait_for_deployed()
    scheduler = agent.scheduler
    assert scheduler._state.resource_state[rid2] == ResourceState(
        compliance=Compliance.NON_COMPLIANT,
        last_deploy_result=DeployResult.SKIPPED,
        blocked=Blocked.TEMPORARILY_BLOCKED,
        last_deployed=scheduler._state.resource_state[rid2].last_deployed,  # ignore
    )
    assert scheduler._state.resource_state[rid1] == ResourceState(
        compliance=Compliance.NON_COMPLIANT,
        last_deploy_result=DeployResult.FAILED,
        blocked=Blocked.NOT_BLOCKED,
        last_deployed=scheduler._state.resource_state[rid1].last_deployed,  # ignore
    )

    # Trigger deploy without incrementing version
    await scheduler.deploy_resource(rid1, reason="Deploy rid1", priority=TaskPriority.USER_DEPLOY)

    async def wait_for_resource_state() -> bool:
        if scheduler._state.resource_state[rid1] != ResourceState(
            compliance=Compliance.COMPLIANT,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=scheduler._state.resource_state[rid1].last_deployed,  # ignore
        ):
            return False
        if scheduler._state.resource_state[rid2] != ResourceState(
            compliance=Compliance.COMPLIANT,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=scheduler._state.resource_state[rid2].last_deployed,  # ignore
        ):
            return False
        return True

    # We can't rely on clienthelper.wait_for_deployed() here to wait until the re-deployment has finished,
    # because that method assumes we are deploying a version that hasn't been deployed before.
    await retry_limited(wait_for_resource_state, timeout=10)

    # Assert that no new version was created
    result = await client.list_versions(tid=environment)
    assert result.code == 200
    versions = result.result["versions"]
    assert len(versions) == 1
    assert versions[0]["version"] == version
