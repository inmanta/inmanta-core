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
from collections.abc import Coroutine
from types import ModuleType
from typing import Any, Callable, Optional

from asyncpg import Connection, UndefinedTableError
from asyncpg.protocol import Record

from inmanta import tracing

# Name of core schema in the DB schema verions
CORE_SCHEMA_NAME = "core"

LOGGER = logging.getLogger(__name__)

SCHEMA_VERSION_TABLE = "schemamanager"

create_schemamanager = """
-- Table: public.schemamanager
CREATE TABLE IF NOT EXISTS public.schemamanager (
    name varchar PRIMARY KEY,
    legacy_version integer,
    installed_versions integer[]
);
"""


class TableNotFound(Exception):
    """Raised when a table is not found in the database"""


class ColumnNotFound(Exception):
    """Raised when a column is not found in the database"""


class Version:
    """Internal representation of a version"""

    def __init__(self, name: str, function: Callable[[Connection], Coroutine[Any, Any, None]]):
        self.name = name
        self.function = function
        self.version = self.parse(name)

    @classmethod
    def parse(cls, name: str) -> int:
        return int(name[1:])


class DBSchema:
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

    @tracing.instrument("ensure_db_schema")
    async def ensure_db_schema(self) -> None:
        await self.ensure_self_update()
        await self._update_db_schema()

    async def ensure_self_update(self) -> None:
        """
        Ensures the table exists and is up to date with respect to the current schema.
        """
        self.logger.info("Creating schema version table")
        await self.connection.execute(create_schemamanager)

    async def _update_db_schema(self, update_functions: Optional[list[Version]] = None) -> None:
        """
        Main update function

        Wrapped in transaction, that holds a lock on the schemamanager table.
        When a version update fails, the whole transaction is rolled back.

        :param update_functions: allows overriding the available update functions, for example for testing purposes.
        """
        update_functions = (
            sorted(update_functions, key=lambda x: x.version) if update_functions is not None else self._get_update_functions()
        )
        async with self.connection.transaction():
            # get lock
            await self.connection.execute(f"LOCK TABLE {SCHEMA_VERSION_TABLE} IN ACCESS EXCLUSIVE MODE")
            # get current version again, in transaction this time
            try:
                installed_versions: set[int] = await self.get_installed_versions()
            except TableNotFound:
                self.logger.exception("Schemamanager table disappeared, should not occur.")
                raise
            # get relevant updates
            updates = [v for v in update_functions if v.version not in installed_versions]
            for version in updates:
                try:
                    # actual update sequence
                    self.logger.info("Updating database schema to version %d", version.version)
                    update_function = version.function
                    await update_function(self.connection)
                    await self.set_installed_version(version.version)
                    # inform asyncpg of the type change so it knows to refresh its caches
                    await self.connection.reload_schema_state()
                except Exception:
                    self.logger.exception(
                        "Database schema update for version %d failed. Rolling back all updates.",
                        version.version,
                    )
                    # propagate exception => roll back transaction
                    raise

    async def get_installed_versions(self) -> set[int]:
        """
        Returns the set of all versions that have been installed.

        :raises TableNotFound:
        """
        versions: Optional[Record] = None
        try:
            versions = await self.connection.fetchrow(
                f"select installed_versions from {SCHEMA_VERSION_TABLE} where name=$1", self.name
            )
        except UndefinedTableError as e:
            raise TableNotFound() from e
        if versions is None or versions["installed_versions"] is None:
            return set()
        return set(versions["installed_versions"])

    async def set_installed_version(self, version: int) -> None:
        """
        Adds a version to the installed versions column.
        """
        await self.connection.execute(
            f"""
            INSERT INTO {SCHEMA_VERSION_TABLE} (name, installed_versions)
            VALUES ($1, $2) ON CONFLICT (name) DO UPDATE
            SET installed_versions = {SCHEMA_VERSION_TABLE}.installed_versions || excluded.installed_versions
            """,
            self.name,
            {version},
        )

    def _get_update_functions(self) -> list[Version]:
        module_names = [modname for _, modname, ispkg in pkgutil.iter_modules(self.package.__path__) if not ispkg]

        def get_modules(mod_name: str) -> tuple[str, ModuleType]:
            fq_module_name = self.package.__name__ + "." + mod_name
            return mod_name, __import__(fq_module_name, fromlist=["update"])

        def make_version(mod_name: str, module: ModuleType) -> Version:
            update_function = module.update
            return Version(mod_name, update_function)

        def disabled(module: ModuleType) -> bool:
            try:
                return module.DISABLED
            except AttributeError:
                return False

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
        filtered_modules = [(module_name, module) for module_name, module in modules_with_names if not disabled(module)]

        version = [make_version(name, mod) for name, mod in filtered_modules]

        return sorted(version, key=lambda x: x.version)
