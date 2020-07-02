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
import pkgutil
import re
from types import ModuleType
from typing import Any, Callable, Coroutine, List, Optional, Tuple

from asyncpg import Connection, UndefinedTableError
from asyncpg.transaction import Transaction

# Name of core schema in the DB schema verions
CORE_SCHEMA_NAME = "core"

LOGGER = logging.getLogger(__name__)

LEGACY_SCHEMA_VERSION_TABLE = "schemaversion"
SCHEMA_VERSION_TABLE = "schemamanager"

create_schemamanager = """
-- Table: public.schemamanager
CREATE TABLE IF NOT EXISTS public.schemamanager (
    name varchar PRIMARY KEY,
    current_version integer NOT NULL
);
"""


class TableNotFound(Exception):
    """ Raised when a table is not found in the database """

    pass


class InvalidSchemaVersion(Exception):
    """ Raised when an invalid database version is found """

    pass


class Version(object):
    """ Internal representation of a version """

    def __init__(self, name: str, function: Callable[[Connection], Coroutine[Any, Any, None]]):
        self.name = name
        self.function = function
        self.version = self.parse(name)

    @classmethod
    def parse(cls, name: str) -> int:
        return int(name[1:])


class DBSchema(object):
    """
    Schema Manager, ensures the schema is up to date.

    Concurrent updates are safe
    """

    def __init__(self, name: str, package: ModuleType, connection: Connection) -> None:
        """

        :param name: unique name for this schema, best equal to extension name and used as prefix for all table names
        :param package: a python package, containing modules with name v%(version)s.py.
            Each module contains a method `async def update(connection: asyncpg.connection) -> None:`
        :param connection: asyncpg connection
        """
        self.name = name
        self.package = package
        self.connection = connection
        self.logger = LOGGER.getChild(f"schema:{self.name}")

    async def ensure_db_schema(self) -> None:
        current_version_db_schema = await self.ensure_self_update()
        update_functions = await self._get_update_functions()
        desired_version = update_functions[-1].version
        if desired_version > current_version_db_schema:
            await self._update_db_schema(update_functions)
        elif desired_version < current_version_db_schema:
            raise InvalidSchemaVersion(
                f"Desired database version {desired_version} is lower "
                f"than the current version {current_version_db_schema}, downgrading is not supported"
            )

    async def ensure_self_update(self) -> int:
        try:
            await self.get_legacy_version()
            await self._legacy_migration()
        except TableNotFound:
            # No legacy table, proceed
            pass

        try:
            return await self.get_current_version()
        except TableNotFound:
            self.logger.info("Creating schema version table")
            # create table
            await self.connection.execute(create_schemamanager)
            return 0

    async def _legacy_migration(self) -> None:
        """
        Migration to new schema management:
        1- as long as the legacy schemaversion table exists, no other operation is allowed by DBSchema
        2- takes a lock on the legacy schemaversion table to ensure exclusivity
        3- migrates the existing version to the new table, for the core slice
        4- drops legacy table
        """
        self.logger.info("Migrating from old schema management to new schema management")
        # tx begin
        async with self.connection.transaction():
            # lock legacy table => if gone -> continue
            try:
                await self.connection.execute(f"LOCK TABLE {LEGACY_SCHEMA_VERSION_TABLE} IN ACCESS EXCLUSIVE MODE")
            except UndefinedTableError:
                self.logger.info("Second process is preforming a database update as well.")
                return
            # get_legacy_version, under lock
            legacy_version_db_schema = await self.get_legacy_version()

            if legacy_version_db_schema > 0:
                self.logger.info("Creating schema version table and setting core version to %d", legacy_version_db_schema)
                # create table
                await self.connection.execute(create_schemamanager)
                await self.connection.execute(
                    f"INSERT INTO {SCHEMA_VERSION_TABLE}(name, current_version) VALUES ($1, $2)",
                    CORE_SCHEMA_NAME,
                    legacy_version_db_schema,
                )
            else:
                self.logger.info("Creating schema version table")
                # create table
                await self.connection.execute(create_schemamanager)

            await self.connection.execute(f"DROP TABLE {LEGACY_SCHEMA_VERSION_TABLE}")

    async def _update_db_schema(self, update_functions: List[Version]) -> None:
        """
        Main update function

        Wrapped in outer transaction, that holds a lock on the schemamanager table.
        Each version update is wrapped in a subtransaction.

        When a subtransaction fails, it is rolled back.
        The outer transaction is committed at that point.

        This logic requires manual transaction management,
        as the exception is propagated over the transaction boundary without causing rollback.
        """
        # outer transaction
        outer: Optional[Transaction]
        outer = self.connection.transaction()
        try:
            # enter transaction
            await outer.start()
            # get lock
            await self.connection.execute(f"LOCK TABLE {SCHEMA_VERSION_TABLE} IN ACCESS EXCLUSIVE MODE")
            # get current version again, in transaction this time
            try:
                sure_db_schema = await self.get_current_version()
            except TableNotFound:
                self.logger.exception("Schemamanager table disappeared, should not occur.")
                raise
            # get relevant updates
            updates = [v for v in update_functions if v.version > sure_db_schema]
            for version in updates:
                try:
                    # wrap in subtransaction
                    async with self.connection.transaction():
                        # actual update sequence
                        self.logger.info("Updating database schema to version %d", version.version)
                        update_function = version.function
                        await update_function(self.connection)
                        # also set version, outer tx will always contain consistent version
                        await self.set_current_version(version.version)
                    # commit subtx
                except Exception:
                    # update failed, subtransaction already rolled back
                    self.logger.exception("Database schema update to version %d failed", version.version)
                    # commit outer
                    await outer.commit()
                    # unset it, to prevent double commit
                    outer = None
                    # propagate excn
                    raise
        except Exception:
            # an exception, from either outer transaction (before subtransaction) or subtransaction
            if outer is not None:
                # subtransaction did not set None, so abort
                await outer.rollback()
                outer = None
            raise
        finally:
            # if the tx is still there, all is good
            if outer is not None:
                await outer.commit()

    async def get_legacy_version(self) -> int:
        try:
            version = await self.connection.fetchrow(f"select current_version from {LEGACY_SCHEMA_VERSION_TABLE}")
        except UndefinedTableError as e:
            raise TableNotFound() from e
        if version is None:
            return 0
        return version["current_version"]

    async def get_current_version(self) -> int:
        try:
            version = await self.connection.fetchrow(
                f"select current_version from {SCHEMA_VERSION_TABLE} where name=$1", self.name
            )
        except UndefinedTableError as e:
            raise TableNotFound() from e
        if version is None:
            return 0
        return version["current_version"]

    async def set_current_version(self, version: int) -> None:
        await self.connection.execute(
            f"INSERT INTO {SCHEMA_VERSION_TABLE}(name, current_version) "
            "VALUES ($1, $2) ON CONFLICT(name) DO UPDATE SET current_version=$2",
            self.name,
            version,
        )

    async def _get_update_functions(self) -> List[Version]:
        module_names = [modname for _, modname, ispkg in pkgutil.iter_modules(self.package.__path__) if not ispkg]

        def get_modules(mod_name: str) -> Tuple[str, ModuleType]:
            fq_module_name = self.package.__name__ + "." + mod_name
            return mod_name, __import__(fq_module_name, fromlist=["update"])

        def make_version(mod_name: str, module: ModuleType) -> Version:
            update_function = module.update
            return Version(mod_name, update_function)

        pattern = re.compile("^v[0-9]+$")

        filtered_module_names = []
        for module_name in module_names:
            if not pattern.match(module_name):
                LOGGER.warning(
                    f"Database schema version file name {module_name} "
                    f"doesn't match the expected pattern: v<version_number>.py, skipping it"
                )
            else:
                filtered_module_names.append(module_name)

        modules_with_names = [get_modules(mod_name) for mod_name in filtered_module_names]
        filtered_modules = [(module_name, module) for module_name, module in modules_with_names if not module.DISABLED]

        version = [make_version(name, mod) for name, mod in filtered_modules]

        return sorted(version, key=lambda x: x.version)
