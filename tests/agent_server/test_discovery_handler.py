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
import os
from collections import abc

import pydantic

import inmanta
from agent_server.conftest import get_agent
from inmanta.agent.handler import DiscoveryHandler, HandlerContext, provider
from inmanta.data import ResourceIdStr
from inmanta.resources import DiscoveryResource, Id, resource


class MyUnmanagedResource(pydantic.BaseModel):
    path: str


@resource("test_model::MyDiscoveryResource", agent="agent", id_attribute="path")
class MyDiscoveryResource(DiscoveryResource):
    fields = ("path",)


@provider("test_model::MyDiscoveryResource", name="my_discoveryresource_handler")
class Mock_DiscoveryHandler(DiscoveryHandler[MyDiscoveryResource, MyUnmanagedResource]):
    def __init__(self, agent: inmanta.agent.agent.AgentInstance, path):
        super().__init__(agent)
        self._path = path
        self._client = None

    def discover_resources(
        self, ctx: HandlerContext, discovery_resource: MyDiscoveryResource
    ) -> abc.Mapping[ResourceIdStr, MyUnmanagedResource]:
        dirs = os.listdir(self._path)

        resources = {
            Id(
                entity_type="std::Directory",
                agent_name="internal",
                attribute="path",
                attribute_value=os.path.join(self._path, dir),
            ).resource_str(): MyUnmanagedResource(path=os.path.join(self._path, dir))
            for dir in dirs
        }

        return resources


async def test_discovery_resource_handler(
    resource_container, server, client, clienthelper, environment, no_agent_backoff, async_finalizer, tmpdir
):
    """
    This test creates sub-directories and checks that they are onboarded as resources of type std::Directory
    """

    def populate_tmp_dir():
        for i in range(6):
            tmpdir.mkdir(f"sub_dir_{i}")

    populate_tmp_dir()

    agent = await get_agent(server, environment, "agent")
    resource_handler = Mock_DiscoveryHandler(agent, tmpdir)

    discovery_resource_id = Id(
        entity_type="test_model::MyDiscoveryResource", agent_name="agent", attribute="path", attribute_value=tmpdir
    )
    discovery_resource = MyDiscoveryResource(discovery_resource_id)
    ctx = HandlerContext(discovery_resource)

    resource_handler.deploy(ctx, discovery_resource)

    result = await client.discovered_resources_get_batch(
        environment,
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6
    expected = [
        {
            "discovered_resource_id": f"std::Directory[internal,path={tmpdir}/sub_dir_{i}]",
            "values": {"path": f"{tmpdir}/sub_dir_{i}"},
        }
        for i in range(6)
    ]
    assert result.result["data"] == expected
