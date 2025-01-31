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

import pytest

import inmanta.graphql.models as models
import inmanta.graphql.schema as schema
import strawberry
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from strawberry.types.info import ContextType
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader


@pytest.fixture
async def setup_database(postgres_db, database_name):
    # Initialize DB
    conn_string = (
        f"postgresql+asyncpg://{postgres_db.user}:{postgres_db.password}@{postgres_db.host}:{postgres_db.port}/{database_name}"
    )
    # Force reinitialization of schema with the correct connection string
    schema.initialize_schema(conn_string)
    async with schema.get_async_session(conn_string) as session:
        project_1 = models.Project(
            id="00000000-1234-5678-1234-000000000001",
            name="test-proj-1",
            environments=[
                models.Environment(
                    id="11111111-1234-5678-1234-000000000001",
                    name="test-env-1",
                    halted=False,
                    notifications=[
                        models.Notification(
                            id="22222222-1234-5678-1234-000000000000",
                            created=datetime.datetime.now(),
                            title="New notification",
                            message="This is a notification",
                            severity="message",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                        models.Notification(
                            id="22222222-1234-5678-1234-000000000001",
                            created=datetime.datetime.now(),
                            title="Another notification",
                            message="This is another notification",
                            severity="error",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                    ],
                    # settings=[
                    #     models.EnvironmentSetting(
                    #         name="setting for env test-env-1",
                    #         type="str",
                    #         default="default",
                    #         recompile=False,
                    #         update_model=False,
                    #         agent_restart=False,
                    #         doc="this is env_setting_1",
                    #     ),
                    #     models.EnvironmentSetting(
                    #         name="another setting for env test-env-1",
                    #         type="str",
                    #         default="default",
                    #         recompile=False,
                    #         update_model=False,
                    #         agent_restart=False,
                    #         doc="this is env_setting_1",
                    #     ),
                    # ],
                )
            ],
        )
        project_2 = models.Project(
            id="00000000-1234-5678-1234-100000000001",
            name="test-proj-2",
            environments=[
                models.Environment(
                    id="11111111-1234-5678-1234-100000000001",
                    name="test-env-2",
                    halted=False,
                    notifications=[
                        models.Notification(
                            id="22222222-1234-5678-1234-100000000000",
                            created=datetime.datetime.now(),
                            title="New notification",
                            message="This is a notification 2",
                            severity="message",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                        models.Notification(
                            id="22222222-1234-5678-1234-100000000001",
                            created=datetime.datetime.now(),
                            title="Another notification",
                            message="This is another notification 2",
                            severity="error",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                    ],
                    # settings=[
                    #     models.EnvironmentSetting(
                    #         name="setting for env test-env-2",
                    #         type="str",
                    #         default="default",
                    #         recompile=False,
                    #         update_model=False,
                    #         agent_restart=False,
                    #         doc="this is env_setting_1",
                    #     ),
                    #     models.EnvironmentSetting(
                    #         name="another setting for env test-env-2",
                    #         type="str",
                    #         default="default",
                    #         recompile=False,
                    #         update_model=False,
                    #         agent_restart=False,
                    #         doc="this is env_setting_1",
                    #     ),
                    # ],
                ),
                models.Environment(
                    id="11111111-1234-5678-1234-100000000002",
                    name="test-env-3",
                    halted=False,
                    notifications=[
                        models.Notification(
                            id="22222222-1234-5678-1234-200000000000",
                            created=datetime.datetime.now(),
                            title="New notification",
                            message="This is a notification 3",
                            severity="message",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                        models.Notification(
                            id="22222222-1234-5678-1234-200000000001",
                            created=datetime.datetime.now(),
                            title="Another notification",
                            message="This is another notification 4",
                            severity="error",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                    ],
                    # settings=[
                    #     models.EnvironmentSetting(
                    #         name="setting for env test-env-3",
                    #         type="str",
                    #         default="default",
                    #         recompile=False,
                    #         update_model=False,
                    #         agent_restart=False,
                    #         doc="this is env_setting_1",
                    #     ),
                    #     models.EnvironmentSetting(
                    #         name="another setting for env test-env-4",
                    #         type="str",
                    #         default="default",
                    #         recompile=False,
                    #         update_model=False,
                    #         agent_restart=False,
                    #         doc="this is env_setting_1",
                    #     ),
                    # ],
                ),
            ],
        )
        session.add_all([project_1, project_2])
        await session.commit()
        await session.flush()
        schema.mapper.finalize()


async def test_query_projects(server, client, setup_database):
    """
    Display basic querying capabilities
    """
    query = """
{
  projects {
    id
    name
    environments {
        edges {
            node {
              id
              projectRelationship {
                id
                name
                environments {
                    edges {
                        node {
                            name
                        }
                    }
                }
              }
            }
        }
    }
  }
}
    """
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == {
        "data": {
            "projects": [
                {
                    "environments": {"edges": [{"node": {"id": "11111111-1234-5678-1234-000000000001"}}]},
                    "id": "00000000-1234-5678-1234-000000000001",
                    "name": "test-proj-1",
                },
                {
                    "environments": {
                        "edges": [
                            {"node": {"id": "11111111-1234-5678-1234-100000000001"}},
                            {"node": {"id": "11111111-1234-5678-1234-100000000002"}},
                        ]
                    },
                    "id": "00000000-1234-5678-1234-100000000001",
                    "name": "test-proj-2",
                },
            ]
        },
        "errors": None,
        "extensions": {},
    }


async def test_query_projects_with_filtering(server, client, setup_database):
    """
    Display basic filtering capabilities
    """
    query_filter_on = """
{
  projects(id: "00000000-1234-5678-1234-100000000001"){
    id
    }
}
    """
    filtered_data = [{"id": "00000000-1234-5678-1234-100000000001"}]

    query_filter_off = """
{
  projects{
    id
    }
}
        """
    unfiltered_data = [
        {"id": "00000000-1234-5678-1234-000000000001"},
        {"id": "00000000-1234-5678-1234-100000000001"},
    ]
    scenarios = [
        (query_filter_on, filtered_data),
        (query_filter_off, unfiltered_data),
    ]
    for query, expected_data in scenarios:
        result = await client.graphql(query=query)
        assert result.code == 200
        assert result.result["data"] == {
            "data": {"projects": expected_data},
            "errors": None,
            "extensions": {},
        }


async def test_query_path(server, client, setup_database):
    """
    This test shows capabilities to trigger different sql queries
    based on the graphql input query


    For example
    - a query that joins environment and project tables when querying project -> environments
    or
    - a query that solely relies on the environment table.
    """
    query_via_project = """
{
  projects(id: "00000000-1234-5678-1234-000000000001") {
    id
    environments {
        edges {
            node {
                id
                name
            }
        }
    }
  }
}
    """
    expected_data_via_project = {
        "data": {
            "projects": [
                {
                    "environments": {"edges": [{"node": {"id": "11111111-1234-5678-1234-000000000001", "name": "test-env-1"}}]},
                    "id": "00000000-1234-5678-1234-000000000001",
                }
            ]
        },
        "errors": None,
        "extensions": {},
    }
    query_via_environments = """
{
  environments(id: "11111111-1234-5678-1234-000000000001") {
    id
    name
  }
}
        """
    expected_data_via_environment = {
        "data": {"environments": [{"id": "11111111-1234-5678-1234-000000000001", "name": "test-env-1"}]},
        "errors": None,
        "extensions": {},
    }
    scenarios = [
        (query_via_project, expected_data_via_project),
        (query_via_environments, expected_data_via_environment),
    ]
    for query, expected_data in scenarios:
        result = await client.graphql(query=query)
        assert result.code == 200
        assert result.result["data"] == expected_data
