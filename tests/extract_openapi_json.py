"""
    Copyright 2020 Inmanta

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
import json

import pytest


@pytest.mark.asyncio
async def test_extract_openapi_for_docs(server, client):
    result = await client.get_api_docs("openapi")
    assert result.code == 200
    content = result.result["data"]
    content["servers"][0]["url"] = "http://<inmanta-server-address>"
    content["info"]["description"] = "Back to <a href='./index.html'>Main documentation</a> for more information"
    json_content = json.dumps(content)
    with open("openapi.json", "w") as json_file:
        json_file.write(json_content)
