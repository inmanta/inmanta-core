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
import datetime
import logging
import uuid
from collections.abc import Mapping

import pytest

import utils
from inmanta import config, const, data
from inmanta.agent.agent_new import Agent
from inmanta.deploy.state import Blocked, Compliance, DeployResult, ResourceState



async def test_agent_disconnect(
    resource_container, environment, server, client, clienthelper, caplog, agent_no_state_check: Agent
):
    pass
    caplog.set_level(logging.INFO)
    config.Config.set("config", "server-timeout", "1")
    config.Config.set("config", "agent-reconnect-delay", "1")

    version = await clienthelper.get_version()
    await clienthelper.put_version_simple([utils.get_resource(version)], version)

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    await asyncio.wait_for(server.stop(), timeout=15)

    def disconnected():
        return not agent_no_state_check.scheduler._running

    await utils.retry_limited(disconnected, 1)

    utils.log_index(caplog, "inmanta.scheduler", logging.WARNING, "Connection to server lost, stopping scheduler")

