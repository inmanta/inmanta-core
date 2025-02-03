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


@mapper.type(inmanta.graphql.models.AgentProcess)
class AgentProcess:

    @staticmethod
    async def get_environments(id: str | None = strawberry.UNSET) -> typing.Sequence["AgentProcess"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.AgentProcess)
            if id:
                stmt = stmt.filter_by(id=id)
            agent_processes = await session.scalars(stmt)
            return agent_processes.all()


@mapper.type(inmanta.graphql.models.AgentInstance)
class AgentInstance:

    @staticmethod
    async def get_environments(id: str | None = strawberry.UNSET) -> typing.Sequence["AgentInstance"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.AgentInstance)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
            return results.all()


@mapper.type(inmanta.graphql.models.Agent)
class Agent:

    @staticmethod
    async def get_environments(id: str | None = strawberry.UNSET) -> typing.Sequence["Agent"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Agent)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
            return results.all()


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


@mapper.type(inmanta.graphql.models.Code)
class Code:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["Code"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Code)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Compile)
class Compile:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["Compile"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Compile)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Report)
class Report:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["Report"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Report)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.ConfigurationModel)
class ConfigurationModel:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["ConfigurationModel"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.ConfigurationModel)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Dryrun)
class Dryrun:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["Dryrun"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Dryrun)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Resource)
class Resource:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["Resource"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Resource)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.ResourceAction)
class ResourceAction:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["ResourceAction"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.ResourceAction)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.UnknownParameter)
class UnknownParameter:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["UnknownParameter"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.UnknownParameter)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.DiscoveredResource)
class DiscoveredResource:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["DiscoveredResource"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.DiscoveredResource)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.EnvironmentMetricsGauge)
class EnvironmentMetricsGauge:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["EnvironmentMetricsGauge"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.EnvironmentMetricsGauge)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.EnvironmentMetricsTimer)
class EnvironmentMetricsTimer:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["EnvironmentMetricsTimer"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.EnvironmentMetricsTimer)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Parameter)
class Parameter:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["Parameter"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Parameter)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.ResourcePersistentState)
class ResourcePersistentState:
    @staticmethod
    async def get_projects(id: str | None = strawberry.UNSET) -> typing.Sequence["ResourcePersistentState"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.ResourcePersistentState)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


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
