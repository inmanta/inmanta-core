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
import uuid

from inmanta import data
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
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
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


async def test_put_partial_replace_resource_set(server, client, environment, clienthelper):
    """
    When an partial compile updates a certain resource set, the entire resource set
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
    version = await clienthelper.get_version()
    resources_partial = [
        {
            "key": "key2",
            "value": "value123",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        version=version,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        compiler_version=get_compiler_version(),
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
            "test::Resource[agent1,key=key2]": "set-a",
        },
    )

    assert result.code == 200
    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 1
    assert resource_list[0].resource_version_id == "test::Resource[agent1,key=key2],v=2"
    assert resource_sets_from_db == {"test::Resource[agent1,key=key2]": "set-a"}


async def test_put_partial_merge_not_in_resource_set(server, client, environment, clienthelper):
    """
    The resources in an partial compile that don't belong to a resource set (rest set) are merged
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
    version = await clienthelper.get_version()
    resources_partial = [
        {
            "key": "key2",
            "value": "value123",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        version=version,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        compiler_version=get_compiler_version(),
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
    version = await clienthelper.get_version()
    resources_partial = [
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
        version=version,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        compiler_version=get_compiler_version(),
        resource_sets={"test::Resource[agent1,key=key1]": "set-b"},
    )

    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: A partial compile cannot migrate a "
        "resource(test::Resource[agent1,key=key1],v=2) to another resource set"
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
    version = await clienthelper.get_version()
    resources_partial = [
        {
            "key": "key1",
            "value": "value123",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        version=version,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        compiler_version=get_compiler_version(),
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
    version = await clienthelper.get_version()
    resources_partial = [
        {
            "key": "key1",
            "value": "value1123",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value234",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        version=version,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        compiler_version=get_compiler_version(),
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
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version, "test::Resource[agent1,key=key3],v=%d" % version],
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


async def test_put_partial_dependency_graph(server, client, environment, clienthelper):
    """
    The model should have a dependency graph that is closed (i.e. doesn't have any dangling dependencies),
    even after a partial compile
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
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
        "test::Resource[agent1,key=key2]": "set-a",
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
    version = await clienthelper.get_version()
    resources_partial = [
        {
            "key": "key1",
            "value": "value123",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        version=version,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        compiler_version=get_compiler_version(),
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
            "test::Resource[agent1,key=key2]": "set-a",
        },
    )

    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: The model should have a dependency graph that is closed and no dangling dependencies: "
        "{'test::Resource[agent1,key=key2]'}"
    )


async def test_put_partial_mixed_scenario(server, client, environment, clienthelper):
    """
    A test that starts with: resources in several different resource sets and resources in the shared set.
    The partial update does: An update of a subset of the resources sets an addition of shared resources
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
    ]
    resource_sets = {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-a",
        "test::Resource[agent1,key=key3]": "set-b",
        "test::Resource[agent1,key=key4]": "set-b",
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
    version = await clienthelper.get_version()
    resources_partial = [
        {
            "key": "key1",
            "value": "100",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "200",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key7",
            "value": "700",
            "id": "test::Resource[agent1,key=key7],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_partial(
        tid=environment,
        version=version,
        resources=resources_partial,
        resource_state={},
        unknowns=[],
        version_info=None,
        compiler_version=get_compiler_version(),
        resource_sets={
            "test::Resource[agent1,key=key1]": "set-a",
            "test::Resource[agent1,key=key2]": "set-a",
            "test::Resource[agent1,key=key3]": "set-b",
            "test::Resource[agent1,key=key4]": "set-b",
        },
    )

    assert result.code == 200
    resource_list = await data.Resource.get_resources_in_latest_version(uuid.UUID(environment))
    resource_sets_from_db = {resource.resource_id: resource.resource_set for resource in resource_list}
    assert len(resource_list) == 7
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
    assert resource_list[6].attributes == {"key": "key7", "value": "700", "purged": False, "requires": [], "send_event": False}
    assert resource_sets_from_db == {
        "test::Resource[agent1,key=key1]": "set-a",
        "test::Resource[agent1,key=key2]": "set-a",
        "test::Resource[agent1,key=key3]": "set-b",
        "test::Resource[agent1,key=key4]": "set-b",
        "test::Resource[agent1,key=key5]": None,
        "test::Resource[agent1,key=key6]": None,
        "test::Resource[agent1,key=key7]": None,
    }
