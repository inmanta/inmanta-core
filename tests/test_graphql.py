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
import uuid

import pytest

import inmanta.data.sqlalchemy as models
from inmanta import const, data
from inmanta.server import SLICE_COMPILER
from inmanta.server.services.compilerservice import CompilerService
from inmanta.util import retry_limited
from utils import run_compile_and_wait_until_compile_is_done


@pytest.fixture
async def setup_database(project_default):
    def add_notifications(env_id: uuid.UUID) -> list[models.Notification]:
        notifications = []
        for i in range(8):
            created = (datetime.datetime.now().astimezone() - datetime.timedelta(days=1)).replace(hour=i)
            notifications.append(
                models.Notification(
                    id=uuid.uuid4(),
                    title="Notification" if i % 2 else "Error",
                    message="Something happened" if i % 2 else "Something bad happened",
                    environment=env_id,
                    severity=const.NotificationSeverity.message if i % 2 else const.NotificationSeverity.error,
                    uri="/api/v2/notification",
                    created=created.astimezone(),
                    read=i in {2, 4},
                    cleared=i in {4, 5},
                )
            )
        return notifications

    # Initialize DB
    async with data.get_session() as session:
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

        session.add_all(
            [
                environment_1,
                environment_2,
                environment_3,
                *add_notifications(environment_1.id),
                *add_notifications(environment_2.id),
            ]
        )
        await session.commit()
        await session.flush()


async def test_graphql_schema(server, client):
    """
    Tests to see if the graphql schema endpoint is working
    """
    result = await client.graphql_schema()
    assert result.code == 200
    assert result.result["data"]["__schema"]


async def test_query_is_expert_mode(server, client, setup_database, project_default):
    """
    Tests the custom attribute isExpertMode
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
                            "project": project_default,
                        }
                    },
                    {
                        "node": {
                            "halted": False,
                            "id": "11111111-1234-5678-1234-000000000002",
                            "isExpertMode": True,
                            "project": project_default,
                        }
                    },
                    {
                        "node": {
                            "halted": True,
                            "id": "11111111-1234-5678-1234-000000000003",
                            "isExpertMode": False,
                            "project": project_default,
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
    async with data.get_session() as session:
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

    # Get the first 5 elements
    result = await client.graphql(query=query % "first: 5")
    assert result.code == 200
    environments = result.result["data"]["data"]["environments"]
    results = environments["edges"]
    assert len(results) == 5
    first_cursor = results[0]["cursor"]
    last_cursor = results[4]["cursor"]
    # Assert that the paging information is correct
    assert environments["pageInfo"]["startCursor"] == first_cursor
    assert environments["pageInfo"]["endCursor"] == last_cursor
    assert environments["pageInfo"]["hasNextPage"] is True
    assert environments["pageInfo"]["hasPreviousPage"] is False

    # Get 5 environments starting from the second to last cursor of the previous result
    second_to_last_cursor = results[3]["cursor"]
    result = await client.graphql(query=query % f'first: 5, after:"{second_to_last_cursor}"')
    assert result.code == 200
    environments = result.result["data"]["data"]["environments"]
    results = environments["edges"]
    assert len(results) == 5
    # Assert that the first cursor of these results is the last from the previous results
    first_cursor = results[0]["cursor"]
    assert first_cursor == last_cursor
    new_last_cursor = results[4]["cursor"]
    assert environments["pageInfo"]["startCursor"] == first_cursor
    assert environments["pageInfo"]["endCursor"] == new_last_cursor
    assert environments["pageInfo"]["hasNextPage"] is True
    assert environments["pageInfo"]["hasPreviousPage"] is True


async def test_is_environment_compiling(server, client, clienthelper, environment, mocked_compiler_service_block):

    compilerslice = server.get_slice(SLICE_COMPILER)
    assert isinstance(compilerslice, CompilerService)
    env = await data.Environment.get_by_id(environment)

    query = """
    {
        environments {
            edges {
                node {
                  id
                  isCompiling
                }
            }
        }
    }
        """

    def get_response(is_compiling: bool) -> dict:
        return {
            "data": {
                "environments": {
                    "edges": [
                        {
                            "node": {
                                "id": environment,
                                "isCompiling": is_compiling,
                            }
                        },
                    ]
                }
            },
            "errors": None,
            "extensions": {},
        }

    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == get_response(is_compiling=False)

    # Trigger compile
    await compilerslice.request_recompile(env=env, force_update=False, do_export=False, remote_id=uuid.uuid4())
    # prevent race conditions where compile request is not yet in queue
    await retry_limited(lambda: compilerslice._env_to_compile_task.get(uuid.UUID(environment), None) is not None, timeout=10)

    # Assert that GraphQL reports that environment is compiling
    result = await client.graphql(query=query)
    assert result.code == 200
    # Check if regular endpoint confirms that it is compiling
    regular_check = await client.is_compiling(environment)
    assert regular_check.code == 200
    assert result.result["data"] == get_response(is_compiling=True)

    # Finish compile
    await run_compile_and_wait_until_compile_is_done(compilerslice, mocked_compiler_service_block, env.id)

    # Assert that GraphQL reports that environment is no longer compiling
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == get_response(is_compiling=False)


async def test_notifications(server, client, setup_database):
    """
    Assert that the notifications query works with filtering and sorting
    """

    query = """
        {
          notifications %s {
              pageInfo{
                startCursor,
                endCursor,
                hasPreviousPage,
                hasNextPage
            }
            edges {
              cursor
              node {
                title
                environment
                created
                cleared
              }
            }
          }
        }
    """
    # Get full list of notifications
    result = await client.graphql(query=query % "")
    assert result.code == 200
    edges = result.result["data"]["data"]["notifications"]["edges"]
    # Environments 1 and 2 have 2 cleared and 6 uncleared notifications
    assert len(edges) == 16

    # Get list of notifications filtered by cleared
    result = await client.graphql(
        query=query
        % """
            (filter: {
              cleared: false
              environment: "11111111-1234-5678-1234-000000000001"
            },
            orderBy: {
                created: "desc"
            })
    """
    )
    assert result.code == 200
    edges = result.result["data"]["data"]["notifications"]["edges"]
    # Environments 1 has 6 uncleared notifications
    assert len(edges) == 6
    # Assert that each notification is uncleared and that the most recent notifications appear first
    # Arbitrary date that is more recent than any of the created notifications
    previous_time = datetime.datetime.now().astimezone()
    for edge in edges:
        assert edge["node"]["cleared"] is False
        assert edge["node"]["environment"] == "11111111-1234-5678-1234-000000000001"
        created = datetime.datetime.fromisoformat(edge["node"]["created"])
        assert created < previous_time
        previous_time = created

    # Get first page of notifications
    result = await client.graphql(
        query=query
        % """
            (filter: {
              cleared: false
              environment: "11111111-1234-5678-1234-000000000001"
            },
            orderBy: {
                created: "desc"
            },
            first: 3)
    """
    )
    assert result.code == 200
    notifications = result.result["data"]["data"]["notifications"]
    pageInfo = notifications["pageInfo"]
    assert pageInfo["hasPreviousPage"] is False
    assert pageInfo["hasNextPage"] is True
    edges = notifications["edges"]
    assert len(edges) == 3
    assert edges[0]["cursor"] == pageInfo["startCursor"]
    assert edges[-1]["cursor"] == pageInfo["endCursor"]
    # Assert that each notification is uncleared and that the most recent notifications appear first
    # Arbitrary date that is more recent than any of the created notifications
    previous_time = datetime.datetime.now().astimezone()
    for edge in edges:
        assert edge["node"]["cleared"] is False
        assert edge["node"]["environment"] == "11111111-1234-5678-1234-000000000001"
        created = datetime.datetime.fromisoformat(edge["node"]["created"])
        assert created < previous_time
        previous_time = created

    # Get first page of notifications
    next_page_filter = (
        """
            (filter: {
              cleared: false
              environment: "11111111-1234-5678-1234-000000000001"
            },
            orderBy: {
                created: "desc"
            },
            first: 3, after: "%s")
    """
        % pageInfo["endCursor"]
    )
    result = await client.graphql(query=query % next_page_filter)
    assert result.code == 200
    notifications = result.result["data"]["data"]["notifications"]
    pageInfo = notifications["pageInfo"]
    assert pageInfo["hasPreviousPage"] is True
    assert pageInfo["hasNextPage"] is False
    edges = notifications["edges"]
    assert len(edges) == 3
    assert edges[0]["cursor"] == pageInfo["startCursor"]
    assert edges[-1]["cursor"] == pageInfo["endCursor"]

    # previous_time is the created time of the last result of the first page
    for edge in edges:
        assert edge["node"]["cleared"] is False
        assert edge["node"]["environment"] == "11111111-1234-5678-1234-000000000001"
        created = datetime.datetime.fromisoformat(edge["node"]["created"])
        assert created < previous_time
        previous_time = created
