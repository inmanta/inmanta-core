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
import itertools
from collections import defaultdict
from typing import Any
from uuid import UUID

import pytest
from dateutil.tz import UTC

from inmanta import const, data
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
        resource_deploy_times.append(
            datetime.datetime.strptime(f"2021-07-07T11:{i}:00.0", "%Y-%m-%dT%H:%M:%S.%f").astimezone(UTC)
        )

    # nr 0 is not used
    is_version_released = [None, False, True, True, True, False]

    # Add multiple versions of model, with 2 of them not released
    for i in range(1, 6):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=cm_times[cm_time_idx],
            total=1,
            released=is_version_released[i],
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
    deploy_times = {env.id: defaultdict(list), env2.id: defaultdict(list), env3.id: defaultdict(list)}

    counter = itertools.count()

    async def create_resource(
        path: str,
        status: ResourceState,
        version: int,
        attributes: dict[str, object],
        agent: str = "internal",
        resource_type: str = "std::File",
        environment: UUID = env.id,
    ):
        key = f"{resource_type}[{agent},path={path}]"

        if environment == env.id:
            # check consistency of the testcase itself
            if not is_version_released[version]:
                assert status == ResourceState.available

        update_last_deployed = status in const.DONE_STATES

        res = data.Resource.new(
            environment=environment,
            resource_version_id=ResourceVersionIdStr(f"{key},v={version}"),
            attributes={**attributes, **{"path": path}},
            status=status,
        )
        await res.insert()

        last_deploy = resource_deploy_times[next(counter)]
        deploy_times[environment][key].append(last_deploy)
        if update_last_deployed:
            await res.update_persistent_state(last_deploy=last_deploy)

        return res

    # A resource with multiple resources in its requires list, and multiple versions where it was released,
    # and is also present in versions that were not released
    resources[env.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.available,
            1,
            {"key1": "val1", "requires": ["std::Directory[internal,path=/tmp/dir1]"]},
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.skipped,
            2,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1]", "std::File[internal,path=/tmp/dir1/file2]"],
            },
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deploying,
            3,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1]", "std::File[internal,path=/tmp/dir1/file2]"],
            },
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            4,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1]", "std::File[internal,path=/tmp/dir1/file2]"],
            },
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.available,
            5,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1]", "std::File[internal,path=/tmp/dir1/file2]"],
            },
        )
    )

    # A resource that didn't change its attributes, but was only released with the second version and has no requirements
    resources[env.id]["std::Directory[internal,path=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1",
            ResourceState.available,
            1,
            {"key2": "val2", "requires": []},
            resource_type="std::Directory",
        )
    )
    resources[env.id]["std::Directory[internal,path=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1", ResourceState.deploying, 2, {"key2": "val2", "requires": []}, resource_type="std::Directory"
        )
    )
    resources[env.id]["std::Directory[internal,path=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1", ResourceState.deployed, 3, {"key2": "val2", "requires": []}, resource_type="std::Directory"
        )
    )
    resources[env.id]["std::Directory[internal,path=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1", ResourceState.deployed, 4, {"key2": "val2", "requires": []}, resource_type="std::Directory"
        )
    )

    # A resource that changed the attributes in the last released version,
    # so the last and the first time the attributes are the same, is the same as well;
    # And it also has a single requirement
    resources[env.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource("/tmp/dir1/file2", ResourceState.available, 1, {"key3": "val3", "requires": []})
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deployed,
            2,
            {"key3": "val3", "requires": ["std::Directory[internal,path=/tmp/dir1]"]},
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deployed,
            3,
            {"key3": "val3", "requires": ["std::Directory[internal,path=/tmp/dir1]"]},
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deploying,
            4,
            {"key3": "val3updated", "requires": ["std::Directory[internal,path=/tmp/dir1]"]},
        )
    )

    # Add an unreleased resource
    resources[env.id]["std::File[internal,path=/etc/filexyz]"].append(
        await create_resource(
            "/etc/filexyz",
            ResourceState.available,
            5,
            {"key4": "val4", "requires": []},
        )
    )
    resources[env.id]["std::File[internal,path=/etc/never_deployed]"].append(
        await create_resource(
            "/etc/never_deployed",
            ResourceState.undefined,
            3,
            {"key5": "val5", "requires": []},
        )
    )
    resources[env.id]["std::File[internal,path=/etc/never_deployed]"].append(
        await create_resource(
            "/etc/never_deployed",
            ResourceState.unavailable,
            4,
            {"key5": "val5", "requires": []},
        )
    )

    resources[env.id]["std::File[internal,path=/etc/deployed_only_with_different_hash]"].append(
        await create_resource(
            "/etc/deployed_only_with_different_hash",
            ResourceState.deployed,
            3,
            {"key6": "val6", "requires": []},
        )
    )

    resources[env.id]["std::File[internal,path=/etc/deployed_only_with_different_hash]"].append(
        await create_resource(
            "/etc/deployed_only_with_different_hash",
            ResourceState.undefined,
            4,
            {"key6": "val6different", "requires": []},
        )
    )

    resources[env.id]["std::File[internal,path=/etc/deployed_only_in_earlier_version]"].append(
        await create_resource(
            "/etc/deployed_only_in_earlier_version",
            ResourceState.deployed,
            3,
            {"key7": "val7", "requires": ["std::File[internal,path=/etc/requirement_in_later_version]"]},
        )
    )

    resources[env.id]["std::File[internal,path=/etc/requirement_in_later_version]"].append(
        await create_resource(
            "/etc/requirement_in_later_version",
            ResourceState.deploying,
            3,
            {"key8": "val8", "requires": []},
        )
    )
    resources[env.id]["std::File[internal,path=/etc/requirement_in_later_version]"].append(
        await create_resource(
            "/etc/requirement_in_later_version",
            ResourceState.deployed,
            4,
            {"key8": "val8", "requires": []},
        )
    )
    resources[env.id]["std::File[internal,path=/etc/requirement_in_later_version]"].append(
        await create_resource(
            "/etc/requirement_in_later_version",
            ResourceState.available,
            5,
            {"key8": "val8", "requires": []},
        )
    )

    resources[env.id]["std::File[internal,path=/tmp/orphaned]"].append(
        await create_resource(
            "/tmp/orphaned",
            ResourceState.deployed,
            3,
            {"key9": "val9", "requires": ["std::File[internal,path=/tmp/orphaned_req]"]},
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/orphaned_req]"].append(
        await create_resource(
            "/tmp/orphaned_req",
            ResourceState.deployed,
            3,
            {"key9": "val9", "requires": []},
        )
    )

    # Add the same resources the first one requires in another environment
    resources[env2.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.unavailable,
            4,
            {"key3": "val3", "requires": ["std::Directory[internal,path=/tmp/dir1]"]},
            resource_type="std::Directory",
            environment=env2.id,
        )
    )

    resources[env2.id]["std::Directory[internal,path=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1",
            ResourceState.available,
            4,
            {"key2": "val2", "requires": []},
            resource_type="std::Directory",
            environment=env2.id,
        )
    )

    # Add the same main resource to another environment with higher version
    resources[env3.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deploying,
            6,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1]", "std::File[internal,path=/tmp/dir1/file2]"],
            },
            environment=env3.id,
        )
    )
    ids = {
        "multiple_requires": "std::File[internal,path=/tmp/dir1/file1]",
        "no_requires": "std::Directory[internal,path=/tmp/dir1]",
        "single_requires": "std::File[internal,path=/tmp/dir1/file2]",
        "unreleased": "std::File[internal,path=/etc/filexyz]",
        "never_deployed": "std::File[internal,path=/etc/never_deployed]",
        "deployed_only_with_different_hash": "std::File[internal,path=/etc/deployed_only_with_different_hash]",
        "deployed_only_in_earlier_version": "std::File[internal,path=/etc/deployed_only_in_earlier_version]",
        "orphaned_and_requires_orphaned": "std::File[internal,path=/tmp/orphaned]",
    }

    yield env, cm_times, ids, resources, deploy_times


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
    env, cm_times, ids, resources, deploy_times = env_with_resources
    multiple_requires = ids["multiple_requires"]
    result = await client.resource_details(env.id, multiple_requires)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 2
    generated_time = parse_timestamp(result.result["data"]["first_generated_time"])
    assert generated_time == cm_times[1].astimezone(datetime.timezone.utc)
    deploy_time = parse_timestamp(result.result["data"]["last_deploy"])
    assert deploy_time == deploy_times[env.id][multiple_requires][3]
    await assert_matching_attributes(result.result["data"], resources[env.id][multiple_requires][3])
    assert result.result["data"]["requires_status"] == {
        "std::Directory[internal,path=/tmp/dir1]": "deployed",
        "std::File[internal,path=/tmp/dir1/file2]": "deploying",
    }
    assert result.result["data"]["status"] == "deployed"

    no_requires = ids["no_requires"]
    result = await client.resource_details(env.id, no_requires)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 2
    generated_time = parse_timestamp(result.result["data"]["first_generated_time"])
    assert generated_time == cm_times[1].astimezone(datetime.timezone.utc)
    deploy_time = parse_timestamp(result.result["data"]["last_deploy"])
    assert deploy_time == deploy_times[env.id][no_requires][3]
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
    assert deploy_time == deploy_times[env.id][single_requires][2]
    await assert_matching_attributes(result.result["data"], resources[env.id][single_requires][3])
    assert result.result["data"]["requires_status"] == {"std::Directory[internal,path=/tmp/dir1]": "deployed"}
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
        "std::File[internal,path=/etc/requirement_in_later_version]": "deployed"
    }

    orphaned = ids["orphaned_and_requires_orphaned"]
    result = await client.resource_details(env.id, orphaned)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 3
    assert result.result["data"]["status"] == "orphaned"
    await assert_matching_attributes(result.result["data"], resources[env.id][orphaned][0])
    assert result.result["data"]["requires_status"] == {"std::File[internal,path=/tmp/orphaned_req]": "orphaned"}
