"""
Copyright 2026 Inmanta

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

from collections import abc

import pytest

from inmanta import config, const
from inmanta.agent.handler import DiscoveryHandler, HandlerContext, provider
from inmanta.data.model import BaseModel
from inmanta.resources import DiscoveryResource, Id, resource
from inmanta.types import ResourceIdStr
from utils import wait_until_deployment_finishes

MAX_REQUEST_BODY_SIZE = 1024 * 1024


@pytest.fixture
def server_pre_start(server_config) -> None:
    config.Config.set("server", "max-request-body-size", str(MAX_REQUEST_BODY_SIZE))


def discovered_value(i: int) -> str:
    """
    The value of the i-th discovered resource: 1 kB for the first 100 resources and 30 kB for the others.
    """
    return f"{i:0{1_000 if i < 100 else 30_000}}"


def discovered_resource_id(i: int) -> ResourceIdStr:
    return Id(
        entity_type="test::LargeUnmanagedResource",
        agent_name="discovery_agent",
        attribute="key",
        attribute_value=str(i),
    ).resource_str()


async def deploy_discovery_resource(client, clienthelper, environment: str, batch_size: int) -> ResourceIdStr:
    """
    Deploy a discovery resource whose handler discovers 200 resources and reports them in batches of the given size.
    Return the id of the discovery resource.
    """

    @resource("test::LargeDiscoveryResource", agent="discovery_agent", id_attribute="key")
    class LargeDiscoveryResource(DiscoveryResource):
        fields = ("key",)

    class LargeUnmanagedResource(BaseModel):
        val: str

    @provider("test::LargeDiscoveryResource", name="large_discovery_handler")
    class LargeDiscoveryHandler(DiscoveryHandler[LargeDiscoveryResource, LargeUnmanagedResource]):
        discovered_resources_batch_size = batch_size

        def discover_resources(
            self, ctx: HandlerContext, discovery_resource: LargeDiscoveryResource
        ) -> abc.Mapping[ResourceIdStr, LargeUnmanagedResource]:
            return {discovered_resource_id(i): LargeUnmanagedResource(val=discovered_value(i)) for i in range(200)}

    version = await clienthelper.get_version()
    resource_id = ResourceIdStr("test::LargeDiscoveryResource[discovery_agent,key=key1]")
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[{"key": "key1", "id": f"{resource_id},v={version}", "send_event": True, "purged": False, "requires": []}],
        unknowns=[],
        version_info={},
        module_version_info={},
    )
    assert result.code == 200, result.result
    result = await client.release_version(environment, version, push=True)
    assert result.code == 200, result.result
    await wait_until_deployment_finishes(client, environment, version=version)
    return resource_id


async def get_discovered_values(client, environment: str) -> dict[str, object]:
    return {
        discovered.discovered_resource_id: discovered.values
        async for discovered in client.discovered_resources_get_batch(environment, limit=50).all()
    }


async def test_discovery_handler_reports_in_batches(server, client, clienthelper, environment, agent) -> None:
    """
    Verify that a DiscoveryHandler reports its discovered resources in batches of discovered_resources_batch_size,
    so that a discovery whose result is too large for a single request to the server still succeeds.
    """
    # The 200 discovered resources are about 3 MB in total, while one batch of 20 is at most 600 kB
    resource_id = await deploy_discovery_resource(client, clienthelper, environment, batch_size=20)

    result = await client.resource_details(tid=environment, rid=resource_id)
    assert result.code == 200, result.result
    assert result.result["data"]["status"] == const.ResourceState.deployed.value

    assert await get_discovered_values(client, environment) == {
        discovered_resource_id(i): {"val": discovered_value(i)} for i in range(200)
    }


async def test_discovery_handler_batch_too_large(server, client, clienthelper, environment, agent) -> None:
    """
    Verify that a DiscoveryHandler fails when a batch is rejected by the server. The batches before it stay stored and
    the batches after it are not sent.
    """
    # The first two batches of 50 hold 1 kB values and fit in a request. The third holds 30 kB values: 1.5 MB.
    resource_id = await deploy_discovery_resource(client, clienthelper, environment, batch_size=50)

    result = await client.resource_details(tid=environment, rid=resource_id)
    assert result.code == 200, result.result
    assert result.result["data"]["status"] == const.ResourceState.failed.value

    assert await get_discovered_values(client, environment) == {
        discovered_resource_id(i): {"val": discovered_value(i)} for i in range(100)
    }

    result = await client.resource_logs(environment, resource_id, filter={"minimal_log_level": ["ERROR"]})
    assert result.code == 200, result.result
    messages = [log["msg"] for log in result.result["data"]]
    assert any(
        msg.startswith("Failed to report discovered resources to the server")
        and msg.endswith("100 of the 200 discovered resources were reported before this failure.")
        for msg in messages
    ), messages
