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

import typing

import inmanta.data.sqlalchemy as models
import strawberry
from inmanta.data import get_session, get_session_factory
from sqlalchemy import Select, asc, desc, select
from strawberry import relay
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from strawberry.types.info import ContextType
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader, StrawberrySQLAlchemyMapper

mapper: StrawberrySQLAlchemyMapper[typing.Any] = StrawberrySQLAlchemyMapper()
SCHEMA: strawberry.Schema | None = None


def get_expert_mode(root: "Environment") -> bool:
    if not hasattr(root, "settings"):
        return False
    return bool(root.settings.get("enable_lsm_expert_mode", False))


@mapper.type(models.Project)
class Project:
    pass


@mapper.type(models.Environment)
class Environment:
    is_expert_mode: bool = strawberry.field(resolver=get_expert_mode)


def get_schema() -> strawberry.Schema:
    if SCHEMA is None:
        initialize_schema()
    assert SCHEMA
    return SCHEMA


class StrawberryFilter:
    def get_filter_dict(self) -> dict[str, typing.Any]:
        return {key: value for key, value in self.__dict__.items() if value is not strawberry.UNSET}


class StrawberryOrder:
    pass


@strawberry.input
class EnvironmentFilter(StrawberryFilter):
    id: typing.Optional[str] = strawberry.UNSET


@strawberry.input(one_of=True)
class EnvironmentOrder(StrawberryOrder):
    id: typing.Optional[str] = strawberry.UNSET
    name: typing.Optional[str] = strawberry.UNSET


def add_filter_and_sort(
    stmt: Select[typing.Any],
    filter: typing.Union[StrawberryFilter, strawberry.UNSET],
    order_by: typing.Union[StrawberryOrder, strawberry.UNSET],
) -> Select[typing.Any]:
    if filter is not strawberry.UNSET:
        stmt = stmt.filter_by(**filter.get_filter_dict())
    if order_by is not strawberry.UNSET:
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


def initialize_schema() -> None:
    global SCHEMA
    loader = StrawberrySQLAlchemyLoader(async_bind_factory=get_session_factory())

    class CustomInfo(Info):
        @property
        def context(self) -> ContextType:  # type: ignore[type-var]
            return typing.cast(ContextType, {"sqlalchemy_loader": loader})

    @strawberry.type
    class Query:
        @relay.connection(mapper.connection_types["EnvironmentConnection"])  # type: ignore[misc]
        async def environments(
            self,
            order_by: typing.Optional[EnvironmentOrder] = strawberry.UNSET,
            filter: EnvironmentFilter | None = strawberry.UNSET,
        ) -> typing.Iterable[models.Environment]:
            async with get_session() as session:
                stmt = select(models.Environment)
                stmt = add_filter_and_sort(stmt, filter, order_by)
                _environments = await session.scalars(stmt)
                return _environments.all()

    SCHEMA = strawberry.Schema(query=Query, config=StrawberryConfig(info_class=CustomInfo))
