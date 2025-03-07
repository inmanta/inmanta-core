import logging
import uuid

import pytest

from sqlalchemy import select, insert

import inmanta.data.sqlalchemy as models
from inmanta.data import get_session
from inmanta.data.sqlalchemy import ModuleRequirements, FilesInModule

LOGGER = logging.getLogger(__name__)



@pytest.fixture
async def setup_database(project_default):
    # Initialize DB
    async with get_session() as session:
        environment_1 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000001"),
            name="test-env-b",
            project=project_default,
            halted=False,
            settings={
                "enable_lsm_expert_mode": False,
            },
        )
        environment_2 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000002"),
            name="test-env-c",
            project=project_default,
            halted=False,
            settings={
                "enable_lsm_expert_mode": True,
            },
        )
        environment_3 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000003"),
            name="test-env-a",
            project=project_default,
            halted=True,
        )
        session.add_all([environment_1, environment_2, environment_3])
        await session.commit()
        await session.flush()



async def test_sql_alchemy_read(client, server):
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

    stmt = select(models.Environment.id, models.Environment.name).order_by(models.Environment.name)
    async with get_session() as session:
        result_execute = await session.execute(stmt)
        assert result_execute.all() == [
            (uuid.UUID(env_1_id), env_1_name),
            (uuid.UUID(env_2_id), env_2_name),
        ]


async def test_sql_alchemy_write(client, server):
    """
    Create projects and envs using sql alchemy
    Read using regular endpoints
    """


    # WRITE - SQL Alchemy

    proj_id = uuid.uuid4()
    stmt = insert(models.Project)
    data = [
        {
            "id": proj_id,
            "name": "proj_1"
        }
    ]

    async with get_session() as session:
        result_execute = await session.execute(stmt, data)
        await session.commit()

    stmt = insert(models.Environment).returning(models.Environment.id)
    data = [
        {
            "id": uuid.uuid4(),
            "name": "env_1",
            "project": proj_id
        }
    ]

    async with get_session() as session:
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
    stmt = insert(models.Project)
    data = [
        {
            "id": proj_id,
            "name": "proj_1"
        }
    ]

    async with get_session() as session:
        result_execute = await session.execute(stmt, data)
        await session.commit()

    stmt = insert(models.Environment).returning(models.Environment.id)
    data = [
        {
            "id": uuid.uuid4(),
            "name": "env_1",
            "project": proj_id
        }
    ]

    async with get_session() as session:
        result_execute = await session.execute(stmt, data)
        await session.commit()
        env_id = result_execute.scalars().all()[0]


    # READ - SQL Alchemy

    stmt = select(models.Environment.id, models.Environment.name).order_by(models.Environment.name)
    async with get_session() as session:
        result_execute = await session.execute(stmt)
        assert result_execute.all() == [
            (env_id, "env_1"),
        ]


async def test_code_upload_and_retrieval(server, client, environment):
    """
    Test code upload for different modules and versions.
    Test code retrieval.
    """
    await client.upload_file(hv, content=base64.b64encode(data).decode("ascii"))
    return hv


    module_requirements_stmt = insert(ModuleRequirements)
    files_in_module_stmt = insert(FilesInModule)

    modules_data = {
        'minimalwaitingmodule': {
            'files_in_module': [{
                                    'hash': 'ac20beb5c6c92237a4ad0d442926ca66f35dab32',
                                    'module_name': 'inmanta_plugins.minimalwaitingmodule',
                                    'path': '/home/hugo/work/inmanta/github-repos/inmanta-core/tests/data/modules/minimalwaitingmodule/plugins/__init__.py',
                                    'requires': []}],
            'module_name': 'minimalwaitingmodule',
            'module_version': '7eaaa3c767d79d8348678afa16db69602e53c66c'},
        'std': {
            'files_in_module': [{
                                    'hash': '783979f77d1a40fa9b9c54c445c6f090de5797a1',
                                    'module_name': 'inmanta_plugins.std.resources',
                                    'path': '/tmp/tmp8kf8r_bg/std/plugins/resources.py',
                                    'requires': ['Jinja2>=3.1,<4', 'email_validator>=1.3,<3', 'pydantic>=1.10,<3',
                                                 'inmanta-core>=8.7.0.dev']}, {
                                    'hash': '4ac629bdc461bf185971b82b4fc3dd457fba3fdd',
                                    'module_name': 'inmanta_plugins.std.types',
                                    'path': '/tmp/tmp8kf8r_bg/std/plugins/types.py',
                                    'requires': ['Jinja2>=3.1,<4', 'email_validator>=1.3,<3', 'pydantic>=1.10,<3',
                                                 'inmanta-core>=8.7.0.dev']}, {
                                    'hash': '835f0e49da1e099d13e87b95d7f296ff68b57348',
                                    'module_name': 'inmanta_plugins.std',
                                    'path': '/tmp/tmp8kf8r_bg/std/plugins/__init__.py',
                                    'requires': ['Jinja2>=3.1,<4', 'email_validator>=1.3,<3', 'pydantic>=1.10,<3',
                                                 'inmanta-core>=8.7.0.dev']}],
            'module_name': 'std',
            'module_version': '6e929def427efefe814ce4ae0c00a9653628fdcb'}}
    module_requirements_data = []
    files_in_module_data = []
    for module_name, python_module in modules_data.items():

        requirements: set[str] = set()

        for file in python_module["files_in_module"]:
            file_in_module = {
                "module_name": module_name,
                "module_version": python_module["module_version"],
                "environment": environment,
                "file_content_hash": file['hash'],
                "file_path": file['path'],
            }
            requirements.update(file['requires'])
            files_in_module_data.append(file_in_module)

        module_requirements = {
            "module_name": module_name,
            "module_version": python_module["module_version"],
            "environment": environment,
            "requirements": requirements,
        }

        module_requirements_data.append(module_requirements)

    async with get_session() as session:
        await session.execute(module_requirements_stmt, module_requirements_data)
        await session.execute(files_in_module_stmt, files_in_module_data)
        await session.commit()
    #

    # # ------------ Code upload ------------
    #
    #
    # # WRITE - SQL Alchemy
    #
    # proj_id = uuid.uuid4()
    # env_id = uuid.uuid4()
    # stmt = insert(models.FilesInModule)
    # data = [
    #     {
    #         "module_name": f"module_{module_index}",
    #         "module_version": f"{major}.2.3",
    #         "environment": env_id ,
    #         "file_content_hash":,
    #         "file_path":f"/path/to/file_{file_index}",
    #     }
    # ]
    #
    # async with get_session() as session:
    #     result_execute = await session.execute(stmt, data)
    #     await session.commit()
    #
    # stmt = insert(models.Environment).returning(models.Environment.id)
    # data = [
    #     {
    #         "id": uuid.uuid4(),
    #         "name": "env_1",
    #         "project": proj_id
    #     }
    # ]
    #
    # async with get_session() as session:
    #     result_execute = await session.execute(stmt, data)
    #     await session.commit()
    #     env_id = result_execute.scalars().all()[0]
    #
    #
    # # READ - SQL Alchemy
    #
    # stmt = select(models.Environment.id, models.Environment.name).order_by(models.Environment.name)
    # async with get_session() as session:
    #     result_execute = await session.execute(stmt)
    #     assert result_execute.all() == [
    #         (env_id, "env_1"),
    #     ]
