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

import asyncio
import uuid

import pytest

from inmanta import data
from inmanta.data import model


@pytest.fixture
async def environment_with_discovered_resources(server_multi, environment_multi: str) -> int:
    """
    Create discovered resources in the environment created by the environment_multi fixture
    and return the number of discovered resources that were created.
    """
    nr_of_discovered_resources = 6
    await data.DiscoveredResource.insert_many(
        [
            model.LinkedDiscoveredResource(
                discovered_resource_id=f"test::Resource[agent1,name=resource{i}]",
                values={"name": f"resource{i}"},
                discovery_resource_id="test::Discovery[agent1,name=discovery]",
            ).to_dao(uuid.UUID(environment_multi))
            for i in range(nr_of_discovered_resources)
        ]
    )
    return nr_of_discovered_resources


async def test_client_all_pages(
    server_multi, client_multi, environment_multi: str, environment_with_discovered_resources: int
) -> None:
    """
    Verify that the paging methods of a PageableResult follow the paging links, for every combination
    of authentication and SSL supported by the server.
    """
    environment_id = uuid.UUID(environment_multi)
    all_resources = await client_multi.discovered_resources_get_batch(tid=environment_id).value()
    assert len(all_resources) == environment_with_discovered_resources

    # Paging on an awaited Result
    result = await client_multi.discovered_resources_get_batch(tid=environment_id, limit=2)
    assert [resource async for resource in result.all()] == all_resources

    # Paging without awaiting the Result
    assert [
        resource async for resource in client_multi.discovered_resources_get_batch(tid=environment_id, limit=2).all()
    ] == all_resources

    # value() is limited to a single page
    assert await client_multi.discovered_resources_get_batch(tid=environment_id, limit=2).value() == all_resources[0:2]

    def assert_all_pages_sync() -> None:
        assert list(client_multi.discovered_resources_get_batch(tid=environment_id, limit=2).all_sync()) == all_resources

    await asyncio.get_running_loop().run_in_executor(None, assert_all_pages_sync)
