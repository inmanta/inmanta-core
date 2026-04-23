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

import asyncio
import json
import logging
import os.path
from functools import total_ordering
from typing import Mapping, Optional

import asyncpg

from inmanta.data import start_engine, stop_engine
from inmanta.data.model import DataBaseReport, ReportedStatus
from inmanta.server import SLICE_DATABASE
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.protocol import ServerStartFailure
from inmanta.types import ArgumentTypes
from inmanta.util import IntervalSchedule, Scheduler
from inmanta.vendor.pyformance import gauge, global_registry
from inmanta.vendor.pyformance.meters.gauge import AnyGauge, CallbackGauge
from packaging import version

LOGGER = logging.getLogger(__name__)


@total_ordering
class PostgreSQLVersion:
    def __init__(self, version: int):
        """
        :param version: This method expects the machine-readable version as defined in
            https://www.postgresql.org/docs/current/libpq-status.html#LIBPQ-PQSERVERVERSION.
            e.g. "v17.6" should be passed as 170006
        """

        self.version = version

    @classmethod
    async def from_database(cls, conn: asyncpg.Connection) -> "PostgreSQLVersion":
        """
        Helper method to retrieve the postgreSQL version used in the database. This method queries
        the database by using the conn parameter. The caller is responsible for closing this
        connection.
        """
        result = await conn.fetch("SHOW server_version_num")
        pg_server_version_machine_readable = int(result[0]["server_version_num"])

        return PostgreSQLVersion(version=pg_server_version_machine_readable)

    @classmethod
    def from_compatibility_file(cls) -> "PostgreSQLVersion | None":
        """
        Helper method to retrieve the minimal required postgreSQL version configured under the
        system_requirements->postgres_version section of the compatibility file. Returns None
        if the server.compatibility_file option is set to None or to empty string.

        :raises ServerStartFailure: If the compatibility file doesn't exist.
        :raises ServerStartFailure: If the 'system_requirements->postgres_version' section is not present
            in the compatibility file.
        """
        compatibility_data = {}
        compatibility_file: str | None = opt.server_compatibility_file.get()
        if not compatibility_file:
            # Bypass the check if compatibility_file is None or ""
            return None

        if not os.path.exists(compatibility_file):
            raise protocol.ServerStartFailure("The configured compatibility file doesn't exist: %s" % compatibility_file)

        with open(compatibility_file) as fh:
            compatibility_data = json.load(fh)

        required_version: int | None = compatibility_data.get("system_requirements", {}).get("postgres_version")
        if required_version is None:
            raise protocol.ServerStartFailure(
                "Invalid compatibility file schema. Missing 'system_requirements.postgres_version' section in file: %s"
                % compatibility_file
            )
        human_readable_version = version.Version(str(required_version))
        machine_readable_version = human_readable_version.major * 10_000 + human_readable_version.minor

        return PostgreSQLVersion(version=machine_readable_version)

    def __lt__(self, other: "PostgreSQLVersion") -> bool:
        return self.version < other.version

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PostgreSQLVersion):
            return self.version == other.version
        return False

    def __str__(self) -> str:
        """
        Returns the human readable version of this PostgreSQLVersion.
        """
        major = self.version // 10_000
        minor = self.version - major * 10_000
        return f"{major}.{minor}"


class DatabaseMonitor:

    def __init__(
        self,
        pool: asyncpg.pool.Pool,
        db_name: str,
        db_host: str,
    ) -> None:
        if pool.is_closing():
            raise Exception("Connection pool is closing or closed.")
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
        if self._pool is None or self._pool.is_closing():
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
            CallbackGauge(callback=lambda: 1 if (self._pool is not None and not self._pool.is_closing()) else 0),
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
        if self._pool is not None and not self._pool.is_closing():
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
        database_status_checker = DatabaseStatusChecker()
        await database_status_checker.check_database_before_server_start()
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
            # Check if JIT is enabled
            jit_available = await connection.fetchval("SELECT pg_jit_available();")
            if jit_available:
                LOGGER.warning("JIT is enabled in the PostgreSQL database. This might result in poor query performance.")

    async def disconnect_database(self) -> None:
        """Disconnect the database"""
        await stop_engine()
        self._pool = None

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
    create_db_schema: bool = False,
    connection_pool_min_size: int = 10,
    connection_pool_max_size: int = 10,
    connection_timeout: float = 60.0,
) -> asyncpg.pool.Pool:
    """
    Initialize the sql alchemy engine for the current process and return the underlying
    asyncpg database connection pool.

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

    pool = await start_engine(
        database_username=database_username,
        database_password=database_password,
        database_host=database_host,
        database_port=database_port,
        database_name=database_name,
        create_db_schema=create_db_schema,
        connection_pool_min_size=connection_pool_min_size,
        connection_pool_max_size=connection_pool_max_size,
        connection_timeout=connection_timeout,
    )

    LOGGER.info("Connected to PostgreSQL database %s on %s:%d", database_name, database_host, database_port)
    return pool


class DatabaseStatusChecker:

    async def check_database_before_server_start(self) -> None:
        """
        Ensure database connectivity before starting the server and log information about the DB server
        e.g. the PostgreSQL version of the db server and the status of the standby servers.

        This method will check that the PostgreSQL version of the db server meets the required version if such a minimal
        required postgres version is configured under system_requirements->postgres_version in the compatibility file
        (server.compatibility_file option).

        These checks are performed before starting any slice e.g. to bail before any database migration is attempted
        in case an incompatible PostgreSQL version is detected.
        """
        conn: asyncpg.Connection | None = None
        try:
            conn = await self._database_connectivity_check()
            await self._database_version_compatibility_check(conn)
            await self._log_database_replication_status(conn)
        finally:
            if conn is not None:
                await conn.close(timeout=5)  # close the connection

        LOGGER.info("Successfully checked database before server start.")

    async def _get_db_connection(self) -> asyncpg.Connection:
        # Retrieve database connection settings from the configuration
        db_settings = {
            "host": opt.db_host.get(),
            "port": opt.db_port.get(),
            "user": opt.db_username.get(),
            "password": opt.db_password.get(),
            "database": opt.db_name.get(),
        }

        # Attempt to create a database connection
        return await asyncpg.connect(**db_settings, timeout=5)  # raises TimeoutError after 5 seconds

    async def _wait_for_db(self, db_wait_time: int) -> asyncpg.Connection:
        """Wait for the database to be up by attempting to connect at intervals. Once a connection
        is established, it is returned. The caller is responsible for closing it.

        :param db_wait_time: Maximum time to wait for the database to be up, in seconds.
        """

        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                LOGGER.info(
                    "Trying to establish a connection to database '%s' at %s:%s.",
                    opt.db_name.get(),
                    opt.db_host.get(),
                    opt.db_port.get(),
                )
                # Attempt to create a database connection
                conn = await self._get_db_connection()
                LOGGER.info(
                    "Successfully reached database '%s' at %s:%s.",
                    opt.db_name.get(),
                    opt.db_host.get(),
                    opt.db_port.get(),
                )
                return conn
            except TimeoutError:
                LOGGER.info("Waiting for database to be up: Connection attempt timed out.")
            except Exception:
                LOGGER.info("Waiting for database to be up.", exc_info=True)
            # Check if the maximum wait time has been exceeded
            if 0 < db_wait_time < asyncio.get_event_loop().time() - start_time:
                LOGGER.error("Timeout: database server not up after %d seconds." % db_wait_time)
                raise ServerStartFailure("Timeout: database server not up after %d seconds." % db_wait_time)
            # Sleep for a second before retrying
            await asyncio.sleep(1)

    async def _database_connectivity_check(self) -> asyncpg.Connection:
        """
        This method attempts to connect to the database and returns the connection object.
        The caller is reponsible for closing the connection.

        The database.wait_time option controls the retry behaviour for this method:
            database.wait_time < 0 : keep retrying forever until a connection is established
            database.wait_time = 0 : try only once to establish a connection
            database.wait_time > 0 : keep retrying until this wait_time timeout is reached or a connection is established

        :raises Exception: If the connectivity cannot be established within the configured database.wait_time.
        """
        db_wait_time: int = opt.db_wait_time.get()

        if db_wait_time != 0:
            # Wait for the database to be up before starting the server
            LOGGER.info("Waiting until database server is up.")
            conn = await self._wait_for_db(db_wait_time=db_wait_time)
        else:
            LOGGER.debug("Not waiting until the database server is up because database.wait_time option is set to 0.")
            conn = await self._get_db_connection()
        return conn

    async def _database_version_compatibility_check(self, conn: asyncpg.Connection) -> None:
        """
        This method looks for the required PostgreSQL version defined in the compatibility file (Whose path is configured by
        the server.compatibility_file option) and checks that the PostgreSQL version of the database meets this requirement.

        The check is bypassed if the server_compatibility_file option is set to None or to an empty string.

        :param conn: the connection to use to query the db
        :raises ServerStartFailure: If the compatibility file doesn't exist or its schema is missing the
            `system_requirements->postgres_version` section.
        :raises ServerStartFailure: If the database version is lower than the required version defined in
            the compatibility file.
        """
        required_postgresql_version = PostgreSQLVersion.from_compatibility_file()
        database_postgresql_version = await PostgreSQLVersion.from_database(conn)

        if required_postgresql_version is None:
            LOGGER.debug(
                "Bypassing minimal required postgres version check because the "
                "'server.compatibility_file' option is not set."
            )
        else:
            if database_postgresql_version < required_postgresql_version:
                raise protocol.ServerStartFailure(
                    f"The database at {opt.db_host.get()} is using PostgreSQL version "
                    f"{database_postgresql_version}. This version is not supported by this "
                    "version of the Inmanta orchestrator. Please make sure to update to PostgreSQL "
                    f"{required_postgresql_version}."
                )
        LOGGER.info("Database is running PostgreSQL server version %s.", database_postgresql_version)

    async def _log_database_replication_status(self, conn: asyncpg.Connection) -> None:
        """
        Fetch and log the replication status. This method relies on the pg_stat_replication that holds information
        about the standby servers, i.e. one row per replica. More info in the postgresql docs:
        https://www.postgresql.org/docs/16/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW

        :param conn: the connection to use to query the db
        """
        query = """
        SELECT
            pid,                    -- pid of the WAL (Write Ahead Log) sender process
            client_addr,            -- IP of the replica connected to this sender
            client_port,            -- Port used by the replica to communicate with this sender
            state,                  -- WAL sender status
            sync_state,             -- State of the replica
            sent_lsn,               -- Last WAL LSN (Log Sequence Number) sent on this connection
            write_lsn,              -- Last WAL LSN written to disk on the replica
            flush_lsn,              -- Last WAL LSN flushed to disk on the replica
            replay_lsn,             -- Last WAL LSN replayed into the database on the replica
            pg_wal_lsn_diff(sent_lsn, replay_lsn) AS replay_lag_bytes
                                    -- This diff represents how far behind this replica lags.
        FROM pg_stat_replication;
        """
        result = await conn.fetch(query)
        if result:
            if result[0]["client_port"] is None:
                # If a user that doesn't hold the 'pg_monitor' role tries to query the pg_stat_replication table, no error
                # is raised, but instead a 'censored' view is returned with most values filled with NULL.
                # If the returned value for the port is None, we assume that the user has insufficient privileges, since it
                # shouldn't be None (As per the docs: "TCP port number that the client is using for communication with this
                # WAL sender, or -1 if a Unix socket is used").
                LOGGER.warning(
                    "Cannot check database replication status: insufficient privileges for user %s. Please "
                    "make sure the configured user has the `pg_monitor` role.",
                    opt.db_username.get(),
                )
            else:
                LOGGER.info(
                    "Database replication status (Only the directly connected standby servers "
                    "will appear below: downstream standby servers or nodes that are down won't appear.)"
                )
                for row in result:
                    LOGGER.info(
                        "Replica (ip=%s port=%s sync_state=%s) - "
                        "Sender process (pid=%s, state=%s) - "
                        "Log Sequence Numbers (sent=%s write=%s flush=%s replay=%s diff_send_replay=%s)",
                        row["client_addr"],
                        row["client_port"],
                        row["sync_state"],
                        row["pid"],
                        row["state"],
                        row["sent_lsn"],
                        row["write_lsn"],
                        row["flush_lsn"],
                        row["replay_lsn"],
                        row["replay_lag_bytes"],
                    )
        else:
            LOGGER.info(
                "Database replication is not active: couldn't find any standby server directly connected to the primary. "
                "If you intend to use database replication, please check the status and the configuration "
                "of the cluster before restarting the Inmanta server (More info in the 'HA setup' section of the "
                "documentation)."
            )

        LOGGER.info("Checking database before server start...")
