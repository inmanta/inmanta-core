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

import pytest

from inmanta import const
from inmanta.data import Environment, ResourceAction, ResourcePersistentState

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_resource_state_table(postgres_db, database_name, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]) -> None:
    # This migration script adds a column. Just verify that the script doesn't fail.
    await migrate_db_from()
    env = await Environment.get_one(name="dev-1")
    assert env

    # Verify time on last success
    rps = await ResourcePersistentState.get_one(
        environment=env.id, resource_id="std::AgentConfig[internal,agentname=localhost]"
    )

    actions = await ResourceAction.query_resource_actions(
        environment=env.id, resource_id="std::AgentConfig[internal,agentname=localhost]", action=const.ResourceAction.deploy
    )
    last_deploy = actions[0]  # increment
    last_success = actions[1]  # deploy, no_change
    last_produced_events = None  # never did changes

    assert rps.last_deploy == last_deploy.finished
    assert rps.last_success == last_success.started
    assert rps.last_produced_events == last_produced_events

    # Verify that orphaned resource is included in resource_persistent_state
    orphaned_rps = await ResourcePersistentState.get_one(
        environment=env.id, resource_id="std::File[localhost,path=/tmp/test_orphan]"
    )
    assert orphaned_rps
    assert orphaned_rps.last_deployed_version == 4  # Last version where the resource existed
