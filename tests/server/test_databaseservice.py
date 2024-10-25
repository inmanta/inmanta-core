"""
    Copyright 2020 Inmanta

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

import asyncio
import logging

import pytest
from asyncpg import Connection

from inmanta import data
from inmanta.server import config as opt
from inmanta.server.services import databaseservice
from utils import log_contains, retry_limited


@pytest.mark.skip("To be considered in final cleanup")
async def test_agent_process_cleanup(server, environment, agent_factory):
    opt.agent_processes_to_keep.set("1")
    a1 = await agent_factory(environment, hostname="host", agent_map=[], agent_names=["agent1"])
    a2 = await agent_factory(environment, hostname="host", agent_map=[], agent_names=["agent1"])
    await asyncio.gather(*[a1.stop(), a2.stop()])

    async def _wait_until_expire_is_finished():
        result = await data.AgentProcess.get_list()
        return len([r for r in result if r.expired is not None]) == 2

    await retry_limited(_wait_until_expire_is_finished, timeout=10)
    # Execute cleanup
    database_slice = server.get_slice(databaseservice.SLICE_DATABASE)
    await database_slice._purge_agent_processes()
    # Assert cleanup
    result = await data.AgentProcess.get_list()
    assert len(result) == 1


@pytest.fixture(scope="function")
async def set_pool_size_to_one():
    """
    Sets the database pool's max and min size to 1 and resets their prior values upon exiting.
    """
    save_min_size = opt.db_connection_pool_min_size.get()
    save_max_size = opt.db_connection_pool_max_size.get()

    opt.db_connection_pool_min_size.set("1")
    opt.db_connection_pool_max_size.set("1")

    yield

    opt.db_connection_pool_min_size.set(str(save_min_size))
    opt.db_connection_pool_max_size.set(str(save_max_size))


async def test_pool_exhaustion_watcher(set_pool_size_to_one, server, caplog):
    """
    Test the basic functionalities of the ExhaustedPoolWatcher class
    """

    def exhaustion_events_recorded() -> bool:
        """
        Returns true if some database exhaustion events have been recorded
        """
        n_events: int = database_slice._db_monitor._db_pool_watcher._exhausted_pool_events_count
        return n_events > 0

    with caplog.at_level(logging.WARNING, "inmanta.server.services.databaseservice"):
        database_slice = server.get_slice(databaseservice.SLICE_DATABASE)

        pool = database_slice._pool
        assert pool is not None
        connection: Connection = await pool.acquire()
        try:
            # Make sure _check_database_pool_exhaustion gets called (scheduled to run every 200ms)
            # and records some exhaustion events.
            await retry_limited(exhaustion_events_recorded, 1)
        finally:
            await connection.close()

        # Call _report_database_pool_exhaustion manually (scheduled to run every 24h)
        await database_slice._db_monitor._report_database_pool_exhaustion()

        log_contains(
            caplog,
            "inmanta.server.services.databaseservice",
            logging.WARNING,
            "Database pool was exhausted",
        )
