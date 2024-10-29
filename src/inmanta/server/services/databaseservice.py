"""
    Copyright 2019 Inmanta

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

import logging
from typing import Optional

import asyncpg
from pyformance import gauge
from pyformance.meters import CallbackGauge

from inmanta import data, util
from inmanta.server import SLICE_DATABASE
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.types import ArgumentTypes

LOGGER = logging.getLogger(__name__)


class DatabaseService(protocol.ServerSlice):
    """Slice to initialize the database"""

    def __init__(self) -> None:
        super().__init__(SLICE_DATABASE)
        self._pool: Optional[asyncpg.pool.Pool] = None
        self._db_pool_watcher: Optional[util.ExhaustedPoolWatcher] = None

    async def start(self) -> None:
        await super().start()
        self.start_monitor()
        await self.connect_database()

        # Schedule cleanup agentprocess and agentinstance tables
        agent_process_purge_interval = opt.agent_process_purge_interval.get()
        if agent_process_purge_interval > 0:
            self.schedule(
                self._purge_agent_processes, interval=agent_process_purge_interval, initial_delay=0, cancel_on_stop=False
            )

        assert self._pool is not None  # Make mypy happy
        self._db_pool_watcher = util.ExhaustedPoolWatcher(self._pool)
        # Schedule database pool exhaustion watch:
        # Check for pool exhaustion every 200 ms
        self.schedule(self._check_database_pool_exhaustion, interval=0.2, cancel_on_stop=True, quiet_mode=True)
        # Report pool exhaustion every 24h
        self.schedule(self._report_database_pool_exhaustion, interval=3_600 * 24, cancel_on_stop=True)

    async def stop(self) -> None:
        await super().stop()
        await self.disconnect_database()
        self._pool = None

    def get_dependencies(self) -> list[str]:
        return []

    async def connect_database(self) -> None:
        """Connect to the database"""
        self._pool = await initialize_database_connection_pool(
            database_host=opt.db_host.get(),
            database_port=opt.db_port.get(),
            database_name=opt.db_name.get(),
            database_username=opt.db_username.get(),
            database_password=opt.db_password.get(),
            create_db_schema=True,
            connection_pool_min_size=opt.server_db_connection_pool_min_size.get(),
            connection_pool_max_size=opt.server_db_connection_pool_max_size.get(),
            connection_timeout=opt.server_db_connection_timeout.get(),
        )

        # Check if JIT is enabled
        async with self._pool.acquire() as connection:
            jit_available = await connection.fetchval("SELECT pg_jit_available();")
            if jit_available:
                LOGGER.warning("JIT is enabled in the PostgreSQL database. This might result in poor query performance.")

    async def disconnect_database(self) -> None:
        """Disconnect the database"""
        await data.disconnect()

    async def get_status(self) -> dict[str, ArgumentTypes]:
        """Get the status of the database connection"""
        connected = await self.get_connection_status()
        status = {
            "connected": connected,
            "database": opt.db_name.get(),
            "host": opt.db_host.get(),
        }
        if self._pool is not None:
            status["max_pool"] = self._pool.get_max_size()
            status["open_connections"] = self._pool.get_size()
            status["free_connections"] = self._pool.get_idle_size()

        return status

    def start_monitor(self) -> None:
        """Attach to monitoring system"""
        gauge(
            "db.connected",
            CallbackGauge(
                callback=lambda: 1 if (self._pool is not None and not self._pool._closing and not self._pool._closed) else 0
            ),
        )
        gauge("db.max_pool", CallbackGauge(callback=lambda: self._pool.get_max_size() if self._pool is not None else 0))
        gauge("db.open_connections", CallbackGauge(callback=lambda: self._pool.get_size() if self._pool is not None else 0))
        gauge(
            "db.free_connections", CallbackGauge(callback=lambda: self._pool.get_idle_size() if self._pool is not None else 0)
        )

    async def get_connection_status(self) -> bool:
        if self._pool is not None and not self._pool._closing and not self._pool._closed:
            try:
                async with self._pool.acquire(timeout=10):
                    return True
            except Exception:
                LOGGER.exception("Connection to PostgreSQL failed")
        return False

    async def _purge_agent_processes(self) -> None:
        agent_processes_to_keep = opt.agent_processes_to_keep.get()
        await data.AgentProcess.cleanup(nr_expired_records_to_keep=agent_processes_to_keep)

    async def _report_database_pool_exhaustion(self) -> None:
        assert self._db_pool_watcher is not None  # Make mypy happy
        self._db_pool_watcher.report_and_reset(LOGGER)

    async def _check_database_pool_exhaustion(self) -> None:
        assert self._db_pool_watcher is not None  # Make mypy happy
        self._db_pool_watcher.check_for_pool_exhaustion()


async def initialize_database_connection_pool(
    database_host: str,
    database_port: int,
    database_name: str,
    database_username: str,
    database_password: str,
    create_db_schema: bool,
    connection_pool_min_size: int,
    connection_pool_max_size: int,
    connection_timeout: float,
) -> asyncpg.pool.Pool:
    """
    Initialize the database connection pool for the current process and return it.

    :param database_host: Database host address.
    :param database_port: Port number to connect to at the server host.
    :param database_name: Name of the database to connect to.
    :param database_username: Username for database authentication.
    :param database_password: Password for database authentication.
    :param create_db_schema: Make sure the DB schema is created and up-to-date.
    :param connection_pool_min_size: Initialize the pool with this number of connections .
    :param connection_pool_max_size: Limit the size of the pool to this number of connections .
    :param connection_timeout: Connection timeout (in seconds) when interacting with the database.
    """

    out = await data.connect(
        host=database_host,
        port=database_port,
        database=database_name,
        username=database_username,
        password=database_password,
        create_db_schema=create_db_schema,
        connection_pool_min_size=connection_pool_min_size,
        connection_pool_max_size=connection_pool_max_size,
        connection_timeout=connection_timeout,
    )
    LOGGER.info("Connected to PostgreSQL database %s on %s:%d", database_name, database_host, database_port)
    return out
