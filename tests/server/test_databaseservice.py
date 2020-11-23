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
import asyncio

import pytest

from inmanta import data
from inmanta.server import config as opt
from inmanta.server.services import databaseservice
from utils import retry_limited


@pytest.mark.asyncio
async def test_agent_process_cleanup(server, environment, agent_factory):
    opt.agent_processes_to_keep.set("1")
    a1 = await agent_factory(environment, hostname="host", agent_map=[], agent_names=["agent1"])
    a2 = await agent_factory(environment, hostname="host", agent_map=[], agent_names=["agent1"])
    await asyncio.gather(*[a1.stop(), a2.stop()])

    async def _wait_until_expire_is_finished():
        result = await data.AgentProcess.get_list()
        return len([r for r in result if r.expired is not None]) == 2

    await retry_limited(_wait_until_expire_is_finished, timeout=10)
    # Execute cleanup
    database_slice = server.get_slice(databaseservice.SLICE_DATABASE)
    await database_slice._purge_agent_processes()
    # Assert cleanup
    result = await data.AgentProcess.get_list()
    assert len(result) == 1
