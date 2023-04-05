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
import uuid


async def test_discovery_resource_single(server, client, agent, environment):
    result = await client.unmanaged_resources_create(
        environment, agent.name, "unmanaged_res", {"value1": "test1", "value2": "test2"}
    )
    assert result.code == 200

    discovered_resource = await client.unmanaged_resources_get(environment, agent.name, "unmanaged_res")
    assert discovered_resource.agent == agent.name
    assert discovered_resource.environement == environment
    assert discovered_resource.unmanaged_resource_name == "unmanaged_res"
    assert discovered_resource.value == {"value1": "test1", "value2": "test2"}
