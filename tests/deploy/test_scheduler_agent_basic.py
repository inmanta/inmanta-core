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

import tempfile
import typing
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

import pytest

import inmanta.types
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.executor import E, ResourceDetails, ResourceInstallSpec
from inmanta.config import Config


class DummyExecutor(executor.Executor):

    async def execute(self, gid: uuid.UUID, resource_details: ResourceDetails, reason: str) -> None:
        pass

    async def dry_run(self, resources: Sequence[ResourceDetails], dry_run_id: uuid.UUID) -> None:
        pass

    async def get_facts(self, resource: ResourceDetails) -> inmanta.types.Apireturn:
        pass

    async def open_version(self, version: int) -> None:
        pass

    async def close_version(self, version: int) -> None:
        pass


class DummyManager(executor.ExecutorManager[executor.Executor]):

    async def get_executor(
        self, agent_name: str, agent_uri: str, code: typing.Collection[ResourceInstallSpec]
    ) -> DummyExecutor:
        pass

    async def stop_for_agent(self, agent_name: str) -> list[DummyExecutor]:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor], timeout: float) -> None:
        pass


class TestAgent(Agent):

    def create_executor_manager(self) -> executor.ExecutorManager[executor.Executor]:
        return DummyManager()


@pytest.fixture
def environment() -> uuid.UUID:
    return "83d604a0-691a-11ef-ae04-c8f750463317"


@pytest.fixture
async def config(inmanta_config, tmp_path):
    Config.set("config", "state-dir", str(tmp_path))
    Config.set("config", "log-dir", str(tmp_path / "logs"))
    Config.set("server", "agent-timeout", "2")
    Config.set("agent", "agent-repair-interval", "0")
    Config.set("agent", "executor-mode", "forking")
    Config.set("agent", "executor-venv-retention-time", "60")
    Config.set("agent", "executor-retention-time", "10")


@pytest.fixture
async def agent(environment, config):
    out = TestAgent(environment)
    await out.start_working()
    yield out
    await out.stop_working()


async def test_fixtures(agent):
    pass
