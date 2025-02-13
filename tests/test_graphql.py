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
import logging
import subprocess
import sys
import uuid

import pytest

import inmanta.graphql.models as models
import inmanta.graphql.schema as schema

from sqlalchemy import select, insert

from inmanta.graphql.models import Environment, Project
from inmanta.graphql.schema import get_async_session, start_engine, get_pool, get_raw_connection

from sqlalchemy import text

LOGGER = logging.getLogger(__name__)

@pytest.fixture
def sql_alchemy_connection_string(postgres_db, database_name):
    yield f"postgresql+asyncpg://{postgres_db.user}:{postgres_db.password}@{postgres_db.host}:{postgres_db.port}/{database_name}"

@pytest.fixture
async def setup_database_no_data(sql_alchemy_connection_string):
    # Initialize DB
    # Force reinitialization of schema with the correct connection string
    schema.initialize_schema(sql_alchemy_connection_string)

@pytest.fixture
def start_sqlalchemy_engine(sql_alchemy_connection_string):
    start_engine(
        url=sql_alchemy_connection_string,
        pool_size=2,
        max_overflow=4,
        pool_timeout=60,
        echo=True,
    )
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
            id=uuid.UUID("00000000-1234-5678-1234-000000000001"),
            name="test-proj-1",
            environments=[
                models.Environment(
                    id=uuid.UUID("11111111-1234-5678-1234-000000000001"),
                    name="test-env-1",
                    halted=False,
                    notification=[
                        models.Notification(
                            id=uuid.UUID("22222222-1234-5678-1234-000000000000"),
                            created=datetime.datetime.now(),
                            title="New notification",
                            message="This is a notification",
                            severity="message",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                        models.Notification(
                            id=uuid.UUID("22222222-1234-5678-1234-000000000001"),
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
            id=uuid.UUID("00000000-1234-5678-1234-100000000001"),
            name="test-proj-2",
            environments=[
                models.Environment(
                    id=uuid.UUID("11111111-1234-5678-1234-100000000001"),
                    name="test-env-2",
                    halted=False,
                    notification=[
                        models.Notification(
                            id=uuid.UUID("22222222-1234-5678-1234-100000000000"),
                            created=datetime.datetime.now(),
                            title="New notification",
                            message="This is a notification 2",
                            severity="message",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                        models.Notification(
                            id=uuid.UUID("22222222-1234-5678-1234-100000000001"),
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
                    id=uuid.UUID("11111111-1234-5678-1234-100000000002"),
                    name="test-env-3",
                    halted=False,
                    notification=[
                        models.Notification(
                            id=uuid.UUID("22222222-1234-5678-1234-200000000000"),
                            created=datetime.datetime.now(),
                            title="New notification",
                            message="This is a notification 3",
                            severity="message",
                            read=False,
                            cleared=False,
                            uri=None,
                        ),
                        models.Notification(
                            id=uuid.UUID("22222222-1234-5678-1234-200000000001"),
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


# async def test_generate_sqlalchemy_models(postgres_db, database_name):
#     conn_string = (
#         f"postgresql+asyncpg://{postgres_db.user}:{postgres_db.password}@{postgres_db.host}:{postgres_db.port}/{database_name}"
#     )
#     subprocess.run(["sqlacodegen", conn_string])


async def test_query_projects(server, client, setup_database):
    """
    Display basic querying capabilities with recursive relationships
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
              project_ {
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
                    "environments": {
                        "edges": [
                            {
                                "node": {
                                    "id": "11111111-1234-5678-1234-000000000001",
                                    "project_": {
                                        "environments": {"edges": [{"node": {"name": "test-env-1"}}]},
                                        "id": "00000000-1234-5678-1234-000000000001",
                                        "name": "test-proj-1",
                                    },
                                }
                            }
                        ]
                    },
                    "id": "00000000-1234-5678-1234-000000000001",
                    "name": "test-proj-1",
                },
                {
                    "environments": {
                        "edges": [
                            {
                                "node": {
                                    "id": "11111111-1234-5678-1234-100000000001",
                                    "project_": {
                                        "environments": {
                                            "edges": [{"node": {"name": "test-env-2"}}, {"node": {"name": "test-env-3"}}]
                                        },
                                        "id": "00000000-1234-5678-1234-100000000001",
                                        "name": "test-proj-2",
                                    },
                                }
                            },
                            {
                                "node": {
                                    "id": "11111111-1234-5678-1234-100000000002",
                                    "project_": {
                                        "environments": {
                                            "edges": [{"node": {"name": "test-env-2"}}, {"node": {"name": "test-env-3"}}]
                                        },
                                        "id": "00000000-1234-5678-1234-100000000001",
                                        "name": "test-proj-2",
                                    },
                                }
                            },
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


async def test_sql_alchemy_read(client, server, setup_database_no_data):
    """
    Create project and envs using regular endpoints
    Read using sql alchemy capabilities
    """

    # Create project
    result = await client.create_project("test_project")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # Create environments
    env_1_name = "env_1"
    result = await client.create_environment(project_id=project_id, name=env_1_name)
    assert result.code == 200
    env_1_id = result.result["environment"]["id"]

    env_2_name = "env_2"
    result = await client.create_environment(project_id=project_id, name=env_2_name)
    assert result.code == 200
    env_2_id = result.result["environment"]["id"]

    stmt = select(Environment.id, Environment.name).order_by(Environment.name)
    async with get_async_session() as session:
        result_execute = await session.execute(stmt)
        assert result_execute.all() == [
            (uuid.UUID(env_1_id), env_1_name),
            (uuid.UUID(env_2_id), env_2_name),
        ]


async def test_sql_alchemy_write(client, server, setup_database_no_data):
    """
    Create projects and envs using sql alchemy
    Read using regular endpoints
    """
    proj_id = uuid.uuid4()
    stmt = insert(Project)
    data = [
        {
            "id": proj_id,
            "name": "proj_1"
        }
    ]

    async with get_async_session() as session:
        result_execute = await session.execute(stmt, data)
        await session.commit()

    stmt = insert(Environment).returning(Environment.id)
    data = [
        {
            "id": uuid.uuid4(),
            "name": "env_1",
            "project": proj_id
        }
    ]

    async with get_async_session() as session:
        result_execute = await session.execute(stmt, data)
        await session.commit()
        env_id = result_execute.scalars().all()[0]

    result = await client.list_environments()
    assert result.code == 200
    assert "environments" in result.result
    assert result.result["environments"] == [
        {
             'description': '',
             'halted': False,
             'icon': '',
             'id': str(env_id),
             'is_marked_for_deletion': False,
             'name': 'env_1',
             'project': str(proj_id),
             'repo_branch': '',
             'repo_url': '',
             'settings': {}
        }
    ]

    result = await client.list_projects()
    assert result.code == 200
    assert "projects" in result.result
    assert result.result["projects"] == [
        {
            'environments': [str(env_id)],
            'id': str(proj_id),
            'name': 'proj_1'
        }
    ]


async def test_sql_alchemy_connection_pool(client, server, setup_database_no_data):
    """
    Create projects and envs using sql alchemy
    Read using regular endpoints
    """
    proj_id = uuid.uuid4()
    stmt = insert(Project)
    data = [
        {
            "id": proj_id,
            "name": "proj_1"
        }
    ]

    async with get_async_session() as session:
        result_execute = await session.execute(stmt, data)
        await session.commit()

    stmt = insert(Environment).returning(Environment.id)
    data = [
        {
            "id": uuid.uuid4(),
            "name": "env_1",
            "project": proj_id
        }
    ]

    async with get_async_session() as session:
        result_execute = await session.execute(stmt, data)
        await session.commit()
        env_id = result_execute.scalars().all()[0]

    result = await client.list_environments()
    assert result.code == 200
    assert "environments" in result.result
    assert result.result["environments"] == [
        {
             'description': '',
             'halted': False,
             'icon': '',
             'id': str(env_id),
             'is_marked_for_deletion': False,
             'name': 'env_1',
             'project': str(proj_id),
             'repo_branch': '',
             'repo_url': '',
             'settings': {}
        }
    ]

    result = await client.list_projects()
    assert result.code == 200
    assert "projects" in result.result
    assert result.result["projects"] == [
        {
            'environments': [str(env_id)],
            'id': str(proj_id),
            'name': 'proj_1'
        }
    ]


async def test_sql_alchemy_project_create(client, server):
    """
    Create project and envs using regular endpoints
    Read using sql alchemy capabilities
    """

    # Create project
    ids = []
    names = []
    project_name: str = "test_project0"
    result = await client.create_project(project_name)
    assert result.code == 200
    ids.append(result.result["project"]["id"])
    names.append(project_name)

    project_name: str = "test_project1"
    result = await client.create_project(project_name)
    assert result.code == 200
    ids.append(result.result["project"]["id"])
    names.append(project_name)

    project_name: str = "test_project2"
    result = await client.create_project(project_name)
    assert result.code == 200
    ids.append(result.result["project"]["id"])
    names.append(project_name)


    result = await client.list_projects()
    assert result.code == 200
    assert "projects" in result.result
    assert result.result["projects"] == [
        {
            'id': str(project_id),
            'name': project_name
        }
        for (project_id, project_name) in zip(ids, names)
    ]


async def test_sql_alchemy_pool_reuse(client, server, setup_database_no_data):
    # https://docs.sqlalchemy.org/en/20/core/engines.html#custom-dbapi-connect-arguments-on-connect-routines
    pass

    async with get_async_session() as session:

        pass



async def test_sql_alchemy_pool_reusedd(start_sqlalchemy_engine):
    pass
    # https://docs.sqlalchemy.org/en/20/core/engines.html#custom-dbapi-connect-arguments-on-connect-routines



    # async with get_async_session() as session:
    #     pass
    #     res = await session.execute(text("select 2"))
    #     print("go", res.scalar())
        # result_execute = await session.execute(stmt, data)
        # await session.commit()


    # pool = get_pool()
    # with pool.connect() as conn:
    #     pass
    #     res = await session.execute(text("select 2"))
    #     print("go", res.scalar())

    # conn = await get_raw_connection()
    # pass
    # print(conn.dbapi_connection)
