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

import uuid
from collections import abc
from urllib import parse

import pytest

from inmanta import const, data, util
from inmanta.agent.handler import DiscoveryHandler, HandlerContext, provider
from inmanta.data import ResourceIdStr
from inmanta.data.model import BaseModel
from inmanta.resources import DiscoveryResource, Id, resource
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.util import retry_limited
from utils import wait_for_n_deployed_resources


@pytest.fixture
def all_values() -> list[str]:
    """
    This fixture returns a list of values that will be discovered by the handler registered via the
    discovery_resource_and_handler fixture.
    """
    return ["one", "two", "three"]


@pytest.fixture
def discovery_resource_and_handler(all_values: list[str]) -> None:
    """
    This fixture registers a DiscoveryResource and DiscoveryHandler that discovers all the values returned by
    the all_values fixtures.
    """

    @resource("test::MyDiscoveryResource", agent="discovery_agent", id_attribute="key")
    class MyDiscoveryResource(DiscoveryResource):
        fields = ("key",)

    class MyUnmanagedResource(BaseModel):
        val: str

    @provider("test::MyDiscoveryResource", name="my_discovery_handler")
    class MyDiscoveryHandler(DiscoveryHandler[MyDiscoveryResource, MyUnmanagedResource]):
        def discover_resources(
            self, ctx: HandlerContext, discovery_resource: MyDiscoveryResource
        ) -> abc.Mapping[ResourceIdStr, MyUnmanagedResource]:
            return {
                Id(
                    entity_type="test::MyUnmanagedResource",
                    agent_name="discovery_agent",
                    attribute="val",
                    attribute_value=val,
                ).resource_str(): MyUnmanagedResource(val=val)
                for val in all_values
            }


async def test_discovery_resource_handler_basic_test(
    server,
    client,
    clienthelper,
    environment,
    agent,
    discovery_resource_and_handler,
    all_values: list[str],
):
    """
    This test case verifies the basic functionality of a DiscoveryHandler.
    Is also verifies that executing a dry-run or a get-fact request on a DiscoveryResource doesn't fail
    and doesn't do anything by default.
    """

    version = await clienthelper.get_version()
    resource_id = "test::MyDiscoveryResource[discovery_agent,key=key1]"
    resource_version_id = f"{resource_id},v={version}"

    resources = [
        {
            "key": "key1",
            "id": resource_version_id,
            "send_event": True,
            "purged": False,
            "requires": [],
        }
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=util.get_compiler_version(),
    )
    assert result.code == 200

    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    assert resource_list, resource_list

    # Ensure that a dry-run doesn't do anything for a DiscoveryHandler
    result = await client.dryrun_request(tid=environment, id=1)
    assert result.code == 200
    dry_run_id = result.result["dryrun"]["id"]

    async def dry_run_finished() -> bool:
        result = await client.dryrun_report(tid=environment, id=dry_run_id)
        assert result.code == 200
        return result.result["dryrun"]["todo"] == 0

    await util.retry_limited(dry_run_finished, timeout=10)

    result = await client.dryrun_report(tid=environment, id=dry_run_id)
    assert result.code == 200
    resources_in_dryrun = result.result["dryrun"]["resources"]
    assert len(resources_in_dryrun) == 1
    assert not resources_in_dryrun[resource_version_id]["changes"], resources_in_dryrun

    # Ensure that the deployment of the DiscoveryResource results in discovered resources.
    result = await client.release_version(environment, version, push=True)
    assert result.code == 200

    await wait_for_n_deployed_resources(client, environment, version, n=1)

    # Test batch retrieval
    result = await client.discovered_resources_get_batch(environment)
    assert result.code == 200
    discovered = result.result["data"]
    expected = [
        {
            "discovered_resource_id": f"test::MyUnmanagedResource[discovery_agent,val={val}]",
            "values": {"val": val},
            "managed_resource_uri": None,
            "discovery_resource_id": resource_id,
            "discovery_resource_uri": f"/api/v2/resource/{parse.quote(resource_id)}",
        }
        for val in all_values
    ]

    def sort_on_discovered_resource_id(elem):
        return elem["discovered_resource_id"]

    assert sorted(discovered, key=sort_on_discovered_resource_id) == sorted(expected, key=sort_on_discovered_resource_id)

    # Test single resource retrieval

    result = await client.discovered_resources_get(
        environment, f"test::MyUnmanagedResource[discovery_agent,val={all_values[0]}]"
    )
    assert result.code == 200
    assert result.result["data"] == expected[0]

    # Make sure that a get_facts call on a DiscoveryHandler doesn't fail
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    status_code, message = await agent_manager.request_parameter(env_id=uuid.UUID(environment), resource_id=resource_id)
    assert status_code == 503, message

    async def fact_discovery_finished_successfully() -> bool:
        result = await client.get_resource_actions(
            tid=environment,
            resource_type="test::MyDiscoveryResource",
            agent="discovery_agent",
            attribute="key",
            attribute_value="key1",
        )
        assert result.code == 200
        get_fact_actions = [a for a in result.result["data"] if a["action"] == const.ResourceAction.getfact.value]
        return len(get_fact_actions) > 0

    await retry_limited(fact_discovery_finished_successfully, timeout=10)


@pytest.mark.parametrize("direct_dependency_failed", [True, False])
async def test_discovery_resource_requires_provides(
    server,
    agent,
    client,
    clienthelper,
    environment,
    discovery_resource_and_handler,
    all_values: list[str],
    direct_dependency_failed: bool,
):
    """
    This test verifies that the requires/provides relationships are taken into account for a DiscoveryResource.
    """

    version = await clienthelper.get_version()

    if direct_dependency_failed:
        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": f"test::FailFastCRUD[agent1,key=key1],v={version}",
                "send_event": True,
                "purged": False,
                "purge_on_delete": False,
                "requires": [],
            },
            {
                "key": "key1",
                "id": f"test::MyDiscoveryResource[discovery_agent,key=key1],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [f"test::FailFastCRUD[agent1,key=key1],v={version}"],
            },
        ]
    else:
        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": f"test::FailFastCRUD[agent1,key=key1],v={version}",
                "send_event": True,
                "purged": False,
                "purge_on_delete": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": f"test::Resource[agent1,key=key2],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [f"test::FailFastCRUD[agent1,key=key1],v={version}"],
            },
            {
                "key": "key1",
                "id": f"test::MyDiscoveryResource[discovery_agent,key=key1],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [f"test::Resource[agent1,key=key2],v={version}"],
            },
        ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=util.get_compiler_version(),
    )
    assert result.code == 200, result.result

    result = await client.release_version(environment, version, push=True)
    assert result.code == 200

    await wait_for_n_deployed_resources(client, environment, version, n=len(resources))

    result = await client.get_version(tid=environment, id=version)
    assert result.code == 200
    discovery_resources = [r for r in result.result["resources"] if r["resource_type"] == "test::MyDiscoveryResource"]
    assert len(discovery_resources) == 1
    assert discovery_resources[0]["status"] == "skipped"

    result = await client.discovered_resources_get_batch(environment)
    assert result.code == 200
    assert result.result["data"] == []
