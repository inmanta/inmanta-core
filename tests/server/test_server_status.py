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

from inmanta import protocol
from inmanta.data import Environment
from inmanta.server.bootloader import InmantaBootloader


@pytest.mark.asyncio
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
    assert len(status["features"]) == 1


@pytest.mark.asyncio
async def test_server_status_database_unreachable(server, client):
    await Environment.close_connection_pool()
    result = await client.get_server_status()
    assert result.code == 200
    database_slice = None
    for slice in result.result["data"]["slices"]:
        if slice["name"] == "core.database":
            database_slice = slice
    assert database_slice
    assert not database_slice["status"]["connected"]


@pytest.mark.asyncio
async def test_server_status_database_down(
    server_config, server_pre_start, postgres_db, ensure_running_postgres_db_post, async_finalizer
):
    ibl = InmantaBootloader()
    await ibl.start()
    async_finalizer.add(ibl.stop)
    postgres_db.stop()
    client = protocol.Client("client")
    result = await client.get_server_status()
    assert result.code == 200
    database_slice = None
    for slice in result.result["data"]["slices"]:
        if slice["name"] == "core.database":
            database_slice = slice
    assert database_slice
    assert not database_slice["status"]["connected"]
