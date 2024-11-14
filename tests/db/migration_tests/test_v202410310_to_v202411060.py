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

from inmanta.data import Environment, ResourcePersistentState
from inmanta import const, resources
from inmanta.deploy import state

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.parametrize("no_agent", [True])
@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_new_resource_status_column(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    await migrate_db_from()

    env = await Environment.get_one(name="dev-3")
    resource_persistent_state = await ResourcePersistentState.get_list(environment=env.id)
    resource_state_by_resource_id = {record.resource_id: record.resource_status for record in resource_persistent_state}
    assert resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key1]")] is state.ResourceStatus.UP_TO_DATE
    assert resource_state_by_resource_id[resources.ResourceIdStr("test::Fail[agent1,key=key2]")] is state.ResourceStatus.HAS_UPDATE
    assert resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key3]")] is state.ResourceStatus.HAS_UPDATE
    assert resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key4]")] is state.ResourceStatus.UNDEFINED
    assert resource_state_by_resource_id[
               resources.ResourceIdStr("test::Resource[agent1,key=key5]")] is state.ResourceStatus.HAS_UPDATE
    assert resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key6]")] is state.ResourceStatus.ORPHAN
    assert resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key7]")] is state.ResourceStatus.UP_TO_DATE
