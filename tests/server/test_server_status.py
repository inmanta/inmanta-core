"""
    Copyright 2019 Inmanta

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
import pytest


@pytest.mark.asyncio
async def test_server_status(server, client):
    result = await client.get_server_status()

    assert result.code == 200
    status = result.result
    assert "version" in status

    assert len([x for x in status["slices"] if x["name"] == "core.server"]) == 1

    db_status = [x for x in status["slices"] if x["name"] == "core.database"]
    assert len([x for x in status["slices"] if x["name"] == "core.database"]) == 1
    assert db_status[0]["status"]["connected"] is True
