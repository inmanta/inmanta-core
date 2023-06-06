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

from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta.server.config import get_bind_port


async def test_discovery_resource_single(server, client, agent, environment):
    """
    Test that an unmanaged resource can be created and retrieved successfully for a single resource.
    """
    unmanaged_resource_id = "test::Resource[agent1,key=key]"
    values = {"value1": "test1", "value2": "test2"}
    result = await agent._client.discovered_resource_create(
        tid=environment,
        unmanaged_resource_id=unmanaged_resource_id,
        values=values,
    )
    assert result.code == 200

    result = await client.unmanaged_resources_get(environment, unmanaged_resource_id)
    assert result.code == 200

    assert result.result["data"]["unmanaged_resource_id"] == unmanaged_resource_id
    assert result.result["data"]["values"] == values

    # try to store the same resource a second time
    result = await agent._client.discovered_resource_create(
        tid=environment,
        unmanaged_resource_id=unmanaged_resource_id,
        values=values,
    )
    assert result.code == 409
    error_message = (
        "Request conflicts with the current state of the resource: "
        f"Key (environment, unmanaged_resource_id)=({environment}, "
        "test::Resource[agent1,key=key]) already exists."
    )
    assert error_message in result.result["message"]


async def test_discovered_resource_create_batch(server, client, agent, environment):
    """
    Test that a batch of discovered resources can be created
    """
    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key1=key1]", "values": {"value1": "test1", "value2": "test2"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key2=key2]", "values": {"value1": "test3", "value2": "test4"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key3=key3]", "values": {"value1": "test5", "value2": "test6"}},
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 200

    for res in resources:
        result = await client.unmanaged_resources_get(environment, res["unmanaged_resource_id"])
        assert result.code == 200
        assert result.result["data"]["unmanaged_resource_id"] == res["unmanaged_resource_id"]
        assert result.result["data"]["values"] == res["values"]

    # try to store a batch with 2 times the same resource
    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key4=key4]", "values": {"value1": "test7", "value2": "test8"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key4=key4]", "values": {"value1": "test9", "value2": "test10"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key6=key6]", "values": {"value1": "test11", "value2": "test12"}},
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 409
    error_message = (
        "Request conflicts with the current state of the resource: "
        f"Key (environment, unmanaged_resource_id)=({environment}, "
        "test::Resource[agent1,key4=key4]) already exists."
    )
    assert error_message in result.result["message"]


async def test_unmanaged_resource_get_paging(server, client, agent, environment):
    """
    Test that unmanaged resources can be retrieved with paging. The test creates multiple resources, retrieves them
    with various paging options, and verifies that the expected resources are returned.
    """
    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key1=key1]", "values": {"value1": "test1", "value2": "test2"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key2=key2]", "values": {"value1": "test3", "value2": "test4"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key3=key3]", "values": {"value1": "test5", "value2": "test6"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key4=key4]", "values": {"value1": "test7", "value2": "test8"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key5=key5]", "values": {"value1": "test9", "value2": "test10"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key6=key6]", "values": {"value1": "test11", "value2": "test12"}},
    ]

    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 200

    result = await client.unmanaged_resources_get_batch(
        environment,
    )
    assert result.code == 200
    assert len(result.result["data"]) == 6

    result = await client.unmanaged_resources_get_batch(environment, limit=2)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"] == resources[:2]

    assert result.result["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = "http://localhost:%s" % (port,)
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
    assert response["data"] == resources[2:4]
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
    assert response["data"] == resources[0:2]
    assert response["links"].get("prev") is None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 6, "before": 0, "after": 4, "page_size": 2}


async def test_discovery_resource_bad_res_id(server, client, agent, environment):
    """
    Test that exceptions are raised when creating unmanaged resources with invalid IDs.
    """
    result = await agent._client.discovered_resource_create(
        tid=environment, unmanaged_resource_id="test", values={"value1": "test1", "value2": "test2"}
    )
    assert result.code == 400
    assert "Failed to validate argument" in result.result["message"]

    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key1=key1]", "values": {"value1": "test1", "value2": "test2"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key2=key2]", "values": {"value1": "test3", "value2": "test4"}},
        {"unmanaged_resource_id": "test", "values": {"value1": "test5", "value2": "test6"}},
    ]
    result = await agent._client.discovered_resource_create_batch(environment, resources)
    assert result.code == 400
    assert "Failed to validate argument" in result.result["message"]
