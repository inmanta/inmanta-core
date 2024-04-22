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
import concurrent.futures.thread
import os
import typing
import uuid

import pytest

import inmanta.agent
import inmanta.agent.executor
import inmanta.config
import inmanta.data
import inmanta.loader
import inmanta.protocol.ipc_light
import inmanta.util
import utils
from inmanta.agent.forking_executor import MPManager
from packaging import version


@pytest.fixture
async def mp_manager_factory(tmp_path) -> typing.Iterator[typing.Callable[[uuid.UUID], MPManager]]:
    managers = []
    threadpools = []
    MPManager.init_once()

    def make_mpmanager(agent_session_id: uuid.UUID) -> MPManager:
        log_folder = tmp_path / "logs"
        storage_folder = tmp_path / "executors"
        venvs = tmp_path / "venvs"
        threadpool = concurrent.futures.thread.ThreadPoolExecutor()
        venv_manager = inmanta.agent.executor.VirtualEnvironmentManager(str(venvs))
        manager = MPManager(
            threadpool,
            venv_manager,
            agent_session_id,
            uuid.uuid4(),
            log_folder=str(log_folder),
            storage_folder=str(storage_folder),
            cli_log=True,
        )
        managers.append(manager)
        threadpools.append(threadpool)
        return manager

    yield make_mpmanager
    for threadpool in threadpools:
        threadpool.shutdown(wait=False)
    await asyncio.gather(*(manager.stop() for manager in managers))
    await asyncio.gather(*(manager.join([], 10) for manager in managers))


@pytest.fixture
async def mpmanager(mp_manager_factory, agent: inmanta.agent.Agent) -> MPManager:
    return mp_manager_factory(agent.sessionid)


@pytest.fixture
async def mpmanager_light(mp_manager_factory) -> typing.Iterator[MPManager]:
    """Fake the agent"""
    return mp_manager_factory(None)


@pytest.fixture(scope="session")
def pip_index(tmp_path_factory) -> utils.PipIndex:
    tmpdir = tmp_path_factory.mktemp("pip_index")
    pip_index = utils.PipIndex(artifact_dir=str(tmpdir))
    utils.create_python_package(
        name="pkg1",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg1"),
        publish_index=pip_index,
    )
    utils.create_python_package(
        name="pkg2",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg2"),
        publish_index=pip_index,
    )
    return pip_index
