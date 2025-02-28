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
from inmanta.data import get_session


@pytest.fixture
async def setup_database():
    # Initialize DB
    async with get_session() as session:
        project = models.Project(id=uuid.UUID("00000000-1234-5678-1234-000000000001"), name="test-proj")
        environment_1 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000001"),
            name="test-env-b",
            project=project.id,
            halted=False,
            settings={
                "enable_lsm_expert_mode": False,
            },
        )
        environment_2 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000002"),
            name="test-env-c",
            project=project.id,
            halted=False,
            settings={
                "enable_lsm_expert_mode": True,
            },
        )
        environment_3 = models.Environment(
            id=uuid.UUID("11111111-1234-5678-1234-000000000003"),
            name="test-env-a",
            project=project.id,
            halted=True,
        )
        session.add_all([project, environment_1, environment_2, environment_3])
        await session.commit()
        await session.flush()


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
    Display basic paging capabilities
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


async def test_query_environments_with_sorting(server, client, setup_database):
    """
    Display basic sorting capabilities
    """
    query = """
{
    environments(%s){
        edges {
            node {
              id
              name
            }
        }
    }
}
"""
    test_cases = [
        ('orderBy:{name: "asc"}', ["test-env-a", "test-env-b", "test-env-c"]),
        ('orderBy:{name: "desc"}', ["test-env-c", "test-env-b", "test-env-a"]),
        ('orderBy:{id: "asc"}', ["test-env-b", "test-env-c", "test-env-a"]),
        ('orderBy:{id: "desc"}', ["test-env-a", "test-env-c", "test-env-b"]),
    ]

    for test_case in test_cases:
        result = await client.graphql(query=query % test_case[0])
        assert result.code == 200
        results = result.result["data"]["data"]["environments"]["edges"]
        assert [node["node"]["name"] for node in results] == test_case[1]


async def test_query_environments_with_paging(server, client, setup_database):
    """
    Display basic paging capabilities
    """
    async with get_session() as session:
        project = models.Project(id=uuid.UUID("00000000-1234-5678-1234-000000000002"), name="test-proj-2")
        instances = [project]
        for i in range(10):
            instances.append(
                models.Environment(
                    id=uuid.UUID(f"21111111-1234-5678-1234-00000000000{i}"),
                    name=f"test-env-{i}",
                    project=project.id,
                    halted=False,
                )
            )
        session.add_all(instances)
        await session.commit()
        await session.flush()
    query = """
{
    environments(%s){
        pageInfo{
            startCursor,
            endCursor,
            hasPreviousPage,
            hasNextPage
        }
        edges {
            cursor
            node {
              id
              name
            }
        }
    }
}
"""
    test_cases = [
        ("first: 3", ["test-env-b", "test-env-c", "test-env-a"]),
        ("first: 5", ["test-env-b", "test-env-c", "test-env-a", "test-env-0", "test-env-1"]),
        ("last: 5", ["test-env-5", "test-env-6", "test-env-7", "test-env-8", "test-env-9"]),
    ]

    for test_case in test_cases:
        result = await client.graphql(query=query % test_case[0])
        assert result.code == 200
        results = result.result["data"]["data"]["environments"]["edges"]
        assert [node["node"]["name"] for node in results] == test_case[1]

    result = await client.graphql(query=query % "first: 5")
    assert result.code == 200
    environments = result.result["data"]["data"]["environments"]
    results = environments["edges"]
    assert len(results) == 5
    first_cursor = results[0]["cursor"]
    last_cursor = results[4]["cursor"]
    assert environments["pageInfo"]["startCursor"] == first_cursor
    assert environments["pageInfo"]["endCursor"] == last_cursor
    assert environments["pageInfo"]["hasNextPage"] is True
    assert environments["pageInfo"]["hasPreviousPage"] is False

    second_to_last_cursor = results[3]["cursor"]

    result = await client.graphql(query=query % f'first: 5, after:"{second_to_last_cursor}"')
    assert result.code == 200
    environments = result.result["data"]["data"]["environments"]
    results = environments["edges"]
    assert len(results) == 5
    first_cursor = results[0]["cursor"]
    assert first_cursor == last_cursor
    new_last_cursor = results[4]["cursor"]
    assert environments["pageInfo"]["startCursor"] == first_cursor
    assert environments["pageInfo"]["endCursor"] == new_last_cursor
    assert environments["pageInfo"]["hasNextPage"] is True
    assert environments["pageInfo"]["hasPreviousPage"] is True
