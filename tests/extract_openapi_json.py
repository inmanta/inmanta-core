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
