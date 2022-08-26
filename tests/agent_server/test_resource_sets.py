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
from inmanta import data
from inmanta.protocol.common import Result
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
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 1
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key2],v=2"
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
    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key1],v=2"
    assert resource_list[1].resource_version_id == "test::Resource[agent1,key=key2],v=2"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": None, "test::Resource[agent1,key=key2]": None}


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
    ]
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        resource_sets={"test::Resource[agent1,key=key1]": "set-a"},
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
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key1]": "set-b"},
    )

    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: A partial compile cannot migrate resource "
        "test::Resource[agent1,key=key1],v=2 to another resource set"
    )


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
        "Invalid request: Resource (test::Resource[agent1,key=key1],v=2) without a "
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
    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key1],v=2"
    assert resource_list[1].resource_version_id == "test::Resource[agent1,key=key2],v=2"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": "set-a", "test::Resource[agent1,key=key2]": "set-b"}


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
            "requires": ["test::Resource[agent1,key=key1]"],
        },
        {
            "key": "key3",
            "value": "3",
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "value": "4",
            "id": "test::Resource[agent1,key=key4],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key3]"],
        },
        {
            "key": "key5",
            "value": "5",
            "id": "test::Resource[agent1,key=key5],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key6",
            "value": "6",
            "id": "test::Resource[agent1,key=key6],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key7",
            "value": "7",
            "id": "test::Resource[agent1,key=key7],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key8",
            "value": "8",
            "id": "test::Resource[agent1,key=key8],v=%d" % version,
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
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "200",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key9",
            "value": "900",
            "id": "test::Resource[agent1,key=key9],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key91",
            "value": "910",
            "id": "test::Resource[agent1,key=key91],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key92",
            "value": "920",
            "id": "test::Resource[agent1,key=key92],v=0",
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
    assert resource_list[0].attributes == {"key": "key1", "value": "100", "purged": False, "requires": [], "send_event": False}
    assert resource_list[1].attributes == {"key": "key2", "value": "200", "purged": False, "requires": [], "send_event": False}
    assert resource_list[2].attributes == {"key": "key3", "value": "3", "purged": False, "requires": [], "send_event": False}
    assert resource_list[3].attributes == {
        "key": "key4",
        "value": "4",
        "purged": False,
        "requires": ["test::Resource[agent1,key=key3]"],
        "send_event": False,
    }
    assert resource_list[4].attributes == {"key": "key5", "value": "5", "purged": False, "requires": [], "send_event": False}
    assert resource_list[5].attributes == {"key": "key6", "value": "6", "purged": False, "requires": [], "send_event": False}
    assert resource_list[6].attributes == {"key": "key9", "value": "900", "purged": False, "requires": [], "send_event": False}
    assert resource_list[7].attributes == {"key": "key91", "value": "910", "purged": False, "requires": [], "send_event": False}
    assert resource_list[8].attributes == {"key": "key92", "value": "920", "purged": False, "requires": [], "send_event": False}
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
    assert result.result["message"] == (
        "Invalid request: Invalid resource id in resource set: " "Invalid id for resource hello"
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

    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(env_id_1))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key1],v=2"
    assert resource_list[1].resource_version_id == "test::Resource[agent1,key=key2],v=2"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": None, "test::Resource[agent1,key=key2]": None}

    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(env_id_2))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 1
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key1],v=1"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": None}


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
    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].attributes == {"key": "key1", "value": "1", "purged": False, "requires": [], "send_event": False}
    assert resource_list[1].attributes == {"key": "key2", "value": "2", "purged": False, "requires": [], "send_event": False}
    assert resource_sets_from_db == {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-b",
    }
