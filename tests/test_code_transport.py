def test_basic_read_write(server):
    """

    :return:
    """



import datetime
import logging
import subprocess
import sys
import uuid

import pytest

from sqlalchemy import select, insert

from inmanta.data.sqlalchemy import Environment, Project
from inmanta.data import get_session

LOGGER = logging.getLogger(__name__)


@pytest.fixture
async def setup_database(postgres_db, database_name):
    # Initialize DB

    async with get_session() as session:
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



async def test_sql_alchemy_read(client, server, setup_database_no_data):
    """
    Create project and envs using regular endpoints
    Read using sql alchemy capabilities
    """

    # WRITE - Regular API

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

    # READ - SQL Alchemy

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


    # WRITE - SQL Alchemy

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

    # READ - Regular API

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

async def test_basic_read_write(server):

    # WRITE - SQL Alchemy

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


    # READ - SQL Alchemy

    stmt = select(Environment.id, Environment.name).order_by(Environment.name)
    async with get_session() as session:
        result_execute = await session.execute(stmt)
        assert result_execute.all() == [
            (uuid.UUID(env_1_id), env_1_name),
            (uuid.UUID(env_2_id), env_2_name),
        ]
