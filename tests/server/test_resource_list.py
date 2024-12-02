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

import asyncio
import json
import logging
import time
import typing
import urllib.parse
import uuid
from datetime import datetime
from operator import itemgetter
from uuid import UUID

import pytest
from dateutil.tz import UTC
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

import inmanta.util
import util.performance
import utils
from inmanta import data
from inmanta.agent.executor import DeployResult
from inmanta.const import ResourceState
from inmanta.data.model import LatestReleasedResource, ResourceIdStr, ResourceVersionIdStr
from inmanta.deploy import persistence
from inmanta.server import config


async def test_resource_list_no_released_version(server, client):
    """Test that if there are no released versions of a resource, the result set is empty"""
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
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    name = "file1"
    key = f"std::testing::NullResource[agent1,name={name}]"
    res1_v1 = data.Resource.new(
        environment=env.id, resource_version_id=ResourceVersionIdStr(f"{key},v={version}"), attributes={"name": name}
    )
    await res1_v1.insert()

    result = await client.resource_list(env.id)
    assert result.code == 200
    assert len(result.result["data"]) == 0


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
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()

    version = 1
    name = "file" + str(1)
    key = "std::testing::NullResource[agent1,name=" + name + "]"
    res1_v1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"name": name})
    await res1_v1.insert()
    version = 2
    res1_v2 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"name": name},
        status=ResourceState.deploying,
    )
    await res1_v2.insert()
    version = 3
    res1_v3 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"name": name},
        status=ResourceState.deployed,
    )
    await res1_v3.insert()
    version = 4
    res1_v4 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"name": name, "new_attr": 123, "requires": ["abc"]},
        status=ResourceState.deployed,
    )
    await res1_v4.insert()
    await res1_v4.update_persistent_state(last_non_deploying_status=ResourceState.deployed)

    version = 1
    name = "file" + str(2)
    key = "std::testing::NullResource[agent1,name=" + name + "]"
    res2_v1 = data.Resource.new(environment=env.id, resource_version_id=key + ",v=%d" % version, attributes={"name": name})
    await res2_v1.insert()
    version = 2
    res2_v2 = data.Resource.new(
        environment=env.id,
        resource_version_id=key + ",v=%d" % version,
        attributes={"name": name},
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
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()

    async def create_resource(
        agent: str, path: str, resource_type: str, status: ResourceState, versions: list[int], environment: UUID = env.id
    ):
        for version in versions:
            key = f"{resource_type}[{agent},path={path}]"
            res = data.Resource.new(
                environment=environment,
                resource_version_id=ResourceVersionIdStr(f"{key},v={version}"),
                attributes={"path": path, "version": version},
                status=status,
            )
            await res.insert()
            await res.update_persistent_state(
                last_deploy=datetime.now(tz=UTC),
                last_non_deploying_status=(
                    status
                    if status
                    not in [
                        ResourceState.available,
                        ResourceState.deploying,
                        ResourceState.undefined,
                        ResourceState.skipped_for_undefined,
                    ]
                    else None
                ),
            )

    await create_resource("agent1", "/etc/file1", "test::File", ResourceState.available, [1, 2, 3])
    await create_resource("agent1", "/etc/file2", "test::File", ResourceState.deploying, [1, 2])  # Orphaned
    await create_resource("agent2", "/etc/file3", "test::File", ResourceState.deployed, [2])  # Orphaned
    await create_resource("agent2", "/tmp/file4", "test::File", ResourceState.unavailable, [3])
    await create_resource("agent2", "/tmp/dir5", "test::Directory", ResourceState.skipped, [3])
    await create_resource("agent3", "/tmp/dir6", "test::Directory", ResourceState.deployed, [3])

    env2 = data.Environment(name="dev-test2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()
    cm = data.ConfigurationModel(
        environment=env2.id,
        version=3,
        date=datetime.now(),
        total=1,
        released=True,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()
    await create_resource("agent1", "/tmp/file7", "test::File", ResourceState.deployed, [3], environment=env2.id)
    await create_resource("agent1", "/tmp/file2", "test::File", ResourceState.deployed, [3], environment=env2.id)
    await create_resource("agent2", "/tmp/dir5", "test::Directory", ResourceState.skipped, [3], environment=env2.id)

    env3 = data.Environment(name="dev-test3", project=project.id, repo_url="", repo_branch="")
    await env3.insert()
    cm = data.ConfigurationModel(
        environment=env3.id,
        version=6,
        date=datetime.now(),
        total=1,
        released=True,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()
    await create_resource("agent2", "/etc/file3", "test::File", ResourceState.deployed, [6], environment=env3.id)

    yield env


async def test_filter_resources(server, client, env_with_resources):
    """Test querying resources."""
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

    result = await client.resource_list(env.id, filter={"resource_id_value": ["file"]})
    assert result.code == 200
    assert len(result.result["data"]) == 4

    result = await client.resource_list(env.id, filter={"resource_id_value": ["/etc/file", "/tmp/file"]})
    assert result.code == 200
    assert len(result.result["data"]) == 4

    result = await client.resource_list(env.id, filter={"resource_type": ["Directory"]})
    assert result.code == 200
    assert len(result.result["data"]) == 2

    result = await client.resource_list(env.id, filter={"resource_type": ["File"]})
    assert result.code == 200
    assert len(result.result["data"]) == 4

    result = await client.resource_list(env.id, filter={"resource_type": ["File"], "resource_id_value": "5"})
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

    result = await client.resource_list(env.id, filter={"status": ["!deployed"]})
    assert result.code == 200
    assert len(result.result["data"]) == 5
    assert not any(resource["status"] == "deployed" for resource in result.result["data"])

    result = await client.resource_list(env.id, filter={"status": ["!deployed", "orphaned"]})
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"][0]["status"] == "orphaned"

    result = await client.resource_list(env.id, filter={"status": ["!orphaned"]})
    assert result.code == 200
    assert len(result.result["data"]) == 4
    assert not any(resource["status"] == "orphaned" for resource in result.result["data"])

    result = await client.resource_list(env.id, filter={"status": ["!orphaned", "!deployed", "skipped"]})
    assert result.code == 200
    assert len(result.result["data"]) == 1

    result = await client.resource_list(env.id, filter={"status": ["!orphaned", "orphaned"]})
    assert result.code == 400

    result = await client.resource_list(env.id, filter={"status": ["!!!!orphaned"]})
    assert result.code == 400

    result = await client.resource_list(env.id, filter={"status": [1, 2]})
    assert result.code == 400

    result = await client.resource_list(
        env.id,
        filter={
            "resource_id_value": ["/etc/file", "/tmp/file"],
            "resource_type": "File",
            "agent": "agent1",
            "status": ["!orphaned"],
        },
    )
    assert result.code == 200
    assert len(result.result["data"]) == 1


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
async def test_resources_paging(server, client, order_by_column, order, env_with_resources):
    """Test querying resources with paging, using different sorting parameters."""
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

    port = config.server_bind_port.get()
    base_url = f"http://localhost:{port}"
    http_client = AsyncHTTPClient()

    # Test link for self page
    url = f"""{base_url}{result.result["links"]["self"]}"""
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert response == result.result

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


async def test_none_resources_paging(server, client, env_with_resources):
    """Test the output when listing resources when the pagination criteria does not match any result.
    We want to assert that metadata and the provided links are still consistent in that particular situation"""
    env = env_with_resources

    no_result_desc_prev = await client.resource_list(
        env.id,
        limit=2,
        sort="agent.DESC",
        end="aaaa",
        last_id="aaa",
    )
    assert no_result_desc_prev.code == 200
    assert len(no_result_desc_prev.result["data"]) == 0
    assert no_result_desc_prev.result["links"] == {
        "prev": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False&start=aaaa&first_id=aaa",
        "first": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False",
        "self": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False",
    }
    assert no_result_desc_prev.result["metadata"] == {"after": 0, "before": 6, "page_size": 2, "total": 6}

    # If we try to fetch resources on the linked page, it should return something
    query_parameters_desc_prev = dict(
        urllib.parse.parse_qsl(urllib.parse.urlsplit(no_result_desc_prev.result["links"]["prev"]).query)
    )

    actual_result_desc_prev = await client.resource_list(env.id, **query_parameters_desc_prev)
    assert actual_result_desc_prev.code == 200
    expected_result_desc_prev = {
        "prev": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False&start=agent1&"
        "first_id=test%3A%3AFile%5Bagent1%2Cpath%3D%2Fetc%2Ffile2%5D",
        "first": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False",
        "self": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False&first_id=aaa&start=aaaa",
    }
    assert actual_result_desc_prev.result["links"] == expected_result_desc_prev
    assert actual_result_desc_prev.result["metadata"] == {"after": 0, "before": 4, "page_size": 2, "total": 6}
    assert len(actual_result_desc_prev.result["data"]) == 2

    no_result_desc_next = await client.resource_list(
        env.id,
        limit=2,
        sort="agent.DESC",
        start="zzz",
        first_id="zzzz",
    )
    assert no_result_desc_next.code == 200
    assert len(no_result_desc_next.result["data"]) == 0
    assert no_result_desc_next.result["links"] == {
        "next": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False&end=zzz&last_id=zzzz",
        "self": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False&first_id=zzzz&start=zzz",
    }
    assert no_result_desc_next.result["metadata"] == {"after": 6, "before": 0, "page_size": 2, "total": 6}

    # If we try to fetch resources on the linked page, it should return something
    query_parameters_desc_next = dict(
        urllib.parse.parse_qsl(urllib.parse.urlsplit(no_result_desc_next.result["links"]["next"]).query)
    )

    actual_result_desc_next = await client.resource_list(env.id, **query_parameters_desc_next)
    assert actual_result_desc_next.code == 200
    expected_result_desc_next = {
        "next": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False&end=agent2&last_id=test%3A%3AFile%5Bagent2%2"
        "Cpath%3D%2Ftmp%2Ffile4%5D",
        "self": "/api/v2/resource?limit=2&sort=agent.desc&deploy_summary=False",
    }
    assert actual_result_desc_next.result["links"] == expected_result_desc_next
    assert actual_result_desc_next.result["metadata"] == {"after": 4, "before": 0, "page_size": 2, "total": 6}
    assert len(actual_result_desc_next.result["data"]) == 2

    no_result_asc_prev = await client.resource_list(
        env.id,
        limit=2,
        sort="agent.ASC",
        start="zzz",
        first_id="zzzz",
    )
    assert no_result_asc_prev.code == 200
    assert len(no_result_asc_prev.result["data"]) == 0
    assert no_result_asc_prev.result["links"] == {
        "prev": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False&end=zzz&last_id=zzzz",
        "first": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False",
        "self": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False&first_id=zzzz&start=zzz",
    }
    assert no_result_asc_prev.result["metadata"] == {"after": 0, "before": 6, "page_size": 2, "total": 6}

    # If we try to fetch resources on the linked page, it should return something
    query_parameters_asc_prev = dict(
        urllib.parse.parse_qsl(urllib.parse.urlsplit(no_result_asc_prev.result["links"]["prev"]).query)
    )

    actual_result_asc_prev = await client.resource_list(env.id, **query_parameters_asc_prev)
    assert actual_result_asc_prev.code == 200
    expected_result_asc_prev = {
        "prev": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False&end=agent2&"
        "last_id=test%3A%3AFile%5Bagent2%2Cpath%3D%2Ftmp%2Ffile4%5D",
        "first": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False",
        "self": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False",
    }
    assert actual_result_asc_prev.result["links"] == expected_result_asc_prev
    assert actual_result_asc_prev.result["metadata"] == {"after": 0, "before": 4, "page_size": 2, "total": 6}
    assert len(actual_result_asc_prev.result["data"]) == 2

    no_result_asc_next = await client.resource_list(
        env.id,
        limit=2,
        sort="agent.ASC",
        end="aaaaa",
        last_id="aa",
    )
    assert no_result_asc_next.code == 200
    assert len(no_result_asc_next.result["data"]) == 0
    assert no_result_asc_next.result["links"] == {
        "next": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False&start=aaaaa&first_id=aa",
        "self": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False",
    }
    assert no_result_asc_next.result["metadata"] == {"after": 6, "before": 0, "page_size": 2, "total": 6}

    # If we try to fetch resources on the linked page, it should return something
    query_parameters_asc_next = dict(
        urllib.parse.parse_qsl(urllib.parse.urlsplit(no_result_asc_next.result["links"]["next"]).query)
    )

    actual_result_asc_next = await client.resource_list(env.id, **query_parameters_asc_next)
    assert actual_result_asc_next.code == 200
    expected_result_asc_next = {
        "next": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False&start=agent1&"
        "first_id=test%3A%3AFile%5Bagent1%2Cpath%3D%2Fetc%2Ffile2%5D",
        "self": "/api/v2/resource?limit=2&sort=agent.asc&deploy_summary=False&first_id=aa&start=aaaaa",
    }
    assert actual_result_asc_next.result["links"] == expected_result_asc_next
    assert actual_result_asc_next.result["metadata"] == {"after": 4, "before": 0, "page_size": 2, "total": 6}
    assert len(actual_result_asc_next.result["data"]) == 2


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
async def test_filter_validation(server, client, filter, expected_status, env_with_resources):
    result = await client.resource_list(env_with_resources.id, limit=2, filter=filter)
    assert result.code == expected_status


async def test_paging_param_validation(server, client, env_with_resources):
    result = await client.resource_list(env_with_resources.id, limit=2, start="1", end="10")
    assert result.code == 400

    result = await client.resource_list(env_with_resources.id, limit=2, start="1", last_id="1234")
    assert result.code == 400

    result = await client.resource_list(env_with_resources.id, limit=2, first_id="1234", end="10")
    assert result.code == 400

    result = await client.resource_list(env_with_resources.id, limit=2, first_id="1234", last_id="5678")
    assert result.code == 400


async def test_deploy_summary(server, client, env_with_resources):
    """Test querying the deployment summary of resources."""
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
        },
    }
    result = await client.resource_list(env2.id, deploy_summary=True)
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"] == empty_summary


@pytest.fixture
async def very_big_env(server, client, environment, clienthelper, null_agent, instances: int) -> int:
    env_obj = await data.Environment.get_by_id(environment)
    await env_obj.set(data.AUTO_DEPLOY, True)

    deploy_counter = 0
    # The mix:
    # 100 versions -> increments , all hashes change after 50 steps
    # each with 5000 resources (50 sets of 100 resources)
    # one undefined
    # one skip for undef
    # one failed
    # one skipped
    # 500 orphans: in second half, produce 10 orphans each
    # every 10th version is not released

    async def make_resource_set(tenant_index: int, iteration: int) -> int:
        is_full = tenant_index == 0 and iteration == 0
        if is_full:
            version = await clienthelper.get_version()
        else:
            version = 0

        def resource_id(ri: int) -> str:
            if iteration > 0 and ri > 40:
                ri += 10
            return f"test::XResource{int(ri / 20)}[agent{tenant_index},sub={ri}]"

        resources = [
            {
                "id": f"{resource_id(ri)},v={version}",
                "send_event": False,
                "purged": False,
                "requires": [] if ri % 2 == 0 else [resource_id(ri - 1)],
                "my_attribute": iteration,
            }
            for ri in range(100)
        ]
        resource_state = {resource_id(0): ResourceState.undefined}
        resource_sets = {resource_id(ri): f"set{tenant_index}" for ri in range(100)}
        if is_full:
            result = await client.put_version(
                environment,
                version,
                resources,
                resource_state,
                [],
                {},
                compiler_version=inmanta.util.get_compiler_version(),
                resource_sets=resource_sets,
            )
            assert result.code == 200
        else:
            result = await client.put_partial(
                environment,
                resource_state=resource_state,
                unknowns=[],
                version_info={},
                resources=resources,
                resource_sets=resource_sets,
            )
            assert result.code == 200
            version = result.result["data"]
        await utils.wait_until_version_is_released(client, environment, version)

        # Get all resources
        result = await client.get_version(tid=environment, id=version)
        assert result.code == 200
        all_resources: list[dict[str, object]] = result.result["resources"]

        # Filter out resources part of the increment
        increment: set[ResourceIdStr]
        increment, _ = await data.ConfigurationModel.get_increment(environment, version)
        resources_in_increment_for_agent: list[dict[str, object]] = [
            r for r in all_resources if r["resource_id"] in increment and r["agent"] == f"agent{tenant_index}"
        ]

        to_db_update_manager = persistence.ToDbUpdateManager(client, uuid.UUID(environment))

        async def deploy(resource: dict[str, object]) -> None:
            nonlocal deploy_counter
            rid = ResourceIdStr(resource["resource_id"])
            rvid = ResourceVersionIdStr(resource["resource_version_id"])
            actionid = uuid.uuid4()
            deploy_counter = deploy_counter + 1
            await to_db_update_manager.send_in_progress(actionid, rvid)
            if "sub=4]" in rid:
                return
            else:
                if "sub=2]" in rid:
                    status = ResourceState.failed
                elif "sub=3]" in rid:
                    status = ResourceState.skipped
                else:
                    status = ResourceState.deployed
                await to_db_update_manager.send_deploy_done(
                    result=DeployResult(
                        rvid=rvid,
                        action_id=actionid,
                        status=status,
                        messages=[],
                        changes={},
                        change=None,
                    )
                )

        await asyncio.gather(*(deploy(resource) for resource in resources_in_increment_for_agent))

    for iteration in [0, 1]:
        for tenant in range(instances):
            await make_resource_set(tenant, iteration)
            logging.getLogger(__name__).warning("deploys: %d, tenant: %d, iteration: %d", deploy_counter, tenant, iteration)

    return instances


@pytest.mark.slowtest
@pytest.mark.parametrize("instances", [2])  # set the size
@pytest.mark.parametrize("trace", [False])  # make it analyze the queries
async def test_resources_paging_performance(client, environment, very_big_env: int, trace: bool, async_finalizer):
    """Scaling test, not part of the norma testsuite"""
    # Basic sanity
    result = await client.resource_list(environment, limit=5, deploy_summary=True)
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"] == {
        "by_state": {
            "available": very_big_env - 1,
            "cancelled": 0,
            "deployed": (95 * very_big_env),
            "deploying": 1,
            "failed": very_big_env,
            "skipped": very_big_env,
            "skipped_for_undefined": very_big_env,
            "unavailable": 0,
            "undefined": very_big_env,
        },
        "total": very_big_env * 100,
    }

    port = config.server_bind_port.get()
    base_url = f"http://localhost:{port}"
    http_client = AsyncHTTPClient()

    # Test link for self page
    filters = [
        ({}, very_big_env * 110),
        ({"status": "!orphaned"}, very_big_env * 100),
        ({"status": "deploying"}, 1),
        ({"status": "deployed"}, 95 * very_big_env),
        ({"status": "available"}, very_big_env - 1),
        ({"agent": "agent0"}, 110),
        ({"agent": "someotheragent"}, 0),
        ({"resource_id_value": "39"}, very_big_env),
    ]

    orders = [
        f"{field}.{direction}"
        for field, direction in [
            ("agent", "DESC"),
            ("agent", "ASC"),
            ("resource_type", "DESC"),
            ("resource_type", "ASC"),
            ("status", "DESC"),
            ("status", "ASC"),
            ("resource_id_value", "DESC"),
            ("resource_id_value", "ASC"),
        ]
    ]

    if trace:
        util.performance.hook_base_document()

        async def unpatch():
            util.performance.unhook_base_document()

        async_finalizer(unpatch)

    for filter, totalcount in filters:
        for order in orders:
            # Pages 1-3
            async def time_call() -> typing.Union[float, dict[str, str]]:
                start = time.monotonic()
                result = await client.resource_list(environment, deploy_summary=True, filter=filter, limit=10, sort=order)
                assert result.code == 200
                assert result.result["metadata"]["total"] == totalcount
                return (time.monotonic() - start) * 1000, result.result.get("links", {})

            async def time_page(links: dict[str, str], name: str) -> typing.Union[float, dict[str, str]]:
                start = time.monotonic()
                if name not in links:
                    return 0, {}
                url = f"""{base_url}{links[name]}"""
                request = HTTPRequest(
                    url=url,
                    headers={"X-Inmanta-tid": str(environment)},
                )
                response = await http_client.fetch(request, raise_error=False)
                assert response.code == 200
                result = json.loads(response.body.decode("utf-8"))
                assert result["metadata"]["total"] == totalcount
                return (time.monotonic() - start) * 1000, result["links"]

            latency_page1, links = await time_call()
            latency_page2, links = await time_page(links, "next")
            latency_page3, links = await time_page(links, "next")

            logging.getLogger(__name__).warning(
                "Timings %s %s %d %d %d", filter, order, latency_page1, latency_page2, latency_page3
            )
