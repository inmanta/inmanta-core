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

import inmanta.types
from inmanta.data import Environment, ResourcePersistentState, Scheduler
from inmanta.deploy import state
from inmanta.deploy.state import Compliance
from utils import assert_resource_persistent_state

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.parametrize("no_agent", [True])
@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_new_resource_status_column(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    # after the migration script for which this test case was originally created, v202501140 was added on top of it.
    await migrate_db_from()

    envs = await Environment.get_list()
    for env in envs:
        scheduler = await Scheduler.get_one(environment=env.id)
        assert scheduler is not None
        assert scheduler.last_processed_model_version is None

    env = await Environment.get_one(name="dev-3")
    resource_persistent_state = await ResourcePersistentState.get_list(environment=env.id)
    resource_state_by_resource_id = {record.resource_id: record for record in resource_persistent_state}
    assert_resource_persistent_state(
        resource_state_by_resource_id[inmanta.types.ResourceIdStr("test::Resource[agent1,key=key1]")],
        is_undefined=False,
        is_orphan=False,
        last_handler_run=state.HandlerResult.SUCCESSFUL,
        blocked=state.Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.COMPLIANT,
        last_deploy_compliant=True,
    )
    assert_resource_persistent_state(
        resource_state_by_resource_id[inmanta.types.ResourceIdStr("test::Fail[agent1,key=key2]")],
        is_undefined=False,
        is_orphan=False,
        last_handler_run=state.HandlerResult.FAILED,
        blocked=state.Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.NON_COMPLIANT,
        last_deploy_compliant=False,
    )
    assert_resource_persistent_state(
        resource_state_by_resource_id[inmanta.types.ResourceIdStr("test::Resource[agent1,key=key3]")],
        is_undefined=False,
        is_orphan=False,
        last_handler_run=state.HandlerResult.SKIPPED,
        blocked=state.Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.NON_COMPLIANT,
        last_deploy_compliant=False,
    )
    assert_resource_persistent_state(
        resource_state_by_resource_id[inmanta.types.ResourceIdStr("test::Resource[agent1,key=key4]")],
        is_undefined=True,
        is_orphan=False,
        last_handler_run=state.HandlerResult.NEW,
        blocked=state.Blocked.BLOCKED,
        expected_compliance=Compliance.UNDEFINED,
        last_deploy_compliant=None,
    )
    assert_resource_persistent_state(
        resource_state_by_resource_id[inmanta.types.ResourceIdStr("test::Resource[agent1,key=key5]")],
        is_undefined=False,
        is_orphan=False,
        last_handler_run=state.HandlerResult.NEW,
        blocked=state.Blocked.BLOCKED,
        expected_compliance=Compliance.NON_COMPLIANT,
        last_deploy_compliant=None,
    )
    assert_resource_persistent_state(
        resource_state_by_resource_id[inmanta.types.ResourceIdStr("test::Resource[agent1,key=key6]")],
        is_undefined=False,
        is_orphan=True,
        # The last_handler_run field is not accurate, because it's an orphan. Tracking this accurately
        # would require an expensive query in the database migration script.
        last_handler_run=state.HandlerResult.NEW,
        blocked=state.Blocked.NOT_BLOCKED,
        expected_compliance=None,
        last_deploy_compliant=None,
    )
    assert_resource_persistent_state(
        resource_state_by_resource_id[inmanta.types.ResourceIdStr("test::Resource[agent1,key=key7]")],
        is_undefined=False,
        is_orphan=False,
        last_handler_run=state.HandlerResult.SUCCESSFUL,
        blocked=state.Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.COMPLIANT,
        last_deploy_compliant=True,
    )
    assert_resource_persistent_state(
        resource_state_by_resource_id[inmanta.types.ResourceIdStr("test::Resource[agent1,key=key8]")],
        is_undefined=False,
        is_orphan=False,
        last_handler_run=state.HandlerResult.NEW,
        blocked=state.Blocked.NOT_BLOCKED,
        expected_compliance=Compliance.HAS_UPDATE,
        last_deploy_compliant=None,
    )
