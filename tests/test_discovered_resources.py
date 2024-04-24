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

import json
import uuid
from datetime import datetime
from typing import Optional

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.data.model import ResourceVersionIdStr
from inmanta.server.config import get_bind_port


async def test_discovery_resource_single(server, client, agent, environment):
    """
    Test that a discovered resource can be created and retrieved successfully for a single resource.
    """
    discovered_resource_id = "test::Resource[agent1,key=key]"
    values = {"value1": "test1", "value2": "test2"}
    result = await agent._client.discovered_resource_create(
        tid=environment,
        discovered_resource_id=discovered_resource_id,
        values=values,
    )
    assert result.code == 200

    result = await client.discovered_resources_get(environment, discovered_resource_id)
    assert result.code == 200

    assert result.result["data"]["discovered_resource_id"] == discovered_resource_id
    assert result.result["data"]["values"] == values

    values = {"value1": "test3", "value2": "test4"}
    # try to store the same resource a second time
    result = await agent._client.discovered_resource_create(
        tid=environment,
        discovered_resource_id=discovered_resource_id,
        values=values,
    )
    assert result.code == 200

    result = await client.discovered_resources_get(environment, discovered_resource_id)
    assert result.code == 200

    assert result.result["data"]["discovered_resource_id"] == discovered_resource_id
    assert result.result["data"]["values"] == values


async def test_discovered_resource_create_batch(server, client, agent, environment):
    """
    Test that a batch of discovered resources can be created
    """
    resources = [
        {"discovered_resource_id": "test::Resource[agent1,key1=key1]", "values": {"value1": "test1", "value2": "test2"}},
        {"discovered_resource_id": "test::Resource[agent1,key2=key2]", "values": {"value1": "test3", "value2": "test4"}},
        {"discovered_resource_id": "test::Resource[agent1,key3=key3]", "values": {"value1": "test5", "value2": "test6"}},
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 200

    for res in resources:
        result = await client.discovered_resources_get(environment, res["discovered_resource_id"])
        assert result.code == 200
        assert result.result["data"]["discovered_resource_id"] == res["discovered_resource_id"]
        assert result.result["data"]["values"] == res["values"]

    # try to store the same resources a second time
    resources = [
        {"discovered_resource_id": "test::Resource[agent1,key1=key1]", "values": {"value1": "test7", "value2": "test8"}},
        {"discovered_resource_id": "test::Resource[agent1,key2=key2]", "values": {"value1": "test9", "value2": "test10"}},
        {"discovered_resource_id": "test::Resource[agent1,key6=key6]", "values": {"value1": "test11", "value2": "test12"}},
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 200

    for res in resources:
        result = await client.discovered_resources_get(environment, res["discovered_resource_id"])
        assert result.code == 200
        assert result.result["data"]["discovered_resource_id"] == res["discovered_resource_id"]
        assert result.result["data"]["values"] == res["values"]


@pytest.mark.parametrize(
    "apply_filter",
    [
        True,
        False,
        None,
    ],
)
async def test_discovered_resource_get_paging(server, client, agent, environment, apply_filter: Optional[bool], clienthelper):
    """
    Test that discovered resources can be retrieved with paging. The test creates multiple resources, retrieves them
    with various paging options, and verifies that the expected resources are returned.

    Also tests the linking between unmanaged and managed resources via the apply_filter parameter:

    - True: Activate filtering and keep only discovered resources that are managed.
    - False: Activate filtering and keep only discovered resources that are NOT managed.
    - None: Disable filtering: return all discovered resources regardless of whether they're managed.
    """
    discovered_resources = [
        {
            "discovered_resource_id": f"test::Resource[agent1,key{i}=key{i}]",
            "values": {"value1": f"test{i}", "value2": f"test{i+1}"},
        }
        for i in range(1, 7)
    ]

    result = await agent._client.discovered_resource_create_batch(environment, discovered_resources)
    assert result.code == 200

    version1 = await clienthelper.get_version()
    orphaned_resources = [
        {
            "id": ResourceVersionIdStr(f"{res['discovered_resource_id']},v={version1}"),
            "values": res["values"],
            "requires": [],
            "purged": False,
            "send_event": False,
        }
        for res in discovered_resources[2:-2]
    ]
    await clienthelper.put_version_simple(resources=orphaned_resources, version=version1)

    # # Create 2 versions of the model
    # for i in range(1, 3):
    #     cm = data.ConfigurationModel(
    #         environment=uuid.UUID(environment),
    #         version=i,
    #         date=datetime.now(),
    #         total=1,
    #         released=True,
    #         version_info={},
    #         is_suitable_for_partial_compiles=False,
    #     )
    #     await cm.insert()
    #
    # # Create some orphans for version 1
    # version = 1



    # for resource in orphaned_resources:
    #     resource = data.Resource.new(
    #         environment=uuid.UUID(environment), resource_version_id=resource["id"], attributes=resource["values"]
    #     )
    #     await resource.insert()

    # Create some Resources that are already managed:
    version2 = await clienthelper.get_version()
    managed_resources = [
        {
            "id": ResourceVersionIdStr(f"{res['discovered_resource_id']},v={version2}"),
            "values": res["values"],
            "requires": [],
            "purged": False,
            "send_event": False,
        }
        for res in discovered_resources[:2]
    ]
    await clienthelper.put_version_simple(resources=managed_resources, version=version2)

    # for resource in managed_resources:
    #     resource = data.Resource.new(
    #         environment=uuid.UUID(environment), resource_version_id=resource["id"], attributes=resource["values"]
    #     )
    #     await resource.insert()

    # Resource repartition and expected filtering results:

    #                                        |              FILTER
    # discovered    managed   orphaned       |  TRUE        FALSE          NONE
    # ---------------------------------------+-------------------------------------
    #     R1            x                    |   x                           x
    #     R2            x                    |   x                           x
    #     R3                      x          |   x                           x
    #     R4                      x          |   x                           x
    #     R5                                 |                x              x
    #     R6                                 |                x              x

    if apply_filter is None:
        filter = None
        expected_result = discovered_resources
    else:
        filter = {"managed": apply_filter}
        if apply_filter:
            expected_result = discovered_resources[:-2]
        else:
            expected_result = discovered_resources[-2:]

    result = await client.discovered_resources_get_batch(
        environment,
        filter=filter,
    )
    assert result.code == 200
    assert result.result["data"] == expected_result

    result = await client.discovered_resources_get_batch(environment, limit=2)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"] == discovered_resources[:2]

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = f"http://localhost:{port}"
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": environment},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert response["data"] == discovered_resources[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 2, "after": 2, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": environment},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert response["data"] == discovered_resources[0:2]
    assert response["links"].get("prev") is None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}


async def test_discovery_resource_bad_res_id(server, client, agent, environment):
    """
    Test that exceptions are raised when creating discovered resources with invalid IDs.
    """
    result = await agent._client.discovered_resource_create(
        tid=environment, discovered_resource_id="test", values={"value1": "test1", "value2": "test2"}
    )
    assert result.code == 400
    assert "Failed to validate argument" in result.result["message"]

    resources = [
        {"discovered_resource_id": "test::Resource[agent1,key1=key1]", "values": {"value1": "test1", "value2": "test2"}},
        {"discovered_resource_id": "test::Resource[agent1,key2=key2]", "values": {"value1": "test3", "value2": "test4"}},
        {"discovered_resource_id": "test", "values": {"value1": "test5", "value2": "test6"}},
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 400
    assert "Failed to validate argument" in result.result["message"]
