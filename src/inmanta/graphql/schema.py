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

import logging
import typing
from contextlib import asynccontextmanager

import inmanta.graphql.models
import strawberry
from sqlalchemy import AsyncAdaptedQueuePool, event, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from strawberry.types.info import ContextType
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader, StrawberrySQLAlchemyMapper

mapper = StrawberrySQLAlchemyMapper()

ASYNC_SESSION: typing.Optional[AsyncSession] = None
SCHEMA: strawberry.Schema | None = None
ENGINE: AsyncEngine | None = None
POOL: AsyncAdaptedQueuePool | None = None

LOGGER = logging.getLogger(__name__)

# @mapper.type(inmanta.graphql.models.EnvironmentSetting)
# class EnvironmentSetting:
#     pass


@mapper.type(inmanta.graphql.models.Notification)
class Notification:
    pass


@mapper.type(inmanta.graphql.models.Environment)
class Environment:

    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Environment"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Environment)
            if id:
                stmt = stmt.filter_by(id=id)
            _environments = await session.scalars(stmt)
            return _environments.all()


@mapper.type(inmanta.graphql.models.AgentProcess)
class AgentProcess:

    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["AgentProcess"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.AgentProcess)
            if id:
                stmt = stmt.filter_by(id=id)
            agent_processes = await session.scalars(stmt)
            return agent_processes.all()


@mapper.type(inmanta.graphql.models.AgentInstance)
class AgentInstance:

    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["AgentInstance"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.AgentInstance)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
            return results.all()


@mapper.type(inmanta.graphql.models.Agent)
class Agent:

    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Agent"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Agent)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
            return results.all()


@mapper.type(inmanta.graphql.models.Project)
class Project:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Project"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Project)
            if id:
                stmt = stmt.filter_by(id=id)
            projects = await session.scalars(stmt)
        return projects.all()


@mapper.type(inmanta.graphql.models.Code)
class Code:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Code"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Code)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Compile)
class Compile:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Compile"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Compile)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Report)
class Report:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Report"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Report)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.ConfigurationModel)
class ConfigurationModel:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["ConfigurationModel"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.ConfigurationModel)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Dryrun)
class Dryrun:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Dryrun"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Dryrun)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Resource)
class Resource:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Resource"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Resource)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.ResourceAction)
class ResourceAction:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["ResourceAction"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.ResourceAction)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.UnknownParameter)
class UnknownParameter:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["UnknownParameter"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.UnknownParameter)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.DiscoveredResource)
class DiscoveredResource:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["DiscoveredResource"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.DiscoveredResource)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.EnvironmentMetricsGauge)
class EnvironmentMetricsGauge:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["EnvironmentMetricsGauge"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.EnvironmentMetricsGauge)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.EnvironmentMetricsTimer)
class EnvironmentMetricsTimer:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["EnvironmentMetricsTimer"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.EnvironmentMetricsTimer)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.Parameter)
class Parameter:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["Parameter"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.Parameter)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


@mapper.type(inmanta.graphql.models.ResourcePersistentState)
class ResourcePersistentState:
    @staticmethod
    async def fetch_all(id: str | None = strawberry.UNSET) -> typing.Sequence["ResourcePersistentState"]:
        async with get_async_session() as session:
            stmt = select(inmanta.graphql.models.ResourcePersistentState)
            if id:
                stmt = stmt.filter_by(id=id)
            results = await session.scalars(stmt)
        return results.all()


def get_async_session(connection_string: typing.Optional[str] = None) -> AsyncSession:
    if ENGINE is None:
        raise Exception("Cannot get session because engine wasn't started. Make sure to call start_engine() first.")
    if ASYNC_SESSION is None:
        # should not happen
        raise Exception("Engine is started but session factory wasn't initialized properly.")

    return ASYNC_SESSION()


def get_schema():
    if SCHEMA is None:
        initialize_schema()
    return SCHEMA


def my_on_checkout(dbapi_conn, connection_rec, connection_proxy):
    LOGGER.debug()


async def stop_engine():
    global ENGINE
    await ENGINE.dispose()
    ENGINE = None


def start_engine(
    url: str,
    pool_size: int = 10,
    max_overflow: int = 0,
    pool_timeout: float = 60.0,
    echo: bool = False,
):
    """
    engine vs connection vs session overview
    https://stackoverflow.com/questions/34322471/sqlalchemy-engine-connection-and-session-difference
    """
    global ENGINE
    global ASYNC_SESSION
    global POOL

    if ENGINE is not None:
        raise Exception("Engine already running: cannot call start_engine twice.")
    LOGGER.debug("Creating engine...")
    ENGINE = create_async_engine(
        url=url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        echo=echo,
    )
    POOL = ENGINE.pool
    ASYNC_SESSION = async_sessionmaker(ENGINE)

    @event.listens_for(ENGINE.sync_engine, "do_connect")
    def do_connect(dialect, conn_rec, cargs, cparams):
        print("some-function")
        print(dialect, conn_rec, cargs, cparams)

    @event.listens_for(ENGINE.sync_engine, "engine_connect")
    def engine_connect(conn, branch):
        # print("engine_connect", conn.exec_driver_sql("select 1").scalar())
        print("engine_connect")
        print(branch)

    @event.listens_for(ENGINE.sync_engine, "checkout")
    def my_on_checkout(dbapi_conn, connection_rec, connection_proxy):
        print("pool checkout")
        print(dbapi_conn, connection_rec, connection_proxy)


@asynccontextmanager
async def get_connection_ctx_mgr():
    async with ENGINE.connect() as connection:
        connection_fairy = await connection.get_raw_connection()

        # the really-real innermost driver connection is available
        # from the .driver_connection attribute
        raw_asyncio_connection = connection_fairy.driver_connection
        yield raw_asyncio_connection


def get_pool():
    return POOL


def get_engine():
    return ENGINE


def initialize_schema() -> strawberry.Schema:
    global SCHEMA
    loader = StrawberrySQLAlchemyLoader(async_bind_factory=ASYNC_SESSION)

    class CustomInfo(Info):
        @property
        def context(self) -> ContextType:
            return {
                "sqlalchemy_loader": loader,
            }

    @strawberry.type
    class Query:
        environments: typing.List[Environment] = strawberry.field(resolver=Environment.fetch_all)
        projects: typing.List[Project] = strawberry.field(resolver=Project.fetch_all)

    SCHEMA = strawberry.Schema(query=Query, config=StrawberryConfig(info_class=CustomInfo))
    return SCHEMA
