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

from inmanta.data import Environment


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202310040.sql"))
async def test_type_change(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    # env = await Environment.get_one(name="dev-1")
    # assert isinstance(env.settings["autostart_agent_deploy_interval"], str)
    # assert isinstance(env.settings["autostart_agent_repair_interval"], str)

    await migrate_db_from()

    env = await Environment.get_one(name="dev-1")
    assert isinstance(env.settings["autostart_agent_deploy_interval"], str)
    assert isinstance(env.settings["autostart_agent_repair_interval"], str)
