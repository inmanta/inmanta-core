import logging
import pkgutil
from types import ModuleType
from typing import List, Optional

import asyncpg
from asyncpg import UndefinedTableError

LOGGER = logging.getLogger(__name__)

LEGACY_SCHEMA_VERSION_TABLE = "schemaversion"
SCHEMA_VERSION_TABLE = "schemamanager"

# no version table found
VERSION_NONE = None
# Legacy version table is present but empty (unlikely)
VERSION_LEGACY = 0

CORE_NAME = "core"

create_schemamanager = """
-- Table: public.schemaversion
CREATE TABLE IF NOT EXISTS public.schemamanager (
    name varchar PRIMARY KEY,
    current_version integer NOT NULL
);
"""


class Version(object):
    """ Internal representation of a version """

    def __init__(self, name, function):
        self.name = name
        self.function = function
        self.version = self.parse(name)

    @classmethod
    def parse(cls, name: str) -> int:
        return int(name[1:])


class DBSchema(object):
    """
    Schema Manager, ensures the schema is up to date,
    """

    def __init__(self, name: str, package: ModuleType, connection: asyncpg.Connection) -> None:
        self.name = name
        self.package = package
        self.connection = connection

    async def legacy_migration(self):
        LOGGER.info("Migrating from old schema management to new schema management")
        # tx begin
        async with self.connection.transaction():
            # lock legacy table => if gone -> continue
            try:
                await self.connection.execute(f"LOCK TABLE {LEGACY_SCHEMA_VERSION_TABLE} IN ACCESS EXCLUSIVE MODE")
            except UndefinedTableError:
                LOGGER.info("Second process is preforming a database update as well.")
                return
            # get_legacy_version
            legacy_version_db_schema = await self.get_legacy_version()

            if legacy_version_db_schema > 0:
                LOGGER.info("Creating schema version table and setting core version to %d", legacy_version_db_schema)
                # create table
                await self.connection.execute(create_schemamanager)
                await self.connection.execute(
                    f"INSERT INTO {SCHEMA_VERSION_TABLE}(name, current_version) VALUES ($1, $2)",
                    CORE_NAME,
                    legacy_version_db_schema,
                )
            else:
                LOGGER.info("Creating schema version table")
                # create table
                await self.connection.execute(create_schemamanager)

            await self.connection.execute(f"DROP TABLE {LEGACY_SCHEMA_VERSION_TABLE}")

    async def ensure_self_update(self) -> int:
        legacy_version_db_schema = await self.get_legacy_version()
        if legacy_version_db_schema is not None:
            await self.legacy_migration()
        current_version_db_schema = await self.get_current_version()

        if current_version_db_schema is None:
            LOGGER.info("Creating schema version table")
            # create table
            await self.connection.execute(create_schemamanager)
            return 0
        return current_version_db_schema

    async def ensure_db_schema(self) -> None:
        current_version_db_schema = await self.ensure_self_update()
        update_functions = await self._get_update_functions()
        if update_functions[-1].version > current_version_db_schema:
            await self._update_db_schema(update_functions)

    async def _update_db_schema(self, update_functions: List[Version]) -> None:
        outer = self.connection.transaction()
        try:
            await outer.start()
            await self.connection.execute(f"LOCK TABLE {SCHEMA_VERSION_TABLE} IN ACCESS EXCLUSIVE MODE")
            sure_db_schema = await self.get_current_version()
            if sure_db_schema is None:
                sure_db_schema = 0
            updates = [v for v in update_functions if v.version > sure_db_schema]
            for version in updates:
                try:
                    async with self.connection.transaction():
                        LOGGER.info("Updating database schema to version %d", version.version)
                        update_function = version.function
                        await update_function(self.connection)
                        await self.set_current_version(version.version)
                except Exception:
                    LOGGER.exception("Database schema update to version %d failed", version.version)
                    await outer.commit()
                    outer = None
                    raise
        except Exception:
            if outer is not None:
                await outer.rollback()
                outer = None
            raise
        finally:
            if outer is not None:
                await outer.commit()

    async def get_legacy_version(self) -> Optional[int]:
        try:
            version = await self.connection.fetchrow(f"select current_version from {LEGACY_SCHEMA_VERSION_TABLE}")
        except UndefinedTableError:
            return None
        if version is None:
            return VERSION_LEGACY
        return version["current_version"]

    async def get_current_version(self) -> Optional[int]:
        try:
            version = await self.connection.fetchrow(
                f"select current_version from {SCHEMA_VERSION_TABLE} where name=$1", self.name
            )
        except UndefinedTableError:
            return None
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

        def make_version(mod_name):
            fq_module_name = self.package.__name__ + "." + mod_name
            module = __import__(fq_module_name, fromlist=("update"))
            update_function = module.update
            return Version(mod_name, update_function)

        version = [make_version(v) for v in module_names]

        return sorted(version, key=lambda x: x.version)
