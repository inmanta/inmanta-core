"""
    Copyright 2021 Inmanta

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
from datetime import datetime

import pytest

from inmanta import data
from inmanta.const import ResourceState
from inmanta.data.model import ResourceVersionIdStr


@pytest.mark.asyncio
async def test_resource_list_no_released_version(server, client, environment, clienthelper, agent):
    version = await clienthelper.get_version()
    rvid_r1_v1 = ResourceVersionIdStr(f"std::File[agent1,path=/etc/file1],v={version}")
    resources = [
        {"path": "/etc/file1", "id": rvid_r1_v1, "requires": [], "purged": False, "send_event": False},
    ]
    await clienthelper.put_version_simple(resources, version)

    action_id = uuid.uuid4()
    result = await agent._client.resource_deploy_start(tid=environment, rvid=rvid_r1_v1, action_id=action_id)
    assert result.code == 200

    result = await client.resource_list(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 0


@pytest.mark.asyncio
async def test_has_only_one_version_from_resource(server, client):
    """ Test querying resource actions via the API, including the pagination links."""
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # Add multiple versions of model, with 2 of them released
    for i in range(1, 4):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.now(),
            total=1,
            released=i != 1,
            version_info={},
        )
        await cm.insert()

    version = 1
    path = "/etc/file" + str(1)
    key = "std::File[agent1,path=" + path + "]"
    res1_v1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
    await res1_v1.insert()
    version = 2
    res1_v2 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"path": path},
        status=ResourceState.deploying,
    )
    await res1_v2.insert()
    version = 3
    res1_v3 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"path": path},
        status=ResourceState.deployed,
    )
    await res1_v3.insert()

    version = 1
    path = "/etc/file" + str(2)
    key = "std::File[agent1,path=" + path + "]"
    res1_v1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
    await res1_v1.insert()
    version = 2
    res1_v2 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"path": path},
        status=ResourceState.deploying,
    )
    await res1_v2.insert()

    result = await client.resource_list(env.id)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"][0]["status"] == "deployed"
    assert result.result["data"][1]["status"] == "deploying"

    # Test sorting
    # TODO: move to different test case, refactor
    result = await client.resource_list(env.id, sort="status.desc")
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"][0]["status"] == "deploying"
    assert result.result["data"][1]["status"] == "deployed"

    result = await client.resource_list(env.id, sort="value.desc")
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"][0]["id_details"]["attribute_value"] == "/etc/file2"
    assert result.result["data"][1]["id_details"]["attribute_value"] == "/etc/file1"

    result = await client.resource_list(env.id, sort="state.desc")
    assert result.code == 400



