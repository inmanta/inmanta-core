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

import asyncio

from inmanta import data
from inmanta.server.server import Server
from inmanta.server.services.compilerservice import CompilerService


async def test_server_status(server, client):
    result = await client.get_server_status()

    assert result.code == 200
    status = result.result["data"]
    assert "version" in status
    assert "product" in status
    assert "edition" in status

    assert len([x for x in status["slices"] if x["name"] == "core.server"]) == 1

    db_status = [x for x in status["slices"] if x["name"] == "core.database"]
    assert len([x for x in status["slices"] if x["name"] == "core.database"]) == 1
    assert db_status[0]["status"]["connected"] is True

    assert "features" in status
    assert len(status["features"]) > 0


async def test_server_status_database_unreachable(server, client):
    await data.Environment.close_connection_pool()
    result = await client.get_server_status()
    assert result.code == 200
    database_slice = None
    for slice in result.result["data"]["slices"]:
        if slice["name"] == "core.database":
            database_slice = slice
    assert database_slice
    assert not database_slice["status"]["connected"]


async def test_server_status_timeout(server, client, monkeypatch):
    monkeypatch.setattr(Server, "GET_SERVER_STATUS_TIMEOUT", 0.1)

    async def hang(self):
        await asyncio.sleep(0.2)
        return {}

    monkeypatch.setattr(CompilerService, "get_status", hang)

    result = await client.get_server_status()
    assert result.code == 200
    compiler_slice = None
    for slice in result.result["data"]["slices"]:
        if slice["name"] == "core.compiler":
            compiler_slice = slice
    assert compiler_slice
    assert "error" in compiler_slice["status"]
