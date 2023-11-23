"""
    Copyright 2021 Inmanta

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
from collections.abc import AsyncIterator, Awaitable
from typing import Callable

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta import protocol
from inmanta.const import LogLevel, ResourceAction
from inmanta.data.model import ResourceLog
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
async def migrate_v202106210_to_v202109100(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, server_config
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Returns a callable that performs a v202105170 database restore and migrates to v202106080.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v202106210.sql")) as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v202105170
    yield ibl.start
    await ibl.stop(timeout=15)


@pytest.mark.slowtest
async def test_valid_loglevels(migrate_v202106210_to_v202109100: Callable[[], Awaitable[None]]) -> None:
    """
    Test whether the value column was added to the resource table.
    """

    # Migrate DB schema
    await migrate_v202106210_to_v202109100()

    client = protocol.Client("client")

    # This call fails if invalid log levels are in the DB
    result = await client.resource_logs(
        tid="18c3a11d-132f-4293-987c-de797eb36244", rid="std::AgentConfig[internal,agentname=localhost],v=1"
    )

    assert result.code == 200
    logs: list[ResourceLog] = [ResourceLog(**log) for log in result.result["data"]]

    # NOTSET level is replaced by trace
    for log in logs:
        if log.action == ResourceAction.store:
            assert log.level == LogLevel.TRACE

    # other are still the same
    for log in logs:
        if log.action == ResourceAction.pull:
            assert log.level == LogLevel.INFO
