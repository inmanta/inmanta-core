"""
Copyright 2026 Inmanta

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

import uuid
from typing import TYPE_CHECKING, Any

import asyncpg

from inmanta.data import sqlalchemy_generated as generated
from inmanta.data.model import AgentName
from inmanta.data.model import InmantaModule as InmantaModuleDTO
from inmanta.data.model import InmantaModuleName, InmantaModuleVersion
from inmanta.data.sqlalchemy_generated import *  # noqa: F401, F403
from inmanta.deploy import state
from sqlalchemy import Case, and_, case, or_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, foreign, relationship
from sqlalchemy.orm.clsregistry import _MultipleClassMarker

# inmanta.data.sqlalchemy_generated holds the verbatim sqlacodegen output for the current database schema and must not be
# edited by hand. This module layers the manual additions (helper methods, hybrid properties and the Resource.state
# relationship) on top of it by subclassing rather than by mutating the generated classes in place: every customized model
# is a single-table-inheritance subclass of its generated counterpart, so it maps to the same table while adding
# Python-level behaviour.
#
# The subclasses deliberately reuse the names of their generated parents so that they stay the canonical model classes
# (e.g. `Resource` keeps referring to the resource table). Since both the parent and the subclass then share a name in
# SQLAlchemy's string-based relationship lookup, the unqualified targets in the generated file (e.g.
# relationship("ResourcePersistentState")) would become ambiguous. `_shadow_generated` drops the generated parent from
# that lookup so every such reference resolves to our subclass, leaving exactly one canonical mapped class per table.


def _shadow_generated(subclass: type) -> None:
    """
    Remove the generated parent of `subclass` from the declarative string-lookup registry, so that unqualified
    relationship targets referring to the shared class name resolve to `subclass` instead of raising an "ambiguous
    class" error at mapper configuration time.
    """
    entry = generated.Base.registry._class_registry.get(subclass.__name__)
    if isinstance(entry, _MultipleClassMarker):
        for registered in list(entry):
            if registered is not None and registered is not subclass:
                entry.remove_item(registered)


class _TableHelpers:
    """
    Mixin with helper methods shared by the model classes. It is a plain (unmapped) mixin so that the model classes below
    keep `sqlalchemy_generated.Base` as their SQLAlchemy declarative base.
    """

    if TYPE_CHECKING:
        # Provided by the mapped classes this mixin is combined with.
        __tablename__: str

    @classmethod
    async def delete_all(cls, environment: uuid.UUID, connection: asyncpg.connection.Connection) -> None:
        await connection.execute("DELETE FROM %s WHERE environment=$1" % cls.__tablename__, environment)


# ---------------------------------------------------------------------------
# InmantaModule
# ---------------------------------------------------------------------------
class InmantaModule(_TableHelpers, generated.InmantaModule):  # type: ignore[no-redef]
    @classmethod
    async def register_modules(
        cls,
        environment: uuid.UUID,
        modules: dict[InmantaModuleName, InmantaModuleDTO],
        connection: asyncpg.Connection,
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
            INSERT INTO {generated.ModuleFiles.__tablename__}(
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


# ---------------------------------------------------------------------------
# ModuleFiles
# ---------------------------------------------------------------------------
class ModuleFiles(_TableHelpers, generated.ModuleFiles):  # type: ignore[no-redef]
    @classmethod
    async def delete_version(
        cls, environment: uuid.UUID, model_version: int, connection: asyncpg.connection.Connection
    ) -> None:
        await connection.execute(
            f"""
            DELETE FROM {ModuleFiles.__tablename__}
            WHERE (environment, inmanta_module_name, inmanta_module_version) IN (
                SELECT environment, inmanta_module_name, inmanta_module_version
                FROM {generated.AgentModules.__tablename__}
                WHERE environment=$1
                AND cm_version=$2
            )
            """,
            environment,
            model_version,
        )


# ---------------------------------------------------------------------------
# AgentModules
# ---------------------------------------------------------------------------
class AgentModules(_TableHelpers, generated.AgentModules):  # type: ignore[no-redef]
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


# ---------------------------------------------------------------------------
# ResourcePersistentState: hybrid properties
# ---------------------------------------------------------------------------
class ResourcePersistentState(_TableHelpers, generated.ResourcePersistentState):  # type: ignore[no-redef]
    @hybrid_property
    def is_orphan(self) -> bool:
        """
        Is this resource not present in the latest released version of the model?
        Kept for backwards compatibility.
        """
        return self.orphaned_after is not None

    @is_orphan.inplace.expression
    @classmethod
    def _is_orphan_expression(cls) -> Case[Any]:
        return case(
            (cls.orphaned_after.is_not(None), True),
            else_=False,
        )

    @hybrid_property
    def compliance(self) -> "state.Compliance | None":
        """
        Compliance status of this resource
        """
        return state.get_compliance_status(
            self.orphaned_after,
            self.is_undefined,
            self.last_deployed_attribute_hash,
            self.current_intent_attribute_hash,
            self.last_handler_run_compliant,
        )

    @compliance.inplace.expression
    @classmethod
    def _compliance_expression(cls) -> Case[Any]:
        return case(
            (cls.orphaned_after.is_not(None), None),
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


# ---------------------------------------------------------------------------
# Resource: manually defined relationship to ResourcePersistentState
# ---------------------------------------------------------------------------
class Resource(_TableHelpers, generated.Resource):  # type: ignore[no-redef]
    # This relationship has no matching foreign key in the database, so it is not generated by sqlacodegen and has to be
    # declared by hand. The Mapped["ResourcePersistentState"] annotation makes it a scalar relationship: a resource maps
    # to exactly one persistent state. SQLAlchemy would otherwise infer a collection here, since the foreign() side is on
    # ResourcePersistentState.
    state: Mapped["ResourcePersistentState"] = relationship(
        "ResourcePersistentState",
        primaryjoin=lambda: and_(
            Resource.resource_id == foreign(ResourcePersistentState.resource_id),
            Resource.environment == foreign(ResourcePersistentState.environment),
        ),
        viewonly=True,
        doc="The persistent state of this resource",
    )


# Redirect the shared class names to the subclasses defined above, so that the relationships declared in
# sqlalchemy_generated resolve to these canonical model classes rather than their generated parents.
for _subclass in (InmantaModule, ModuleFiles, AgentModules, ResourcePersistentState, Resource):
    _shadow_generated(_subclass)
