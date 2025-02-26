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
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from strawberry import relay
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from strawberry.types.info import ContextType
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader, StrawberrySQLAlchemyMapper

mapper = StrawberrySQLAlchemyMapper()

ASYNC_SESSION: typing.Optional[AsyncSession] = None
SCHEMA = None

@mapper.type(models.Environment)
class Environment:
    pass


def get_async_session(connection_string: typing.Optional[str] = None) -> AsyncSession:
    if ASYNC_SESSION is None:
        initialize_schema(connection_string)
    return ASYNC_SESSION()


def get_schema(connection_string: typing.Optional[str] = None):
    if SCHEMA is None:
        initialize_schema(connection_string)
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


def add_filter_and_sort(stmt, filter: StrawberryFilter, order_by: StrawberryOrder):
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


def initialize_schema(connection_string: typing.Optional[str] = None):
    global ASYNC_SESSION
    global SCHEMA
    async_engine = create_async_engine(connection_string or "sqlite+aiosqlite:///database.db", echo="debug")
    ASYNC_SESSION = async_sessionmaker(async_engine)
    loader = StrawberrySQLAlchemyLoader(async_bind_factory=ASYNC_SESSION)

    class CustomInfo(Info):
        @property
        def context(self) -> ContextType:
            return {
                "sqlalchemy_loader": loader,
            }

    @strawberry.type
    class Query:
        @relay.connection(mapper.connection_types["EnvironmentConnection"])
        async def environments(
            self, order_by: typing.Optional[EnvironmentOrder] = strawberry.UNSET, filter: EnvironmentFilter | None = strawberry.UNSET
        ) -> typing.Iterable[Environment]:
            async with get_async_session() as session:
                stmt = select(models.Environment)
                stmt = add_filter_and_sort(stmt, filter, order_by)
                _environments = await session.scalars(stmt)
                a = _environments.all()
                return a

    SCHEMA = strawberry.Schema(query=Query, config=StrawberryConfig(info_class=CustomInfo))
    return SCHEMA
