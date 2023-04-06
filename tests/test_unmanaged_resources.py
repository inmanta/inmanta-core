"""
    Copyright 2016 Inmanta

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


async def test_discovery_resource_create_single(server, client, agent, environment):
    result = await client.unmanaged_resource_create(
        environment, "test::Resource[agent1,key=key],v=1", {"value1": "test1", "value2": "test2"}
    )
    assert result.code == 200

    result = await client.unmanaged_resources_get(environment, "test::Resource[agent1,key=key],v=1")
    assert result.code == 200

    assert result.result["data"]["environment"] == environment
    assert result.result["data"]["unmanaged_resource_id"] == "test::Resource[agent1,key=key],v=1"
    assert result.result["data"]["values"] == {"value1": "test1", "value2": "test2"}


async def test_discovery_resource_bad_res_id(server, client, agent, environment):
    # TODO it seems my validator doesn't work, haven't found out why yet
    result = await client.unmanaged_resource_create(environment, "test", {"value1": "test1", "value2": "test2"})
    assert result.code != 200


async def test_unmanaged_resource_create_batch(server, client, agent, environment):
    resources = [
        {"unmanaged_resource_id": "test::Resource[agent1,key1=key1],v=1", "values": {"value1": "test1", "value2": "test2"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key2=key2],v=1", "values": {"value1": "test3", "value2": "test4"}},
        {"unmanaged_resource_id": "test::Resource[agent1,key2=key3],v=1", "values": {"value1": "test5", "value2": "test6"}},
    ]
    result = await client.unmanaged_resource_create_batch(environment, resources)
    assert result.code == 200

    for res in resources:
        result = await client.unmanaged_resources_get(environment, res["unmanaged_resource_id"])
        assert result.code == 200
        assert result.result["data"]["environment"] == environment
        assert result.result["data"]["unmanaged_resource_id"] == res["unmanaged_resource_id"]
        assert result.result["data"]["values"] == res["values"]
