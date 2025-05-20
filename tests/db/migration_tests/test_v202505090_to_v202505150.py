"""
Copyright 2025 Inmanta

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

import os
import re
from collections import abc

import asyncpg
import pytest

from inmanta import data
from inmanta.protocol import Client

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_is_undefined_to_resource_table(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    # This migration script adds the is_undefined column to the resource table
    # It should be set to true iff the status of the resource is undefined

    await migrate_db_from()

    env = await data.Environment.get_one(name="dev-3")
    assert env

    client = Client("client")
    # Undefined resource
    res = await client.get_resource(tid=env.id, id="test::Resource[agent1,key=key4],v=3")
    assert res.code == 200
    assert res.result["resource"]["is_undefined"]

    # Available resource
    res = await client.get_resource(tid=env.id, id="test::Resource[agent1,key=key8],v=3")
    assert res.code == 200
    assert not res.result["resource"]["is_undefined"]
