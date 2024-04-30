"""
    Copyright 2024 Inmanta

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

import inmanta.data
import inmanta.protocol

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_update_compile_for_more_env_vars(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    await migrate_db_from()
    # check in DB
    all_compiles = await inmanta.data.Compile.get_list()
    assert len(all_compiles) > 0
    for compile in all_compiles:
        assert compile.requested_environment_variables in [{"add_one_resource": "true"}, {}]
        assert compile.used_environment_variables == compile.requested_environment_variables
        assert compile.mergeable_environment_variables == {}

    env = await inmanta.data.Environment.get_one(name="dev-1")
    assert env
    # check API result
    client = inmanta.protocol.Client("client")
    result = await client.get_reports(tid=env.id)
    assert result.code == 200
    assert len(result.result["reports"]) > 0
    for compile in result.result["reports"]:
        assert compile["requested_environment_variables"] in [{"add_one_resource": "true"}, {}]
        assert compile["environment_variables"] == compile["requested_environment_variables"]
        assert compile["mergeable_environment_variables"] == {}
