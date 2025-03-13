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

import dataclasses
import typing

import inmanta.data.sqlalchemy as models
import strawberry
from inmanta.data import get_session, get_session_factory
from inmanta.server.services.compilerservice import CompilerService
from sqlalchemy import Select, asc, desc, select
from strawberry import relay
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from strawberry.types.info import ContextType
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader, StrawberrySQLAlchemyMapper


@dataclasses.dataclass
class GraphQLMetadata:
    compiler_service: CompilerService


class StrawberryFilter:
    def get_filter_dict(self) -> dict[str, typing.Any]:
        return {key: value for key, value in self.__dict__.items() if value is not strawberry.UNSET}


class StrawberryOrder:
    pass


def add_filter_and_sort(
    stmt: Select[typing.Any],
    filter: typing.Optional[StrawberryFilter] = strawberry.UNSET,
    order_by: typing.Optional[StrawberryOrder] = strawberry.UNSET,
) -> Select[typing.Any]:
    if filter and filter is not strawberry.UNSET:
        stmt = stmt.filter_by(**filter.get_filter_dict())
    if order_by and order_by is not strawberry.UNSET:
        for key in order_by.__dict__.keys():
            order = getattr(order_by, key)
            if order is not strawberry.UNSET:
                if order == "asc":
                    stmt = stmt.order_by(asc(key))
                elif order == "desc":
                    stmt = stmt.order_by(desc(key))
                else:
                    raise Exception(f"Invalid order {order} for field {key}. Only 'asc' or 'desc' is allowed.")
    return stmt


def get_schema(metadata: GraphQLMetadata) -> strawberry.Schema:
    """
    Initializes the Strawberry GraphQL schema.
    It is initiated in a function instead of being declared at the module level, because we have to do this
    after the SQLAlchemy engine is initialized.
    """

    mapper: StrawberrySQLAlchemyMapper[typing.Any] = StrawberrySQLAlchemyMapper()
    loader = StrawberrySQLAlchemyLoader(async_bind_factory=get_session_factory())

    def get_expert_mode(root: "Environment") -> bool:
        """
        Checks settings of environment to figure out if expert mode is enabled or not
        """
        assert hasattr(root, "settings")  # Make mypy happy
        return bool(root.settings.get("enable_lsm_expert_mode", False))

    def get_is_compiling(root: "Environment") -> bool:
        """
        Checks compiler service to figure out if environment is compiling or not
        """
        assert hasattr(root, "id")  # Make mypy happy
        return metadata.compiler_service.is_environment_compiling(environment_id=root.id)

    @mapper.type(models.Environment)
    class Environment:
        # Add every relation/attribute that we don't want to expose in our GraphQL endpoint to `__exclude__`
        __exclude__ = [
            "project_",
            "agentprocess",
            "code",
            "compile",
            "configurationmodel",
            "discoveredresource",
            "environmentmetricsgauge",
            "environmentmetricstimer",
            "notification",
            "parameter",
            "resource_persistent_state",
            "unknownparameter",
            "agent",
        ]
        is_expert_mode: bool = strawberry.field(resolver=get_expert_mode)
        is_compiling: bool = strawberry.field(resolver=get_is_compiling)

    @strawberry.input
    class EnvironmentFilter(StrawberryFilter):
        id: typing.Optional[str] = strawberry.UNSET

    @strawberry.input(one_of=True)
    class EnvironmentOrder(StrawberryOrder):
        id: typing.Optional[str] = strawberry.UNSET
        name: typing.Optional[str] = strawberry.UNSET

    class CustomInfo(Info):
        @property
        def context(self) -> ContextType:  # type: ignore[type-var]
            return typing.cast(ContextType, {"sqlalchemy_loader": loader})

    @strawberry.type
    class Query:
        @relay.connection(relay.ListConnection[Environment])  # type: ignore[misc, type-var]
        async def environments(
            self,
            filter: typing.Optional[EnvironmentFilter] = strawberry.UNSET,
            order_by: typing.Optional[EnvironmentOrder] = strawberry.UNSET,
        ) -> typing.Iterable[models.Environment]:
            async with get_session() as session:
                stmt = select(models.Environment)
                stmt = add_filter_and_sort(stmt, filter, order_by)
                _environments = await session.scalars(stmt)
                return _environments.all()

    return strawberry.Schema(query=Query, config=StrawberryConfig(info_class=CustomInfo))
