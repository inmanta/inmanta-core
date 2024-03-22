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

import asyncio
import uuid
from collections import abc
from typing import Optional

import utils
from inmanta import const, data
from inmanta.protocol.common import Result
from inmanta.resources import ResourceIdStr
from inmanta.util import get_compiler_version


async def test_resource_sets_via_put_version(server, client, environment, clienthelper):
    version = await clienthelper.get_version()

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[],
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
        },
    )
    assert result.code == 400

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2]"],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key4",
            "value": None,
            "id": "test::Resource[agent1,key=key4],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-b",
        "test::Resource[agent1,key=key3]": None,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200

    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    expected_resource_sets = {**resource_sets, "test::Resource[agent1,key=key4]": None}
    assert resource_sets_from_db == expected_resource_sets

    # also assert pip config can be None on put_version
    pip_config_result = await client.get_pip_config(
        tid=environment,
        version=version,
    )
    assert pip_config_result.code == 200
    assert pip_config_result.result["data"] is None


async def test_put_partial_version_allocation(server, client, environment, clienthelper) -> None:
    """
    Verify dynamic version allocation behavior for the put_partial endpoint.
    """
    # partial without a full to base it on gets rejected with clear error message
    result = await client.put_partial(
        tid=environment,
        resources=[],
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={},
    )
    assert result.code == 400
    assert "partial export requires a base model but no versions have been exported yet" in result.result["message"]

    def resources(version: int) -> list[dict[str, object]]:
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": [],
            },
        ]

    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
    }

    # full export
    full_version = await clienthelper.get_version()
    result: Result = await client.put_version(
        tid=environment,
        version=full_version,
        resources=resources(full_version),
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200

    async def put_partial_simple(version: int = 0, expected_error: Optional[tuple[int, str]] = None) -> Optional[int]:
        result: Result = await client.put_partial(
            tid=environment,
            resources=resources(version),
            resource_state={},
            unknowns=[],
            version_info={},
            resource_sets=resource_sets,
        )
        if expected_error is not None:
            code, message = expected_error
            assert result.code == code, result.result
            assert message in result.result["message"]
            return None
        else:
            assert result.code == 200, result.result
            return result.result["data"]

    await put_partial_simple(full_version + 1, (400, "Resources for partial export should not contain version information"))
    assert await put_partial_simple() == full_version + 1
    assert await put_partial_simple() == full_version + 2
    # allocate new version without storing a new model
    await clienthelper.get_version()
    assert await put_partial_simple() == full_version + 4
    model: Optional[data.ConfigurationModel] = await data.ConfigurationModel.get_version(environment, full_version + 4)
    assert model is not None
    assert model.partial_base == full_version + 2

    # test concurrent calls
    concurrency_base: int = full_version + 5
    nb_versions: int = 5
    futures: abc.Sequence[abc.Awaitable[int]] = [put_partial_simple() for _ in range(nb_versions)]
    concurrency_versions: abc.Sequence[int] = await asyncio.gather(*futures)
    assert set(concurrency_versions) == set(range(concurrency_base, concurrency_base + nb_versions))
    for version in concurrency_versions:
        model = await data.ConfigurationModel.get_version(environment, version)
        assert model is not None
        assert model.partial_base == version - 1

    # also assert pip config can be None on put_partial
    pip_config_result = await client.get_pip_config(tid=environment, version=full_version + 2)
    assert pip_config_result.code == 200
    assert pip_config_result.result["data"] is None


async def test_put_partial_replace_resource_set(server, client, environment, clienthelper):
    """
    When a partial compile updates a certain resource set, the entire resource set
    is replaced by the same resource set in the partial compile.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key2",
            "value": "value123",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={
            "test::Resource[agent1,key=key2]": "set-a",
        },
    )

    assert result.code == 200, result.result
    assert result.result is not None
    assert "data" in result.result
    assert result.result["data"] == version + 1
    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    assert len(resource_list) == 1
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key2],v=2"
    assert resource_list[0].model == 2
    assert len(resource_list[0].attributes["requires"]) == 0
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert resource_sets_from_db == {"test::Resource[agent1,key=key2]": "set-a"}


async def test_put_partial_resources_in_resource_set(server, client, environment, clienthelper):
    """
    Verify that all resources specified in resource_sets are also present in the
    resources
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key2",
            "value": "value123",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
            "test::Resource[agent1,key=key2]": "set-a",
        },
    )

    assert result.code == 400, result.result
    assert result.result["message"] == (
        "Invalid request: The following resource ids provided in the resource_sets "
        "parameter are not present in the resources list: "
        "test::Resource[agent1,key=key1]"
    )


async def test_put_partial_merge_not_in_resource_set(server, client, environment, clienthelper):
    """
    The resources in a partial compile that don't belong to a resource set (rest set) are merged
    together with the resources in the rest set of the previous version of the model.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets={},
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key2",
            "value": "value123",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={},
    )

    assert result.code == 200
    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version(uuid.UUID(environment)), key=lambda resource: resource.resource_id
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key1],v=2"
    assert resource_list[1].resource_version_id == "test::Resource[agent1,key=key2],v=2"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": None, "test::Resource[agent1,key=key2]": None}
    for r in resource_list:
        assert r.model == 2


async def test_put_partial_migrate_resource_to_other_resource_set(server, client, environment, clienthelper):
    """
    Resources cannot migrate to a different resource set using a partial compile.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets={"test::Resource[agent1,key=key1]": "set-a-old", "test::Resource[agent1,key=key2]": "set-b-old"},
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key1]": "set-a-new", "test::Resource[agent1,key=key2]": "set-b-new"},
    )

    assert result.code == 400
    expected_lines = [
        "Invalid request: The following Resource(s) cannot be migrated to a different resource set using a partial compile, "
        "a full compile is necessary for this process:",
        "    test::Resource[agent1,key=key1] moved from set-a-old to set-a-new",
        "    test::Resource[agent1,key=key2] moved from set-b-old to set-b-new",
    ]

    assert all(line in result.result["message"] for line in expected_lines)


async def test_put_partial_update_not_in_resource_set(server, client, environment, clienthelper):
    """
    A partial compile can never update resources that were not assigned to a specific resource set
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets={},
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key1",
            "value": "value123",
            "id": "test::Resource[agent1,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={},
    )

    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: Resource (test::Resource[agent1,key=key1]) without a "
        "resource set cannot be updated via a partial compile"
    )


async def test_put_partial_update_multiple_resource_set(server, client, environment, clienthelper):
    """
    A partial compile can update multiple resource sets at the same time.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-b",
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key1",
            "value": "value1123",
            "id": "test::Resource[agent1,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value234",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
            "test::Resource[agent1,key=key2]": "set-b",
        },
    )

    assert result.code == 200
    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version(uuid.UUID(environment)), key=lambda resource: resource.resource_id
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key1],v=2"
    assert resource_list[1].resource_version_id == "test::Resource[agent1,key=key2],v=2"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": "set-a", "test::Resource[agent1,key=key2]": "set-b"}
    for r in resource_list:
        assert r.model == 2


async def test_resource_sets_dependency_graph(server, client, environment, clienthelper):
    """
    The model should have a dependency graph that is closed (i.e. doesn't have any dangling dependencies).
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2]", "test::Resource[agent1,key=key3]"],
        },
    ]
    resource_sets = {}
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: The model should have a dependency graph that is closed and no dangling dependencies: "
        "{'test::Resource[agent1,key=key2]', 'test::Resource[agent1,key=key3]'}"
    ) or (
        "Invalid request: The model should have a dependency graph that is closed and no dangling dependencies: "
        "{'test::Resource[agent1,key=key3]', 'test::Resource[agent1,key=key2]'}"
    )


async def test_put_partial_mixed_scenario(server, client, environment, clienthelper):
    """
    A test that starts with: resources in several different resource sets and resources in the shared set.
    The partial update does: An update of a subset of the resources sets an addition of shared resources
    and adds a new resource_set and removes one.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "1",
            "id": f"test::Resource[agent1,key=key1],v={version}",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "2",
            "id": f"test::Resource[agent1,key=key2],v={version}",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key1],v={version}"],
        },
        {
            "key": "key3",
            "value": "3",
            "id": f"test::Resource[agent1,key=key3],v={version}",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "value": "4",
            "id": f"test::Resource[agent1,key=key4],v={version}",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key3],v={version}"],
        },
        {
            "key": "key5",
            "value": "5",
            "id": f"test::Resource[agent1,key=key5],v={version}",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key6",
            "value": "6",
            "id": f"test::Resource[agent1,key=key6],v={version}",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key7",
            "value": "7",
            "id": f"test::Resource[agent1,key=key7],v={version}",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key8",
            "value": "8",
            "id": f"test::Resource[agent1,key=key8],v={version}",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-a",
        "test::Resource[agent1,key=key3]": "set-b",
        "test::Resource[agent1,key=key4]": "set-b",
        "test::Resource[agent1,key=key7]": "set-c",
        "test::Resource[agent1,key=key8]": "set-c",
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key1",
            "value": "100",
            "id": "test::Resource[agent1,key=key1],v=0",
            "version": 0,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "200",
            "id": "test::Resource[agent1,key=key2],v=0",
            "version": 0,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key9",
            "value": "900",
            "id": "test::Resource[agent1,key=key9],v=0",
            "version": 0,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key91",
            "value": "910",
            "id": "test::Resource[agent1,key=key91],v=0",
            "version": 0,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key92",
            "value": "920",
            "id": "test::Resource[agent1,key=key92],v=0",
            "version": 0,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
            "test::Resource[agent1,key=key2]": "set-a",
            "test::Resource[agent1,key=key91]": "set-f",
            "test::Resource[agent1,key=key92]": "set-f",
        },
        removed_resource_sets=["set-c"],
    )

    assert result.code == 200, result.result
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version(uuid.UUID(environment)),
        key=lambda r: r.attributes["key"],
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 9
    assert resource_list[0].attributes == {
        "key": "key1",
        "value": "100",
        "purged": False,
        "requires": [],
        "send_event": False,
    }
    assert resource_list[1].attributes == {
        "key": "key2",
        "value": "200",
        "purged": False,
        "requires": [],
        "send_event": False,
    }
    assert resource_list[2].attributes == {
        "key": "key3",
        "value": "3",
        "purged": False,
        "requires": [],
        "send_event": False,
    }
    assert resource_list[3].attributes == {
        "key": "key4",
        "value": "4",
        "purged": False,
        "requires": ["test::Resource[agent1,key=key3]"],
        "send_event": False,
    }
    assert resource_list[4].attributes == {
        "key": "key5",
        "value": "5",
        "purged": False,
        "requires": [],
        "send_event": False,
    }
    assert resource_list[5].attributes == {
        "key": "key6",
        "value": "6",
        "purged": False,
        "requires": [],
        "send_event": False,
    }
    assert resource_list[6].attributes == {
        "key": "key9",
        "value": "900",
        "purged": False,
        "requires": [],
        "send_event": False,
    }
    assert resource_list[7].attributes == {
        "key": "key91",
        "value": "910",
        "purged": False,
        "requires": [],
        "send_event": False,
    }
    assert resource_list[8].attributes == {
        "key": "key92",
        "value": "920",
        "purged": False,
        "requires": [],
        "send_event": False,
    }
    assert resource_sets_from_db == {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-a",
        "test::Resource[agent1,key=key3]": "set-b",
        "test::Resource[agent1,key=key4]": "set-b",
        "test::Resource[agent1,key=key5]": None,
        "test::Resource[agent1,key=key6]": None,
        "test::Resource[agent1,key=key9]": None,
        "test::Resource[agent1,key=key91]": "set-f",
        "test::Resource[agent1,key=key92]": "set-f",
    }


async def test_put_partial_validation_error(server, client, environment, clienthelper):
    """
    A partial compile can update multiple resource sets at the same time.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-b",
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200
    resources_partial = ["key1", "key2"]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
            "test::Resource[agent1,key=key2]": "set-b",
        },
    )

    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: Type validation failed for resources argument. Expected an argument of type List[Dict[str, Any]] but "
        "received ['key1', 'key2']"
    )


async def test_put_partial_verify_params(server, client, environment, clienthelper):
    """
    resource_sets with a non resource id value as a key
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-b",
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key1",
            "value": "value1123",
            "id": "test::Resource[agent1,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value234",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
            "test::Resource[agent1,key=key2]": "set-b",
            "hello": "set-c",
        },
    )

    assert result.code == 400
    assert (
        "The following resource ids provided in the resource_sets parameter are not present in the resources list: hello"
        in result.result["message"]
    )


async def test_put_partial_different_env(server, client):
    """
    verify that put_partial won't modify other env.
    """

    result = await client.create_project("env-test-1")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    create_environment_result = await client.create_environment(project_id=project_id, name="env1")
    assert create_environment_result.code == 200
    env_id_1 = create_environment_result.result["environment"]["id"]

    create_environment_result = await client.create_environment(project_id=project_id, name="env2")
    assert create_environment_result.code == 200
    env_id_2 = create_environment_result.result["environment"]["id"]

    version_env1 = await utils.ClientHelper(client, env_id_1).get_version()
    version_env2 = await utils.ClientHelper(client, env_id_2).get_version()
    assert version_env1 == version_env2
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version_env1,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    result = await client.put_version(
        tid=env_id_1,
        version=version_env1,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets={},
    )
    assert result.code == 200, result.result

    result = await client.put_version(
        tid=env_id_2,
        version=version_env1,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets={},
    )
    assert result.code == 200

    resources_partial = [
        {
            "key": "key2",
            "value": "value123",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=env_id_1,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={},
    )

    assert result.code == 200
    version_env1 = result.result["data"]

    assert version_env1 != version_env2

    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version(uuid.UUID(env_id_1)), key=lambda resource: resource.resource_id
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key1],v=2"
    assert resource_list[1].resource_version_id == "test::Resource[agent1,key=key2],v=2"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": None, "test::Resource[agent1,key=key2]": None}
    for r in resource_list:
        assert r.model == 2

    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version(uuid.UUID(env_id_2)), key=lambda resource: resource.resource_id
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 1
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key1],v=1"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": None}
    for r in resource_list:
        assert r.model == 1


async def test_put_partial_removed_rs_in_rs(server, client, environment, clienthelper):
    """
    Test that an exception is thrown when a resource being exported belongs to a resource set that is being deleted.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-b",
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key2",
            "value": "200",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={
            "test::Resource[agent1,key=key2]": "set-b",
        },
        removed_resource_sets=["set-b"],
    )

    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: Following resource sets are present in the removed resource sets and in the resources "
        "that are exported: {'set-b'}"
    )
    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version(uuid.UUID(environment)), key=lambda resource: resource.resource_id
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].attributes == {"key": "key1", "value": "1", "purged": False, "requires": [], "send_event": False}
    assert resource_list[1].attributes == {"key": "key2", "value": "2", "purged": False, "requires": [], "send_event": False}
    assert resource_sets_from_db == {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-b",
    }


async def test_put_partial_with_resource_state_set(server, client, environment, clienthelper, agent) -> None:
    """
    Test whether the put_partial() endpoint correctly merges the resource states of two resource sets.
    """
    # Compose base version for partial compile
    version = await clienthelper.get_version()
    resources = [
        {
            "key": f"key{i}",
            "version": version,
            "id": f"test::Resource[agent1,key=key{i}],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        }
        for i in range(1, 6)
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-a",
        "test::Resource[agent1,key=key3]": "set-a",
        "test::Resource[agent1,key=key4]": "set-a",
        "test::Resource[agent1,key=key5]": "set-b",
    }
    resource_states = {
        "test::Resource[agent1,key=key1]": const.ResourceState.undefined,
        "test::Resource[agent1,key=key4]": const.ResourceState.available,
        "test::Resource[agent1,key=key5]": const.ResourceState.undefined,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=resource_states,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200, result.result

    # set key2 to deploying
    result = await agent._client.resource_deploy_start(
        tid=environment, rvid=f"test::Resource[agent1,key=key2],v={version}", action_id=uuid.uuid4()
    )
    assert result.code == 200, result.result

    # Set key 3 to deployed

    action_id = uuid.uuid4()
    result = await agent._client.resource_deploy_start(
        tid=environment, rvid=f"test::Resource[agent1,key=key3],v={version}", action_id=action_id
    )
    assert result.code == 200, result.result
    result = await agent._client.resource_deploy_done(
        tid=environment,
        rvid=f"test::Resource[agent1,key=key3],v={version}",
        action_id=action_id,
        status=const.ResourceState.deployed,
        messages=[],
        changes={},
        change=const.Change.nochange,
    )
    assert result.code == 200, result.result

    # Partial compile
    resources_partial = [
        {
            "key": "key5",
            "value": "200",
            "version": 0,
            "id": "test::Resource[agent1,key=key5],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key6",
            "value": "200",
            "version": 0,
            "id": "test::Resource[agent1,key=key6],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key7",
            "value": "200",
            "version": 0,
            "id": "test::Resource[agent1,key=key7],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key5]": "set-b",
        "test::Resource[agent1,key=key6]": "set-b",
        "test::Resource[agent1,key=key7]": "set-b",
    }
    resource_states = {
        "test::Resource[agent1,key=key5]": const.ResourceState.available,
        "test::Resource[agent1,key=key6]": const.ResourceState.undefined,
        "test::Resource[agent1,key=key7]": const.ResourceState.available,
    }
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state=resource_states,
        unknowns=[],
        version_info=None,
        resource_sets=resource_sets,
    )
    assert result.code == 200

    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    assert len(resource_list) == 7
    assert all(r.model == 2 for r in resource_list)
    rid_to_res = {r.resource_id: r for r in resource_list}
    assert rid_to_res["test::Resource[agent1,key=key1]"].status is const.ResourceState.undefined
    assert rid_to_res["test::Resource[agent1,key=key2]"].status is const.ResourceState.available
    assert rid_to_res["test::Resource[agent1,key=key3]"].status is const.ResourceState.available
    assert rid_to_res["test::Resource[agent1,key=key4]"].status is const.ResourceState.available
    assert rid_to_res["test::Resource[agent1,key=key5]"].status is const.ResourceState.available
    assert rid_to_res["test::Resource[agent1,key=key6]"].status is const.ResourceState.undefined
    assert rid_to_res["test::Resource[agent1,key=key7]"].status is const.ResourceState.available


async def test_put_partial_with_undeployable_resources(server, client, environment, clienthelper, agent) -> None:
    """
    Test whether the put_partial() endpoint correctly merges the undeployable and skipped_for_undeployable list
    of a configurationmodel.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "version": version,
            "id": f"test::Resource[agent1,key=key1],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "version": version,
            "id": f"test::Resource[agent1,key=key2],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key1],v={version}"],
        },
        {
            "key": "key3",
            "version": version,
            "id": f"test::Resource[agent1,key=key3],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "version": version,
            "id": f"test::Resource[agent1,key=key4],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key3],v={version}"],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-a",
        "test::Resource[agent1,key=key3]": "set-a",
        "test::Resource[agent1,key=key4]": "set-a",
    }
    resource_states = {
        "test::Resource[agent1,key=key1]": const.ResourceState.undefined,
        "test::Resource[agent1,key=key2]": const.ResourceState.available,
        "test::Resource[agent1,key=key3]": const.ResourceState.undefined,
        "test::Resource[agent1,key=key4]": const.ResourceState.available,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=resource_states,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200, result.result

    cm = await data.ConfigurationModel.get_one(environment=environment, version=version)
    assert cm is not None
    assert sorted(cm.undeployable) == sorted(["test::Resource[agent1,key=key1]", "test::Resource[agent1,key=key3]"])
    assert sorted(cm.skipped_for_undeployable) == sorted(["test::Resource[agent1,key=key2]", "test::Resource[agent1,key=key4]"])

    # Partial compile
    resources_partial = [
        {
            "key": "key1",
            "version": 0,
            "id": "test::Resource[agent1,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "version": 0,
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key1],v=0"],
        },
        {
            "key": "key5",
            "version": 0,
            "id": "test::Resource[agent1,key=key5],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key6",
            "version": 0,
            "id": "test::Resource[agent1,key=key6],v=0",
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key5],v=0"],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-a",
        "test::Resource[agent1,key=key5]": "set-a",
        "test::Resource[agent1,key=key6]": "set-a",
    }
    resource_states = {
        "test::Resource[agent1,key=key1]": const.ResourceState.undefined,
        "test::Resource[agent1,key=key2]": const.ResourceState.available,
        "test::Resource[agent1,key=key5]": const.ResourceState.undefined,
        "test::Resource[agent1,key=key6]": const.ResourceState.available,
    }
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state=resource_states,
        unknowns=[],
        version_info=None,
        resource_sets=resource_sets,
    )
    assert result.code == 200, result.result
    version = result.result["data"]

    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200, result.result

    cm = await data.ConfigurationModel.get_one(environment=environment, version=version)
    assert cm is not None
    assert sorted(cm.undeployable) == sorted(["test::Resource[agent1,key=key1]", "test::Resource[agent1,key=key5]"])
    assert sorted(cm.skipped_for_undeployable) == sorted(["test::Resource[agent1,key=key2]", "test::Resource[agent1,key=key6]"])


async def test_put_partial_with_unknowns(server, client, environment, clienthelper) -> None:
    """
    Test whether the put_partial() endpoint correctly merges unknowns.
    """
    # Compose base version for partial compile
    version = await clienthelper.get_version()
    resources = [
        {
            "key": f"key{i}",
            "version": version,
            "id": f"test::Resource[agent1,key=key{i}],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        }
        for i in range(1, 5)
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-a",
        "test::Resource[agent1,key=key3]": "set-a",
        "test::Resource[agent1,key=key4]": "set-b",
    }
    unknowns = [
        {"resource": "test::Resource[agent1,key=key1]", "parameter": "unknown_1", "source": "fact"},
        {"resource": "test::Resource[agent1,key=key2]", "parameter": "unknown_2", "source": "fact"},
        {"resource": "", "parameter": "unknown_3", "source": "fact"},
        {"resource": "test::Resource[agent1,key=key4]", "parameter": "unknown_4", "source": "fact"},
    ]
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=unknowns,
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200

    # Resolve unknown for test::Resource[agent1,key=key2]
    result = await client.set_param(
        tid=environment,
        id="unknown_2",
        source=const.ParameterSource.fact,
        value="val",
        resource_id="test::Resource[agent1,key=key2]",
    )
    assert result.code == 200

    # Partial compile
    resources_partial = [
        {
            "key": "key5",
            "version": 0,
            "id": "test::Resource[agent1,key=key5],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key5]": "set-b",
    }
    unknowns = [{"resource": "test::Resource[agent1,key=key5]", "parameter": "unknown_5", "source": "fact"}]
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=unknowns,
        version_info=None,
        resource_sets=resource_sets,
    )
    assert result.code == 200

    def assert_unknown(uk: data.UnknownParameter, expected_name: str, expected_resource_id: ResourceIdStr) -> None:
        """
        Verify that the given UnknownParameter matches has the expected content.
        """
        assert uk.name == expected_name
        assert uk.environment == uuid.UUID(environment)
        assert uk.source == "fact"
        assert uk.resource_id == expected_resource_id
        assert uk.version == 2
        assert uk.metadata == {}
        assert not uk.resolved

    unknowns_by_rid = {uk.resource_id: uk for uk in await data.UnknownParameter.get_list(environment=environment, version=2)}
    assert len(unknowns_by_rid) == 3
    assert "test::Resource[agent1,key=key1]" in unknowns_by_rid
    assert "" in unknowns_by_rid
    assert "test::Resource[agent1,key=key5]" in unknowns_by_rid
    assert_unknown(unknowns_by_rid["test::Resource[agent1,key=key1]"], "unknown_1", "test::Resource[agent1,key=key1]")
    assert_unknown(unknowns_by_rid[""], "unknown_3", "")
    assert_unknown(unknowns_by_rid["test::Resource[agent1,key=key5]"], "unknown_5", "test::Resource[agent1,key=key5]")


async def test_put_partial_dep_on_shared_set_removed(server, client, environment, clienthelper) -> None:
    """
    Ensure that the put_partial endpoint correctly updates the provides relationship when a resource A from a specific
    resource set depends on a resource B from the shared resource set and resource A is removed by a partial compile.
    """
    version = await clienthelper.get_version()
    rid1 = "test::Resource[agent1,key=key1]"
    rid2 = "test::Resource[agent2,key=key2]"
    rid3 = "test::Resource[agent2,key=key3]"
    resources = [
        {
            "key": "key1",
            "version": version,
            "id": f"{rid1},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "version": version,
            "id": f"{rid2},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"{rid1},v={version}"],
        },
        {
            "key": "key3",
            "version": version,
            "id": f"{rid3},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {rid2: "set-a", rid3: "set-a"}
    resource_states = {
        rid1: const.ResourceState.available,
        rid2: const.ResourceState.available,
        rid3: const.ResourceState.available,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=resource_states,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200

    # Partial compile
    resources_partial = [
        {
            "key": "key3",
            "version": 0,
            "id": f"{rid3},v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {rid3: "set-a"}
    resource_states = {rid3: const.ResourceState.available}
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state=resource_states,
        unknowns=[],
        version_info=None,
        resource_sets=resource_sets,
    )
    assert result.code == 200

    resources_in_model = await data.Resource.get_list(model=2)
    assert len(resources_in_model) == 2
    rid_to_resource = {res.resource_id: res for res in resources_in_model}
    assert rid_to_resource[rid1].provides == []


async def test_put_partial_dep_on_specific_set_removed(server, client, environment, clienthelper) -> None:
    """
    Ensure that the put_partial endpoint correctly updates the requires/provides relationship when a resource A from the shared
    resource set depends on a resource B from a specific resource set and this dependency is removed by a partial compile.
    """
    version = await clienthelper.get_version()
    rid1 = "test::Resource[agent1,key=key1]"
    rid2 = "test::Resource[agent2,key=key2]"
    rid3 = "test::Resource[agent2,key=key3]"
    resources = [
        {
            "key": "key1",
            "version": version,
            "id": f"{rid1},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"{rid2},v={version}"],
        },
        {
            "key": "key2",
            "version": version,
            "id": f"{rid2},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key3",
            "version": version,
            "id": f"{rid3},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {rid2: "set-a", rid3: "set-b"}
    resource_states = {
        rid1: const.ResourceState.available,
        rid2: const.ResourceState.available,
        rid3: const.ResourceState.available,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=resource_states,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200

    # Partial compile
    resources_partial = [
        {
            "key": "key2",
            "version": 0,
            "id": f"{rid2},v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {rid2: "set-a"}
    resource_states = {rid2: const.ResourceState.available}
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state=resource_states,
        unknowns=[],
        version_info=None,
        resource_sets=resource_sets,
    )
    assert result.code == 200

    resources_in_model = await data.Resource.get_list(model=2)
    assert len(resources_in_model) == 3
    rid_to_resource = {res.resource_id: res for res in resources_in_model}
    assert rid_to_resource[rid1].attributes["requires"] == []
    assert rid_to_resource[rid2].provides == []

    # Test for: https://github.com/inmanta/inmanta-core/issues/7065
    # Make sure dryrun succeeds after a put_partial call
    result = await client.dryrun_trigger(tid=environment, version=2)
    assert result.code == 200


async def test_put_partial_dep_on_non_existing_resource(server, client, environment, clienthelper) -> None:
    """
    Ensure that an exception is raised when a resource passed to the put_partial endpoint has a dependency on a
    non-existing resource. This situation cannot happen when the interaction between the client and the server happens
    via the compiler/exporter, but we verify the behavior here to check the safety of the API endpoint.
    """
    version = await clienthelper.get_version()
    rid1 = "test::Resource[agent1,key=key1]"
    rid2 = "test::Resource[agent1,key=key2]"
    resources = [
        {
            "key": "key1",
            "version": version,
            "id": f"{rid1},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "version": version,
            "id": f"{rid2},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"{rid1},v={version}"],
        },
    ]
    resource_sets = {rid2: "set-a"}
    resource_states = {
        rid1: const.ResourceState.available,
        rid2: const.ResourceState.available,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=resource_states,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200

    # Partial compile
    rid3 = "test::Resource[agent1,key=key3]"
    resources_partial = [
        {
            "key": "key1",
            "version": 0,
            "id": f"{rid1},v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "version": 0,
            "id": f"{rid2},v=0",
            "send_event": False,
            "purged": False,
            "requires": [f"{rid1},v=0"],
        },
        {
            "key": "key3",
            "version": 0,
            "id": f"{rid3},v=0",
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=non_existing_resource]"],
        },
    ]
    resource_sets = {rid2: "set-a", rid3: "set-a"}
    resource_states = {rid2: const.ResourceState.available, rid3: const.ResourceState.available}
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state=resource_states,
        unknowns=[],
        version_info=None,
        resource_sets=resource_sets,
    )
    assert result.code == 400
    assert (
        "Invalid request: The model should have a dependency graph that is closed and no dangling dependencies: "
        "{'test::Resource[agent1,key=non_existing_resource]'}" in result.result["message"]
    )


async def test_put_partial_inter_set_dependency(server, client, environment, clienthelper) -> None:
    """
    Ensure that an exception is raised when the resources passed to the put_partial endpoint define a dependency
    on a resource in another resource set. This situation cannot happen when the interaction between the client and
    the server happens via the compiler/exporter, but we verify the behavior here to check the safety of the API endpoint.
    """
    version = await clienthelper.get_version()
    rid1 = "test::Resource[agent1,key=key1]"
    rid2 = "test::Resource[agent1,key=key2]"
    resources = [
        {
            "key": "key1",
            "version": version,
            "id": f"{rid1},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "version": version,
            "id": f"{rid2},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {rid1: "set-a", rid2: "set-b"}
    resource_states = {
        rid1: const.ResourceState.available,
        rid2: const.ResourceState.available,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=resource_states,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets=resource_sets,
    )
    assert result.code == 200

    # Partial compile
    resources_partial = [
        {
            "key": "key2",
            "version": 0,
            "id": f"{rid2},v=0",
            "send_event": False,
            "purged": False,
            "requires": [f"{rid1},v=0"],
        },
    ]
    resource_sets = {rid2: "set-a"}
    resource_states = {rid2: const.ResourceState.available}
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state=resource_states,
        unknowns=[],
        version_info=None,
        resource_sets=resource_sets,
    )
    assert result.code == 400
    assert (
        "Invalid request: The model should have a dependency graph that is closed and no dangling dependencies: "
        "{'test::Resource[agent1,key=key1]'}" in result.result["message"]
    )


async def test_is_suitable_for_partial_compiles(server, client, environment, clienthelper) -> None:
    """
    Test whether the put_version and the put_partial endpoint correctly sets the is_suitable_for_partial_compiles field
    on a configurationmodel.
    """

    async def execute_put_version(set_cross_resource_set_dependency: bool) -> int:
        """
        Creates a new version using the put_partial endpoint.

        :param set_cross_resource_set_dependency: True iff there is a cross resource set dependency in the new model version.
        :return: The version of the new configurationmodel.
        """
        version = await clienthelper.get_version()
        rid_shared = "test::Resource[agent1,key=shared]"
        rid_set1 = "test::Resource[agent1,key=one]"
        rid_set2 = "test::Resource[agent1,key=two]"
        resources = [
            {
                "key": "shared",
                "version": version,
                "id": f"{rid_shared},v={version}",
                "send_event": False,
                "purged": False,
                "purge_on_delete": True,
                "requires": [],
            },
            {
                "key": "set1",
                "version": version,
                "id": f"{rid_set1},v={version}",
                "send_event": False,
                "purged": False,
                "purge_on_delete": True,
                "requires": [f"{rid_shared},v={version}"],
            },
            {
                "key": "set2",
                "version": version,
                "id": f"{rid_set2},v={version}",
                "send_event": False,
                "purged": False,
                "purge_on_delete": True,
                "requires": [f"{rid_shared},v={version}"],
            },
        ]
        if set_cross_resource_set_dependency:
            resources[2]["requires"].append(f"{rid_set1},v={version}")

        resource_sets = {rid_set1: "set1", rid_set2: "set2"}
        resource_states = {rid_set1: const.ResourceState.available, rid_set2: const.ResourceState.available}
        result = await client.put_version(
            tid=environment,
            version=version,
            resources=resources,
            resource_state=resource_states,
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
            resource_sets=resource_sets,
        )
        assert result.code == 200
        return version

    async def do_partial_compile(base_version: int, should_fail: bool) -> Optional[int]:
        """
        Create a new version of the model using the put_partial endpoint.

        :param base_version: The expected base version for the partial compile.
        :param should_fail: True iff the call to the put_partial endpoint should fail because the base version is not
                            suitable for partial compiles because it has cross resource set dependencies.
        :return: The new version of the model when should_fail is false, otherwise None is returned.
        """
        rid_set1 = "test::Resource[agent1,key=one]"
        resources_partial = [
            {
                "key": "updated_set2",
                "version": 0,
                "id": f"{rid_set1},v=0",
                "send_event": False,
                "purged": False,
                "purge_on_delete": True,
                "requires": [],
            },
        ]
        resource_sets = {rid_set1: "set1"}
        resource_states = {rid_set1: const.ResourceState.available}
        result = await client.put_partial(
            tid=environment,
            resources=resources_partial,
            resource_state=resource_states,
            unknowns=[],
            version_info=None,
            resource_sets=resource_sets,
            removed_resource_sets=["deleted"],
        )
        if not should_fail:
            assert result.code == 200
            return result.result["data"]
        else:
            assert result.code == 400
            assert (
                f"Base version {base_version} is not suitable for a partial compile. A dependency exists between resources"
                " test::Resource[agent1,key=two] and test::Resource[agent1,key=one],"
                " but they belong to different resource sets." in result.result["message"]
            )
            return None

    version = await execute_put_version(set_cross_resource_set_dependency=False)
    cm = await data.ConfigurationModel.get_version(environment, version)
    assert cm.is_suitable_for_partial_compiles
    version = await do_partial_compile(base_version=version, should_fail=False)
    cm = await data.ConfigurationModel.get_version(environment, version)
    assert cm.is_suitable_for_partial_compiles

    version = await execute_put_version(set_cross_resource_set_dependency=True)
    cm = await data.ConfigurationModel.get_version(environment, version)
    assert not cm.is_suitable_for_partial_compiles
    await do_partial_compile(base_version=version, should_fail=True)
