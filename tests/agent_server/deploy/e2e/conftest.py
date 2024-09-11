"""
    Copyright 2024 Inmanta

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

import pytest

import inmanta.server.agentmanager as agentmanager
import utils
from agent_server.deploy.scheduler_test_util import DummyCodeManager
from inmanta import config
from inmanta.agent.agent_new import Agent
from inmanta.agent.in_process_executor import InProcessExecutorManager
from inmanta.config import Config
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.config import server_use_resource_scheduler
from inmanta.util import get_compiler_version, groupby
from utils import resource_action_consistency_check, retry_limited

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
async def auto_start_agent(server_config):
    return False


@pytest.fixture(scope="function")
async def server_config(server_config, auto_start_agent):
    agentmanager.no_auto_start_scheduler = not auto_start_agent
    server_use_resource_scheduler.set("True")
    yield server_config
    agentmanager.no_auto_start_scheduler = False


@pytest.fixture(scope="function")
async def agent(server, environment):
    """Construct an agent that can execute using the resource container"""
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    # First part - test the ResourceScheduler (retrieval of data from DB)

    a = Agent(environment)

    executor = InProcessExecutorManager(
        environment, a._client, asyncio.get_event_loop(), logger, a.thread_pool, a._storage["code"], a._storage["env"], False
    )
    a.executor_manager = executor
    a.scheduler._executor_manager = executor
    a.scheduler._code_manager = DummyCodeManager(a._client)

    await a.start()

    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()
