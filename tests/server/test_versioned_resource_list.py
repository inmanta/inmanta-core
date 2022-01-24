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
import json
import uuid
from datetime import datetime
from operator import itemgetter
from typing import List
from uuid import UUID

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.const import ResourceState
from inmanta.data.model import ResourceVersionIdStr, VersionedResource
from inmanta.server.config import get_bind_port


@pytest.fixture
async def env_with_resources(server, client):
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

    async def create_resource(agent: str, path: str, resource_type: str, versions: List[int], environment: UUID = env.id):
        for version in versions:
            key = f"{resource_type}[{agent},path={path}]"
            res = data.Resource.new(
                environment=environment,
                resource_version_id=ResourceVersionIdStr(f"{key},v={version}"),
                attributes={"path": path, "v": version},
                status=ResourceState.deployed,
            )
            await res.insert()

    await create_resource("agent1", "/etc/file1", "std::File", [1, 2, 3])
    await create_resource("agent1", "/etc/file2", "std::File", [1, 2])
    await create_resource("agent2", "/etc/file3", "std::File", [2])
    await create_resource("agent2", "/tmp/file4", "std::File", [3])
    await create_resource("agent2", "/tmp/dir5", "std::Directory", [3])
    await create_resource("agent2", "/tmp/dir6", "std::Directory", [3])
    await create_resource("agent2", "/tmp/dir7", "std::Directory", [3])
    await create_resource("agent3", "/tmp/dir8", "std::Directory", [3])

    env2 = data.Environment(name="dev-test2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()
    cm = data.ConfigurationModel(
        environment=env2.id,
        version=3,
        date=datetime.now(),
        total=1,
        released=True,
        version_info={},
    )
    await cm.insert()
    await create_resource("agent1", "/tmp/file7", "std::File", [3], environment=env2.id)
    await create_resource("agent1", "/tmp/file2", "std::File", [3], environment=env2.id)

    yield env


@pytest.mark.asyncio
async def test_filter_resources(server, client, env_with_resources):
    """ Test querying resources."""

    result = await client.get_resources_in_version(uuid.uuid4(), 1)
    assert result.code == 404

    env = env_with_resources
    result = await client.get_resources_in_version(env.id, 2)
    assert result.code == 200
    assert len(result.result["data"]) == 3

    result = await client.get_resources_in_version(env.id, 4)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    version = 3
    # Exact match
    result = await client.get_resources_in_version(env.id, version, filter={"agent": ["agent1"]})
    assert result.code == 200
    assert len(result.result["data"]) == 1

    result = await client.get_resources_in_version(env.id, version, filter={"resource_id_value": ["/etc/file1"]})
    assert result.code == 200
    assert len(result.result["data"]) == 1

    # Partial match
    result = await client.get_resources_in_version(env.id, version, filter={"resource_id_value": ["/etc/file"]})
    assert result.code == 200
    assert len(result.result["data"]) == 1

    result = await client.get_resources_in_version(env.id, version, filter={"resource_id_value": ["tmp"]})
    assert result.code == 200
    assert len(result.result["data"]) == 5

    result = await client.get_resources_in_version(env.id, version, filter={"resource_id_value": ["/etc/file", "/tmp/file"]})
    assert result.code == 200
    assert len(result.result["data"]) == 2

    result = await client.get_resources_in_version(env.id, version, filter={"resource_type": ["Directory"]})
    assert result.code == 200
    assert len(result.result["data"]) == 4

    result = await client.get_resources_in_version(
        env.id, version, filter={"resource_type": ["Directory"], "resource_id_value": "1"}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 0

    result = await client.get_resources_in_version(
        env.id, version, filter={"resource_type": ["Directory"], "resource_id_value": "5"}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 1


def resource_ids(resource_objects):
    return [resource["resource_version_id"] for resource in resource_objects]


@pytest.mark.parametrize("order_by_column", ["agent", "resource_type", "resource_id_value"])
@pytest.mark.parametrize("order", ["DESC", "ASC"])
@pytest.mark.asyncio
async def test_resources_paging(server, client, order_by_column, order, env_with_resources):
    """ Test querying resources with paging, using different sorting parameters."""
    env = env_with_resources
    version = 3
    result = await client.get_resources_in_version(
        env.id,
        version,
        filter={"agent": ["1", "2"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 5
    flattened_resources = [VersionedResource(**res).all_fields for res in result.result["data"]]
    all_resources_in_expected_order = sorted(
        flattened_resources, key=itemgetter(order_by_column, "resource_version_id"), reverse=order == "DESC"
    )
    all_resource_ids_in_expected_order = resource_ids(all_resources_in_expected_order)

    result = await client.get_resources_in_version(
        env.id, version, limit=2, sort=f"{order_by_column}.{order}", filter={"agent": ["1", "2"]}
    )
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert resource_ids(result.result["data"]) == all_resource_ids_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 5, "before": 0, "after": 3, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = "http://localhost:%s" % (port,)
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    assert "filter.agent=1" in url
    assert "filter.agent=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert resource_ids(response["data"]) == all_resource_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 5, "before": 2, "after": 1, "page_size": 2}

    # Test link for next page
    url = f"""{base_url}{response["links"]["next"]}"""
    # The filters should be present for the links as well
    assert "limit=2" in url
    assert "filter.agent=1" in url
    assert "filter.agent=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    next_page_instance_ids = resource_ids(response["data"])
    assert next_page_instance_ids == all_resource_ids_in_expected_order[4:]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is None
    assert response["metadata"] == {"total": 5, "before": 4, "after": 0, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    assert "filter.agent=1" in url
    assert "filter.agent=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    prev_page_instance_ids = resource_ids(response["data"])
    assert prev_page_instance_ids == all_resource_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 5, "before": 2, "after": 1, "page_size": 2}


@pytest.mark.asyncio
async def test_sorting_validation(server, client, env_with_resources):
    sort_status_map = {
        "agents.Desc": 400,
        "agent.asc": 200,
        "version.desc": 400,
        "resource_type": 400,
        "total.asc": 400,
        "status.asc": 400,
        "resource_id_value.asc": 200,
    }
    for sort, expected_status in sort_status_map.items():
        result = await client.get_resources_in_version(env_with_resources.id, version=3, sort=sort)
        assert result.code == expected_status


@pytest.mark.asyncio
async def test_filter_validation(server, client, env_with_resources):
    filter_status_map = [
        ("version.desc", 400),
        ({"resource_id_value": ["file1", "res2"]}, 200),
        ({"resource_types": [1, 2]}, 400),
        ({"date": "le:42"}, 400),
        ({"agent": "internal"}, 200),
        ({"released": True}, 400),
        ({"version": "gt:1"}, 400),
    ]
    for filter, expected_status in filter_status_map:
        result = await client.get_resources_in_version(env_with_resources.id, version=3, filter=filter)
        assert result.code == expected_status


@pytest.mark.asyncio
async def test_versioned_resource_details(server, client, env_with_resources):
    result = await client.get_resources_in_version(env_with_resources.id, version=3, sort="resource_id_value.asc")
    assert result.code == 200
    resource_id = result.result["data"][0]["resource_id"]
    result = await client.versioned_resource_details(env_with_resources.id, version=2, rid=resource_id)
    assert result.code == 200
    assert result.result["data"]["attributes"] == {"path": "/etc/file1", "v": 2}
    result = await client.versioned_resource_details(env_with_resources.id, version=3, rid=resource_id)
    assert result.code == 200
    assert result.result["data"]["attributes"] == {"path": "/etc/file1", "v": 3}
    result = await client.versioned_resource_details(env_with_resources.id, version=4, rid=resource_id)
    assert result.code == 404

    result = await client.versioned_resource_details(uuid.uuid4(), version=3, rid=resource_id)
    assert result.code == 404
