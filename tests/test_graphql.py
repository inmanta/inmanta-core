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

import uuid

import pytest

import inmanta.data.sqlalchemy as models
import inmanta.graphql.schema as schema
from inmanta.data import get_session


@pytest.fixture
async def setup_database():
    # Initialize DB
    async with get_session() as session:
        project = models.Project(id=uuid.UUID("00000000-1234-5678-1234-000000000001"), name="test-proj")
        environment_1 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000001"),
            name="test-env-1",
            project=project.id,
            halted=False,
            settings={
                "enable_lsm_expert_mode": False,
            },
        )
        environment_2 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000002"),
            name="test-env-2",
            project=project.id,
            halted=False,
            settings={
                "enable_lsm_expert_mode": True,
            },
        )
        environment_3 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000003"),
            name="test-env-3",
            project=project.id,
            halted=True,
        )
        session.add_all([project, environment_1, environment_2, environment_3])
        await session.commit()
        await session.flush()
        schema.mapper.finalize()


async def test_query_environment_project(server, client, setup_database):
    """
    Display basic querying capabilities with recursive relationships
    """
    query = """
{
    environments {
        edges {
            node {
              id
              halted
              isExpertMode
              project
              project_{
                name
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
            "environments": {
                "edges": [
                    {
                        "node": {
                            "halted": False,
                            "id": "11111111-1234-5678-1234-000000000001",
                            "isExpertMode": False,
                            "project": "00000000-1234-5678-1234-000000000001",
                            "project_": {"name": "test-proj"},
                        }
                    },
                    {
                        "node": {
                            "halted": False,
                            "id": "11111111-1234-5678-1234-000000000002",
                            "isExpertMode": True,
                            "project": "00000000-1234-5678-1234-000000000001",
                            "project_": {"name": "test-proj"},
                        }
                    },
                    {
                        "node": {
                            "halted": True,
                            "id": "11111111-1234-5678-1234-000000000003",
                            "isExpertMode": False,
                            "project": "00000000-1234-5678-1234-000000000001",
                            "project_": {"name": "test-proj"},
                        }
                    },
                ]
            }
        },
        "errors": None,
        "extensions": {},
    }


async def test_query_environments_with_filtering(server, client, setup_database):
    """
    Display basic filtering capabilities
    """
    query = """
{
    environments(filter:{id: "11111111-1234-5678-1234-000000000002"}) {
        edges {
            node {
              id
              halted
              isExpertMode
              project
            }
        }
    }
}
"""
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == {
        "data": {
            "environments": {
                "edges": [
                    {
                        "node": {
                            "halted": False,
                            "id": "11111111-1234-5678-1234-000000000002",
                            "isExpertMode": True,
                            "project": "00000000-1234-5678-1234-000000000001",
                        }
                    }
                ]
            }
        },
        "errors": None,
        "extensions": {},
    }
