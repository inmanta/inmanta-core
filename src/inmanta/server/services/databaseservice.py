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

import asyncpg

from inmanta import data
from inmanta.data.model import DataBaseReport, ReportedStatus
from inmanta.server import SLICE_DATABASE
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.types import ArgumentTypes
from inmanta.util import IntervalSchedule, Scheduler
from inmanta.vendor.pyformance import gauge, global_registry
from inmanta.vendor.pyformance.meters.gauge import AnyGauge, CallbackGauge

LOGGER = logging.getLogger(__name__)


class DatabaseMonitor:

    def __init__(
        self,
        pool: asyncpg.pool.Pool,
        db_name: str,
        db_host: str,
    ) -> None:
        self._pool = pool
        self._scheduler = Scheduler(f"Database monitor for {db_name}")
        self.dn_name = db_name
        self.db_host = db_host
        self.registered_gauges: list[str] = []
        self._db_exhaustion_check_interval = 0.2
        self._exhausted_pool_events_count: int = 0
        self._last_report: int = 0

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
        pool_exhausted: bool = (self._pool.get_size() == self._pool.get_max_size()) and self._pool.get_idle_size() == 0
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

        return DataBaseReport(
            connected=connected,
            database=self.dn_name,
            host=self.db_host,
            max_pool=self._pool.get_max_size(),
            free_pool=self.get_pool_free(),
            open_connections=self._pool.get_size(),
            free_connections=self._pool.get_idle_size(),
            pool_exhaustion_time=self._exhausted_pool_events_count * self._db_exhaustion_check_interval,
        )

    def get_pool_free(self) -> int:
        if self._pool is None or self._pool._closing:
            return 0
        return self._pool.get_max_size() - self._pool.get_size() + self._pool.get_idle_size()

    def _add_gauge(self, name: str, the_gauge: AnyGauge) -> None:
        """Helper to register gauges and keep track of registrations"""
        gauge(name, the_gauge)
        self.registered_gauges.append(name)

    def start_monitor(self) -> None:
        """Attach to monitoring system"""

        self._add_gauge(
            "db.connected",
            CallbackGauge(
                callback=lambda: 1 if (self._pool is not None and not self._pool._closing and not self._pool._closed) else 0
            ),
        )
        self._add_gauge(
            "db.max_pool", CallbackGauge(callback=lambda: self._pool.get_max_size() if self._pool is not None else 0)
        )
        self._add_gauge(
            "db.open_connections",
            CallbackGauge(callback=lambda: self._pool.get_size() if self._pool is not None else 0),
        )
        self._add_gauge(
            "db.free_connections",
            CallbackGauge(callback=lambda: self._pool.get_idle_size() if self._pool is not None else 0),
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
        if self._pool is not None and not self._pool._closing and not self._pool._closed:
            try:
                async with self._pool.acquire(timeout=10):
                    return True
            except Exception:
                LOGGER.exception("Connection to PostgreSQL failed")
        return False


class DatabaseService(protocol.ServerSlice):
    """Slice to initialize the database"""

    def __init__(self) -> None:
        super().__init__(SLICE_DATABASE)
        self._pool: Optional[asyncpg.pool.Pool] = None
        self._db_monitor: Optional[DatabaseMonitor] = None

    async def start(self) -> None:
        await super().start()
        await self.connect_database()

        assert self._pool is not None  # Make mypy happy
        self._db_monitor = DatabaseMonitor(self._pool, opt.db_name.get(), opt.db_host.get())
        self._db_monitor.start()

    async def stop(self) -> None:
        await super().stop()
        if self._db_monitor is not None:
            await self._db_monitor.stop()
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

    async def get_reported_status(self) -> tuple[ReportedStatus, Optional[str]]:
        """
        Returns the reported status of this slice:
            - Error: Not Connected
            - Warning: The pool has less than 5 connections or 10% of the max pool size
            - OK: Otherwise
        """

        try:
            assert self._db_monitor
            status = await self._db_monitor.get_status()
            assert status.connected
        except Exception:
            return ReportedStatus.Error, "Database is not connected"

        if status.free_pool < min(5, status.max_pool // 10):
            return ReportedStatus.Warning, f"Only {status.free_pool} connections left in the pool."

        return ReportedStatus.OK, None

    async def get_status(self) -> Mapping[str, ArgumentTypes]:
        """Get the status of the database connection"""
        assert self._db_monitor is not None  # make mypy happy
        return (await self._db_monitor.get_status()).model_dump(mode="json")

    async def get_postgresql_version(self) -> str | None:
        """Get the Postgres version of the database connection.
        Return None if the database is not connected"""
        if self._db_monitor is None or self._pool is None:
            return None
        status = await self._db_monitor.get_status()
        if not status.connected:
            return None
        async with self._pool.acquire() as connection:
            return await connection.fetchval("SHOW server_version;")


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
