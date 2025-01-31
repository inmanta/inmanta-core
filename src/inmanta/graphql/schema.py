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

import os
import typing

import inmanta.graphql.models
import strawberry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from strawberry.types.info import ContextType
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader, StrawberrySQLAlchemyMapper

mapper = StrawberrySQLAlchemyMapper()

ASYNC_SESSION: typing.Optional[AsyncSession] = None
SCHEMA = None


# @mapper.type(inmanta.graphql.models.EnvironmentSetting)
# class EnvironmentSetting:
#     pass


@mapper.type(inmanta.graphql.models.Notification)
class Notification:
    pass


@mapper.type(inmanta.graphql.models.Environment)
class Environment:

    @staticmethod
    async def get_environments(id: str | None = strawberry.UNSET) -> typing.Sequence["Environment"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Environment)
            if id:
                stmt = stmt.filter_by(id=id)
            _environments = await session.scalars(stmt)
            return _environments.all()


@mapper.type(inmanta.graphql.models.Project)
class Project:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["Project"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Project)
            if id:
                stmt = stmt.filter_by(id=id)
            projects = await session.scalars(stmt)
        return projects.all()


def get_async_session(connection_string: typing.Optional[str] = None) -> AsyncSession:
    if ASYNC_SESSION is None:
        initialize_schema(connection_string)
    return ASYNC_SESSION()


def get_schema(connection_string: typing.Optional[str] = None):
    if SCHEMA is None:
        initialize_schema(connection_string)
    return SCHEMA


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
        environments: typing.List[Environment] = strawberry.field(resolver=Environment.get_environments)
        projects: typing.List[Project] = strawberry.field(resolver=Project.get_projects)

    SCHEMA = strawberry.Schema(query=Query, config=StrawberryConfig(info_class=CustomInfo))
    return SCHEMA
