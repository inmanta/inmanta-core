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


async def test_discovery_resource_single(server, client, agent, environment):
    """
    Test that an unmanaged resource can be created and retrieved successfully for a single resource.
    """
    unmanaged_resource_id = "test::Resource[agent1,key=key],v=1"
    values = {"value1": "test1", "value2": "test2"}
    result = await agent._client.unmanaged_resource_create(
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
    result = await agent._client.unmanaged_resource_create(
        tid=environment,
        unmanaged_resource_id=unmanaged_resource_id,
        values=values,
    )
    assert result.code == 500


async def test_unmanaged_resource_create_batch(server, client, agent, environment):
    """
    Test that a batch of unmanaged resources can be created
    """
    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key1=key1],v=1", "values": {"value1": "test1", "value2": "test2"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key2=key2],v=1", "values": {"value1": "test3", "value2": "test4"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key3=key3],v=1", "values": {"value1": "test5", "value2": "test6"}},
    ]
    result = await agent._client.unmanaged_resource_create_batch(environment, resources)
    assert result.code == 200

    for res in resources:
        result = await client.unmanaged_resources_get(environment, res["unmanaged_resource_id"])
        assert result.code == 200
        assert result.result["data"]["unmanaged_resource_id"] == res["unmanaged_resource_id"]
        assert result.result["data"]["values"] == res["values"]

    # try to store a batch with 2 times the same resource
    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key4=key4],v=1", "values": {"value1": "test7", "value2": "test8"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key4=key4],v=1", "values": {"value1": "test9", "value2": "test10"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key6=key6],v=1", "values": {"value1": "test11", "value2": "test12"}},
    ]
    result = await agent._client.unmanaged_resource_create_batch(environment, resources)
    assert result.code == 500


async def test_unmanaged_resource_get_paging(server, client, agent, environment):
    """
    Test that unmanaged resources can be retrieved with paging. The test creates multiple resources, retrieves them
    with various paging options, and verifies that the expected resources are returned.
    """
    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key1=key1],v=1", "values": {"value1": "test1", "value2": "test2"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key2=key2],v=1", "values": {"value1": "test3", "value2": "test4"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key3=key3],v=1", "values": {"value1": "test5", "value2": "test6"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key4=key4],v=1", "values": {"value1": "test7", "value2": "test8"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key5=key5],v=1", "values": {"value1": "test9", "value2": "test10"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key6=key6],v=1", "values": {"value1": "test11", "value2": "test12"}},
    ]
    result = await agent._client.unmanaged_resource_create_batch(environment, resources)
    assert result.code == 200

    result = await client.unmanaged_resources_get_batch(
        environment, start_resource_id="aaa", end_resource_id="test::Resource[agent1,key3=key3],v=1", limit=2
    )
    assert result.code == 400
    assert "the start_resource_id is not formatted" in result.result["message"]

    result = await client.unmanaged_resources_get_batch(
        environment, start_resource_id="test::Resource[agent1,key1=key1],v=1", end_resource_id="aaa", limit=2
    )
    assert result.code == 400
    assert "the end_resource_id is not formatted" in result.result["message"]

    # will not get more than limit resources
    result = await client.unmanaged_resources_get_batch(environment, limit=2)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    for i in range(0, 2):
        assert result.result["data"][i]["unmanaged_resource_id"] == resources[i]["unmanaged_resource_id"]
        assert result.result["data"][i]["values"] == resources[i]["values"]

    # will not get resources before start_resource_id
    result = await client.unmanaged_resources_get_batch(
        environment, start_resource_id="test::Resource[agent1,key3=key3],v=1", limit=3
    )
    assert result.code == 200
    assert len(result.result["data"]) == 3
    for i in range(3, 6):
        assert result.result["data"][i - 3]["unmanaged_resource_id"] == resources[i]["unmanaged_resource_id"]
        assert result.result["data"][i - 3]["values"] == resources[i]["values"]

    # Verify no resource with a resource_id comming after end_resource_id will be returned.
    result = await client.unmanaged_resources_get_batch(
        environment,
        start_resource_id="test::Resource[agent1,key2=key2],v=1",
        end_resource_id="test::Resource[agent1,key4=key4],v=1",
        limit=3,
    )
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["unmanaged_resource_id"] == resources[2]["unmanaged_resource_id"]
    assert result.result["data"][0]["values"] == resources[2]["values"]


async def test_discovery_resource_bad_res_id(server, client, agent, environment):
    """
    Test that exceptions are raised when creating unmanaged resources with invalid IDs.
    """
    result = await agent._client.unmanaged_resource_create(
        tid=environment, unmanaged_resource_id="test", values={"value1": "test1", "value2": "test2"}
    )
    assert result.code == 400
    assert "Failed to validate argument" in result.result["message"]

    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key1=key1],v=1", "values": {"value1": "test1", "value2": "test2"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key2=key2],v=1", "values": {"value1": "test3", "value2": "test4"}},
        {"unmanaged_resource_id": "test", "values": {"value1": "test5", "value2": "test6"}},
    ]
    result = await agent._client.unmanaged_resource_create_batch(environment, resources)
    assert result.code == 400
    assert "Failed to validate argument" in result.result["message"]
