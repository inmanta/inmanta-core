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


async def test_resource_sets_via_put_partial(server, client, environment, clienthelper):
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
        "test::Resource[agent1,key=key3]": "set-c",
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
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key10",
            "value": "test",
            "id": "test::Resource[agent1,key=key10],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    version = await clienthelper.get_version()
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
            "test::Resource[agent1,key=key3]": None,
        },
        removed_resource_sets=["set-c"],
    )

    assert result.code == 200
