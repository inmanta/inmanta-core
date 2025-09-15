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
import re
import sys
import uuid

import pytest

from inmanta import data
from inmanta.data.model import ReportedStatus
from inmanta.server.services.compilerservice import CompilerService


async def test_server_status(server, client, agent, environment, postgresql_client):
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

    scheduler_status = [x for x in status["slices"] if x["name"] == "core.scheduler_manager"]
    assert len(scheduler_status) == 1

    scheduler_stats = scheduler_status[0]["status"]
    assert scheduler_stats["total"]["connected"] is True
    # test environment is called dev
    assert scheduler_stats["dev"]["connected"] is True

    assert "features" in status
    assert len(status["features"]) > 0

    assert status["python_version"] == sys.version
    postgresql_version = await postgresql_client.fetchval("SELECT version();")
    # Assert that the output is `PostgreSQL X.Y[.Z] ...`
    assert re.match(r"^(PostgreSQL \d+(?:\.\d+)+)", postgresql_version)
    assert status["postgresql_version"] == postgresql_version


async def test_server_status_database_unreachable(server, client):
    await data.disconnect_pool()
    result = await client.get_server_status()
    assert result.code == 200
    database_slice = None
    for slice in result.result["data"]["slices"]:
        if slice["name"] == "core.database":
            database_slice = slice
    assert database_slice
    assert not database_slice["status"]["connected"]
    assert result.result["data"]["postgresql_version"] is None


async def test_server_status_timeout(server, client, monkeypatch):
    """
    Test timeout of get status and how the overall status changes if a timeout happens.
    """
    # Everything is OK
    result = await client.get_server_status()
    assert result.code == 200
    assert result.result["data"]["status"] == ReportedStatus.OK

    result = await client.health()
    assert result.code == 200

    monkeypatch.setattr(CompilerService, "GET_SLICE_STATUS_TIMEOUT", 0.1)

    async def hang(self):
        await asyncio.sleep(0.2)
        return {}

    monkeypatch.setattr(CompilerService, "get_status", hang)

    result = await client.get_server_status()
    assert result.code == 200
    # Error because CompilerService is in the Error state
    assert result.result["data"]["status"] == ReportedStatus.Error
    compiler_slice = None
    for slice in result.result["data"]["slices"]:
        if slice["name"] == "core.compiler":
            compiler_slice = slice
    assert compiler_slice
    assert "error" in compiler_slice["status"]

    result = await client.health()
    assert result.code == 500


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_get_scheduler_status(server, client, environment) -> None:
    result = await client.get_scheduler_status(tid=environment)
    assert result.code == 200

    result = await client.halt_environment(tid=environment)
    assert result.code == 200

    result = await client.get_scheduler_status(tid=environment)
    assert result.code == 404
    assert (
        f"No scheduler is running for environment {environment}, because the environment is halted." in result.result["message"]
    )

    result = await client.resume_environment(tid=environment)
    assert result.code == 200

    result = await client.get_scheduler_status(tid=environment)
    assert result.code == 200

    result = await client.get_scheduler_status(tid=uuid.uuid4())
    assert result.code == 404
    assert "The given environment id does not exist!" in result.result["message"]
