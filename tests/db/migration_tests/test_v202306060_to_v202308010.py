"""
    Copyright 2023 Inmanta

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
from collections import abc

import pytest

from inmanta import const
from inmanta.data import ConfigurationModel, Environment, ResourceAction, ResourcePersistentState


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202306060.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:

    await migrate_db_from()
    env = await Environment.get_one(name="dev-1")
    assert env
    model = await ConfigurationModel.get_latest_version(env.id)
    assert model
    assert model.version == 3

    rps = await ResourcePersistentState.get_list(environment=env.id)

    expected = 0
    for resource in rps:
        if resource.resource_id == "std::AgentConfig[internal,agentname=localhost]":
            # always success
            # verify time on last success
            actions = await ResourceAction.query_resource_actions(
                environment=env.id, resource_id=resource.resource_id, action=const.ResourceAction.deploy
            )
            last_deploy = actions[1]
            assert last_deploy.version == 2
            assert resource.last_success == last_deploy.started
            assert last_deploy.started != last_deploy.finished
            expected += 1
        if resource.resource_id == "std::File[localhost,path=/tmp/test]":
            # always fails
            assert resource.last_success is None
            expected += 1

    # assert we saw both resources
    # I do it this way, so more resources can be added without breaking this
    assert expected == 2
