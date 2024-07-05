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
from collections import defaultdict
from typing import Any
from uuid import UUID

import pytest

from inmanta import data
from inmanta.const import ResourceState
from inmanta.data.model import ResourceVersionIdStr
from inmanta.util import parse_timestamp


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
        cm_times.append(datetime.datetime.strptime(f"2021-07-07T1{i}:00:00.0", "%Y-%m-%dT%H:%M:%S.%f"))
    cm_time_idx = 0
    resource_deploy_times = []
    for i in range(30):
        resource_deploy_times.append(datetime.datetime.strptime(f"2021-07-07T11:{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f"))

    # Add multiple versions of model, with 2 of them released
    for i in range(1, 6):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=cm_times[cm_time_idx],
            total=1,
            released=i != 1 and i != 5,
            version_info={},
            is_suitable_for_partial_compiles=False,
        )
        cm_time_idx += 1
        await cm.insert()

    cm = data.ConfigurationModel(
        environment=env2.id,
        version=4,
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        total=1,
        released=True,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    cm_time_idx += 1
    await cm.insert()

    cm = data.ConfigurationModel(
        environment=env3.id,
        version=6,
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        total=1,
        released=True,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    cm_time_idx += 1
    await cm.insert()
    resources = {env.id: defaultdict(list), env2.id: defaultdict(list), env3.id: defaultdict(list)}

    def total_number_of_resources():
        return sum(
            [
                len(resource_list_by_env)
                for resource_list_by_env in [
                    [
                        specific_resource
                        for specific_resource_list in envdict.values()
                        for specific_resource in specific_resource_list
                    ]
                    for envdict in resources.values()
                ]
            ]
        )

    async def create_resource(
        name: str,
        status: ResourceState,
        version: int,
        attributes: dict[str, object],
        agent: str = "internal",
        resource_type: str = "std::testing::NullResource",
        environment: UUID = env.id,
    ):
        key = f"{resource_type}[{agent},name={name}]"
        res = data.Resource.new(
            environment=environment,
            resource_version_id=ResourceVersionIdStr(f"{key},v={version}"),
            attributes={**attributes, **{"name": name}},
            status=status,
            last_deploy=resource_deploy_times[total_number_of_resources()],
        )
        await res.insert()
        return res

    # A resource with multiple resources in its requires list, and multiple versions where it was released,
    # and is also present in versions that were not released
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.undefined,
            1,
            {"key1": "val1", "requires": ["std::testing::NullResource[internal,name=/tmp/dir1]"]},
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.skipped,
            2,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": [
                    "std::testing::NullResource[internal,name=/tmp/dir1]",
                    "std::testing::NullResource[internal,name=/tmp/dir1/file2]",
                ],
            },
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deploying,
            3,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": [
                    "std::testing::NullResource[internal,name=/tmp/dir1]",
                    "std::testing::NullResource[internal,name=/tmp/dir1/file2]",
                ],
            },
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            4,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": [
                    "std::testing::NullResource[internal,name=/tmp/dir1]",
                    "std::testing::NullResource[internal,name=/tmp/dir1/file2]",
                ],
            },
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.undefined,
            5,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": [
                    "std::testing::NullResource[internal,name=/tmp/dir1]",
                    "std::testing::NullResource[internal,name=/tmp/dir1/file2]",
                ],
            },
        )
    )

    # A resource that didn't change its attributes, but was only released with the second version and has no requirements
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1",
            ResourceState.undefined,
            1,
            {"key2": "val2", "requires": []},
            resource_type="std::testing::NullResource",
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1",
            ResourceState.deploying,
            2,
            {"key2": "val2", "requires": []},
            resource_type="std::testing::NullResource",
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1", ResourceState.deployed, 3, {"key2": "val2", "requires": []}, resource_type="std::testing::NullResource"
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1", ResourceState.deployed, 4, {"key2": "val2", "requires": []}, resource_type="std::testing::NullResource"
        )
    )

    # A resource that changed the attributes in the last released version,
    # so the last and the first time the attributes are the same, is the same as well;
    # And it also has a single requirement
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file2]"].append(
        await create_resource("/tmp/dir1/file2", ResourceState.undefined, 1, {"key3": "val3", "requires": []})
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deployed,
            2,
            {"key3": "val3", "requires": ["std::testing::NullResource[internal,name=/tmp/dir1]"]},
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deployed,
            3,
            {"key3": "val3", "requires": ["std::testing::NullResource[internal,name=/tmp/dir1]"]},
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deploying,
            4,
            {"key3": "val3updated", "requires": ["std::testing::NullResource[internal,name=/tmp/dir1]"]},
        )
    )

    # Add an unreleased resource
    resources[env.id]["std::testing::NullResource[internal,name=/etc/filexyz]"].append(
        await create_resource(
            "/etc/filexyz",
            ResourceState.undefined,
            5,
            {"key4": "val4", "requires": []},
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/etc/never_deployed]"].append(
        await create_resource(
            "/etc/never_deployed",
            ResourceState.undefined,
            3,
            {"key5": "val5", "requires": []},
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/etc/never_deployed]"].append(
        await create_resource(
            "/etc/never_deployed",
            ResourceState.unavailable,
            4,
            {"key5": "val5", "requires": []},
        )
    )

    resources[env.id]["std::testing::NullResource[internal,name=/etc/deployed_only_with_different_hash]"].append(
        await create_resource(
            "/etc/deployed_only_with_different_hash",
            ResourceState.deployed,
            3,
            {"key6": "val6", "requires": []},
        )
    )

    resources[env.id]["std::testing::NullResource[internal,name=/etc/deployed_only_with_different_hash]"].append(
        await create_resource(
            "/etc/deployed_only_with_different_hash",
            ResourceState.undefined,
            4,
            {"key6": "val6different", "requires": []},
        )
    )

    resources[env.id]["std::testing::NullResource[internal,name=/etc/deployed_only_in_earlier_version]"].append(
        await create_resource(
            "/etc/deployed_only_in_earlier_version",
            ResourceState.deployed,
            3,
            {"key7": "val7", "requires": ["std::testing::NullResource[internal,name=/etc/requirement_in_later_version]"]},
        )
    )

    resources[env.id]["std::testing::NullResource[internal,name=/etc/requirement_in_later_version]"].append(
        await create_resource(
            "/etc/requirement_in_later_version",
            ResourceState.deploying,
            3,
            {"key8": "val8", "requires": []},
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/etc/requirement_in_later_version]"].append(
        await create_resource(
            "/etc/requirement_in_later_version",
            ResourceState.deployed,
            4,
            {"key8": "val8", "requires": []},
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/etc/requirement_in_later_version]"].append(
        await create_resource(
            "/etc/requirement_in_later_version",
            ResourceState.skipped,
            5,
            {"key8": "val8", "requires": []},
        )
    )

    resources[env.id]["std::testing::NullResource[internal,name=/tmp/orphaned]"].append(
        await create_resource(
            "/tmp/orphaned",
            ResourceState.deployed,
            3,
            {"key9": "val9", "requires": ["std::testing::NullResource[internal,name=/tmp/orphaned_req]"]},
        )
    )
    resources[env.id]["std::testing::NullResource[internal,name=/tmp/orphaned_req]"].append(
        await create_resource(
            "/tmp/orphaned_req",
            ResourceState.deployed,
            3,
            {"key9": "val9", "requires": []},
        )
    )

    # Add the same resources the first one requires in another environment
    resources[env2.id]["std::testing::NullResource[internal,name=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.unavailable,
            4,
            {"key3": "val3", "requires": ["std::testing::NullResource[internal,name=/tmp/dir1]"]},
            resource_type="std::testing::NullResource",
            environment=env2.id,
        )
    )

    resources[env2.id]["std::testing::NullResource[internal,name=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1",
            ResourceState.available,
            4,
            {"key2": "val2", "requires": []},
            resource_type="std::testing::NullResource",
            environment=env2.id,
        )
    )

    # Add the same main resource to another environment with higher version
    resources[env3.id]["std::testing::NullResource[internal,name=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deploying,
            6,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": [
                    "std::testing::NullResource[internal,name=/tmp/dir1]",
                    "std::testing::NullResource[internal,name=/tmp/dir1/file2]",
                ],
            },
            environment=env3.id,
        )
    )
    ids = {
        "multiple_requires": "std::testing::NullResource[internal,name=/tmp/dir1/file1]",
        "no_requires": "std::testing::NullResource[internal,name=/tmp/dir1]",
        "single_requires": "std::testing::NullResource[internal,name=/tmp/dir1/file2]",
        "unreleased": "std::testing::NullResource[internal,name=/etc/filexyz]",
        "never_deployed": "std::testing::NullResource[internal,name=/etc/never_deployed]",
        "deployed_only_with_different_hash": "std::testing::NullResource[internal,name=/etc/deployed_only_with_different_hash]",
        "deployed_only_in_earlier_version": "std::testing::NullResource[internal,name=/etc/deployed_only_in_earlier_version]",
        "orphaned_and_requires_orphaned": "std::testing::NullResource[internal,name=/tmp/orphaned]",
    }

    yield env, cm_times, ids, resources


async def assert_matching_attributes(resource_api: dict[str, Any], resource_db: data.Resource) -> None:
    """
    This method throws an AssertionError when the attributes of the resource retrieved via the API
    doesn't match with the attributes present in the DAO.
    """
    attributes_api = resource_api["attributes"]
    # Due to a bug, the version field has always been present in the attributes dictionary sent to the server.
    # This bug has been fixed in the database. For backwards compatibility reason the version field is present
    # in the attributes dictionary served out via the API.
    attributes_db = {**resource_db.attributes, "version": resource_db.model}
    assert attributes_api == attributes_db


async def test_resource_details(server, client, env_with_resources):
    """Test the resource details endpoint with multiple resources
    The released versions in the test environment are 2, 3 and 4, while 1 and 5 are not released.
    """
    env, cm_times, ids, resources = env_with_resources
    multiple_requires = ids["multiple_requires"]
    result = await client.resource_details(env.id, multiple_requires)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 2
    generated_time = parse_timestamp(result.result["data"]["first_generated_time"])
    assert generated_time == cm_times[1].astimezone(datetime.timezone.utc)
    deploy_time = parse_timestamp(result.result["data"]["last_deploy"])
    assert deploy_time == resources[env.id][multiple_requires][3].last_deploy.astimezone(datetime.timezone.utc)
    await assert_matching_attributes(result.result["data"], resources[env.id][multiple_requires][3])
    assert result.result["data"]["requires_status"] == {
        "std::testing::NullResource[internal,name=/tmp/dir1]": "deployed",
        "std::testing::NullResource[internal,name=/tmp/dir1/file2]": "deploying",
    }
    assert result.result["data"]["status"] == "deployed"

    no_requires = ids["no_requires"]
    result = await client.resource_details(env.id, no_requires)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 2
    generated_time = parse_timestamp(result.result["data"]["first_generated_time"])
    assert generated_time == cm_times[1].astimezone(datetime.timezone.utc)
    deploy_time = parse_timestamp(result.result["data"]["last_deploy"])
    assert deploy_time == resources[env.id][no_requires][3].last_deploy.astimezone(datetime.timezone.utc)
    await assert_matching_attributes(result.result["data"], resources[env.id][no_requires][3])
    assert result.result["data"]["requires_status"] == {}
    assert result.result["data"]["status"] == "deployed"

    single_requires = ids["single_requires"]
    result = await client.resource_details(env.id, single_requires)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 4
    generated_time = parse_timestamp(result.result["data"]["first_generated_time"])
    assert generated_time == cm_times[3].astimezone(datetime.timezone.utc)
    deploy_time = parse_timestamp(result.result["data"]["last_deploy"])
    assert deploy_time == resources[env.id][single_requires][3].last_deploy.astimezone(datetime.timezone.utc)
    await assert_matching_attributes(result.result["data"], resources[env.id][single_requires][3])
    assert result.result["data"]["requires_status"] == {"std::testing::NullResource[internal,name=/tmp/dir1]": "deployed"}
    assert result.result["data"]["status"] == "deploying"

    result = await client.resource_details(env.id, "non_existing_id")
    assert result.code == 404
    unreleased_resource = ids["unreleased"]
    result = await client.resource_details(env.id, unreleased_resource)
    assert result.code == 404

    never_deployed_resource = ids["never_deployed"]
    result = await client.resource_details(env.id, never_deployed_resource)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 3
    assert result.result["data"]["status"] == "unavailable"
    await assert_matching_attributes(result.result["data"], resources[env.id][never_deployed_resource][1])

    deployed_only_with_different_hash = ids["deployed_only_with_different_hash"]
    result = await client.resource_details(env.id, deployed_only_with_different_hash)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 4
    assert result.result["data"]["status"] == "undefined"
    await assert_matching_attributes(result.result["data"], resources[env.id][deployed_only_with_different_hash][1])

    deployed_only_in_earlier_version = ids["deployed_only_in_earlier_version"]
    result = await client.resource_details(env.id, deployed_only_in_earlier_version)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 3
    assert result.result["data"]["status"] == "orphaned"
    await assert_matching_attributes(result.result["data"], resources[env.id][deployed_only_in_earlier_version][0])
    assert result.result["data"]["requires_status"] == {
        "std::testing::NullResource[internal,name=/etc/requirement_in_later_version]": "deployed"
    }

    orphaned = ids["orphaned_and_requires_orphaned"]
    result = await client.resource_details(env.id, orphaned)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 3
    assert result.result["data"]["status"] == "orphaned"
    await assert_matching_attributes(result.result["data"], resources[env.id][orphaned][0])
    assert result.result["data"]["requires_status"] == {
        "std::testing::NullResource[internal,name=/tmp/orphaned_req]": "orphaned"
    }
