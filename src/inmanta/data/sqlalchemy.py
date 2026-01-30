"""
Copyright 2025 Inmanta
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

import datetime
import uuid
from typing import Any, Optional

import asyncpg

from inmanta.data.model import AgentName
from inmanta.data.model import InmantaModule as InmantaModuleDTO
from inmanta.data.model import InmantaModuleName, InmantaModuleVersion
from inmanta.deploy import state
from sqlalchemy import (
    ARRAY,
    Boolean,
    Case,
    Column,
    DateTime,
    Double,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    and_,
    case,
    or_,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, foreign, mapped_column, relationship

# This file is mostly generated code (generated with sqlacodegen),
# but it suffered some modifications, keep that in mind if you were to regenerate it
# Currently, these models don't offer any additional validation, besides typing, so it's best to avoid inserting/modifying
# DB entries directly using these models.


class Base(DeclarativeBase):

    @classmethod
    async def delete_all(cls, environment: uuid.UUID, connection: asyncpg.connection.Connection) -> None:
        await connection.execute("DELETE FROM %s WHERE environment=$1" % cls.__tablename__, environment)


class InmantaModule(Base):
    __tablename__ = "inmanta_module"

    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="inmanta_module_environment_fkey"),
        PrimaryKeyConstraint("environment", "name", "version", name="inmanta_module_pkey"),
    )

    name: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[str] = mapped_column(String, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    requirements: Mapped[list[str]] = mapped_column(
        ARRAY(String()), nullable=False, server_default=text("ARRAY[]::character varying[]")
    )

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="inmanta_module", viewonly=True)
    module_files: Mapped[list["ModuleFiles"]] = relationship("ModuleFiles", back_populates="inmanta_module", viewonly=True)
    agent_modules: Mapped[list["AgentModules"]] = relationship("AgentModules", back_populates="inmanta_module", viewonly=True)

    @classmethod
    async def register_modules(
        cls, environment: uuid.UUID, modules: dict[InmantaModuleName, InmantaModuleDTO], connection: asyncpg.Connection
    ) -> None:
        """
        This is the first phase of code registration:
        For all provided modules, this method will write to the database:
            - the version being registered for this module. (This is a hash derived from
                the content of the files in this module and its requirements)
            - which files belong to this module for this version.

        Any attempt to register a module or file again is silently ignored.

        The second phase takes place in the AgentModules.register_modules_for_agents method
        where we register which agents require which module version for a given model
        version.

        :param environment: The environment for which to register inmanta modules.
        :param modules: Map of module name to inmanta module data.
        :param connection: The asyncpg connection to use.
        """

        insert_modules_query = f"""
            INSERT INTO {InmantaModule.__tablename__}(
                name,
                version,
                environment,
                requirements
            ) VALUES(
                $1,
                $2,
                $3,
                $4
            )
            ON CONFLICT DO NOTHING;
        """

        insert_files_query = f"""
            INSERT INTO {ModuleFiles.__tablename__}(
                inmanta_module_name,
                inmanta_module_version,
                environment,
                file_content_hash,
                python_module_name,
                is_byte_code
            ) VALUES(
                $1,
                $2,
                $3,
                $4,
                $5,
                $6
            )
            ON CONFLICT DO NOTHING;
        """
        async with connection.transaction():
            await connection.executemany(
                insert_modules_query,
                [
                    (
                        inmanta_module_name,
                        inmanta_module_data.version,
                        environment,
                        inmanta_module_data.requirements,
                    )
                    for inmanta_module_name, inmanta_module_data in modules.items()
                ],
            )
            await connection.executemany(
                insert_files_query,
                [
                    (
                        inmanta_module_name,
                        inmanta_module_data.version,
                        environment,
                        file.hash_value,
                        file.name,
                        file.is_byte_code,
                    )
                    for inmanta_module_name, inmanta_module_data in modules.items()
                    for file in inmanta_module_data.files_in_module
                ],
            )

    @classmethod
    async def delete_version(
        cls, environment: uuid.UUID, model_version: int, connection: asyncpg.connection.Connection
    ) -> None:
        await connection.execute(
            f"""
            DELETE FROM {InmantaModule.__tablename__}
            WHERE (environment, name, version) IN (
                SELECT environment, inmanta_module_name, inmanta_module_version
                FROM public.agent_modules
                WHERE environment=$1
                AND cm_version=$2
            )
            """,
            environment,
            model_version,
        )


class ModuleFiles(Base):
    __tablename__ = "module_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "inmanta_module_name", "inmanta_module_version"],
            ["inmanta_module.environment", "inmanta_module.name", "inmanta_module.version"],
            ondelete="CASCADE",
            name="module_files_environment_inmanta_module_name_inmanta_modul_fkey",
        ),
        ForeignKeyConstraint(
            ["file_content_hash"], ["file.content_hash"], ondelete="RESTRICT", name="module_files_file_content_hash_fkey"
        ),
        PrimaryKeyConstraint(
            "environment", "inmanta_module_name", "inmanta_module_version", "python_module_name", name="module_files_pkey"
        ),
    )

    inmanta_module_name: Mapped[str] = mapped_column(String, primary_key=True)
    inmanta_module_version: Mapped[str] = mapped_column(String, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    file_content_hash: Mapped[str] = mapped_column(String, nullable=False)
    python_module_name: Mapped[str] = mapped_column(String, primary_key=True)
    is_byte_code: Mapped[bool] = mapped_column(Boolean, nullable=False)

    inmanta_module: Mapped["InmantaModule"] = relationship("InmantaModule", back_populates="module_files")
    file: Mapped["File"] = relationship("File", back_populates="module_files")

    @classmethod
    async def delete_version(
        cls, environment: uuid.UUID, model_version: int, connection: asyncpg.connection.Connection
    ) -> None:
        await connection.execute(
            f"""
            DELETE FROM {ModuleFiles.__tablename__}
            WHERE (environment, inmanta_module_name, inmanta_module_version) IN (
                SELECT environment, inmanta_module_name, inmanta_module_version
                FROM {AgentModules.__tablename__}
                WHERE environment=$1
                AND cm_version=$2
            )
            """,
            environment,
            model_version,
        )


class AgentModules(Base):
    __tablename__ = "agent_modules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "agent_name"],
            ["agent.environment", "agent.name"],
            ondelete="CASCADE",
            name="agent_modules_environment_agent_name_fkey",
        ),
        ForeignKeyConstraint(
            ["environment", "cm_version"],
            ["configurationmodel.environment", "configurationmodel.version"],
            ondelete="CASCADE",
            name="agent_modules_environment_cm_version_fkey",
        ),
        ForeignKeyConstraint(
            ["environment", "inmanta_module_name", "inmanta_module_version"],
            ["inmanta_module.environment", "inmanta_module.name", "inmanta_module.version"],
            ondelete="RESTRICT",
            name="agent_modules_environment_inmanta_module_name_inmanta_modu_fkey",
        ),
        PrimaryKeyConstraint("environment", "cm_version", "agent_name", "inmanta_module_name", name="agent_modules_pkey"),
        Index("agent_modules_environment_agent_name_index", "environment", "agent_name"),
        Index(
            "agent_modules_environment_module_name_module_version_index",
            "environment",
            "inmanta_module_name",
            "inmanta_module_version",
        ),
    )

    cm_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_name: Mapped[str] = mapped_column(String, primary_key=True)
    inmanta_module_name: Mapped[str] = mapped_column(String, primary_key=True)
    inmanta_module_version: Mapped[str] = mapped_column(String, nullable=False)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="agent_modules", viewonly=True)
    configurationmodel: Mapped["Configurationmodel"] = relationship(
        "Configurationmodel", back_populates="agent_modules", viewonly=True
    )
    inmanta_module: Mapped["InmantaModule"] = relationship("InmantaModule", back_populates="agent_modules")

    @classmethod
    async def get_registered_modules_data(
        cls, model_version: int, environment: uuid.UUID, connection: asyncpg.Connection
    ) -> dict[InmantaModuleName, tuple[InmantaModuleVersion, set[AgentName]]]:
        """
        Retrieve all registered modules for a given model version.
        For each module, return the registered version as well as the set of agents registered
        for using it.

        This method is meant to be used in a context where we want to use an already open
        asyncpg connection.

        :param model_version: The model version for which to retrieve registered module data.
        :param environment: The environment for which to retrieve registered module data.
        :param connection: The asyncpg connection to use.
        :return: A dict with keys module name and values a tuple of:
            - the version for this module in this model version.
            - the set of agents registered for this module in this model version.
        """
        query = f"""
            SELECT
                agent_name,
                inmanta_module_name,
                inmanta_module_version
            FROM
                {AgentModules.__tablename__}
            WHERE
                cm_version=$1
            AND
                environment=$2
         """
        async with connection.transaction():
            values = [model_version, environment]
            module_usage_info: dict[InmantaModuleName, tuple[InmantaModuleVersion, set[AgentName]]] = {}

            async for record in connection.cursor(query, *values):
                if record["inmanta_module_name"] in module_usage_info:
                    if record["inmanta_module_version"] != module_usage_info[str(record["inmanta_module_name"])][0]:
                        # Should never happen
                        raise Exception(
                            f"Inconsistent database state for model version {model_version}. A single version is expected "
                            f"per inmanta module. At least the two following versions are registered for module "
                            f"{record["inmanta_module_name"]}: [{record["inmanta_module_version"]}, "
                            f"{module_usage_info[str(record["inmanta_module_name"])][0]}]"
                        )
                    else:
                        module_usage_info[str(record["inmanta_module_name"])][1].add(str(record["agent_name"]))
                else:
                    module_usage_info[str(record["inmanta_module_name"])] = (
                        str(record["inmanta_module_version"]),
                        {str(record["agent_name"])},
                    )

            return module_usage_info

    @classmethod
    async def register_modules_for_agents(
        cls,
        model_version: int,
        environment: uuid.UUID,
        module_usage_info: dict[InmantaModuleName, tuple[InmantaModuleVersion, set[AgentName]]],
        connection: asyncpg.Connection,
    ) -> None:
        """
        This is phase 2 of code registration. This method is expected to be called after the
        InmantaModule.register_modules method that takes care of phase 1.

        For a given model version, register which agents use which modules.

        This method is meant to be used in a context where we want to use an already open
        asyncpg connection.

        :param model_version: The model version for which to register modules per agent.
        :param module_usage_info: Maps inmanta module names to a tuple of:
            -   The version to register for this module
            -   The set of agents using this module in this model version.
        :param environment: The environment for which to register modules per agent.
        :param connection: The asyncpg connection to use.
        """
        query = f"""
            INSERT INTO {AgentModules.__tablename__}(
                cm_version,
                environment,
                agent_name,
                inmanta_module_name,
                inmanta_module_version
            ) VALUES(
                $1,
                $2,
                $3,
                $4,
                $5
            )
            ON CONFLICT DO NOTHING;
        """
        async with connection.transaction():
            values = []
            for inmanta_module_name, (inmanta_module_version, agents_to_register) in module_usage_info.items():
                for agent_name in agents_to_register:
                    values.append(
                        (
                            model_version,
                            environment,
                            agent_name,
                            inmanta_module_name,
                            inmanta_module_version,
                        )
                    )

            await connection.executemany(
                query,
                values,
            )

    @classmethod
    async def delete_version(
        cls, environment: uuid.UUID, model_version: int, connection: asyncpg.connection.Connection
    ) -> None:
        await connection.execute(
            f"DELETE FROM {AgentModules.__tablename__} WHERE environment=$1 AND cm_version=$2",
            environment,
            model_version,
        )


class File(Base):
    __tablename__ = "file"
    __table_args__ = (PrimaryKeyConstraint("content_hash", name="file_pkey"),)

    content_hash: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    module_files: Mapped[list["ModuleFiles"]] = relationship("ModuleFiles", back_populates="file")


class InmantaUser(Base):
    __tablename__ = "inmanta_user"
    __table_args__ = (PrimaryKeyConstraint("id", name="user_pkey"), UniqueConstraint("username", name="user_username_key"))

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    auth_method: Mapped[str] = mapped_column(Enum("database", "oidc", name="auth_method"), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    role_assignment: Mapped[list["RoleAssignment"]] = relationship("RoleAssignment", back_populates="user")


class Project(Base):
    __tablename__ = "project"
    __table_args__ = (PrimaryKeyConstraint("id", name="project_pkey"), UniqueConstraint("name", name="project_name_key"))

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    environment: Mapped[list["Environment"]] = relationship("Environment", back_populates="project_")


class Role(Base):
    __tablename__ = "role"
    __table_args__ = (PrimaryKeyConstraint("id", name="role_pkey"), UniqueConstraint("name", name="role_name_key"))

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    role_assignment: Mapped[list["RoleAssignment"]] = relationship("RoleAssignment", back_populates="role")


class Schemamanager(Base):
    __tablename__ = "schemamanager"
    __table_args__ = (PrimaryKeyConstraint("name", name="schemamanager_pkey"),)

    name: Mapped[str] = mapped_column(String, primary_key=True)
    installed_versions: Mapped[Optional[list[int]]] = mapped_column(ARRAY(Integer()))


class Environment(Base):
    __tablename__ = "environment"
    __table_args__: tuple[Any, ...] = (
        ForeignKeyConstraint(["project"], ["project.id"], ondelete="CASCADE", name="environment_project_fkey"),
        PrimaryKeyConstraint("id", name="environment_pkey"),
        Index("environment_name_project_index", "project", "name", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    project: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    halted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    repo_url: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    repo_branch: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    last_version: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    description: Mapped[Optional[str]] = mapped_column(String(255), server_default=text("''::character varying"))
    icon: Mapped[Optional[str]] = mapped_column(String(65535), server_default=text("''::character varying"))
    is_marked_for_deletion: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))

    project_: Mapped["Project"] = relationship("Project", back_populates="environment")
    agentprocess: Mapped[list["Agentprocess"]] = relationship("Agentprocess", back_populates="environment_")
    compile: Mapped[list["Compile"]] = relationship("Compile", back_populates="environment_")
    configurationmodel: Mapped[list["Configurationmodel"]] = relationship("Configurationmodel", back_populates="environment_")
    discoveredresource: Mapped[list["Discoveredresource"]] = relationship("Discoveredresource", back_populates="environment_")
    environmentmetricsgauge: Mapped[list["Environmentmetricsgauge"]] = relationship(
        "Environmentmetricsgauge", back_populates="environment_"
    )
    environmentmetricstimer: Mapped[list["Environmentmetricstimer"]] = relationship(
        "Environmentmetricstimer", back_populates="environment_"
    )
    inmanta_module: Mapped[list["InmantaModule"]] = relationship("InmantaModule", back_populates="environment_")
    parameter: Mapped[list["Parameter"]] = relationship("Parameter", back_populates="environment_")
    resource_persistent_state: Mapped[list["ResourcePersistentState"]] = relationship(
        "ResourcePersistentState", back_populates="environment_"
    )
    resource_set: Mapped[list["ResourceSet"]] = relationship("ResourceSet", back_populates="environment_")
    role_assignment: Mapped[list["RoleAssignment"]] = relationship("RoleAssignment", back_populates="environment_")
    notification: Mapped[list["Notification"]] = relationship("Notification", back_populates="environment_")
    unknownparameter: Mapped[list["Unknownparameter"]] = relationship("Unknownparameter", back_populates="environment_")
    agent: Mapped[list["Agent"]] = relationship("Agent", back_populates="environment_")


class Agentprocess(Base):
    __tablename__ = "agentprocess"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="agentprocess_environment_fkey"),
        PrimaryKeyConstraint("sid", name="agentprocess_pkey"),
        Index("agentprocess_env_expired_index", "environment", "expired"),
        Index("agentprocess_env_hostname_expired_index", "environment", "hostname", "expired"),
        Index("agentprocess_expired_index", "expired"),
        Index("agentprocess_sid_expired_index", "sid", "expired", unique=True),
    )

    hostname: Mapped[str] = mapped_column(String, nullable=False)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    sid: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    first_seen: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_seen: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    expired: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="agentprocess")
    agentinstance: Mapped[list["Agentinstance"]] = relationship("Agentinstance", back_populates="agentprocess")


class Compile(Base):
    __tablename__ = "compile"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="compile_environment_fkey"),
        ForeignKeyConstraint(
            ["substitute_compile_id"], ["compile.id"], ondelete="CASCADE", name="compile_substitute_compile_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="compile_pkey"),
        Index("compile_completed_environment_idx", "completed", "environment"),
        Index("compile_env_remote_id_index", "environment", "remote_id"),
        Index("compile_env_requested_index", "environment", "requested"),
        Index("compile_env_started_index", "environment", "started"),
        Index("compile_environment_version_index", "environment", "version"),
        Index("compile_substitute_compile_id_index", "substitute_compile_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    requested_environment_variables: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    mergeable_environment_variables: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    soft_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    links: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    started: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    completed: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    requested: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB)
    do_export: Mapped[Optional[bool]] = mapped_column(Boolean)
    force_update: Mapped[Optional[bool]] = mapped_column(Boolean)
    success: Mapped[Optional[bool]] = mapped_column(Boolean)
    version: Mapped[Optional[int]] = mapped_column(Integer)
    remote_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)
    handled: Mapped[Optional[bool]] = mapped_column(Boolean)
    substitute_compile_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)
    compile_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    partial: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    removed_resource_sets: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String()), server_default=text("ARRAY[]::character varying[]")
    )
    notify_failed_compile: Mapped[Optional[bool]] = mapped_column(Boolean)
    failed_compile_message: Mapped[Optional[str]] = mapped_column(String)
    exporter_plugin: Mapped[Optional[str]] = mapped_column(String)
    used_environment_variables: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="compile")
    substitute_compile: Mapped[Optional["Compile"]] = relationship(
        "Compile", remote_side=[id], back_populates="substitute_compile_reverse"
    )
    substitute_compile_reverse: Mapped[list["Compile"]] = relationship(
        "Compile", remote_side=[substitute_compile_id], back_populates="substitute_compile"
    )
    notification: Mapped[list["Notification"]] = relationship("Notification", back_populates="compile")
    report: Mapped[list["Report"]] = relationship("Report", back_populates="compile_")


class Configurationmodel(Base):
    __tablename__ = "configurationmodel"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="configurationmodel_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "version", name="configurationmodel_pkey"),
        Index("configurationmodel_env_released_version_index", "environment", "released", "version", unique=True),
        Index("configurationmodel_env_version_total_index", "environment", "version", "total", unique=True),
    )

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    undeployable: Mapped[list[str]] = mapped_column(ARRAY(String()), nullable=False)
    skipped_for_undeployable: Mapped[list[str]] = mapped_column(ARRAY(String()), nullable=False)
    is_suitable_for_partial_compiles: Mapped[bool] = mapped_column(Boolean, nullable=False)
    date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    released: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    version_info: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    total: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    partial_base: Mapped[Optional[int]] = mapped_column(Integer)
    pip_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    project_constraints: Mapped[Optional[str]] = mapped_column(String)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="configurationmodel")
    resource_set: Mapped[list["ResourceSet"]] = relationship(
        "ResourceSet", secondary="resource_set_configuration_model", back_populates="configurationmodel"
    )
    dryrun: Mapped[list["Dryrun"]] = relationship("Dryrun", back_populates="configurationmodel")
    resourceaction: Mapped[list["Resourceaction"]] = relationship("Resourceaction", back_populates="configurationmodel")
    unknownparameter: Mapped[list["Unknownparameter"]] = relationship(
        "Unknownparameter", back_populates="configurationmodel", viewonly=True
    )
    agent_modules: Mapped[list["AgentModules"]] = relationship(
        "AgentModules", back_populates="configurationmodel", viewonly=True
    )


class Discoveredresource(Base):
    __tablename__ = "discoveredresource"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="unmanagedresource_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "discovered_resource_id", name="discoveredresource_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    discovered_resource_id: Mapped[str] = mapped_column(String, primary_key=True)
    values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    discovered_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    discovery_resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=False)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="discoveredresource")


class Environmentmetricsgauge(Base):
    __tablename__ = "environmentmetricsgauge"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="environmentmetricsgauge_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "timestamp", "metric_name", "category", name="environmentmetricsgauge_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String, primary_key=True, server_default=text("'__None__'::character varying"))

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="environmentmetricsgauge")


class Environmentmetricstimer(Base):
    __tablename__ = "environmentmetricstimer"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="environmentmetricstimer_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "timestamp", "metric_name", "category", name="environmentmetricstimer_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float] = mapped_column(Double(53), nullable=False)
    category: Mapped[str] = mapped_column(String, primary_key=True, server_default=text("'__None__'::character varying"))

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="environmentmetricstimer")


class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = (
        ForeignKeyConstraint(["compile_id"], ["compile.id"], ondelete="CASCADE", name="notification_compile_id_fkey"),
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="notification_environment_fkey"),
        PrimaryKeyConstraint("environment", "id", name="notification_pkey"),
        Index("notification_env_created_id_index", "environment", "created", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    created: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    cleared: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    severity: Mapped[Optional[str]] = mapped_column(
        Enum("message", "info", "success", "warning", "error", name="notificationseverity"),
        server_default=text("'message'::notificationseverity"),
    )
    uri: Mapped[Optional[str]] = mapped_column(String)
    compile_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)

    compile: Mapped[Optional["Compile"]] = relationship("Compile", back_populates="notification")
    environment_: Mapped["Environment"] = relationship("Environment", back_populates="notification")


class Parameter(Base):
    __tablename__ = "parameter"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="parameter_environment_fkey"),
        PrimaryKeyConstraint("id", name="parameter_pkey"),
        Index("parameter_env_name_resource_id_index", "environment", "name", "resource_id"),
        Index("parameter_environment_resource_id_index", "environment", "resource_id"),
        Index("parameter_metadata_index", "metadata"),
        Index("parameter_updated_index", "updated"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''::character varying"))
    environment: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    expires: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    resource_id: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    updated: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="parameter")


class ResourcePersistentState(Base):
    __tablename__ = "resource_persistent_state"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment"], ["environment.id"], ondelete="CASCADE", name="resource_persistent_state_environment_fkey"
        ),
        PrimaryKeyConstraint("environment", "resource_id", name="resource_persistent_state_pkey"),
        Index("resource_persistent_state_environment_agent_resource_id_idx", "environment", "agent", "resource_id"),
        Index("resource_persistent_state_environment_resource_id_is_orphan", "environment", "resource_id", "is_orphan"),
        Index(
            "resource_persistent_state_environment_resource_id_value_res_idx", "environment", "resource_id_value", "resource_id"
        ),
        Index("resource_persistent_state_environment_resource_type_resourc_idx", "environment", "resource_type", "resource_id"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    resource_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_non_deploying_status: Mapped[str] = mapped_column(
        Enum(
            "unavailable",
            "skipped",
            "dry",
            "deployed",
            "failed",
            "available",
            "cancelled",
            "undefined",
            "skipped_for_undefined",
            "non_compliant",
            name="non_deploying_resource_state",
        ),
        nullable=False,
        server_default=text("'available'::non_deploying_resource_state"),
    )
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    agent: Mapped[str] = mapped_column(String, nullable=False)
    resource_id_value: Mapped[str] = mapped_column(String, nullable=False)
    is_undefined: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_orphan: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_handler_run: Mapped[str] = mapped_column(String, nullable=False)
    blocked: Mapped[str] = mapped_column(String, nullable=False)
    created: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    last_handler_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_success: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_produced_events: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_deployed_attribute_hash: Mapped[Optional[str]] = mapped_column(String)
    last_deployed_version: Mapped[Optional[int]] = mapped_column(Integer)
    current_intent_attribute_hash: Mapped[Optional[str]] = mapped_column(String)
    is_deploying: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    last_handler_run_compliant: Mapped[Optional[bool]] = mapped_column(Boolean)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="resource_persistent_state")

    @hybrid_property
    def compliance_state(self) -> state.Compliance | None:
        return state.get_compliance_status(
            self.is_orphan,
            self.is_undefined,
            self.last_deployed_attribute_hash,
            self.current_intent_attribute_hash,
            self.last_handler_run_compliant,
        )

    @compliance_state.inplace.expression
    @classmethod
    def _compliance_state_expression(cls) -> Case[Any]:
        return case(
            (cls.is_orphan, None),
            (cls.is_undefined, state.Compliance.UNDEFINED.name),
            (
                or_(
                    cls.last_deployed_attribute_hash.is_(None),
                    cls.current_intent_attribute_hash.is_distinct_from(cls.last_deployed_attribute_hash),
                ),
                state.Compliance.HAS_UPDATE.name,
            ),
            (cls.last_handler_run_compliant.is_(True), state.Compliance.COMPLIANT.name),
            else_=state.Compliance.NON_COMPLIANT.name,
        )


class ResourceSet(Base):
    __tablename__ = "resource_set"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="resource_set_environment_fkey"),
        PrimaryKeyConstraint("environment", "id", name="resource_set_pkey"),
        Index("resource_set_environment_name_id_index", "environment", "name", "id"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String)

    configurationmodel: Mapped[list["Configurationmodel"]] = relationship(
        "Configurationmodel", secondary="resource_set_configuration_model", back_populates="resource_set"
    )
    environment_: Mapped["Environment"] = relationship("Environment", back_populates="resource_set")
    resource: Mapped[list["Resource"]] = relationship("Resource", back_populates="resource_set_")


class RoleAssignment(Base):
    __tablename__ = "role_assignment"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="role_assignment_environment_fkey"),
        ForeignKeyConstraint(["role_id"], ["role.id"], ondelete="RESTRICT", name="role_assignment_role_id_fkey"),
        ForeignKeyConstraint(["user_id"], ["inmanta_user.id"], ondelete="CASCADE", name="role_assignment_user_id_fkey"),
        PrimaryKeyConstraint("user_id", "environment", "role_id", name="role_assignment_pkey"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="role_assignment")
    role: Mapped["Role"] = relationship("Role", back_populates="role_assignment")
    user: Mapped["InmantaUser"] = relationship("InmantaUser", back_populates="role_assignment")


class Scheduler(Environment):
    __tablename__ = "scheduler"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="scheduler_environment_fkey"),
        PrimaryKeyConstraint("environment", name="scheduler_pkey"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    last_processed_model_version: Mapped[Optional[int]] = mapped_column(Integer)


class Agentinstance(Base):
    __tablename__ = "agentinstance"
    __table_args__ = (
        ForeignKeyConstraint(["process"], ["agentprocess.sid"], ondelete="CASCADE", name="agentinstance_process_fkey"),
        PrimaryKeyConstraint("id", name="agentinstance_pkey"),
        UniqueConstraint("tid", "process", "name", name="agentinstance_unique"),
        Index("agentinstance_expired_index", "expired"),
        Index("agentinstance_expired_tid_endpoint_index", "tid", "name", "expired"),
        Index("agentinstance_process_index", "process"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    process: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    tid: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    expired: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    agentprocess: Mapped["Agentprocess"] = relationship("Agentprocess", back_populates="agentinstance")
    agent: Mapped[list["Agent"]] = relationship("Agent", back_populates="agentinstance")


class Dryrun(Base):
    __tablename__ = "dryrun"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "model"],
            ["configurationmodel.environment", "configurationmodel.version"],
            ondelete="CASCADE",
            name="dryrun_environment_fkey",
        ),
        PrimaryKeyConstraint("id", name="dryrun_pkey"),
        Index("dryrun_env_model_index", "environment", "model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    model: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    total: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    todo: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    resources: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    configurationmodel: Mapped["Configurationmodel"] = relationship("Configurationmodel", back_populates="dryrun")


class Report(Base):
    __tablename__ = "report"
    __table_args__ = (
        ForeignKeyConstraint(["compile"], ["compile.id"], ondelete="CASCADE", name="report_compile_fkey"),
        PrimaryKeyConstraint("id", name="report_pkey"),
        Index("report_compile_index", "compile"),
        Index("report_started_compile_returncode", "compile", "returncode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    started: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    command: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    compile: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    completed: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    errstream: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    outstream: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    returncode: Mapped[Optional[int]] = mapped_column(Integer)

    compile_: Mapped["Compile"] = relationship("Compile", back_populates="report")


class Resource(Base):
    __tablename__ = "resource"
    __table_args__ = (
        ForeignKeyConstraint(
            ["resource_set", "environment"],
            ["resource_set.id", "resource_set.environment"],
            ondelete="CASCADE",
            name="resource_resource_set_environment_fkey",
        ),
        PrimaryKeyConstraint("environment", "resource_set", "resource_id", name="resource_pkey"),
        Index("resource_attributes_index", "attributes"),
        Index("resource_env_attr_hash_index", "environment", "attribute_hash"),
        Index("resource_environment_agent_idx", "environment", "agent"),
        Index("resource_environment_resource_id_value_index", "environment", "resource_id_value"),
        Index("resource_environment_resource_set_index", "environment", "resource_set"),
        Index("resource_environment_resource_type_index", "environment", "resource_type"),
        Index("resource_resource_id_index", "resource_id"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    resource_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id_value: Mapped[str] = mapped_column(String, nullable=False)
    resource_set: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    attributes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    attribute_hash: Mapped[Optional[str]] = mapped_column(String)
    is_undefined: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))

    resource_set_: Mapped["ResourceSet"] = relationship("ResourceSet", back_populates="resource")
    # Manually added field
    state: Mapped["ResourcePersistentState"] = relationship(
        "ResourcePersistentState",
        primaryjoin=lambda: and_(
            Resource.resource_id == foreign(ResourcePersistentState.resource_id),
            Resource.environment == foreign(ResourcePersistentState.environment),
        ),
        viewonly=True,
    )


t_resource_set_configuration_model = Table(
    "resource_set_configuration_model",
    Base.metadata,
    Column("environment", UUID, primary_key=True),
    Column("model", Integer, primary_key=True),
    Column("resource_set", UUID, primary_key=True),
    ForeignKeyConstraint(
        ["environment", "model"],
        ["configurationmodel.environment", "configurationmodel.version"],
        ondelete="CASCADE",
        name="resource_set_configuration_model_environment_model_fkey",
    ),
    ForeignKeyConstraint(
        ["environment", "resource_set"],
        ["resource_set.environment", "resource_set.id"],
        name="resource_set_configuration_mod_environment_resource_set_fkey",
    ),
    PrimaryKeyConstraint("environment", "model", "resource_set", name="resource_set_configuration_model_pkey"),
    Index("resource_set_configuration_model_environment_resource_set_in", "environment", "resource_set"),
)


class Resourceaction(Base):
    __tablename__ = "resourceaction"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "version"],
            ["configurationmodel.environment", "configurationmodel.version"],
            ondelete="CASCADE",
            name="resourceaction_environment_fkey",
        ),
        PrimaryKeyConstraint("action_id", name="resourceaction_pkey"),
        Index("resourceaction_environment_action_started_index", "environment", "action", "started"),
        Index("resourceaction_environment_version_started_index", "environment", "version", "started"),
        Index("resourceaction_started_index", "started"),
    )

    action_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    action: Mapped[str] = mapped_column(
        Enum("store", "push", "pull", "deploy", "dryrun", "getfact", "other", name="resourceaction_type"), nullable=False
    )
    started: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_version_ids: Mapped[list[str]] = mapped_column(ARRAY(String()), nullable=False)
    finished: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    messages: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(ARRAY(JSONB()))
    status: Mapped[Optional[str]] = mapped_column(
        Enum(
            "unavailable",
            "skipped",
            "dry",
            "deployed",
            "failed",
            "deploying",
            "available",
            "cancelled",
            "undefined",
            "skipped_for_undefined",
            "non_compliant",
            name="resourcestate",
        ),
        server_default=text("'available'::resourcestate"),
    )
    changes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    change: Mapped[Optional[str]] = mapped_column(Enum("nochange", "created", "purged", "updated", name="change"))

    configurationmodel: Mapped["Configurationmodel"] = relationship("Configurationmodel", back_populates="resourceaction")
    resourceaction_resource: Mapped[list["ResourceactionResource"]] = relationship(
        "ResourceactionResource", back_populates="resource_action"
    )


class Unknownparameter(Base):
    __tablename__ = "unknownparameter"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment", "version"],
            ["configurationmodel.environment", "configurationmodel.version"],
            ondelete="CASCADE",
            name="unknownparameter_environment_version_fkey",
        ),
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="unknownparameter_environment_fkey"),
        PrimaryKeyConstraint("id", name="unknownparameter_pkey"),
        Index("unknownparameter_env_version_index", "environment", "version"),
        Index("unknownparameter_resolved_index", "resolved"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    environment: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String, server_default=text("''::character varying"))
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB)
    resolved: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))

    configurationmodel: Mapped["Configurationmodel"] = relationship(
        "Configurationmodel", back_populates="unknownparameter", viewonly=True
    )
    environment_: Mapped["Environment"] = relationship("Environment", back_populates="unknownparameter", viewonly=True)


class Agent(Base):
    __tablename__ = "agent"
    __table_args__ = (
        ForeignKeyConstraint(["environment"], ["environment.id"], ondelete="CASCADE", name="agent_environment_fkey"),
        ForeignKeyConstraint(["id_primary"], ["agentinstance.id"], ondelete="RESTRICT", name="agent_id_primary_fkey"),
        PrimaryKeyConstraint("environment", "name", name="agent_pkey"),
        Index("agent_id_primary_index", "id_primary"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, primary_key=True)
    last_failover: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    paused: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("false"))
    id_primary: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)
    unpause_on_resume: Mapped[Optional[bool]] = mapped_column(Boolean)

    environment_: Mapped["Environment"] = relationship("Environment", back_populates="agent")
    agentinstance: Mapped[Optional["Agentinstance"]] = relationship("Agentinstance", back_populates="agent")
    agent_modules: Mapped[list["AgentModules"]] = relationship("AgentModules", back_populates="agent", viewonly=True)


class ResourceactionResource(Base):
    __tablename__ = "resourceaction_resource"
    __table_args__ = (
        ForeignKeyConstraint(
            ["resource_action_id"],
            ["resourceaction.action_id"],
            ondelete="CASCADE",
            name="resourceaction_resource_resource_action_id_fkey",
        ),
        PrimaryKeyConstraint(
            "environment", "resource_id", "resource_version", "resource_action_id", name="resourceaction_resource_pkey"
        ),
        Index("resourceaction_resource_environment_resource_version_index", "environment", "resource_version"),
        Index("resourceaction_resource_resource_action_id_index", "resource_action_id"),
    )

    environment: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    resource_action_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    resource_id: Mapped[str] = mapped_column(String, primary_key=True)
    resource_version: Mapped[int] = mapped_column(Integer, primary_key=True)

    resource_action: Mapped["Resourceaction"] = relationship("Resourceaction", back_populates="resourceaction_resource")
