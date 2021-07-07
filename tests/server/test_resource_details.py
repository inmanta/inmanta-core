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
from typing import Dict
from uuid import UUID

import pytest

from inmanta import data
from inmanta.const import ResourceState
from inmanta.data.model import ResourceVersionIdStr


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
    # Add multiple versions of model, with 2 of them released
    for i in range(1, 6):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.datetime.now(tz=datetime.timezone.utc),
            total=1,
            released=i != 1 and i != 5,
            version_info={},
        )
        cm_times.append(cm.date)
        await cm.insert()

    cm = data.ConfigurationModel(
        environment=env2.id,
        version=2,
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        total=1,
        released=True,
        version_info={},
    )
    cm_times.append(cm.date)
    await cm.insert()

    cm = data.ConfigurationModel(
        environment=env3.id,
        version=6,
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        total=1,
        released=True,
        version_info={},
    )
    cm_times.append(cm.date)
    await cm.insert()

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
            last_deploy=datetime.datetime.now(),
        )
        await res.insert()
        return res

    resources = {env.id: defaultdict(list), env2.id: defaultdict(list), env3.id: defaultdict(list)}
    # A resource with multiple resources in its requires list, and multiple versions where it was released,
    # and is also present in versions that were not released
    resources[env.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.undefined,
            1,
            {"key1": "val1", "requires": ["std::Directory[internal,path=/tmp/dir1],v=1"]},
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
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=2", "std::File[internal,path=/tmp/dir1/file2],v=2"],
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
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=2", "std::File[internal,path=/tmp/dir1/file2],v=2"],
            },
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deploying,
            4,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=2", "std::File[internal,path=/tmp/dir1/file2],v=2"],
            },
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file1]"].append(
        await create_resource(
            "/tmp/dir1/file1",
            ResourceState.deployed,
            5,
            {
                "key1": "modified_value",
                "another_key": "val",
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=2", "std::File[internal,path=/tmp/dir1/file2],v=2"],
            },
        )
    )

    # A resource that didn't change its attributes, but was only released with the second version and has no requirements
    resources[env.id]["std::Directory[internal,path=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1", ResourceState.skipped, 1, {"key2": "val2", "requires": []}, resource_type="std::Directory"
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

    # A resource that changed the attributes in the last released version,
    # so the last and the first time the attributes are the same, is the same as well;
    # And it also has a single requirement
    resources[env.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource("/tmp/dir1/file2", ResourceState.skipped_for_undefined, 1, {"key3": "val3", "requires": []})
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deployed,
            2,
            {"key3": "val3", "requires": ["std::Directory[internal,path=/tmp/dir1],v=2"]},
        )
    )
    resources[env.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.deployed,
            3,
            {"key3": "val3updated", "requires": ["std::Directory[internal,path=/tmp/dir1],v=2"]},
        )
    )

    # Add an unreleased resource
    resources[env.id]["std::File[internal,path=/etc/filexyz]"].append(
        await create_resource(
            "/etc/filexyz",
            ResourceState.deployed,
            5,
            {"key4": "val4", "requires": []},
        )
    )

    # Add the same resources the first one requires in another environment
    resources[env2.id]["std::File[internal,path=/tmp/dir1/file2]"].append(
        await create_resource(
            "/tmp/dir1/file2",
            ResourceState.unavailable,
            2,
            {"key3": "val3", "requires": ["std::Directory[internal,path=/tmp/dir1],v=2"]},
            environment=env2.id,
        )
    )

    resources[env2.id]["std::Directory[internal,path=/tmp/dir1]"].append(
        await create_resource(
            "/tmp/dir1",
            ResourceState.available,
            2,
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
                "requires": ["std::Directory[internal,path=/tmp/dir1],v=2", "std::File[internal,path=/tmp/dir1/file2],v=2"],
            },
            environment=env3.id,
        )
    )
    ids = {
        "multiple_requires": "std::File[internal,path=/tmp/dir1/file1]",
        "no_requires": "std::Directory[internal,path=/tmp/dir1]",
        "single_requires": "std::File[internal,path=/tmp/dir1/file2]",
        "unreleased": "std::File[internal,path=/etc/filexyz]",
    }

    yield env, cm_times, ids, resources


@pytest.mark.asyncio
async def test_resource_details(server, client, env_with_resources):
    env, cm_times, ids, resources = env_with_resources
    multiple_requires = ids["multiple_requires"]
    result = await client.resource_details(env.id, multiple_requires)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 2
    generated_time = datetime.datetime.strptime(result.result["data"]["first_generated_time"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    )
    assert generated_time == cm_times[1].astimezone(datetime.timezone.utc)
    deploy_time = datetime.datetime.strptime(result.result["data"]["last_deploy"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    )
    assert deploy_time == resources[env.id][multiple_requires][3].last_deploy.astimezone(datetime.timezone.utc)
    assert result.result["data"]["attributes"] == resources[env.id][multiple_requires][2].attributes
    assert result.result["data"]["requires_status"] == {
        "std::Directory[internal,path=/tmp/dir1],v=2": "deploying",
        "std::File[internal,path=/tmp/dir1/file2],v=2": "deployed",
    }
    no_requires = ids["no_requires"]
    result = await client.resource_details(env.id, no_requires)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 2
    generated_time = datetime.datetime.strptime(result.result["data"]["first_generated_time"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    )
    assert generated_time == cm_times[1].astimezone(datetime.timezone.utc)
    deploy_time = datetime.datetime.strptime(result.result["data"]["last_deploy"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    )
    assert deploy_time == resources[env.id][no_requires][2].last_deploy.astimezone(datetime.timezone.utc)
    assert result.result["data"]["attributes"] == resources[env.id][no_requires][2].attributes
    assert result.result["data"]["requires_status"] == {}

    single_requires = ids["single_requires"]
    result = await client.resource_details(env.id, single_requires)
    assert result.code == 200
    assert result.result["data"]["first_generated_version"] == 3
    generated_time = datetime.datetime.strptime(result.result["data"]["first_generated_time"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    )
    assert generated_time == cm_times[2].astimezone(datetime.timezone.utc)
    deploy_time = datetime.datetime.strptime(result.result["data"]["last_deploy"], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=datetime.timezone.utc
    )
    assert deploy_time == resources[env.id][single_requires][2].last_deploy.astimezone(datetime.timezone.utc)
    assert result.result["data"]["attributes"] == resources[env.id][single_requires][2].attributes
    assert result.result["data"]["requires_status"] == {"std::Directory[internal,path=/tmp/dir1],v=2": "deploying"}

    result = await client.resource_details(env.id, "non_existing_id")
    assert result.code == 404
    unreleased_resource = ids["unreleased"]
    result = await client.resource_details(env.id, unreleased_resource)
    assert result.code == 404
