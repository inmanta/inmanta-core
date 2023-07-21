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
import uuid
from collections import abc
from typing import Optional

import inmanta
from agent_server.conftest import _deploy_resources, wait_for_n_deployed_resources
from inmanta import data
from inmanta.agent.handler import DiscoveryHandler, HandlerContext, provider
from inmanta.agent.io.local import IOBase
from inmanta.data import ResourceIdStr
from inmanta.data.model import BaseModel
from inmanta.resources import DiscoveryResource, Id, resource


async def test_discovery_resource_handler(
    server, client, clienthelper, environment, no_agent_backoff, async_finalizer, tmpdir, agent_factory
):
    """
    This test creates sub-directories and checks that they are onboarded as resources of type std::Directory
    """

    agent = await agent_factory(
        environment=environment,
        agent_map={"host": "localhost"},
        hostname="host",
        agent_names=["discovery_agent"],
        code_loader=True,
    )

    def populate_tmp_dir():
        for i in range(6):
            tmpdir.mkdir(f"sub_dir_{i}")

    populate_tmp_dir()

    assert "discovery_agent" in agent._instances

    @resource("test::MyDiscoveryResource", agent="discovery_agent", id_attribute="key")
    class MyDiscoveryResource(DiscoveryResource):
        fields = ("key",)

    class MyUnmanagedResource(BaseModel):
        path: str

    @provider("test::MyDiscoveryResource", name="my_discoveryresource_handler")
    class Mock_DiscoveryHandler(DiscoveryHandler[MyDiscoveryResource, MyUnmanagedResource]):
        def __init__(self, agent: inmanta.agent.agent.AgentInstance, io: Optional[IOBase] = None):
            super().__init__(agent, io)
            self._top_dir_path = os.path.abspath(tmpdir)
            self._client = None

        def discover_resources(
            self, ctx: HandlerContext, discovery_resource: MyDiscoveryResource
        ) -> abc.Mapping[ResourceIdStr, MyUnmanagedResource]:
            dirs = os.listdir(self._top_dir_path)

            resources = {
                Id(
                    entity_type="std::Directory",
                    agent_name="discovery_agent",
                    attribute="path",
                    attribute_value=os.path.join(self._top_dir_path, dir),
                ).resource_str(): MyUnmanagedResource(path=os.path.join(self._top_dir_path, dir))
                for dir in dirs
            }

            return resources

        def close(self) -> None:
            pass

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value2",
            "id": "test::MyDiscoveryResource[discovery_agent,key=key1],v=%d" % version,
            "send_event": True,
            "purged": False,
            "requires": [],
        }
    ]

    result = await _deploy_resources(client, environment, resources, version, push=True)
    assert result.code == 200

    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))

    assert resource_list, resource_list

    await agent.ensure_code(
        environment=environment,
        version=version,
        resource_types=["test::MyDiscoveryResource"],
    )
    assert result.code == 200

    await wait_for_n_deployed_resources(client, environment, version, n=1)

    result = await client.discovered_resources_get_batch(
        environment,
    )
    assert result.code == 200
    expected = [
        {
            "discovered_resource_id": f"std::Directory[discovery_agent,path={tmpdir}/sub_dir_{i}]",
            "values": {"path": f"{tmpdir}/sub_dir_{i}"},
        }
        for i in range(6)
    ]
    assert result.result["data"] == expected
