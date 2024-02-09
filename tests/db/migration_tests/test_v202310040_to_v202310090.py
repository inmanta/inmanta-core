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

import json
import os
from collections import abc

import asyncpg
import pytest

from inmanta import data


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202310040.sql"))
async def test_type_change(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    result = await postgresql_client.fetch(
        """
            SELECT * FROM public.environment WHERE name='dev-1';
        """
    )
    settings = json.loads(result[0]["settings"])
    assert isinstance(settings[data.AUTOSTART_AGENT_DEPLOY_INTERVAL], int)
    assert isinstance(settings[data.AUTOSTART_AGENT_REPAIR_INTERVAL], int)

    await migrate_db_from()

    result = await postgresql_client.fetch(
        """
            SELECT * FROM public.environment WHERE name='dev-1';
        """
    )
    settings = json.loads(result[0]["settings"])
    assert isinstance(settings[data.AUTOSTART_AGENT_DEPLOY_INTERVAL], str)
    assert isinstance(settings[data.AUTOSTART_AGENT_REPAIR_INTERVAL], str)
