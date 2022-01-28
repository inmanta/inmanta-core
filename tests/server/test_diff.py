"""
    Copyright 2022 Inmanta

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
from typing import Dict

import pytest

from inmanta import data
from inmanta.const import ResourceState
from inmanta.data.model import ResourceVersionIdStr


@pytest.fixture
async def env_with_versions(environment):
    env_id = uuid.UUID(environment)

    for i in range(1, 4):
        cm = data.ConfigurationModel(
            environment=env_id,
            version=i,
            date=datetime.datetime.now(),
            total=1,
            released=i != 1,
            version_info={},
        )
        await cm.insert()


async def create_resource_in_multiple_versions(
    environment: uuid.UUID,
    path: str,
    version_attributes_map: Dict[int, Dict[str, object]],
    agent: str = "internal",
    resource_type: str = "std::File",
    status: ResourceState = ResourceState.deployed,
):
    key = f"{resource_type}[{agent},path={path}]"
    for version, attributes in version_attributes_map.items():
        attributes["requires"] = [f"{req},v={version}" for req in attributes.get("requires", [])]
        res = data.Resource.new(
            environment=environment,
            resource_version_id=ResourceVersionIdStr(f"{key},v={version}"),
            attributes={**attributes, **{"path": path}},
            status=status,
            last_deploy=datetime.datetime.now(),
        )
        await res.insert()


@pytest.mark.asyncio
async def test_list_attr_diff(client, environment, env_with_versions):
    """Test the diff functionality with simple values and lists."""
    env_id = uuid.UUID(environment)
    # Add a resource that doesn't change, so it shouldn't be included in either of the diffs
    constant_value = {"key2": "val2"}
    await create_resource_in_multiple_versions(
        env_id,
        "/tmp/dir1",
        {1: constant_value, 2: constant_value, 3: constant_value},
        resource_type="std::Directory",
    )
    # from v1 to v2 a single value and a list are changed, a list added another deleted,
    # and there is another list where the data type changes from ints to strings.
    # Since the string representations are the same, the latter shouldn't be included in the diff.
    # v2 and v3 have only one difference, the requires list
    await create_resource_in_multiple_versions(
        env_id,
        "/tmp/dir1/file1",
        {
            1: {
                "key1": "val1",
                "list_attr_removed": [1, 2],
                "list_attr_modified": [1, 2],
                "simple_attr_type_change": True,
                "requires": ["std::Directory[internal,path=/tmp/dir1]"],
            },
            2: {
                "key1": "val2",
                "list_attr_added": [3, 4],
                "list_attr_modified": [5, 4, 3],
                "simple_attr_type_change": "True",
                "requires": ["std::Directory[internal,path=/tmp/dir1]"],
            },
            3: {
                "key1": "val2",
                "list_attr_added": [3, 4],
                "list_attr_modified": [5, 4, 3],
                "simple_attr_type_change": "True",
                "requires": ["std::Directory[internal,path=/tmp/dir1]", "std::Directory[internal,path=/tmp/dir2]"],
            },
        },
    )

    result = await client.get_diff_of_versions(environment, 1, 2)
    assert result.code == 200
    # The result shouldn't include resources that haven't changed
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["status"] == "modified"
    assert result.result["data"][0]["attributes"]["key1"] == {
        "from_value": "val1",
        "to_value": "val2",
        "from_value_compare": "val1",
        "to_value_compare": "val2",
    }
    # The requires list is not changed
    assert "requires" not in result.result["data"][0]["attributes"]
    # Attributes, where the data changed but the string representation didn't, are not included in the diff
    assert "simple_attr_type_change" not in result.result["data"][0]["attributes"]
    assert result.result["data"][0]["attributes"]["list_attr_removed"] == {
        "from_value": [1, 2],
        "to_value": None,
        "from_value_compare": "[\n    1,\n    2\n]",
        "to_value_compare": None,
    }
    assert result.result["data"][0]["attributes"]["list_attr_added"] == {
        "from_value": None,
        "to_value": [3, 4],
        "from_value_compare": None,
        "to_value_compare": "[\n    3,\n    4\n]",
    }
    # Make sure that the order of the list elements doesn't change during comparison (so the [5,4,3] list is not sorted)
    assert result.result["data"][0]["attributes"]["list_attr_modified"] == {
        "from_value": [1, 2],
        "to_value": [5, 4, 3],
        "from_value_compare": "[\n    1,\n    2\n]",
        "to_value_compare": "[\n    5,\n    4,\n    3\n]",
    }
    v1_v2_diff = result.result["data"][0]["attributes"]
    # The only difference between v2 and v3 should be the extended requires
    result = await client.get_diff_of_versions(environment, 2, 3)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["status"] == "modified"
    assert len(result.result["data"][0]["attributes"]) == 1
    assert result.result["data"][0]["attributes"]["requires"] == {
        "from_value": ["std::Directory[internal,path=/tmp/dir1]"],
        "to_value": ["std::Directory[internal,path=/tmp/dir1]", "std::Directory[internal,path=/tmp/dir2]"],
        "from_value_compare": '[\n    "std::Directory[internal,path=/tmp/dir1]"\n]',
        "to_value_compare": '[\n    "std::Directory[internal,path=/tmp/dir1]",\n    "std::Directory[internal,path=/tmp/dir2]"\n'
        "]",
    }
    v2_v3_diff = result.result["data"][0]["attributes"]
    # In this specific case, the v1 to v3 diff should be the union of the v1_v2 and v2_v3 diffs
    result = await client.get_diff_of_versions(environment, 1, 3)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["status"] == "modified"
    assert result.result["data"][0]["attributes"] == {**v1_v2_diff, **v2_v3_diff}


@pytest.mark.asyncio
async def test_dict_attr_diff(client, environment, env_with_versions):
    """Test the diff functionality with dicts and nested structures"""
    env_id = uuid.UUID(environment)
    constant_value = {"key2": "val2"}
    await create_resource_in_multiple_versions(
        env_id,
        "/tmp/dir1",
        {1: constant_value, 2: constant_value, 3: constant_value},
        resource_type="std::Directory",
    )
    await create_resource_in_multiple_versions(
        env_id,
        "/tmp/dir2",
        {1: constant_value, 2: constant_value, 3: constant_value},
        resource_type="std::Directory",
    )
    # v1 and v3 are identical
    # The changes from v1 to v2 are adding, removing and modifying dict attributes,
    # as well as a change in the order of the requires list: this shouldn't be included in the diff
    await create_resource_in_multiple_versions(
        env_id,
        "/tmp/dir1/file1",
        {
            1: {
                "dict_attr_removed": {"a": "b"},
                "dict_attr_modified": {"x": [6, 7], "y": "y", "z": {"abc": "test1", "d": ["test2"]}},
                "requires": ["std::Directory[internal,path=/tmp/dir2]", "std::Directory[internal,path=/tmp/dir1]"],
            },
            2: {
                "dict_attr_added": {"x": "y"},
                "dict_attr_modified": {"x": [42], "z": {"abc": "test1", "d": ["test3"]}},
                "requires": ["std::Directory[internal,path=/tmp/dir1]", "std::Directory[internal,path=/tmp/dir2]"],
            },
            3: {
                "dict_attr_removed": {"a": "b"},
                "dict_attr_modified": {"x": [6, 7], "y": "y", "z": {"abc": "test1", "d": ["test2"]}},
                "requires": ["std::Directory[internal,path=/tmp/dir2]", "std::Directory[internal,path=/tmp/dir1]"],
            },
        },
    )
    result = await client.get_diff_of_versions(environment, 1, 2)
    assert result.code == 200
    # The result shouldn't include resources that haven't changed
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["status"] == "modified"
    assert len(result.result["data"][0]["attributes"]) == 3
    v1_v2 = result.result["data"][0]["attributes"]
    assert result.result["data"][0]["attributes"]["dict_attr_removed"] == {
        "from_value": {"a": "b"},
        "to_value": None,
        "from_value_compare": json.dumps({"a": "b"}, indent=4),
        "to_value_compare": None,
    }
    assert result.result["data"][0]["attributes"]["dict_attr_added"] == {
        "from_value": None,
        "to_value": {"x": "y"},
        "from_value_compare": None,
        "to_value_compare": json.dumps({"x": "y"}, indent=4),
    }
    assert result.result["data"][0]["attributes"]["dict_attr_modified"] == {
        "from_value": {"x": [6, 7], "y": "y", "z": {"abc": "test1", "d": ["test2"]}},
        "to_value": {"x": [42], "z": {"abc": "test1", "d": ["test3"]}},
        "from_value_compare": json.dumps(
            {"x": [6, 7], "y": "y", "z": {"abc": "test1", "d": ["test2"]}}, indent=4, sort_keys=True
        ),
        "to_value_compare": json.dumps({"x": [42], "z": {"abc": "test1", "d": ["test3"]}}, indent=4, sort_keys=True),
    }
    # Since v3 is the same as v1, the diff from v2 to v3 is the inverse of the diff from v1 to v2
    result = await client.get_diff_of_versions(environment, 2, 3)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["status"] == "modified"
    v2_v3 = {}
    for attr, values in v1_v2.items():
        swapped_values = {
            "from_value": values["to_value"],
            "to_value": values["from_value"],
            "from_value_compare": values["to_value_compare"],
            "to_value_compare": values["from_value_compare"],
        }
        v2_v3[attr] = swapped_values
    assert result.result["data"][0]["attributes"] == v2_v3
    result = await client.get_diff_of_versions(environment, 1, 3)
    assert result.code == 200
    assert len(result.result["data"]) == 0


def assert_resource_deleted(resource):
    assert resource["status"] == "deleted"
    for name, attr in resource["attributes"].items():
        assert attr["to_value"] is None
        assert attr["to_value_compare"] is None


def assert_resource_added(resource):
    assert resource["status"] == "added"
    for name, attr in resource["attributes"].items():
        assert attr["from_value"] is None
        assert attr["from_value_compare"] is None


@pytest.mark.asyncio
async def test_resources_diff(client, environment, env_with_versions):
    """Test the diff functionality on multiple resources across multiple versions"""
    env_id = uuid.UUID(environment)
    constant_value = {"key2": "val2"}
    # The resource is only present in version 1 and 3, the attribute values don't change
    await create_resource_in_multiple_versions(
        env_id,
        "/tmp/dir1",
        {1: constant_value, 3: constant_value},
        resource_type="std::Directory",
    )
    # The resource is only present in version 1 and 3, the attribute values change
    await create_resource_in_multiple_versions(
        env_id,
        "/tmp/dir1/file1",
        {
            1: {
                "dict_attr_modified": {
                    "x": [6, 7],
                    "y": "z",
                },
                "removed": False,
                "requires": ["std::Directory[internal,path=/tmp/dir1]"],
            },
            3: {
                "dict_attr_modified": {
                    "x": [42],
                },
                "requires": ["std::Directory[internal,path=/tmp/dir1]"],
            },
        },
    )
    # The resource is only present in version 2 and 3, the attribute values don't change
    await create_resource_in_multiple_versions(
        env_id,
        "/tmp/file2",
        {
            2: {
                "dict_attr_removed": {"a": "b"},
                "dict_attr_modified": {"x": [6, 7], "y": "y", "z": {"abc": "test1", "d": ["test2"]}},
            },
            3: {
                "dict_attr_removed": {"a": "b"},
                "dict_attr_modified": {"x": [6, 7], "y": "y", "z": {"abc": "test1", "d": ["test2"]}},
            },
        },
    )
    result = await client.get_diff_of_versions(environment, 1, 2)
    assert result.code == 200
    # 3 resource diffs: the directory and file1 are deleted, while file2 is added
    assert len(result.result["data"]) == 3
    assert result.result["data"][0]["resource_id"] == "std::Directory[internal,path=/tmp/dir1]"
    assert_resource_deleted(result.result["data"][0])
    assert result.result["data"][1]["resource_id"] == "std::File[internal,path=/tmp/dir1/file1]"
    assert_resource_deleted(result.result["data"][1])
    assert result.result["data"][2]["resource_id"] == "std::File[internal,path=/tmp/file2]"
    assert_resource_added(result.result["data"][2])

    # From 2 to 3, the directory and file1 are added and file2 doesn't change
    result = await client.get_diff_of_versions(environment, 2, 3)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"][0]["resource_id"] == "std::Directory[internal,path=/tmp/dir1]"
    assert_resource_added(result.result["data"][0])
    assert result.result["data"][1]["resource_id"] == "std::File[internal,path=/tmp/dir1/file1]"
    assert_resource_added(result.result["data"][1])

    # From 1 to 3, the directory doesn't change, file1 changes and file2 is added
    result = await client.get_diff_of_versions(environment, 1, 3)
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert result.result["data"][0]["resource_id"] == "std::File[internal,path=/tmp/dir1/file1]"
    assert result.result["data"][0]["status"] == "modified"
    assert result.result["data"][0]["attributes"]["dict_attr_modified"] == {
        "from_value": {"x": [6, 7], "y": "z"},
        "to_value": {
            "x": [42],
        },
        "from_value_compare": json.dumps({"x": [6, 7], "y": "z"}, indent=4, sort_keys=True),
        "to_value_compare": json.dumps(
            {
                "x": [42],
            },
            indent=4,
            sort_keys=True,
        ),
    }
    assert result.result["data"][0]["attributes"]["removed"] == {
        "from_value": False,
        "to_value": None,
        "from_value_compare": "False",
        "to_value_compare": None,
    }
    assert result.result["data"][1]["resource_id"] == "std::File[internal,path=/tmp/file2]"
    assert_resource_added(result.result["data"][1])


@pytest.mark.asyncio
async def test_validate_versions(client, environment, env_with_versions):
    """Test the version parameter validation of the diff endpoint."""
    result = await client.get_diff_of_versions(environment, 1, 2)
    assert result.code == 200
    result = await client.get_diff_of_versions(environment, 1, 1)
    assert result.code == 400
    result = await client.get_diff_of_versions(environment, 2, 1)
    assert result.code == 400
    result = await client.get_diff_of_versions(environment, 1, 100)
    assert result.code == 404
    result = await client.get_diff_of_versions(environment, 100, 110)
    assert result.code == 404
    result = await client.get_diff_of_versions(environment, 110, 100)
    assert result.code == 400
