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

from inmanta import const, data
from inmanta.types import ResourceIdStr

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_drop_status_column(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    # Migration script only drops a column.

    await migrate_db_from()
    env = await data.Environment.get_one(name="dev-3")
    assert env

    expected_outcome: dict[ResourceIdStr, const.ResourceState] = {
        ResourceIdStr("test::Resource[agent1,key=key1]"): const.ResourceState.deployed,
        ResourceIdStr("test::Fail[agent1,key=key2]"): const.ResourceState.failed,
        ResourceIdStr("test::Resource[agent1,key=key3]"): const.ResourceState.skipped,
        ResourceIdStr("test::Resource[agent1,key=key4]"): const.ResourceState.undefined,
        ResourceIdStr("test::Resource[agent1,key=key5]"): const.ResourceState.skipped_for_undefined,
        ResourceIdStr("test::Resource[agent1,key=key7]"): const.ResourceState.deployed,
    }
    version, states = await data.Resource.get_latest_resource_states(env.id)
    # Version 3 is not yet released.
    # get_latest_resource_states fetches the latest resource states processed by the scheduler
    assert version == 2
    assert states == expected_outcome

    for key, value in expected_outcome.items():
        state = await data.Resource.get_current_resource_state(env.id, key)
        assert state == value

    res = await data.Resource.get_resource_deploy_summary(env.id)
    assert res.by_state == {
        "available": 0,
        "cancelled": 0,
        "deployed": 2,
        "deploying": 0,
        "failed": 1,
        "skipped": 1,
        "skipped_for_undefined": 1,
        "unavailable": 0,
        "undefined": 1,
        "non_compliant": 0,
    }
