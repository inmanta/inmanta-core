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
import json
import os
from collections import abc

import pytest

from inmanta.const import ResourceState
from inmanta.data import Environment, Resource
from inmanta.db.versions.v202211230 import (
    query_part_convert_provides,
    query_part_convert_requires,
    query_part_convert_rvid_to_rid,
)
from inmanta.resources import Id


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps", "v1.sql"))
async def test_drop_resource_version_id(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    """
    Test the database migration script that adds the `exporter_plugin` column to the database.

    """
    # Migrate DB schema
    await migrate_db_from()
    env = await Environment.get_one(name="dev-1")

    states = await Resource.get_last_non_deploying_state_for_dependencies(
        env.id,
        Id.parse_resource_version_id("std::File[localhost,path=/tmp/test],v=2"),
    )

    assert states == {"std::AgentConfig[internal,agentname=localhost],v=2": ResourceState.deployed}


async def test_query_parts(postgresql_client):
    # base conversion
    test_in_data = "std::AgentConfig[internal,agentname=localhost],v=1"

    out = await postgresql_client.fetchval(f"select {query_part_convert_rvid_to_rid('$1')}", test_in_data)
    assert out == "std::AgentConfig[internal,agentname=localhost]"

    # requires
    test_data_2 = {
        "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220",
        "path": "/tmp/test",
        "group": "root",
        "owner": "root",
        "purged": False,
        "reload": False,
        "version": 1,
        "requires": ["std::AgentConfig[internal,agentname=localhost],v=1", "std::xconf[internal,agentname=localhost],v=1"],
        "send_event": False,
        "permissions": 644,
        "purge_on_delete": False,
    }
    out = await postgresql_client.fetchval(f"select {query_part_convert_requires('$1::jsonb')}", json.dumps(test_data_2))
    out_decoded = json.loads(out)
    test_data_2["requires"] = ["std::AgentConfig[internal,agentname=localhost]", "std::xconf[internal,agentname=localhost]"]
    assert out_decoded == test_data_2

    del test_data_2["requires"]
    out = await postgresql_client.fetchval(f"select {query_part_convert_requires('$1::jsonb')}", json.dumps(test_data_2))
    out_decoded = json.loads(out)
    assert out_decoded == test_data_2

    test_data_2["requires"] = []
    out = await postgresql_client.fetchval(f"select {query_part_convert_requires('$1::jsonb')}", json.dumps(test_data_2))
    out_decoded = json.loads(out)
    assert out_decoded == test_data_2

    # provides
    test_in_data_3 = (["std::AgentConfig[internal,agentname=localhost],v=1", "std::xconf[internal,agentname=localhost],v=1"],)
    out = await postgresql_client.fetchval(f"select {query_part_convert_provides('$1::character varying[]')}", test_in_data_3)
    assert out == ["std::AgentConfig[internal,agentname=localhost]", "std::xconf[internal,agentname=localhost]"]

    # provides
    test_in_data_3 = ([],)
    out = await postgresql_client.fetchval(f"select {query_part_convert_provides('$1::character varying[]')}", test_in_data_3)
    assert out == []
