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
from typing import Mapping, Optional

from pyformance import gauge, global_registry
from pyformance.meters import CallbackGauge

from inmanta.data import (
    CORE_SCHEMA_NAME,
    PACKAGE_WITH_UPDATE_FILES,
    get_connection_ctx_mgr,
    get_pool,
    schema,
    start_engine,
    stop_engine,
)
from inmanta.data.model import DataBaseReport
from inmanta.server import SLICE_DATABASE
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.types import ArgumentTypes
from inmanta.util import IntervalSchedule, Scheduler

LOGGER = logging.getLogger(__name__)


class DatabaseMonitor:

    def __init__(
        self,
        db_name: str,
        db_host: str,
        max_overflow: int,
    ) -> None:
        self._scheduler = Scheduler(f"Database monitor for {db_name}")
        self.dn_name = db_name
        self.db_host = db_host
        self.registered_gauges: list[str] = []
        self._db_exhaustion_check_interval = 0.2
        self._exhausted_pool_events_count: int = 0
        self._last_report: int = 0
        self._max_overflow = max_overflow

    def _report_and_reset(self) -> None:
        """
        Log how long the DB pool was exhausted since the last time the counter
        was reset, if any, and reset the counter.
        """
        since_last = self._exhausted_pool_events_count - self._last_report
        if since_last > 0:
            LOGGER.warning(
                "Database pool was exhausted %d seconds in the past 24h.", since_last * self._db_exhaustion_check_interval
            )
            self._last_report = self._exhausted_pool_events_count

    def _check_for_pool_exhaustion(self) -> None:
        """
        Checks if the database pool is exhausted
        """
        pool = get_pool()
        pool_exhausted: bool = pool.checkedin() == 0 and pool.overflow() == self._max_overflow
        if pool_exhausted:
            self._exhausted_pool_events_count += 1

    def start(self) -> None:
        self.start_monitor()

        async def _report_database_pool_exhaustion() -> None:
            self._report_and_reset()

        async def _check_database_pool_exhaustion() -> None:
            self._check_for_pool_exhaustion()

        # Schedule database pool exhaustion watch:
        # Check for pool exhaustion every 200 ms
        self._scheduler.add_action(
            _check_database_pool_exhaustion,
            IntervalSchedule(self._db_exhaustion_check_interval),
            cancel_on_stop=True,
            quiet_mode=True,
        )

        # Report pool exhaustion every 24h
        self._scheduler.add_action(_report_database_pool_exhaustion, IntervalSchedule(3600 * 24), cancel_on_stop=True)

    async def stop(self) -> None:
        self.stop_monitor()
        await self._scheduler.stop()

    async def get_status(self) -> DataBaseReport:
        """Get the status of the database connection"""
        connected = await self.get_connection_status()

        pool = get_pool()
        max_connections = pool.size() + self._max_overflow
        free_connections_in_pool = pool.checkedin()
        open_overflow_connections = pool.overflow()

        return DataBaseReport(
            connected=connected,
            database=self.dn_name,
            host=self.db_host,
            max_pool=max_connections,
            free_pool=free_connections_in_pool + self._max_overflow - open_overflow_connections,
            open_connections=pool.size() - free_connections_in_pool + open_overflow_connections,
            free_connections=free_connections_in_pool,
            pool_exhaustion_time=self._exhausted_pool_events_count * self._db_exhaustion_check_interval,
        )

    def get_pool_free(self) -> int:
        pool = get_pool()
        if pool is None:
            return 0
        return pool.size() + self._max_overflow - pool.checkedout() - pool.overflow()

    def _add_gauge(self, name: str, the_gauge: CallbackGauge) -> None:
        """Helper to register gauges and keep track of registrations"""
        gauge(name, the_gauge)
        self.registered_gauges.append(name)

    def start_monitor(self) -> None:
        """Attach to monitoring system"""

        # TODO not all these are correct / equivalent to previous asyncpg pool implementation
        self._add_gauge(
            "db.connected",
            CallbackGauge(callback=lambda: 1 if (get_pool() is not None) else 0),
        )
        self._add_gauge(
            "db.max_pool",
            CallbackGauge(callback=lambda: get_pool().size() + self._max_overflow if get_pool() is not None else 0),
        )
        self._add_gauge(
            "db.open_connections",
            CallbackGauge(callback=lambda: get_pool().checkedout() if get_pool() is not None else 0),
        )
        self._add_gauge(
            "db.free_connections",
            CallbackGauge(
                callback=lambda: (
                    get_pool().checkedin() + self._max_overflow - get_pool().overflow() if get_pool() is not None else 0
                )
            ),
        )
        self._add_gauge(
            "db.free_pool",
            CallbackGauge(callback=self.get_pool_free),
        )
        self._add_gauge(
            "db.pool_exhaustion_count",
            CallbackGauge(callback=lambda: self._exhausted_pool_events_count),
        )
        self._add_gauge(
            "db.pool_exhaustion_time",
            CallbackGauge(callback=lambda: self._exhausted_pool_events_count * self._db_exhaustion_check_interval),
        )

    def stop_monitor(self) -> None:
        """Disconnect form pyformance"""
        for key in self.registered_gauges:
            global_registry()._gauges.pop(key, None)

        self.registered_gauges.clear()

    async def get_connection_status(self) -> bool:
        try:
            async with get_connection_ctx_mgr() as conn:
                res = await conn.fetchval("SELECT 1;")
                return res == 1
        except Exception:
            LOGGER.exception("Connection to PostgreSQL failed")
        return False


class DatabaseService(protocol.ServerSlice):
    """Slice to initialize the database"""

    def __init__(self) -> None:
        super().__init__(SLICE_DATABASE)
        self._db_monitor: Optional[DatabaseMonitor] = None

    async def start(self) -> None:
        await super().start()
        await self.connect_database()

        max_overflow = opt.server_db_connection_pool_max_size.get() - opt.server_db_connection_pool_min_size.get()
        self._db_monitor = DatabaseMonitor(opt.db_name.get(), opt.db_host.get(), max_overflow)
        self._db_monitor.start()

    async def stop(self) -> None:
        await super().stop()
        if self._db_monitor is not None:
            await self._db_monitor.stop()
        await self.disconnect_database()

    def get_dependencies(self) -> list[str]:
        return []

    async def connect_database(self) -> None:
        """Connect to the database"""
        await initialize_sql_alchemy_engine(
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
        async with get_connection_ctx_mgr() as connection:
            # Check if JIT is enabled
            jit_available = await connection.fetchval("SELECT pg_jit_available();")
            if jit_available:
                LOGGER.warning("JIT is enabled in the PostgreSQL database. This might result in poor query performance.")

    async def disconnect_database(self) -> None:
        """Disconnect the database"""
        await stop_engine()

    async def get_status(self) -> Mapping[str, ArgumentTypes]:
        """Get the status of the database connection"""
        assert self._db_monitor is not None  # make mypy happy
        return (await self._db_monitor.get_status()).dict()


async def initialize_sql_alchemy_engine(
    database_host: str,
    database_port: int,
    database_name: str,
    database_username: str,
    database_password: str,
    create_db_schema: bool = False,
    connection_pool_min_size: int = 10,
    connection_pool_max_size: int = 10,
    connection_timeout: float = 60.0,
) -> None:
    """
    Initialize the sql alchemy engine for the current process and return it.

    :param database_host: Database host address.
    :param database_port: Port number to connect to at the server host.
    :param database_name: Name of the database to connect to.
    :param database_username: Username for database authentication.
    :param database_password: Password for database authentication.
    :param connection_pool_min_size: Initialize the pool with this number of connections .
    :param connection_pool_max_size: Limit the size of the pool to this number of connections .
    :param connection_timeout: Connection timeout (in seconds) when interacting with the database.
    """

    await start_engine(
        url=f"postgresql+asyncpg://{database_username}:{database_password}@{database_host}:{database_port}/{database_name}",
        pool_size=connection_pool_min_size,
        max_overflow=connection_pool_max_size - connection_pool_min_size,
        pool_timeout=connection_timeout,
        echo=True,
    )

    if create_db_schema:
        async with get_connection_ctx_mgr() as conn:
            await schema.DBSchema(CORE_SCHEMA_NAME, PACKAGE_WITH_UPDATE_FILES, conn).ensure_db_schema()
    LOGGER.info("Connected to PostgreSQL database %s on %s:%d", database_name, database_host, database_port)
