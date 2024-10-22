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
import logging
from functools import partial

from inmanta import config, const
from inmanta.agent.agent_new import Agent
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.bootloader import InmantaBootloader
from utils import get_resource, log_index, retry_limited, wait_until_deployment_finishes


async def test_agent_disconnect(
    resource_container, environment, server, client, clienthelper, async_finalizer, caplog, agent: Agent
):
    caplog.set_level(logging.INFO)
    config.Config.set("config", "server-timeout", "1")
    config.Config.set("config", "agent-reconnect-delay", "1")
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    version = await clienthelper.get_version()
    await clienthelper.put_version_simple([get_resource(version)], version)

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    await asyncio.wait_for(server.stop(), timeout=15)

    def disconnected():
        return not agent.scheduler._running

    await retry_limited(disconnected, 1)

    log_index(caplog, "inmanta.scheduler", logging.WARNING, "Connection to server lost, stopping scheduler")


async def test_server_restart(
    resource_container, server, agent, environment, clienthelper, postgres_db, client, async_finalizer
):
    """
    Test if agent reconnects correctly after server restart
    """
    resource_container.Provider.reset()
    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    await asyncio.wait_for(server.stop(), timeout=15)
    ibl = InmantaBootloader(configure_logging=False)
    server = ibl.restserver
    async_finalizer.add(agent.stop)
    async_finalizer.add(partial(ibl.stop, timeout=15))
    await ibl.start()

    env_id = environment

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "requires": [],
            "purged": True,
            "send_event": False,
            "receive_events": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # do a deploy
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await wait_until_deployment_finishes(client, env_id, version)

    result = await client.get_version(env_id, version)
    assert result.result["model"]["done"] == len(resources)

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")
