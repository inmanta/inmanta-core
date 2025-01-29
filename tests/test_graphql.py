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


async def test_query_projects(server, client):
    """
    Display basic querying capabilities
    """
    query = """
{
  projects {
    id
    name
    environments {
      id
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
                    "id": "00000000-1234-5678-1234-000000000001",
                    "name": "[get_projects] test-proj-1",
                    "environments": [{
                        "id": "11111111-1234-5678-1234-000000000001"}],
                },
                {
                    "id": "00000000-1234-5678-1234-000000000002",
                    "name": "[get_projects] test-proj-2",
                    "environments": [
                        {
                            "id": "11111111-1234-5678-1234-000000000002"},
                        {
                            "id": "11111111-1234-5678-1234-000000000003"},
                    ],
                },
            ]
        },
        "errors": None,
        "extensions": {},
    }


async def test_query_projects_with_filtering(server, client):
    """
    Display basic filtering capabilities
    """
    query_filter_on = """
{
  projects(id: "00000000-1234-5678-1234-000000000002"){
    id
    }
}
    """
    filtered_data = [{
        "id": "00000000-1234-5678-1234-000000000002"
    }]

    query_filter_off = """
    {
      projects{
        id
        }
    }
        """
    unfiltered_data = [
        {"id": "00000000-1234-5678-1234-000000000001"},
        {"id": "00000000-1234-5678-1234-000000000002"},
    ]
    scenarios = [
        (query_filter_on, filtered_data),
        (query_filter_off, unfiltered_data),
    ]
    for query, expected_data in scenarios:
        result = await client.graphql(query=query)
        assert result.code == 200
        assert result.result["data"] == {
            "data": {
                "projects": expected_data
            },
            "errors": None,
            "extensions": {},
        }


async def test_query_path(server, client):
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
      id
      name
    }
  }
}
    """
    expected_data_via_project = {
        "data": {
            "projects": [
                {
                    "id": "00000000-1234-5678-1234-000000000001",
                    "environments": [
                        {
                            "id": "11111111-1234-5678-1234-000000000001",
                            "name": "[projects.environments] test-env-1"
                        }
                    ]
                }
            ]
        },
        'errors': None,
        'extensions': {}
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
        'data': {
            'environments': [{
                'id': '11111111-1234-5678-1234-000000000001',
                'name': '[get_environments] test-env-1'}]},
        'errors': None,
        'extensions': {}}
    scenarios = [
        (query_via_project, expected_data_via_project),
        (query_via_environments, expected_data_via_environment),
    ]
    for query, expected_data in scenarios:
        result = await client.graphql(query=query)
        assert result.code == 200
        assert result.result["data"] == expected_data
