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

import os
import typing
from concurrent.futures import ThreadPoolExecutor

import inmanta.agent.executor as executor
from inmanta.agent import config as cfg
from inmanta.loader import ModuleSource


class InProcessExecutor(executor.Executor):
    def __init__(
        self, executor_id: executor.ExecutorId, executor_virtual_env: executor.ExecutorVirtualEnvironment, storage: str
    ):
        self.executor_id = executor_id
        self.executor_virtual_env: executor.ExecutorVirtualEnvironment = executor_virtual_env
        self.storage = storage

    def load_code(self, sources: typing.Sequence["ModuleSource"]) -> None:
        print("Load the code of sources for executor")


class InProcessExecutorManager(executor.ExecutorManager[InProcessExecutor]):
    """
    This is the executor that provides the backward compatible behavior, confirming to the agent in ISO7.
    """

    def __init__(self, thread_pool: ThreadPoolExecutor, environment_manager: executor.VirtualEnvironmentManager) -> None:
        super().__init__(thread_pool, environment_manager)
        self.storage = self.create_storage()

    async def create_executor(
        self, venv: executor.ExecutorVirtualEnvironment, executor_id: executor.ExecutorId
    ) -> InProcessExecutor:
        """
        Creates an Executor based with the specified agent name and blueprint.
        It ensures the required virtual environment is prepared and source code is loaded.

        :param executor_id: executor identifier containing an agent name and a blueprint configuration.
        :return: An Executor instance
        """

        executor = InProcessExecutor(executor_id, venv, self.storage)
        executor.load_code(executor_id.blueprint.sources)
        return executor

    def create_storage(self) -> str:
        """
        Prepares and returns the path to the storage directory used by Executors for their source code.

        :return: The path to the storage directory.
        """
        state_dir = cfg.state_dir.get()
        code_dir = os.path.join(state_dir, "codes")
        os.makedirs(code_dir, exist_ok=True)
        return code_dir
