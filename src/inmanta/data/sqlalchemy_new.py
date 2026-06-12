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
from typing import Any

import asyncpg

from inmanta.data.model import AgentName
from inmanta.data.model import InmantaModule as InmantaModuleDTO
from inmanta.data.model import InmantaModuleName, InmantaModuleVersion
from inmanta.data.sqlalchemy_generated import *  # noqa: F401, F403
from inmanta.data.sqlalchemy_generated import AgentModules, Base, InmantaModule, ModuleFiles, Resource, ResourcePersistentState
from inmanta.deploy import state
from sqlalchemy import Case, and_, case, or_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import foreign, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
async def _base_delete_all(cls: type[Base], environment: uuid.UUID, connection: asyncpg.connection.Connection) -> None:
    await connection.execute("DELETE FROM %s WHERE environment=$1" % cls.__tablename__, environment)


Base.delete_all = classmethod(_base_delete_all)


# ---------------------------------------------------------------------------
# InmantaModule
# ---------------------------------------------------------------------------
async def _inmanta_module_register_modules(
    cls: type[InmantaModule],
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


async def _inmanta_module_delete_version(
    cls: type[InmantaModule], environment: uuid.UUID, model_version: int, connection: asyncpg.connection.Connection
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


InmantaModule.register_modules = classmethod(_inmanta_module_register_modules)
InmantaModule.delete_version = classmethod(_inmanta_module_delete_version)


# ---------------------------------------------------------------------------
# ModuleFiles
# ---------------------------------------------------------------------------
async def _module_files_delete_version(
    cls: type[ModuleFiles], environment: uuid.UUID, model_version: int, connection: asyncpg.connection.Connection
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


ModuleFiles.delete_version = classmethod(_module_files_delete_version)


# ---------------------------------------------------------------------------
# AgentModules
# ---------------------------------------------------------------------------
async def _agent_modules_get_registered_modules_data(
    cls: type[AgentModules], model_version: int, environment: uuid.UUID, connection: asyncpg.Connection
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


async def _agent_modules_register_modules_for_agents(
    cls: type[AgentModules],
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


async def _agent_modules_delete_version(
    cls: type[AgentModules], environment: uuid.UUID, model_version: int, connection: asyncpg.connection.Connection
) -> None:
    await connection.execute(
        f"DELETE FROM {AgentModules.__tablename__} WHERE environment=$1 AND cm_version=$2",
        environment,
        model_version,
    )


AgentModules.get_registered_modules_data = classmethod(_agent_modules_get_registered_modules_data)
AgentModules.register_modules_for_agents = classmethod(_agent_modules_register_modules_for_agents)
AgentModules.delete_version = classmethod(_agent_modules_delete_version)


# ---------------------------------------------------------------------------
# ResourcePersistentState: hybrid properties
# ---------------------------------------------------------------------------
def _resource_persistent_state_is_orphan(self: ResourcePersistentState) -> bool:
    """
    Is this resource not present in the latest released version of the model?
    Kept for backwards compatibility.
    """
    return self.orphaned_after is not None


def _resource_persistent_state_is_orphan_expression(cls: type[ResourcePersistentState]) -> Case[Any]:
    return case(
        (cls.orphaned_after.is_not(None), True),
        else_=False,
    )


ResourcePersistentState.is_orphan = hybrid_property(_resource_persistent_state_is_orphan).expression(
    _resource_persistent_state_is_orphan_expression
)


def _resource_persistent_state_compliance(self: ResourcePersistentState) -> "state.Compliance | None":
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


def _resource_persistent_state_compliance_expression(cls: type[ResourcePersistentState]) -> Case[Any]:
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


ResourcePersistentState.compliance = hybrid_property(_resource_persistent_state_compliance).expression(
    _resource_persistent_state_compliance_expression
)


# ---------------------------------------------------------------------------
# Resource: manually defined relationship to ResourcePersistentState
# ---------------------------------------------------------------------------
# This relationship has no matching foreign key in the database, so it is not generated by sqlacodegen and has to be
# declared by hand.
# uselist=False makes this a scalar relationship: a resource maps to exactly one persistent state. SQLAlchemy would
# otherwise infer a collection here, since the foreign() side is on ResourcePersistentState. In the original sqlalchemy.py
# this was conveyed by the Mapped["ResourcePersistentState"] annotation, which is not available when assigning the
# relationship dynamically.
Resource.state = relationship(
    "ResourcePersistentState",
    primaryjoin=lambda: and_(
        Resource.resource_id == foreign(ResourcePersistentState.resource_id),
        Resource.environment == foreign(ResourcePersistentState.environment),
    ),
    uselist=False,
    viewonly=True,
    doc="The persistent state of this resource",
)
