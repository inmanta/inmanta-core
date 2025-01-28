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


async def test_test(server, client):
    query = """
{
  books {
    title
    author
  }
}
    """
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == {
        "data": {"books": [{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald"}]},
        "errors": None,
        "extensions": {},
    }



async def test_get_projects(server, client):
    query = """
{
  projects {
    id
    name
    environments
  }
}
    """
    result = await client.graphql(query=query)
    assert result.code == 200
    assert result.result["data"] == {
        "data": {
            "projects": [
                {
                    "id": "",
                    "name": "",
                    "environments": [],
                },{
                    "id": "",
                    "name": "",
                    "environments": [],
                },
            ]
        },
        "errors": None,
        "extensions": {},
    }
