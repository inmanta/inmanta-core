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

from inmanta import resources
from inmanta.data import Environment, ResourcePersistentState, Scheduler
from inmanta.deploy import state

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


def assert_resource_state(
    resource_persistent_state: ResourcePersistentState,
    is_undefined: bool,
    is_orphan: bool,
    deployment_result: state.DeploymentResult,
    blocked_status: state.BlockedStatus,
) -> None:
    assert resource_persistent_state.is_undefined == is_undefined
    assert resource_persistent_state.is_orphan == is_orphan
    assert resource_persistent_state.deployment_result is deployment_result
    assert resource_persistent_state.blocked_status is blocked_status
    # TODO: EXTEND


@pytest.mark.parametrize("no_agent", [True])
@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_new_resource_status_column(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    await migrate_db_from()

    envs = await Environment.get_list()
    for env in envs:
        scheduler = await Scheduler.get_one(environment=env.id)
        assert scheduler is not None
        assert scheduler.last_processed_model_version is None

    env = await Environment.get_one(name="dev-3")
    resource_persistent_state = await ResourcePersistentState.get_list(environment=env.id)
    resource_state_by_resource_id = {record.resource_id: record for record in resource_persistent_state}
    assert_resource_state(
        resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key1]")],
        is_undefined=False,
        is_orphan=False,
        deployment_result=state.DeploymentResult.DEPLOYED,
        blocked_status=state.BlockedStatus.NO,
    )
    assert_resource_state(
        resource_state_by_resource_id[resources.ResourceIdStr("test::Fail[agent1,key=key2]")],
        is_undefined=False,
        is_orphan=False,
        deployment_result=state.DeploymentResult.FAILED,
        blocked_status=state.BlockedStatus.NO,
    )
    assert_resource_state(
        resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key3]")],
        is_undefined=False,
        is_orphan=False,
        deployment_result=state.DeploymentResult.SKIPPED,
        blocked_status=state.BlockedStatus.NO,
    )
    assert_resource_state(
        resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key4]")],
        is_undefined=True,
        is_orphan=False,
        deployment_result=state.DeploymentResult.NEW,
        blocked_status=state.BlockedStatus.YES,
    )
    assert_resource_state(
        resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key5]")],
        is_undefined=False,
        is_orphan=False,
        deployment_result=state.DeploymentResult.NEW,
        blocked_status=state.BlockedStatus.YES,
    )
    assert_resource_state(
        resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key6]")],
        is_undefined=False,
        is_orphan=True,
        # The deployment status is not accurate here, because it's an orphan. Tracking this accurately
        # would require an expensive query in the database migration script.
        deployment_result=state.DeploymentResult.NEW,
        blocked_status=state.BlockedStatus.NO,
    )
    assert_resource_state(
        resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key7]")],
        is_undefined=False,
        is_orphan=False,
        deployment_result=state.DeploymentResult.DEPLOYED,
        blocked_status=state.BlockedStatus.NO,
    )
    assert_resource_state(
        resource_state_by_resource_id[resources.ResourceIdStr("test::Resource[agent1,key=key8]")],
        is_undefined=False,
        is_orphan=False,
        deployment_result=state.DeploymentResult.NEW,
        blocked_status=state.BlockedStatus.NO,
    )
