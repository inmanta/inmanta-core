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
from datetime import datetime
from operator import itemgetter
from typing import List
from uuid import UUID

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.const import ResourceState
from inmanta.data.model import LatestReleasedResource, ResourceVersionIdStr
from inmanta.server.config import get_bind_port


@pytest.mark.asyncio
async def test_resource_list_no_released_version(server, client):
    """ Test that if there are no released versions of a resource, the result set is empty """
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    version = 1
    cm = data.ConfigurationModel(
        environment=env.id,
        version=version,
        date=datetime.now(),
        total=1,
        released=False,
        version_info={},
    )
    await cm.insert()

    path = f"/etc/file{1}"
    key = f"std::File[agent1,path={path}]"
    res1_v1 = data.Resource.new(
        environment=env.id, resource_version_id=ResourceVersionIdStr(f"{key},v={version}"), attributes={"path": path}
    )
    await res1_v1.insert()

    result = await client.resource_list(env.id)
    assert result.code == 200
    assert len(result.result["data"]) == 0


@pytest.mark.asyncio
async def test_has_only_one_version_from_resource(server, client):
    """Test querying resources, when there are multiple released versions of a resource.
    The query should return only the latest one from those
    """
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # Add multiple versions of model, with 2 of them released
    for i in range(1, 5):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.now(),
            total=1,
            released=i != 1 and i != 4,
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
    version = 4
    res1_v4 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"path": path, "new_attr": 123, "requires": ["abc"]},
        status=ResourceState.deployed,
    )
    await res1_v4.insert()

    version = 1
    path = "/etc/file" + str(2)
    key = "std::File[agent1,path=" + path + "]"
    res2_v1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"path": path})
    await res2_v1.insert()
    version = 2
    res2_v2 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"path": path},
        status=ResourceState.deploying,
    )
    await res2_v2.insert()

    result = await client.resource_list(env.id, sort="status.asc")
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"][0]["status"] == "deployed"
    assert result.result["data"][0]["requires"] == []
    # Orphaned, since there is already a version 3 released
    assert result.result["data"][1]["status"] == "orphaned"


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

    async def create_resource(
        agent: str, path: str, resource_type: str, status: ResourceState, versions: List[int], environment: UUID = env.id
    ):
        for version in versions:
            key = f"{resource_type}[{agent},path={path}]"
            res = data.Resource.new(
                environment=environment,
                resource_version_id=ResourceVersionIdStr(f"{key},v={version}"),
                attributes={"path": path},
                status=status,
            )
            await res.insert()

    await create_resource("agent1", "/etc/file1", "std::File", ResourceState.available, [1, 2, 3])
    await create_resource("agent1", "/etc/file2", "std::File", ResourceState.deploying, [1, 2])  # Orphaned
    await create_resource("agent2", "/etc/file3", "std::File", ResourceState.deployed, [2])  # Orphaned
    await create_resource("agent2", "/tmp/file4", "std::File", ResourceState.unavailable, [3])
    await create_resource("agent2", "/tmp/dir5", "std::Directory", ResourceState.skipped, [3])
    await create_resource("agent3", "/tmp/dir6", "std::Directory", ResourceState.deployed, [3])

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
    await create_resource("agent1", "/tmp/file7", "std::File", ResourceState.deployed, [3], environment=env2.id)
    await create_resource("agent1", "/tmp/file2", "std::File", ResourceState.deployed, [3], environment=env2.id)
    await create_resource("agent2", "/tmp/dir5", "std::Directory", ResourceState.skipped, [3], environment=env2.id)

    env3 = data.Environment(name="dev-test3", project=project.id, repo_url="", repo_branch="")
    await env3.insert()
    cm = data.ConfigurationModel(
        environment=env3.id,
        version=6,
        date=datetime.now(),
        total=1,
        released=True,
        version_info={},
    )
    await cm.insert()
    await create_resource("agent2", "/etc/file3", "std::File", ResourceState.deployed, [6], environment=env3.id)

    yield env


@pytest.mark.asyncio
async def test_filter_resources(server, client, env_with_resources):
    """ Test querying resources."""
    env = env_with_resources

    # Exact match
    result = await client.resource_list(env.id, filter={"agent": ["agent1"]})
    assert result.code == 200
    assert len(result.result["data"]) == 2

    result = await client.resource_list(env.id, filter={"resource_id_value": ["/etc/file1"]})
    assert result.code == 200
    assert len(result.result["data"]) == 1

    # Partial match
    result = await client.resource_list(env.id, filter={"resource_id_value": ["/etc/file"]})
    assert result.code == 200
    assert len(result.result["data"]) == 3

    result = await client.resource_list(env.id, filter={"resource_id_value": ["2"]})
    assert result.code == 200
    assert len(result.result["data"]) == 1

    result = await client.resource_list(env.id, filter={"resource_id_value": ["/etc/file", "/tmp/file"]})
    assert result.code == 200
    assert len(result.result["data"]) == 4

    result = await client.resource_list(env.id, filter={"resource_type": ["Directory"]})
    assert result.code == 200
    assert len(result.result["data"]) == 2

    result = await client.resource_list(env.id, filter={"resource_type": ["Directory"], "resource_id_value": "1"})
    assert result.code == 200
    assert len(result.result["data"]) == 0

    result = await client.resource_list(env.id, filter={"resource_type": ["Directory"], "resource_id_value": "5"})
    assert result.code == 200
    assert len(result.result["data"]) == 1

    result = await client.resource_list(env.id, filter={"status": ["orphaned"]})
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert [resource["status"] for resource in result.result["data"]] == ["orphaned", "orphaned"]
    result = await client.resource_list(env.id, filter={"status": ["orphaned", "deployed"]}, sort="status.asc")
    assert result.code == 200
    assert len(result.result["data"]) == 3
    assert [resource["status"] for resource in result.result["data"]] == ["deployed", "orphaned", "orphaned"]

    result = await client.resource_list(env.id, filter={"status": ["deployed"]})
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["status"] == "deployed"


def resource_ids(resource_objects):
    return [resource["resource_version_id"] for resource in resource_objects]


@pytest.mark.parametrize(
    "order_by_column, order",
    [
        ("agent", "DESC"),
        ("agent", "ASC"),
        ("resource_type", "DESC"),
        ("resource_type", "ASC"),
        ("status", "DESC"),
        ("status", "ASC"),
        ("resource_id_value", "DESC"),
        ("resource_id_value", "ASC"),
    ],
)
@pytest.mark.asyncio
async def test_resources_paging(server, client, order_by_column, order, env_with_resources):
    """ Test querying resources with paging, using different sorting parameters."""
    env = env_with_resources

    result = await client.resource_list(
        env.id,
        filter={"agent": ["1", "2"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 5
    flattened_resources = [LatestReleasedResource(**res).all_fields for res in result.result["data"]]
    all_resources_in_expected_order = sorted(
        flattened_resources, key=itemgetter(order_by_column, "resource_version_id"), reverse=order == "DESC"
    )
    all_resource_ids_in_expected_order = resource_ids(all_resources_in_expected_order)

    result = await client.resource_list(env.id, limit=2, sort=f"{order_by_column}.{order}", filter={"agent": ["1", "2"]})
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


@pytest.mark.parametrize(
    "sort, expected_status",
    [
        ("agents.Desc", 400),
        ("agent.asc", 200),
        ("resource_type.dsc", 400),
        ("resource_type", 400),
        ("state.DESC", 400),
        ("status.ASC", 200),
        ("resource_id_values.desc", 400),
        ("resource_id_value.desc", 200),
    ],
)
@pytest.mark.asyncio
async def test_sorting_validation(server, client, sort, expected_status, env_with_resources):
    result = await client.resource_list(env_with_resources.id, limit=2, sort=sort)
    assert result.code == expected_status


@pytest.mark.parametrize(
    "filter, expected_status",
    [
        ("agents.Desc", 400),
        ({"agent": "internal"}, 200),
        ({"agents": ["internal", "remote"]}, 400),
        ({"resource_id_value": ["123", "456"]}, 200),
        ({"resource_id_values": ["123", "456"]}, 400),
        ({"resourceType": ["file"]}, 400),
        ({"state": ["deployed"]}, 400),
    ],
)
@pytest.mark.asyncio
async def test_filter_validation(server, client, filter, expected_status, env_with_resources):
    result = await client.resource_list(env_with_resources.id, limit=2, filter=filter)
    assert result.code == expected_status


@pytest.mark.asyncio
async def test_paging_param_validation(server, client, env_with_resources):
    result = await client.resource_list(env_with_resources.id, limit=2, start="1", end="10")
    assert result.code == 400

    result = await client.resource_list(env_with_resources.id, limit=2, start="1", last_id="1234")
    assert result.code == 400

    result = await client.resource_list(env_with_resources.id, limit=2, first_id="1234", end="10")
    assert result.code == 400

    result = await client.resource_list(env_with_resources.id, limit=2, first_id="1234", last_id="5678")
    assert result.code == 400


@pytest.mark.asyncio
async def test_deploy_summary(server, client, env_with_resources):
    """ Test querying the deployment summary of resources."""
    env = env_with_resources
    expected_summary = {
        "total": 4,
        "by_state": {
            "unavailable": 1,
            "skipped": 1,
            "deployed": 1,
            "deploying": 0,
            "available": 1,
            "failed": 0,
            "cancelled": 0,
            "undefined": 0,
            "skipped_for_undefined": 0,
            "processing_events": 0,
        },
    }
    result = await client.resource_list(env.id, deploy_summary=True)
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"] == expected_summary

    # The summary should not depend on filters or paging
    result = await client.resource_list(env.id, deploy_summary=True, limit=2, filter={"agent": "1"})
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"] == expected_summary

    # If the page is requested with the deploy summary, the links have it enabled as well
    result = await client.resource_list(env.id, deploy_summary=True, limit=2)
    assert result.code == 200
    assert "deploy_summary=True" in result.result["links"]["next"]

    # The summary is returned only when the parameter is set
    result = await client.resource_list(env.id)
    assert result.code == 200
    assert not result.result["metadata"].get("deploy_summary")

    env2 = data.Environment(name="test", project=env.project, repo_url="", repo_branch="")
    await env2.insert()

    # Each state is present in the summary, even if there are no resources
    empty_summary = {
        "total": 0,
        "by_state": {
            "unavailable": 0,
            "skipped": 0,
            "deployed": 0,
            "deploying": 0,
            "available": 0,
            "failed": 0,
            "cancelled": 0,
            "undefined": 0,
            "skipped_for_undefined": 0,
            "processing_events": 0,
        },
    }
    result = await client.resource_list(env2.id, deploy_summary=True)
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"] == empty_summary
