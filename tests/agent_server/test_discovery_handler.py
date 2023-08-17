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

import pytest

import inmanta
from agent_server.conftest import _deploy_resources, wait_for_n_deployed_resources
from inmanta import data
from inmanta.agent.handler import DiscoveryHandler, HandlerContext, provider
from inmanta.agent.io.local import IOBase
from inmanta.data import ResourceIdStr
from inmanta.data.model import BaseModel
from inmanta.resources import DiscoveryResource, Id, resource
from inmanta import util


@pytest.fixture
async def discovery_resource_and_handler(tmpdir):
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


async def test_discovery_resource_handler_basic_test(
    server, client, clienthelper, environment, no_agent_backoff, tmpdir, agent_factory, discovery_resource_and_handler
):
    """
    This test creates sub-directories and checks that they are discovered as resources of type std::Directory.
    This test also verifies that the DiscoveryHandler reports an empty diff when a dry-run is requested.
    """

    agent = await agent_factory(
        environment=environment,
        agent_map={"host": "localhost"},
        hostname="host",
        agent_names=["discovery_agent"],
        code_loader=True,
    )

    # Populate tmpdir
    for i in range(6):
        tmpdir.mkdir(f"sub_dir_{i}")

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

    await agent.ensure_code(
        environment=environment,
        version=version,
        resource_types=["test::MyDiscoveryResource"],
    )

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
    assert not resources_in_dryrun["test::MyDiscoveryResource[discovery_agent,key=key1],v=1"]["changes"], resources_in_dryrun

    # Ensure that the deployment of the DiscoveryResource results in discovered resources.
    result = await client.release_version(environment, version, push=True)
    assert result.code == 200

    await wait_for_n_deployed_resources(client, environment, version, n=1)

    result = await client.get_version(tid=environment, id=version)
    assert result.code == 200

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

    # TODO: Test facts


async def test_discovery_resource_requires_provides(
    server, client, clienthelper, environment, no_agent_backoff, tmpdir, agent_factory, discovery_resource_and_handler, resource_container
):
    """
    This test verifies that the requires/provides relationships are taken into account for a DiscoveryResource.
    """

    agent = await agent_factory(
        environment=environment,
        agent_map={"host": "localhost"},
        hostname="host",
        agent_names=["discovery_agent", "agent1"],
        code_loader=True,
    )

    # Populate tmpdir
    for i in range(6):
        tmpdir.mkdir(f"sub_dir_{i}")

    version = await clienthelper.get_version()

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
            "value": "value2",
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

    await agent.ensure_code(
        environment=environment,
        version=version,
        resource_types=["test::MyDiscoveryResource"],
    )

    result = await client.release_version(environment, version, push=True)
    assert result.code == 200

    await wait_for_n_deployed_resources(client, environment, version, n=1)

    result = await client.get_version(tid=environment, id=version)
    assert result.code == 200

    result = await client.resource_logs(tid=environment, rid="test::MyDiscoveryResource[discovery_agent,key=key1]")
    assert result.code == 200

    result = await client.discovered_resources_get_batch(
        environment,
    )
    assert result.code == 200
    assert result.result["data"] == []

