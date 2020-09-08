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
import logging

import pytest

from agent_server.conftest import get_agent
from inmanta import config
from utils import get_resource, log_index, retry_limited


@pytest.mark.asyncio
async def test_agent_disconnect(resource_container, environment, server, client, clienthelper, async_finalizer, caplog):
    caplog.set_level(logging.INFO)
    config.Config.set("config", "server-timeout", "1")
    config.Config.set("config", "agent-reconnect-delay", "1")
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    version = await clienthelper.get_version()
    await clienthelper.put_version_simple([get_resource(version)], version)

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    agent = await get_agent(server, environment, "agent1")
    async_finalizer.add(agent.stop)

    await server.stop()

    def disconnected():
        return not agent._instances["agent1"]._enabled

    await retry_limited(disconnected, 1)

    i = log_index(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Agent assuming primary role for agent1")
    i = log_index(caplog, "inmanta.agent.agent", logging.WARNING, "Connection to server lost, taking agents offline", i)
    log_index(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Agent agent1 stopped because Connection to server lost", i)
