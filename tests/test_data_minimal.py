"""
Copyright 2018 Inmanta

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
import enum
import logging
import time
import uuid
from collections import abc
from datetime import UTC
from typing import Optional, cast

import asyncpg
import pytest
from asyncpg import Connection, ForeignKeyViolationError

import sqlalchemy
import utils
from inmanta import const, data, util
from inmanta.const import AgentStatus, LogLevel
from inmanta.data import ArgumentCollector, QueryType, get_engine, start_engine, stop_engine
from inmanta.deploy import state
from inmanta.resources import Id
from inmanta.types import ResourceVersionIdStr


async def test_connect_too_small_connection_pool(sqlalchemy_url: str):
    await start_engine(
        url=sqlalchemy_url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
    )
    engine = get_engine()
    assert engine is not None
    connection: Connection = await engine.connect()

    try:
        with pytest.raises(sqlalchemy.exc.TimeoutError):
            await engine.connect()
    finally:
        await connection.close()
        await stop_engine()


async def test_connect_default_parameters(sql_alchemy_engine):
    assert sql_alchemy_engine is not None
    async with sql_alchemy_engine.connect() as connection:
        assert connection is not None


async def test_postgres_client(postgresql_client):
    await postgresql_client.execute("CREATE TABLE test(id serial PRIMARY KEY, name VARCHAR (25) NOT NULL)")
    await postgresql_client.execute("INSERT INTO test VALUES(5, 'jef')")
    records = await postgresql_client.fetch("SELECT * FROM test")
    assert len(records) == 1
    first_record = records[0]
    assert first_record["id"] == 5
    assert first_record["name"] == "jef"
    await postgresql_client.execute("DELETE FROM test WHERE test.id = " + str(first_record["id"]))
    records = await postgresql_client.fetch("SELECT * FROM test")
    assert len(records) == 0


async def test_db_schema_enum_consistency(init_dataclasses_and_load_schema) -> None:
    """
    Verify that enumeration fields defined in data document objects match values defined in the db schema.
    """
    all_db_document_classes: abc.Set[type[data.BaseDocument]] = utils.get_all_subclasses(data.BaseDocument) - {
        data.BaseDocument
    }
    exclude_enums = [state.DeployResult, state.Blocked]  # These enums are modelled in the db using a varchar
    for cls in all_db_document_classes:
        enums: abc.Mapping[str, data.Field] = {
            name: field
            for name, field in cls.get_field_metadata().items()
            if issubclass(field.field_type, enum.Enum) and field.field_type not in exclude_enums
        }
        for enum_column, field in enums.items():
            db_enum_values: abc.Sequence[asyncpg.Record] = await cls._fetch_query(
                """
                SELECT enumlabel
                FROM pg_enum
                INNER JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
                INNER JOIN information_schema.columns c ON pg_type.typname = c.udt_name
                WHERE table_schema='public' AND table_name=$1 AND column_name=$2
                """,
                cls._get_value(cls.table_name()),
                cls._get_value(enum_column),
            )
            # verify the db enum and the Python enum have the exact same values
            assert set(field.field_type) == {
                field._from_db_single(enum_column, record["enumlabel"]) for record in db_enum_values
            }

#
# async def test_project(init_dataclasses_and_load_schema):
#     project = data.Project(name="test")
#     await project.insert()
#
#     projects = await data.Project.get_list(name="test")
#     assert len(projects) == 1
#     assert projects[0].id == project.id
#
#     other = await data.Project.get_by_id(project.id)
#     assert project != other
#     assert project.id == other.id
#
#
# async def test_project_unique(init_dataclasses_and_load_schema):
#     project = data.Project(name="test")
#     await project.insert()
#
#     project = data.Project(name="test")
#     with pytest.raises(asyncpg.UniqueViolationError):
#         await project.insert()
#
#
# def test_project_no_project_name(init_dataclasses_and_load_schema):
#     with pytest.raises(AttributeError):
#         data.Project()
