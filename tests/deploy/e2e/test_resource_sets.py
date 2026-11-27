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
import base64
import dataclasses
import datetime
import hashlib
import uuid
from collections import abc
from typing import Optional

import pytest

import utils
from inmanta import const, data, util
from inmanta.agent import executor
from inmanta.data.model import ModuleSourceMetadata
from inmanta.deploy import persistence, state
from inmanta.loader import InmantaModule
from inmanta.protocol.common import Result
from inmanta.resources import Id
from inmanta.types import ResourceIdStr


async def test_requires_in_shared_set(server, client, environment, clienthelper):
    """
    Check behaviour of put_partial when we update a resource in a resource set with a dependency to a resource in the shared set
    """
    version = await clienthelper.get_version()
    # resource 2 in resource set has a dependency to resource 1 in the shared set
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
            "requires": ["test::Resource[agent1,key=key1]"],
        },
    ]
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets={"test::Resource[agent1,key=key2]": "set-1"},
        module_version_info={},
    )
    assert result.code == 200
    # Update resource 2, resource 1 remains unchanged
    resources = [
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
            "value": "value234",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key1]"],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key2]": "set-1"},
        module_version_info={},
    )
    assert result.code == 200
    resource_list = await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment))
    assert len(resource_list) == 2


async def test_put_partial_copies_unchanged_resource_sets(server, client, environment, clienthelper):
    """
    Check if unchanged resource sets are present in the latest version after a put_partial
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
        {
            "key": "shared_key",
            "value": "shared_value",
            "id": "test::Resource[agent1,key=shared_key],v=%d" % version,
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
        resource_sets={"test::Resource[agent1,key=key1]": "set-1", "test::Resource[agent1,key=key2]": "set-2"},
        module_version_info={},
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
        resource_sets={"test::Resource[agent1,key=key1]": "set-1"},
        module_version_info={},
    )
    assert result.code == 200
    resource_list = await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment))
    assert len(resource_list) == 3


async def test_resource_sets_via_put_version(server, client, environment, clienthelper):
    version_1 = await clienthelper.get_version()

    result = await client.put_version(
        tid=environment,
        version=version_1,
        resources=[],
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
        },
        module_version_info={},
    )
    assert result.code == 400
    assert (
        "Invalid request: The following resource ids provided in the resource_sets "
        "parameter are not present in the resources list: test::Resource[agent1,key=key1]"
    ) in result.result["message"]

    def make_resources(version: int):
        return [
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
        version=version_1,
        resources=make_resources(version_1),
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200

    # Create project
    result = await client.list_projects()
    assert result.code == 200
    project_id = result.result["projects"][0]["id"]

    # Create environment
    result = await client.create_environment(project_id=project_id, name="env_2")
    env_2 = result.result["environment"]["id"]
    # Create another version on a different environment
    res = await client.reserve_version(env_2)
    assert res.code == 200
    version = res.result["data"]
    result_2 = await client.put_version(
        tid=env_2,
        version=version,
        resources=make_resources(version),
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result_2.code == 200

    resource_list = await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    expected_resource_sets = {**resource_sets, "test::Resource[agent1,key=key4]": None}
    assert resource_sets_from_db == expected_resource_sets

    env_id = uuid.UUID(environment)
    res_sets = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version)
    assert len(res_sets) == 3
    assert set([rs.name for rs in res_sets]) == set(resource_sets_from_db.values())

    # Check to see if new resource sets are added and the old ones are present in this version
    version_2 = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version_2,
        resources=make_resources(version_2),
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets={**resource_sets, "test::Resource[agent1,key=key4]": "set-c"},
        module_version_info={},
    )
    assert result.code == 200

    res_sets = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version_2)
    assert len(res_sets) == 4
    assert set([rs.name for rs in res_sets]) == {None, "set-a", "set-b", "set-c"}

    # Test clear_resource_sets_in_version
    async with data.ResourceSet.get_connection() as con:
        total_resource_sets = await data.ResourceSet.get_list(connection=con)
        # env1(4 version2 + 3 version1) + env2(3 version1)
        assert len(total_resource_sets) == 10
        resource_sets_env1 = await data.ResourceSet.get_list(environment=env_id, connection=con)
        # 4 version2 + 3 version1
        assert len(resource_sets_env1) == 7
        total_resources = await data.Resource.get_list(connection=con)
        # env1(4 version2 + 4 version1) + env2(4 version1)
        assert len(total_resources) == 12
        # Clear version only
        await data.ResourceSet.clear_resource_sets_in_version(environment=env_id, version=version_2, connection=con)
        res_sets = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version_2, connection=con)
        assert len(res_sets) == 0

        # Assert it did not change other versions
        res_sets = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version_1)
        assert len(res_sets) == 3
        total_resource_sets = await data.ResourceSet.get_list(connection=con)
        # env1(3 version1) + env2(3 version1)
        assert len(total_resource_sets) == 6
        total_resources = await data.Resource.get_list(connection=con)
        # 4 version2 + 4 version1
        assert len(total_resources) == 8

        # Clear remaining version of environment
        await data.ResourceSet.clear_resource_sets_in_version(environment=env_id, version=version_1, connection=con)
        res_sets = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version_1, connection=con)
        assert len(res_sets) == 0

        # Check that it did not delete resource sets of other environments
        resource_sets_env2 = await data.ResourceSet.get_list(environment=env_2, connection=con)
        # 3 version1
        assert len(resource_sets_env2) == 3
        total_resources = await data.Resource.get_list(connection=con)
        # env2(4 version1)
        assert len(total_resources) == 4

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
        module_version_info={},
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
        resource_sets=resource_sets,
        module_version_info={},
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
            module_version_info={},
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

    content = "# test"
    sha1sum = hashlib.new("sha1")
    sha1sum.update(content.encode())
    hv: str = sha1sum.hexdigest()
    await client.upload_file(hv, content=base64.b64encode(content.encode()).decode("ascii"))

    module_source_metadata = ModuleSourceMetadata(
        name="inmanta_plugins.test",
        hash_value=hv,
        is_byte_code=False,
    )

    module_version_info = {
        "test": InmantaModule(
            name="test",
            version="0.0.0",
            files_in_module=[module_source_metadata],
            requirements=[],
            for_agents=["agent1"],
        )
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info=module_version_info,
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
        module_version_info=module_version_info,
    )

    assert result.code == 200, result.result
    assert result.result is not None
    assert "data" in result.result
    assert result.result["data"] == version + 1
    resource_list = await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment))
    assert len(resource_list) == 1
    assert resource_list[0].resource_id == "test::Resource[agent1,key=key2]"
    assert resource_list[0].attributes["value"] == resources_partial[0]["value"]
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
        resource_sets=resource_sets,
        module_version_info={},
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
        module_version_info={},
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
        resource_sets={},
        module_version_info={},
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
        module_version_info={},
    )

    assert result.code == 200
    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment)),
        key=lambda resource: resource.resource_id,
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_id == "test::Resource[agent1,key=key1]"
    assert resource_list[0].attributes["value"] == "value1"
    assert resource_list[1].resource_id == "test::Resource[agent1,key=key2]"
    assert resource_list[1].attributes["value"] == "value123"
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
        resource_sets={"test::Resource[agent1,key=key1]": "set-a-old", "test::Resource[agent1,key=key2]": "set-b-old"},
        module_version_info={},
    )
    assert result.code == 200
    env_id = uuid.UUID(environment)
    res_sets_1 = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version)
    assert len(res_sets_1) == 2
    assert {r.name for r in res_sets_1} == {"set-a-old", "set-b-old"}

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
        module_version_info={},
    )

    assert result.code == 400
    expected_lines = [
        "Invalid request: The following resource(s) are included in the partial compile, but they were already present in"
        " a resource set that is not part of the partial compile:",
        "    test::Resource[agent1,key=key1] exists in resource set set-a-old"
        " and the partial compile adds it to resource set set-a-new",
        "    test::Resource[agent1,key=key2] exists in resource set set-b-old"
        " and the partial compile adds it to resource set set-b-new",
        "A resource cannot belong to more than one resource set at the same time.",
    ]

    assert all(line in result.result["message"] for line in expected_lines)

    # Swap them
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key1]": "set-b-old", "test::Resource[agent1,key=key2]": "set-a-old"},
        module_version_info={},
    )

    assert result.code == 200, result.result

    res_sets_2 = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version + 1)
    assert len(res_sets_2) == 2
    assert {r.name for r in res_sets_1} == {"set-a-old", "set-b-old"}

    # Assert that the ids of the resource sets are different because both of them had changes
    assert {r.id for r in res_sets_1}.isdisjoint({r.id for r in res_sets_2})

    # Swap the new sets and removal of the old one
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key1]": "set-a-new", "test::Resource[agent1,key=key2]": "set-b-new"},
        module_version_info={},
        removed_resource_sets=["set-b-old", "set-a-old"],
    )

    assert result.code == 200, result.result

    res_sets = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version + 2)
    assert len(res_sets) == 2
    assert {r.name for r in res_sets} == {"set-a-new", "set-b-new"}

    # Allow move into shared
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key1]": "set-a-new"},
        module_version_info={},
        removed_resource_sets=["set-b-new"],
    )

    assert result.code == 200, result.result

    res_sets = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version + 3)
    assert len(res_sets) == 2
    assert {r.name for r in res_sets} == {"set-a-new", None}

    resource_list = await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    expected_resource_sets = {"test::Resource[agent1,key=key1]": "set-a-new", "test::Resource[agent1,key=key2]": None}
    assert resource_sets_from_db == expected_resource_sets

    # Don't allow escape out of shared
    # Swap the new sets and removal of the old one
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key1]": "set-a-new", "test::Resource[agent1,key=key2]": "set-b-new"},
        module_version_info={},
    )
    assert result.code == 400, result.result
    assert (
        "Invalid request: A partial compile only migrate resources between resource set that are pushed together: "
        "trying to move test::Resource[agent1,key=key2] from resource set <SHARED> to set-b-new." in result.result["message"]
    )

    # Don't allow escape out of shared
    # Swap the new sets and removal of the old one
    # Try to trick it by providing None as an updated set
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial
        + [
            {
                "key": "key3",
                "value": "value2",
                "id": "test::Resource[agent1,key=key3],v=0",
                "send_event": False,
                "purged": False,
                "requires": [],
            }
        ],
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a-new",
            "test::Resource[agent1,key=key2]": "set-b-new",
            "test::Resource[agent1,key=key3]": None,
        },
        module_version_info={},
    )
    assert result.code == 400, result.result
    assert (
        "A partial compile only migrate resources between resource set that are pushed together: "
        "trying to move test::Resource[agent1,key=key2] from resource set <SHARED> to set-b-new." in result.result["message"]
    )

    # Reset for require provides test
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
            "requires": ["test::Resource[agent1,key=key1]"],
        },
    ]
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets={"test::Resource[agent1,key=key1]": "set-a-old", "test::Resource[agent1,key=key2]": "set-a-old"},
        module_version_info={},
    )
    assert result.code == 200

    res_sets = await data.ResourceSet.get_resource_sets_in_version(environment=env_id, version=version)
    assert len(res_sets) == 1
    assert res_sets[0].name == "set-a-old"

    # Move one side of a require-provide to another resource set, updating both sets
    version = 0
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
            "requires": ["test::Resource[agent1,key=key1]"],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key1]": "set-a-old", "test::Resource[agent1,key=key2]": "set-b-old"},
        module_version_info={},
    )
    assert result.code == 200, result.result
    version = result.result["data"]
    resources_in_version = await data.Resource.get_resources_for_version_as_dto(env_id, version)
    rid_to_resource = {res.resource_id: res for res in resources_in_version}
    assert rid_to_resource["test::Resource[agent1,key=key1]"].resource_set == "set-a-old"
    assert rid_to_resource["test::Resource[agent1,key=key2]"].resource_set == "set-b-old"
    assert rid_to_resource["test::Resource[agent1,key=key2]"].attributes["requires"] == ["test::Resource[agent1,key=key1]"]

    # Try to move on part of require-provide updating only requires
    version = 0
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

    result = await client.put_partial(
        tid=environment,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets={"test::Resource[agent1,key=key1]": "set-b-old"},
        module_version_info={},
    )
    assert result.code == 400, result.result
    assert (
        "Invalid request: The following resource(s) are included in the partial compile, but they were already present in"
        " a resource set that is not part of the partial compile:" in result.result["message"]
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
        resource_sets={},
        module_version_info={},
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
        module_version_info={},
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
        resource_sets=resource_sets,
        module_version_info={},
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
        module_version_info={},
    )

    assert result.code == 200
    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment)),
        key=lambda resource: resource.resource_id,
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_id == "test::Resource[agent1,key=key1]"
    assert resource_list[0].attributes["value"] == "value1123"
    assert resource_list[1].resource_id == "test::Resource[agent1,key=key2]"
    assert resource_list[1].attributes["value"] == "value234"
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
        resource_sets=resource_sets,
        module_version_info={},
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
            # Make sure we still support having version on the attributes
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "2",
            "id": f"test::Resource[agent1,key=key2],v={version}",
            # Make sure we ignore the check on version on a put_version
            "version": version + 123,
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key1],v={version}"],
        },
        {
            "key": "key3",
            "value": "3",
            "id": f"test::Resource[agent1,key=key3],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "value": "4",
            "id": f"test::Resource[agent1,key=key4],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key3],v={version}"],
        },
        {
            "key": "key5",
            "value": "5",
            "id": f"test::Resource[agent1,key=key5],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key6",
            "value": "6",
            "id": f"test::Resource[agent1,key=key6],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key7",
            "value": "7",
            "id": f"test::Resource[agent1,key=key7],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key8",
            "value": "8",
            "id": f"test::Resource[agent1,key=key8],v={version}",
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

    # Dependencies: arrow represents "requires" relation
    # R4 -> R3
    # R2 -> R1

    # Sets:
    # set-a  ( R1, R2)
    # set-b  ( R3, R4)
    # set-c  ( R7, R8)
    # None   ( R5, R6)

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200
    resources_partial = [
        {
            "key": "key1",
            "value": "100",
            "id": "test::Resource[agent1,key=key1],v=0",
            # Make sure we still support having version=0 on the attributes
            "version": 0,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "200",
            "id": "test::Resource[agent1,key=key2],v=0",
            # Make sure we ignore the check on version on a put_partial
            "version": 123,
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
        module_version_info={},
    )

    # Sets:
    # set-a  ( R1, R2)
    # set-b  ( R3, R4)
    # set-f  ( R91, R92)
    # None   ( R5, R6, R9)
    assert result.code == 200, result.result
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment)),
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
        resource_sets=resource_sets,
        module_version_info={},
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
        module_version_info={},
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
        resource_sets=resource_sets,
        module_version_info={},
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
        module_version_info={},
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
        resource_sets={},
        module_version_info={},
    )
    assert result.code == 200, result.result

    result = await client.put_version(
        tid=env_id_2,
        version=version_env1,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets={},
        module_version_info={},
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
        module_version_info={},
    )

    assert result.code == 200
    version_env1 = result.result["data"]

    assert version_env1 != version_env2

    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(env_id_1)),
        key=lambda resource: resource.resource_id,
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].resource_id == "test::Resource[agent1,key=key1]"
    assert resource_list[0].attributes["value"] == "value1"
    assert resource_list[1].resource_id == "test::Resource[agent1,key=key2]"
    assert resource_list[1].attributes["value"] == "value123"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key1]": None, "test::Resource[agent1,key=key2]": None}

    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(env_id_2)),
        key=lambda resource: resource.resource_id,
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 1
    assert resource_list[0].resource_id == "test::Resource[agent1,key=key1]"
    assert resource_list[0].attributes["value"] == "value1"
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
        resource_sets=resource_sets,
        module_version_info={},
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
        module_version_info={},
    )

    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: Following resource sets are present in the removed resource sets and in the resources "
        "that are exported: {'set-b'}"
    )
    # Explicitly sort the list because postgres gives no guarantee regarding order without explicit ORDER BY clause
    resource_list = sorted(
        await data.Resource.get_resources_in_latest_version_as_dto(uuid.UUID(environment)),
        key=lambda resource: resource.resource_id,
    )
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 2
    assert resource_list[0].attributes == {"key": "key1", "value": "1", "purged": False, "requires": [], "send_event": False}
    assert resource_list[1].attributes == {"key": "key2", "value": "2", "purged": False, "requires": [], "send_event": False}
    assert resource_sets_from_db == {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-b",
    }


async def test_put_partial_with_resource_state_set(server, client, environment, clienthelper) -> None:
    """
    Test whether the put_partial() endpoint correctly merges the resource states of two resource sets.
    """
    result = await client.halt_environment(environment)
    assert result.code == 200

    env_id = uuid.UUID(environment)
    # Compose base version for partial compile
    version = await clienthelper.get_version()
    resources = [
        {
            "key": f"key{i}",
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
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200, result.result

    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200

    update_manager = persistence.ToDbUpdateManager(client, env_id)

    # set key2 to deploying
    start_time: datetime.datetime = datetime.datetime.now().astimezone()
    await update_manager.send_in_progress(
        action_id=uuid.uuid4(), resource_id=Id.parse_id(f"test::Resource[agent1,key=key2],v={version}")
    )
    end_time: datetime.datetime = datetime.datetime.now().astimezone()

    # Set key 3 to deployed
    action_id = uuid.uuid4()
    rvid3 = Id.parse_id(f"test::Resource[agent1,key=key3],v={version}")
    await update_manager.send_in_progress(action_id=action_id, resource_id=rvid3)
    await update_manager.send_deploy_done(
        attribute_hash=util.make_attribute_hash(rvid3.resource_str(), attributes=resources[2]),
        result=executor.DeployReport(
            rvid=rvid3.resource_version_str(),
            action_id=action_id,
            resource_state=const.HandlerResourceState.deployed,
            messages=[],
            changes={},
            change=const.Change.nochange,
        ),
        state=state.ResourceState(
            compliance=state.Compliance.COMPLIANT,
            last_handler_run=state.HandlerResult.SUCCESSFUL,
            blocked=state.Blocked.NOT_BLOCKED,
            last_deployed=datetime.datetime.now().astimezone(),
            last_handler_run_compliant=True,
        ),
        started=start_time,
        finished=end_time,
    )

    # Partial compile
    resources_partial = [
        {
            "key": "key5",
            "value": "200",
            "id": "test::Resource[agent1,key=key5],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key6",
            "value": "200",
            "id": "test::Resource[agent1,key=key6],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key7",
            "value": "200",
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
        module_version_info={},
    )
    assert result.code == 200

    result = await client.release_version(tid=environment, id=result.result["data"])
    assert result.code == 200

    # Simulate the scheduler fixing the state after the release_version
    rps = await data.ResourcePersistentState.get_one(environment=environment, resource_id="test::Resource[agent1,key=key5]")
    await rps.update(is_undefined=False, blocked=state.Blocked.NOT_BLOCKED)

    result = await client.resource_list(tid=environment)
    assert result.code == 200
    assert len(result.result["data"]) == 7
    rid_to_res = {r["resource_id"]: r for r in result.result["data"]}

    assert rid_to_res["test::Resource[agent1,key=key1]"]["status"] == const.ResourceState.undefined.value
    # Resource is still set as deploying even though a new one released
    assert rid_to_res["test::Resource[agent1,key=key2]"]["status"] == const.ResourceState.deploying.value
    assert rid_to_res["test::Resource[agent1,key=key3]"]["status"] == const.ResourceState.deployed.value
    assert rid_to_res["test::Resource[agent1,key=key4]"]["status"] == const.ResourceState.available.value
    assert rid_to_res["test::Resource[agent1,key=key5]"]["status"] == const.ResourceState.available.value
    assert rid_to_res["test::Resource[agent1,key=key6]"]["status"] == const.ResourceState.undefined.value
    assert rid_to_res["test::Resource[agent1,key=key7]"]["status"] == const.ResourceState.available.value


async def test_put_partial_with_undeployable_resources(server, client, environment, clienthelper, agent_no_state_check) -> None:
    """
    Test whether the put_partial() endpoint correctly merges the undeployable and skipped_for_undeployable list
    of a configurationmodel.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "id": f"test::Resource[agent1,key=key1],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "id": f"test::Resource[agent1,key=key2],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key1],v={version}"],
        },
        {
            "key": "key3",
            "id": f"test::Resource[agent1,key=key3],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "id": f"test::Resource[agent1,key=key4],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key3],v={version}"],
        },
        {
            "key": "key91",
            "id": f"test::Resource[agent1,key=key91],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key92",
            "id": f"test::Resource[agent1,key=key92],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key91],v={version}"],
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
        "test::Resource[agent1,key=key91]": const.ResourceState.undefined,
        "test::Resource[agent1,key=key92]": const.ResourceState.available,
    }
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=resource_states,
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200, result.result

    cm = await data.ConfigurationModel.get_one(environment=environment, version=version)
    assert cm is not None
    assert sorted(cm.undeployable) == sorted(
        ["test::Resource[agent1,key=key1]", "test::Resource[agent1,key=key3]", "test::Resource[agent1,key=key91]"]
    )
    assert sorted(cm.skipped_for_undeployable) == sorted(
        ["test::Resource[agent1,key=key2]", "test::Resource[agent1,key=key4]", "test::Resource[agent1,key=key92]"]
    )

    # Partial compile
    resources_partial = [
        {
            "key": "key1",
            "id": "test::Resource[agent1,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "id": "test::Resource[agent1,key=key2],v=0",
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key1],v=0"],
        },
        {
            "key": "key5",
            "id": "test::Resource[agent1,key=key5],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key6",
            "id": "test::Resource[agent1,key=key6],v=0",
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key5],v=0"],
        },
        {
            "key": "key91",
            "id": "test::Resource[agent1,key=key91],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
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
        "test::Resource[agent1,key=key91]": const.ResourceState.undefined,
    }
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state=resource_states,
        unknowns=[],
        version_info=None,
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200, result.result
    version = result.result["data"]

    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200, result.result

    cm = await data.ConfigurationModel.get_one(environment=environment, version=version)
    assert cm is not None
    assert sorted(cm.undeployable) == sorted(
        ["test::Resource[agent1,key=key1]", "test::Resource[agent1,key=key5]", "test::Resource[agent1,key=key91]"]
    )
    assert sorted(cm.skipped_for_undeployable) == sorted(
        ["test::Resource[agent1,key=key2]", "test::Resource[agent1,key=key6]", "test::Resource[agent1,key=key92]"]
    )


async def test_put_partial_with_unknowns(server, client, environment, clienthelper) -> None:
    """
    Test whether the put_partial() endpoint correctly merges unknowns.
    """
    # Compose base version for partial compile
    version = await clienthelper.get_version()
    resources = [
        {
            "key": f"key{i}",
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
        "test::Resource[agent1,key=key4]": "set-b",
    }
    unknowns = [
        {"resource": "test::Resource[agent1,key=key1]", "parameter": "unknown_1", "source": "fact"},
        {"resource": "test::Resource[agent1,key=key2]", "parameter": "unknown_2", "source": "fact"},
        {"resource": "", "parameter": "unknown_3", "source": "fact"},
        {"resource": "test::Resource[agent1,key=key4]", "parameter": "unknown_4", "source": "fact"},
        {"resource": "test::Resource[agent1,key=key5]", "parameter": "unknown_5", "source": "fact"},
    ]
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=unknowns,
        version_info={},
        resource_sets=resource_sets,
        module_version_info={},
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
            "key": "key6",
            "id": "test::Resource[agent1,key=key6],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::Resource[agent1,key=key6]": "set-b",
    }
    unknowns = [{"resource": "test::Resource[agent1,key=key6]", "parameter": "unknown_6", "source": "fact"}]
    result = await client.put_partial(
        tid=environment,
        resources=resources_partial,
        resource_state={},
        unknowns=unknowns,
        version_info=None,
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200

    def assert_unknown(uk: data.UnknownParameter, expected_name: str, expected_resource_id: ResourceIdStr) -> None:
        """
        Verify that the given UnknownParameter matches the expected content.
        """
        assert uk.name == expected_name
        assert uk.environment == uuid.UUID(environment)
        assert uk.source == "fact"
        assert uk.resource_id == expected_resource_id
        assert uk.version == 2
        assert uk.metadata == {}
        assert not uk.resolved

    unknowns_by_rid = {uk.resource_id: uk for uk in await data.UnknownParameter.get_list(environment=environment, version=2)}
    assert len(unknowns_by_rid) == 4
    assert "test::Resource[agent1,key=key1]" in unknowns_by_rid
    assert "" in unknowns_by_rid
    assert "test::Resource[agent1,key=key5]" in unknowns_by_rid
    assert "test::Resource[agent1,key=key6]" in unknowns_by_rid
    assert_unknown(unknowns_by_rid["test::Resource[agent1,key=key1]"], "unknown_1", "test::Resource[agent1,key=key1]")
    assert_unknown(unknowns_by_rid[""], "unknown_3", "")
    assert_unknown(unknowns_by_rid["test::Resource[agent1,key=key5]"], "unknown_5", "test::Resource[agent1,key=key5]")
    assert_unknown(unknowns_by_rid["test::Resource[agent1,key=key6]"], "unknown_6", "test::Resource[agent1,key=key6]")


async def test_put_partial_dep_on_specific_set_removed(server, client, environment, clienthelper, agent) -> None:
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
            "id": f"{rid1},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"{rid2},v={version}"],
        },
        {
            "key": "key2",
            "id": f"{rid2},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key3",
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
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200

    # Partial compile
    resources_partial = [
        {
            "key": "key2",
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
        module_version_info={},
    )
    assert result.code == 200

    resources_in_model = await data.Resource.get_resources_for_version(environment=environment, version=2)
    assert len(resources_in_model) == 3
    rid_to_resource = {res.resource_id: res for res in resources_in_model}
    assert rid_to_resource[rid1].attributes["requires"] == []

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
            "id": f"{rid1},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
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
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200

    # Partial compile
    rid3 = "test::Resource[agent1,key=key3]"
    resources_partial = [
        {
            "key": "key1",
            "id": f"{rid1},v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "id": f"{rid2},v=0",
            "send_event": False,
            "purged": False,
            "requires": [f"{rid1},v=0"],
        },
        {
            "key": "key3",
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
        module_version_info={},
    )
    assert result.code == 400
    assert (
        "Invalid request: The model should have a dependency graph that is closed and no dangling dependencies: "
        "{'test::Resource[agent1,key=non_existing_resource]'}" in result.result["message"]
    )


async def test_put_partial_inter_set_dependency(server, client, environment, clienthelper) -> None:
    """
    Ensure that an exception is raised when the resources passed to the put_partial endpoint define a dependency
    on a resource in another resource set that is not part of the partial export. This situation cannot happen when the
    interaction between the client and the server happens via the compiler/exporter, but we verify the behavior here to
    check the safety of the API endpoint.
    """
    version = await clienthelper.get_version()
    rid1 = "test::Resource[agent1,key=key1]"
    rid2 = "test::Resource[agent1,key=key2]"
    resources = [
        {
            "key": "key1",
            "id": f"{rid1},v={version}",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
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
        resource_sets=resource_sets,
        module_version_info={},
    )
    assert result.code == 200

    # Partial compile
    resources_partial = [
        {
            "key": "key2",
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
        module_version_info={},
    )
    assert result.code == 400
    assert (
        "Invalid request: The model should have a dependency graph that is closed and no dangling dependencies: "
        "{'test::Resource[agent1,key=key1]'}" in result.result["message"]
    )


@dataclasses.dataclass(frozen=True)
class ResourceInModel:
    """
    A test::Resource that is part of a model exported to the server.

    :param key: The key of the test::Resource.
    :param resource_set: The resource set the resource belongs to or None if it belongs to the shared resource set.
    :param requires: The keys of the test::Resources this resource requires.
    :param value: The value attribute of the test::Resource.
    """

    key: str
    resource_set: str | None = None
    requires: abc.Set[str] = frozenset()
    value: str = "value"

    def get_resource_id(self) -> ResourceIdStr:
        return ResourceIdStr(f"test::Resource[agent1,key={self.key}]")

    def to_resource_dict(self, version: int = 0) -> dict[str, object]:
        return create_resource_with_requires(self.key, requires=sorted(self.requires), version=version, value=self.value)


def get_resource_id_to_non_shared_resource_set(model: abc.Sequence[ResourceInModel]) -> dict[ResourceIdStr, str]:
    """
    Return a dictionary that maps the resource id of each resource in the given model, that doesn't belong to the shared
    resource set, to the name of its resource set. This is the format of the resource_sets argument of the put_version
    and put_partial endpoints.
    """
    return {res.get_resource_id(): res.resource_set for res in model if res.resource_set is not None}


async def get_resources_in_model_version(environment: uuid.UUID, version: int) -> dict[str, ResourceInModel]:
    """
    Return a dictionary that maps the key of each test::Resource in the given version to the resource itself.
    """
    resources_in_version = await data.Resource.get_resources_for_version_as_dto(environment, version)
    return {
        res.attributes["key"]: ResourceInModel(
            key=res.attributes["key"],
            resource_set=res.resource_set,
            requires={Id.parse_id(req).attribute_value for req in res.attributes["requires"]},
            value=res.attributes["value"],
        )
        for res in resources_in_version
    }


def get_dangling_requires_error_message(dependent: str, dependency: str) -> str:
    """
    Return the error message of a partial export that removes the dependency test::Resource while the dependent
    test::Resource still requires it.
    """
    return (
        "Invalid request: The partial export removes resources that are referenced by other resources using the requires"
        " relationship. Include the resource sets of these resources in the partial export or drop these requires"
        f" relationships first: test::Resource[agent1,key={dependent}] ->"
        f" test::Resource[agent1,key={dependency}]"
    )


SHARED = ResourceInModel("shared")
B1_REQUIRES_SHARED = ResourceInModel("b1", resource_set="set-b", requires={"shared"})
B2 = ResourceInModel("b2", resource_set="set-b")
A1_REQUIRES_SHARED = ResourceInModel("a1", resource_set="set-a", requires={"shared"})
A1_REQUIRES_B1_AND_SHARED = ResourceInModel("a1", resource_set="set-a", requires={"b1", "shared"})
A1_REQUIRES_B2_AND_SHARED = ResourceInModel("a1", resource_set="set-a", requires={"b2", "shared"})


async def export_initial_model_and_partial_export(
    client,
    environment: str,
    clienthelper,
    initial_model: abc.Sequence[ResourceInModel],
    partial_export: abc.Sequence[ResourceInModel],
    removed_resource_sets: abc.Sequence[str],
) -> Result:
    """
    Do a full export of the initial model, followed by a partial export of the given resources, and return the result of
    the partial export.
    """
    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[res.to_resource_dict(version) for res in initial_model],
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=get_resource_id_to_non_shared_resource_set(initial_model),
        module_version_info={},
    )
    assert result.code == 200, result.result
    return await client.put_partial(
        tid=environment,
        resources=[res.to_resource_dict() for res in partial_export],
        resource_state={},
        unknowns=[],
        version_info=None,
        resource_sets=get_resource_id_to_non_shared_resource_set(partial_export),
        removed_resource_sets=list(removed_resource_sets),
        module_version_info={},
    )


@pytest.mark.parametrize(
    "initial_model, partial_export, removed_resource_sets, expected_model",
    [
        pytest.param(
            [SHARED, A1_REQUIRES_B1_AND_SHARED, B1_REQUIRES_SHARED, B2],
            [SHARED, dataclasses.replace(B1_REQUIRES_SHARED, value="updated"), B2],
            [],
            [SHARED, A1_REQUIRES_B1_AND_SHARED, dataclasses.replace(B1_REQUIRES_SHARED, value="updated"), B2],
            id="update-required-resource-set-retains-requires",
        ),
        pytest.param(
            [SHARED, A1_REQUIRES_B1_AND_SHARED, B1_REQUIRES_SHARED, B2],
            [SHARED, A1_REQUIRES_SHARED],
            [],
            [SHARED, A1_REQUIRES_SHARED, B1_REQUIRES_SHARED, B2],
            id="drop-cross-resource-set-requires",
        ),
        pytest.param(
            [SHARED, A1_REQUIRES_SHARED, B1_REQUIRES_SHARED, B2],
            [SHARED, A1_REQUIRES_B2_AND_SHARED, B1_REQUIRES_SHARED, B2],
            [],
            [SHARED, A1_REQUIRES_B2_AND_SHARED, B1_REQUIRES_SHARED, B2],
            id="add-cross-resource-set-requires",
        ),
        pytest.param(
            [SHARED, A1_REQUIRES_B2_AND_SHARED, B1_REQUIRES_SHARED, B2],
            [SHARED, A1_REQUIRES_SHARED, B1_REQUIRES_SHARED],
            [],
            [SHARED, A1_REQUIRES_SHARED, B1_REQUIRES_SHARED],
            id="remove-required-resource-together-with-requires",
        ),
        pytest.param(
            [SHARED, A1_REQUIRES_B1_AND_SHARED, B1_REQUIRES_SHARED],
            [SHARED, dataclasses.replace(B1_REQUIRES_SHARED, resource_set="set-c")],
            ["set-b"],
            [SHARED, A1_REQUIRES_B1_AND_SHARED, dataclasses.replace(B1_REQUIRES_SHARED, resource_set="set-c")],
            id="move-required-resource-to-other-resource-set",
        ),
    ],
)
async def test_cross_resource_set_requires(
    server,
    client,
    environment,
    clienthelper,
    initial_model: abc.Sequence[ResourceInModel],
    partial_export: abc.Sequence[ResourceInModel],
    removed_resource_sets: abc.Sequence[str],
    expected_model: abc.Sequence[ResourceInModel],
) -> None:
    """
    Verify that a partial export is accepted and results in the expected model, when a resource in a resource set
    requires a resource in another resource set.
    """
    result = await export_initial_model_and_partial_export(
        client, environment, clienthelper, initial_model, partial_export, removed_resource_sets
    )
    assert result.code == 200, result.result
    assert await get_resources_in_model_version(uuid.UUID(environment), result.result["data"]) == {
        res.key: res for res in expected_model
    }


@pytest.mark.parametrize(
    "initial_model, partial_export, removed_resource_sets, expected_error",
    [
        pytest.param(
            [SHARED, A1_REQUIRES_B1_AND_SHARED, B1_REQUIRES_SHARED, B2],
            [SHARED, A1_REQUIRES_B1_AND_SHARED],
            [],
            "Invalid request: The model should have a dependency graph that is closed and no dangling dependencies: "
            "{'test::Resource[agent1,key=b1]'}",
            id="requires-resource-set-not-in-partial-export",
        ),
        pytest.param(
            [SHARED, A1_REQUIRES_B2_AND_SHARED, B1_REQUIRES_SHARED, B2],
            [SHARED, B1_REQUIRES_SHARED],
            [],
            get_dangling_requires_error_message(dependent="a1", dependency="b2"),
            id="remove-required-resource",
        ),
        pytest.param(
            [SHARED, A1_REQUIRES_B2_AND_SHARED, B1_REQUIRES_SHARED, B2],
            [SHARED],
            ["set-b"],
            get_dangling_requires_error_message(dependent="a1", dependency="b2"),
            id="remove-required-resource-set",
        ),
    ],
)
async def test_cross_resource_set_requires_rejected(
    server,
    client,
    environment,
    clienthelper,
    initial_model: abc.Sequence[ResourceInModel],
    partial_export: abc.Sequence[ResourceInModel],
    removed_resource_sets: abc.Sequence[str],
    expected_error: str,
) -> None:
    """
    Verify that a partial export is rejected when it would leave a requires relationship from a resource in a resource
    set to a resource in another resource set that is not part of the model.
    """
    result = await export_initial_model_and_partial_export(
        client, environment, clienthelper, initial_model, partial_export, removed_resource_sets
    )
    assert result.code == 400
    assert result.result["message"] == expected_error


async def test_cross_resource_set_requires_undefined_propagation(
    server, client, environment, clienthelper, agent, resource_container
) -> None:
    """
    Verify that the scheduler marks a resource as skipped for undefined when a partial export makes a resource in another
    resource set, that it requires, undefined. And that the resource is deployed again when that resource becomes defined
    again.
    """
    rid_a1 = ResourceIdStr("test::Resource[agent1,key=a1]")
    rid_b1 = ResourceIdStr("test::Resource[agent1,key=b1]")

    async def release_and_wait(version: int) -> dict[ResourceIdStr, str]:
        """
        Release the given version, wait until it's deployed and return the status of each resource.
        """
        result = await client.release_version(tid=environment, id=version)
        assert result.code == 200
        await utils.wait_until_deployment_finishes(client, environment, version=version)
        result = await client.resource_list(tid=environment)
        assert result.code == 200
        return {r["resource_id"]: r["status"] for r in result.result["data"]}

    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[
            create_resource_with_requires("a1", requires=["b1"], version=version),
            create_resource_with_requires("b1", requires=[], version=version),
        ],
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets={rid_a1: "set-a", rid_b1: "set-b"},
        module_version_info={},
    )
    assert result.code == 200, result.result
    assert await release_and_wait(version) == {
        rid_a1: const.ResourceState.deployed.value,
        rid_b1: const.ResourceState.deployed.value,
    }

    for b1_state, expected_states in [
        (
            const.ResourceState.undefined,
            {rid_a1: const.ResourceState.skipped_for_undefined.value, rid_b1: const.ResourceState.undefined.value},
        ),
        (
            const.ResourceState.available,
            {rid_a1: const.ResourceState.deployed.value, rid_b1: const.ResourceState.deployed.value},
        ),
    ]:
        result = await client.put_partial(
            tid=environment,
            resources=[create_resource_with_requires("b1", requires=[])],
            resource_state={rid_b1: b1_state},
            unknowns=[],
            version_info=None,
            resource_sets={rid_b1: "set-b"},
            module_version_info={},
        )
        assert result.code == 200, result.result
        assert await release_and_wait(result.result["data"]) == expected_states


def create_resource_with_requires(
    key: str, requires: abc.Iterable[str], version: int = 0, value: str = "value"
) -> dict[str, object]:
    """
    Create a test::Resource with the given key and value that requires the test::Resources with the given keys.
    """
    return {
        "key": key,
        "value": value,
        "id": f"test::Resource[agent1,key={key}],v={version}",
        "send_event": False,
        "purged": False,
        "requires": [f"test::Resource[agent1,key={require}]" for require in requires],
    }


def assert_cycle_in_error_message(result: Result, expected_cycle: abc.Sequence[str]) -> None:
    """
    Assert that the given result rejected a version because of the given cycle in the requires relationships.

    :param result: The result of the put_version or put_partial call.
    :param expected_cycle: The keys of the test::Resources in the cycle, in the order of the requires relationships.
                           The reported cycle can start at any of these resources.
    """
    assert result.code == 400
    prefix = "Invalid request: The requires relationships of the resources contain a cycle: "
    message = result.result["message"]
    assert message.startswith(prefix), message
    reported_cycle = message.removeprefix(prefix).split(" -> ")
    # The first and the last resource of the reported cycle are the same
    assert reported_cycle[0] == reported_cycle[-1]
    expected_rids = [f"test::Resource[agent1,key={key}]" for key in expected_cycle]
    start_index = expected_rids.index(reported_cycle[0])
    assert reported_cycle[:-1] == expected_rids[start_index:] + expected_rids[:start_index]


async def test_put_version_requires_cycle(server, client, environment, clienthelper) -> None:
    """
    Verify that a full compile is rejected when the requires relationships of its resources contain a cycle.
    """

    async def put_version(resources_by_key: abc.Mapping[str, abc.Sequence[str]]) -> Result:
        version = await clienthelper.get_version()
        return await client.put_version(
            tid=environment,
            version=version,
            resources=[create_resource_with_requires(key, requires, version) for key, requires in resources_by_key.items()],
            resource_state={},
            unknowns=[],
            version_info={},
            resource_sets={},
            module_version_info={},
        )

    # A resource that requires itself
    result = await put_version({"r1": ["r1"]})
    assert_cycle_in_error_message(result, expected_cycle=["r1"])

    # A cycle of three resources and a resource that requires a resource in the cycle
    result = await put_version({"r1": ["r2"], "r2": ["r3"], "r3": ["r1"], "r4": ["r1"]})
    assert_cycle_in_error_message(result, expected_cycle=["r1", "r2", "r3"])

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert result.result["versions"] == []

    # A diamond doesn't contain a cycle
    result = await put_version({"r1": ["r2", "r3"], "r2": ["r4"], "r3": ["r4"], "r4": []})
    assert result.code == 200


async def test_put_partial_requires_cycle(server, client, environment, clienthelper) -> None:
    """
    Verify that a partial compile is rejected when the requires relationships of the new version, i.e. the base version
    merged with the partial compile, contain a cycle.
    """
    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[
            create_resource_with_requires("s1", ["a1"], version),
            create_resource_with_requires("s2", [], version),
            create_resource_with_requires("s3", ["s4"], version),
            create_resource_with_requires("s4", ["s5"], version),
            create_resource_with_requires("s5", [], version),
            create_resource_with_requires("a1", ["s2"], version),
            create_resource_with_requires("b1", [], version),
        ],
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets={
            "test::Resource[agent1,key=a1]": "set-a",
            "test::Resource[agent1,key=b1]": "set-b",
        },
        module_version_info={},
    )
    assert result.code == 200

    async def put_partial(resources_by_key: abc.Mapping[str, abc.Sequence[str]]) -> Result:
        return await client.put_partial(
            tid=environment,
            resources=[create_resource_with_requires(key, requires) for key, requires in resources_by_key.items()],
            resource_state={},
            unknowns=[],
            version_info=None,
            resource_sets=({"test::Resource[agent1,key=b1]": "set-b"} if "b1" in resources_by_key else {}),
            module_version_info={},
        )

    # The cycle is part of the partial compile
    result = await put_partial({"b1": ["s2"], "s2": ["b1"]})
    assert_cycle_in_error_message(result, expected_cycle=["b1", "s2"])

    # The cycle is introduced by merging the partial compile with the base version: the requires s1 -> a1 and a1 -> s2
    # are retained from the base version.
    result = await put_partial({"s1": [], "s2": ["s1"]})
    assert_cycle_in_error_message(result, expected_cycle=["s1", "a1", "s2"])

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert [v["version"] for v in result.result["versions"]] == [version]

    # A partial compile that requires the chain s3 -> s4 -> s5, without forming a cycle
    result = await put_partial({"b1": ["s3"], "s3": ["s4"], "s4": ["s5"], "s5": []})
    assert result.code == 200


async def test_get_requires_that_can_form_cycle(server, client, environment, clienthelper) -> None:
    """
    Verify that ResourceSet.get_requires_that_can_form_cycle only returns the requires relationships between resources
    that are reachable from the dependency of a requires relationship that is new with respect to the base version and
    that can reach the dependent of such a requires relationship.
    """
    env_id = uuid.UUID(environment)
    resource_sets = {
        "test::Resource[agent1,key=a1]": "set-a",
        "test::Resource[agent1,key=a2]": "set-a",
        "test::Resource[agent1,key=a3]": "set-a",
    }
    version_1 = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version_1,
        resources=[
            create_resource_with_requires("s1", ["a2"], version_1),
            create_resource_with_requires("s2", ["s3"], version_1),
            create_resource_with_requires("s3", ["s4"], version_1),
            create_resource_with_requires("s4", [], version_1),
            create_resource_with_requires("a1", [], version_1),
            create_resource_with_requires("a2", [], version_1),
            create_resource_with_requires("a3", [], version_1),
            create_resource_with_requires("b1", ["s2"], version_1),
        ],
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets={**resource_sets, "test::Resource[agent1,key=b1]": "set-b"},
        module_version_info={},
    )
    assert result.code == 200

    async def put_partial() -> int:
        """
        Do a partial compile of set-a and the shared resource set that adds the requires a1 -> s1 and a2 -> a3 to
        version 1. All other requires of the partial compile already exist in version 1.
        """
        result = await client.put_partial(
            tid=environment,
            resources=[
                create_resource_with_requires("s1", ["a2"]),
                create_resource_with_requires("s2", ["s3"]),
                create_resource_with_requires("s3", ["s4"]),
                create_resource_with_requires("s4", []),
                create_resource_with_requires("a1", ["s1"]),
                create_resource_with_requires("a2", ["a3"]),
                create_resource_with_requires("a3", []),
            ],
            resource_state={},
            unknowns=[],
            version_info=None,
            resource_sets=resource_sets,
            module_version_info={},
        )
        assert result.code == 200
        return result.result["data"]

    version_2 = await put_partial()
    version_3 = await put_partial()

    async with data.ResourceSet.get_connection() as con:

        async def get_requires_that_can_form_cycle(base_version: int, version: int) -> dict[ResourceIdStr, set[ResourceIdStr]]:
            new_resource_set_ids = await con.fetch(
                """
                SELECT resource_set FROM public.resource_set_configuration_model WHERE environment=$1 AND model=$2
                EXCEPT
                SELECT resource_set FROM public.resource_set_configuration_model WHERE environment=$1 AND model=$3
                """,
                env_id,
                version,
                base_version,
            )
            return await data.ResourceSet.get_requires_that_can_form_cycle(
                environment=env_id,
                base_version=base_version,
                version=version,
                resource_set_ids={record["resource_set"] for record in new_resource_set_ids},
                connection=con,
            )

        # The new requires are a1 -> s1 and a2 -> a3. Resources s1 and a2 are reachable from s1 or a3 and can reach a1
        # or a2. The requires of the shared resources s2 and s3 were rewritten, but they are not new.
        assert await get_requires_that_can_form_cycle(base_version=version_1, version=version_2) == {
            "test::Resource[agent1,key=s1]": {"test::Resource[agent1,key=a2]"},
        }
        # All requires of the rewritten resource sets already exist in the base version
        assert await get_requires_that_can_form_cycle(base_version=version_2, version=version_3) == {}
