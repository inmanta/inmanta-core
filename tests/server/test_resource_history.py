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
import datetime
import json
import uuid
from collections import defaultdict
from operator import itemgetter
from typing import Dict
from uuid import UUID

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.const import ResourceState
from inmanta.data.model import ResourceVersionIdStr
from inmanta.server.config import get_bind_port


@pytest.fixture
async def env_with_resources(server, client):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    env2 = data.Environment(name="dev2", project=project.id, repo_url="", repo_branch="")
    await env2.insert()

    env3 = data.Environment(name="dev3", project=project.id, repo_url="", repo_branch="")
    await env3.insert()

    cm_times = []
    for i in range(1, 10):
        cm_times.append(datetime.datetime.strptime(f"2021-07-07T11:{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f"))
    cm_time_idx = 0
    resource_deploy_times = []
    for i in range(40):
        resource_deploy_times.append(datetime.datetime.strptime(f"2021-07-07T11:{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f"))

    # Add multiple versions of model, with 2 of them released
    for i in range(1, 10):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=cm_times[cm_time_idx],
            total=1,
            released=i != 1 and i != 9,
            version_info={},
        )
        cm_time_idx += 1
        await cm.insert()

    cm = data.ConfigurationModel(
        environment=env2.id,
        version=8,
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        total=1,
        released=True,
        version_info={},
    )
    cm_time_idx += 1
    await cm.insert()

    cm = data.ConfigurationModel(
        environment=env3.id,
        version=8,
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        total=1,
        released=True,
        version_info={},
    )
    cm_time_idx += 1
    await cm.insert()
    resources = defaultdict(list)

    def total_number_of_resources():
        return sum([len(resource_list) for resource_list in resources.values()])

    async def create_resource(
        path: str,
        status: ResourceState,
        version: int,
        attributes: Dict[str, object],
        agent: str = "internal",
        resource_type: str = "std::File",
        environment: UUID = env.id,
    ):
        key = f"{resource_type}[{agent},path={path}]"
        res = data.Resource.new(
            environment=environment,
            resource_version_id=ResourceVersionIdStr(f"{key},v={version}"),
            attributes={**attributes, **{"path": path}},
            status=status,
            last_deploy=resource_deploy_times[total_number_of_resources()],
        )
        await res.insert()
        return res

    # A resource with multiple resources in its requires list, and multiple versions where it was released,
    # and is also present in versions that were not released
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.undefined,
            1,
            {"key1": "val1", "requires": ["std::Directory[internal,path=/tmp/dir1],v=1"]},
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.skipped,
            2,
            {
                "key1": "val1",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=2", "std::File[internal,path=/tmp/dir1/file2],v=2"],
            },
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deploying,
            3,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=3", "std::File[internal,path=/tmp/dir1/file2],v=3"],
            },
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            4,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=4", "std::File[internal,path=/tmp/dir1/file2],v=4"],
            },
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            5,
            {
                "key1": "modified_value2",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=5", "std::File[internal,path=/tmp/dir1/file2],v=5"],
            },
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            6,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=6", "std::File[internal,path=/tmp/dir1/file2],v=6"],
            },
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            7,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=7", "std::File[internal,path=/tmp/dir1/file2],v=7"],
            },
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            8,
            {
                "key1": "different_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=8", "std::File[internal,path=/tmp/dir1/file2],v=8"],
            },
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            9,
            {
                "key1": "different_value_2",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=9", "std::File[internal,path=/tmp/dir1/file2],v=9"],
            },
        )
    )

    # A resource that didn't change its attributes, but was only released with the second version and has no requirements
    for i in range(1, 9):
        resources["std::Directory[internal,path=/tmp/dir1]"].append(
            await create_resource(
                "/tmp/dir1",
                ResourceState.undefined,
                i,
                {"key2": "val2", "requires": []},
                resource_type="std::Directory",
            )
        )

    # A resource that changed the attributes in the last released version,
    # And it also has a single requirement
    resources["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource("/tmp/dir1/file2", ResourceState.undefined, 1, {"key3": "val3", "requires": []})
    )
    resources["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deployed,
            2,
            {"key3": "val3", "requires": ["std::Directory[internal,path=/tmp/dir1],v=2"]},
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deployed,
            3,
            {"key3": "val3", "requires": ["std::Directory[internal,path=/tmp/dir1],v=3"]},
        )
    )
    resources["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deploying,
            8,
            {"key3": "val3updated", "requires": ["std::Directory[internal,path=/tmp/dir1],v=8"]},
        )
    )

    # Add an unreleased resource
    resources["std::File[internal,path=/etc/filexyz]"].append(
        await create_resource(
            "/etc/filexyz",
            ResourceState.undefined,
            9,
            {"key4": "val4", "requires": []},
        )
    )

    # Add the same resources the first one requires in another environment
    resources["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.unavailable,
            8,
            {"key3": "val3", "requires": ["std::Directory[internal,path=/tmp/dir1],v=4"]},
            resource_type="std::Directory",
            environment=env2.id,
        )
    )

    resources["std::Directory[internal,path=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1",
            ResourceState.available,
            8,
            {"key2": "val2", "requires": []},
            resource_type="std::Directory",
            environment=env2.id,
        )
    )

    # Add the same main resource to another environment with higher version
    resources["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deploying,
            8,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=6", "std::File[internal,path=/tmp/dir1/file2],v=6"],
            },
            environment=env3.id,
        )
    )
    ids = {
        "long_history": "std::File[internal,path=/tmp/dir1/file1]",
        "single_entry": "std::Directory[internal,path=/tmp/dir1]",
        "short_history": "std::File[internal,path=/tmp/dir1/file2]",
        "unreleased": "std::File[internal,path=/etc/filexyz]",
    }

    yield env, cm_times, ids, resources


@pytest.mark.asyncio
async def test_resource_history(client, server, env_with_resources):
    env, cm_times, ids, resources = env_with_resources
    resource_with_long_history = ids["long_history"]
    result = await client.resource_history(env.id, resource_with_long_history, sort="date.asc")
    assert result.code == 200
    assert len(result.result["data"]) == 5
    actual = []
    for entry in result.result["data"]:
        actual.append(
            {
                "date": datetime.datetime.strptime(entry["date"], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=datetime.timezone.utc),
                "attributes": entry["attributes"],
            }
        )
    expected = [
        {
            "date": cm_times[1].astimezone(datetime.timezone.utc),
            "attributes": resources[resource_with_long_history][1].attributes,
        },
        {
            "date": cm_times[2].astimezone(datetime.timezone.utc),
            "attributes": resources[resource_with_long_history][2].attributes,
        },
        {
            "date": cm_times[4].astimezone(datetime.timezone.utc),
            "attributes": resources[resource_with_long_history][4].attributes,
        },
        {
            "date": cm_times[5].astimezone(datetime.timezone.utc),
            "attributes": resources[resource_with_long_history][5].attributes,
        },
        {
            "date": cm_times[7].astimezone(datetime.timezone.utc),
            "attributes": resources[resource_with_long_history][7].attributes,
        },
    ]
    assert actual == expected
    result = await client.resource_history(env.id, resource_with_long_history, sort="date.desc")
    assert result.code == 200
    assert len(result.result["data"]) == 5
    actual = []
    for entry in result.result["data"]:
        actual.append(
            {
                "date": datetime.datetime.strptime(entry["date"], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=datetime.timezone.utc),
                "attributes": entry["attributes"],
            }
        )
    expected.reverse()
    assert actual == expected
    result = await client.resource_history(env.id, ids["unreleased"], sort="date.desc")
    assert result.code == 200
    assert len(result.result["data"]) == 0

    result = await client.resource_history(env.id, ids["single_entry"], sort="date.asc")
    assert result.code == 200
    assert len(result.result["data"]) == 1

    result = await client.resource_history(env.id, ids["short_history"])
    assert result.code == 200
    assert len(result.result["data"]) == 2


def attribute_hashes(resource_objects):
    return [resource["attribute_hash"] for resource in resource_objects]


@pytest.mark.parametrize(
    "order_by_column, order",
    [
        ("date", "DESC"),
        ("date", "ASC"),
    ],
)
@pytest.mark.asyncio
async def test_resource_history_paging(server, client, order_by_column, order, env_with_resources):
    """ Test querying resource history with paging, using different sorting parameters."""
    env, cm_times, ids, resources = env_with_resources
    resource_with_long_history = ids["long_history"]

    result = await client.resource_history(env.id, resource_with_long_history)
    assert result.code == 200
    assert len(result.result["data"]) == 5
    all_resources_in_expected_order = sorted(
        result.result["data"], key=itemgetter(order_by_column, "attribute_hash"), reverse=order == "DESC"
    )
    all_resource_ids_in_expected_order = attribute_hashes(all_resources_in_expected_order)

    result = await client.resource_history(env.id, resource_with_long_history, limit=2, sort=f"{order_by_column}.{order}")
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert attribute_hashes(result.result["data"]) == all_resource_ids_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 5, "before": 0, "after": 3, "page_size": 2}
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
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert attribute_hashes(response["data"]) == all_resource_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 5, "before": 2, "after": 1, "page_size": 2}

    # Test link for next page
    url = f"""{base_url}{response["links"]["next"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    next_page_instance_ids = attribute_hashes(response["data"])
    assert next_page_instance_ids == all_resource_ids_in_expected_order[4:]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is None
    assert response["metadata"] == {"total": 5, "before": 4, "after": 0, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    prev_page_instance_ids = attribute_hashes(response["data"])
    assert prev_page_instance_ids == all_resource_ids_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 5, "before": 2, "after": 1, "page_size": 2}

    result = await client.resource_history(env.id, resource_with_long_history, limit=5, sort=f"{order_by_column}.{order}")
    assert result.code == 200
    assert len(result.result["data"]) == 5
    assert attribute_hashes(result.result["data"]) == all_resource_ids_in_expected_order

    assert result.result["metadata"] == {"total": 5, "before": 0, "after": 0, "page_size": 5}


@pytest.mark.asyncio
async def test_history_not_continuous_versions(server, client, environment):
    """Test the scenario when there are gaps in the version numbers,
    but the attributes remain the same. There should be only one item in the history in this case."""
    # Setup
    environment = uuid.UUID(environment)
    cm_times = []
    for i in range(1, 10):
        cm_times.append(datetime.datetime.strptime(f"2021-07-07T11:{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f"))

    async def create_resource(
        path: str,
        status: ResourceState,
        version: int,
        attributes: Dict[str, object],
        agent: str = "internal",
        resource_type: str = "std::File",
    ):
        key = f"{resource_type}[{agent},path={path}]"
        res = data.Resource.new(
            environment=environment,
            resource_version_id=ResourceVersionIdStr(f"{key},v={version}"),
            attributes={**attributes, **{"path": path}},
            status=status,
            last_deploy=datetime.datetime.now(),
        )
        await res.insert()
        return res

    # No version 3 and 5
    versions = [1, 2, 4, 6]
    for version in versions:
        await data.ConfigurationModel(
            environment=environment,
            version=version,
            date=cm_times[version],
            total=1,
            released=True,
            version_info={},
        ).insert()
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            version,
            {
                "key1": "val1",
            },
        )

    result = await client.resource_history(environment, "std::File[internal,path=/tmp/dir1/file1]")
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["attributes"] == {"key1": "val1", "path": "/tmp/dir1/file1"}
