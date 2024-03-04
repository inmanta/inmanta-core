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

import abc
import asyncio
import dataclasses
import functools
import hashlib
import json
import logging
import os
import typing
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

import pkg_resources

from inmanta.agent import config as cfg
from inmanta.data.model import PipConfig
from inmanta.env import PythonEnvironment
from inmanta.loader import ModuleSource
from inmanta.resources import Resource
from inmanta.util import NamedLock

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class EnvBlueprint:
    """Represents a blueprint for creating virtual environments with specific pip configurations and requirements."""

    pip_config: PipConfig
    requirements: Sequence[str]
    _hash_cache: Optional[str] = dataclasses.field(default=None, init=False, repr=False)

    def generate_blueprint_hash(self) -> str:
        """
        Generate a stable hash for an EnvBlueprint instance by serializing its pip_config
        and requirements in a sorted, consistent manner. This ensures that the hash value is
        independent of the order of requirements and consistent across interpreter sessions.
        Also cache the hash to only compute it once.
        """
        if self._hash_cache is None:
            blueprint_dict: Dict[str, Any] = {
                "pip_config": self.pip_config.dict(),
                "requirements": sorted(self.requirements),
            }

            # Serialize the blueprint dictionary to a JSON string, ensuring consistent ordering
            serialized_blueprint = json.dumps(blueprint_dict, sort_keys=True)

            # Use md5 to generate a hash of the serialized blueprint
            hash_obj = hashlib.md5(serialized_blueprint.encode("utf-8"))
            self._hash_cache = hash_obj.hexdigest()
        return self._hash_cache

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EnvBlueprint):
            return False
        return self.generate_blueprint_hash() == other.generate_blueprint_hash()

    def __hash__(self) -> int:
        return int(self.generate_blueprint_hash(), 16)


@dataclasses.dataclass
class ExecutorBlueprint(EnvBlueprint):
    """Extends EnvBlueprint to include sources for the executor environment."""

    sources: Sequence[ModuleSource]
    _hash_cache: Optional[str] = dataclasses.field(default=None, init=False, repr=False)

    def generate_blueprint_hash(self) -> str:
        """
        Generate a stable hash for an ExecutorBlueprint instance by serializing its pip_config, sources
        and requirements in a sorted, consistent manner. This ensures that the hash value is
        independent of the order of requirements and consistent across interpreter sessions.
        Also cache the hash to only compute it once.
        """
        if self._hash_cache is None:
            blueprint_dict = {
                "pip_config": self.pip_config.dict(),
                "requirements": sorted(self.requirements),
                # Use the hash values of the sources, sorted to ensure consistent ordering
                "sources": sorted(source.hash_value for source in self.sources),
            }

            # Serialize the extended blueprint dictionary to a JSON string, ensuring consistent ordering
            serialized_blueprint = json.dumps(blueprint_dict, sort_keys=True)

            # Use md5 to generate a hash of the serialized blueprint
            hash_obj = hashlib.md5(serialized_blueprint.encode("utf-8"))
            self._hash_cache = hash_obj.hexdigest()
        return self._hash_cache

    def to_env_blueprint(self) -> EnvBlueprint:
        """
        Converts this ExecutorBlueprint instance into an EnvBlueprint instance.
        """
        return EnvBlueprint(pip_config=self.pip_config, requirements=self.requirements)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExecutorBlueprint):
            return False
        return self.generate_blueprint_hash() == other.generate_blueprint_hash()

    def __hash__(self) -> int:
        return int(self.generate_blueprint_hash(), 16)


@dataclasses.dataclass
class ExecutorId:
    """Identifies an executor with an agent name and its blueprint configuration."""

    agent_name: str
    blueprint: ExecutorBlueprint

    def __hash__(self) -> int:
        combined_str = self.agent_name + self.blueprint.generate_blueprint_hash()
        hash_obj = hashlib.md5(combined_str.encode("utf-8"))
        return int(hash_obj.hexdigest(), 16)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExecutorId):
            return False
        return (
            self.agent_name == other.agent_name
            and self.blueprint.generate_blueprint_hash() == other.blueprint.generate_blueprint_hash()
        )


class ExecutorVirtualEnvironment(PythonEnvironment):
    """
    Manages a single virtual environment for an executor,
    including the creation and installation of packages based on a blueprint.

    :param env_path: The file system path where the virtual environment should be created or exists.
    :param threadpool: A ThreadPoolExecutor instance
    """

    def __init__(self, env_path: str, threadpool: ThreadPoolExecutor):
        super().__init__(env_path=env_path)
        self.thread_pool = threadpool

    async def create_and_install_environment(self, blueprint: EnvBlueprint) -> None:
        """
        Creates and configures the virtual environment according to the provided blueprint.

        :param blueprint: An instance of EnvBlueprint containing the configuration for
            the pip installation and the requirements to install.
        """
        loop = asyncio.get_running_loop()
        req: list[str] = list(blueprint.requirements)
        self.init_env()
        if len(req):  # install_for_config expects at least 1 requirement or a path to install
            install_for_config = functools.partial(
                self.install_for_config,
                requirements=list(pkg_resources.parse_requirements(req)),
                config=blueprint.pip_config,
            )
            await loop.run_in_executor(self.thread_pool, install_for_config)


def initialize_envs_directory() -> str:
    """
    Initializes the base directory for storing virtual environments. If the directory
    does not exist, it is created.

    :return: The path to the environments directory.
    """
    state_dir = cfg.state_dir.get()
    env_dir = os.path.join(state_dir, "envs")
    os.makedirs(env_dir, exist_ok=True)
    return env_dir


class VirtualEnvironmentManager:
    """
    Manages virtual environments to ensure efficient reuse.
    This manager handles the creation of new environments based on specific blueprints and maintains a directory
    for storing these environments.
    """

    def __init__(self, envs_dir: str) -> None:
        self._environment_map: dict[EnvBlueprint, ExecutorVirtualEnvironment] = {}
        self.envs_dir: str = envs_dir
        self._locks: NamedLock = NamedLock()

    def get_or_create_env_directory(self, blueprint: EnvBlueprint) -> tuple[str, bool]:
        """
        Retrieves the directory path for a virtual environment based on the given blueprint.
        If the directory does not exist, it creates a new one. This method ensures that each
        virtual environment has a unique storage location.

        :param blueprint: The blueprint of the environment for which the storage is being determined.
        :return: A tuple containing the path to the directory and a boolean indicating whether the directory was newly created.
        """
        env_dir_name: str = blueprint.generate_blueprint_hash()
        env_dir: str = os.path.join(self.envs_dir, env_dir_name)

        # Check if the directory already exists and create it if not
        if not os.path.exists(env_dir):
            os.makedirs(env_dir)
            return env_dir, True  # Returning the path and True for newly created directory
        else:
            LOGGER.info("Found existing virtual environment at %s", env_dir)
            return env_dir, False  # Returning the path and False for existing directory

    async def create_environment(self, blueprint: EnvBlueprint, threadpool: ThreadPoolExecutor) -> ExecutorVirtualEnvironment:
        """
        Creates a new virtual environment based on the provided blueprint or reuses an existing one if suitable.
        This involves setting up the virtual environment and installing any required packages as specified in the blueprint.

        :param blueprint: The blueprint specifying the configuration for the new virtual environment.
        :param threadpool: A ThreadPoolExecutor
        :return: An instance of ExecutorVirtualEnvironment representing the created or reused environment.

        TODO: Improve handling of bad venv scenarios, such as when the folder exists but is empty or corrupted.
        """
        env_storage, is_new = self.get_or_create_env_directory(blueprint)
        process_environment = ExecutorVirtualEnvironment(env_storage, threadpool)
        if is_new:
            await process_environment.create_and_install_environment(blueprint)
        self._environment_map[blueprint] = process_environment

        return process_environment

    async def get_environment(self, blueprint: EnvBlueprint, threadpool: ThreadPoolExecutor) -> ExecutorVirtualEnvironment:
        """
        Retrieves an existing virtual environment that matches the given blueprint or creates a new one if no match is found.
        Utilizes NamedLock to ensure thread-safe operations for each unique blueprint.
        """
        assert isinstance(blueprint, EnvBlueprint), "Only EnvBlueprint instances are accepted, subclasses are not allowed."

        if blueprint in self._environment_map:
            return self._environment_map[blueprint]
        # Acquire a lock based on the blueprint's hash
        async with self._locks.get(blueprint.generate_blueprint_hash()):
            if blueprint in self._environment_map:
                return self._environment_map[blueprint]
            return await self.create_environment(blueprint, threadpool)


class Executor(abc.ABC):
    """
    Represents an executor responsible for deploying resources within a specified virtual environment.
    It is identified by an ExecutorId and operates within the context of a given ExecutorVirtualEnvironment.

    :param executor_id: Unique identifier for the executor, encapsulating the agent name and its configuration blueprint.
    :param executor_virtual_env: The virtual environment in which this executor operates
    :param storage: File system path to where the executor's resources are stored.
    """

    def execute(self, resources: list[Resource]) -> None:
        print("Start deploy of resources")


MyExecutor = typing.TypeVar("MyExecutor", bound=Executor)


class ExecutorManager(abc.ABC, typing.Generic[MyExecutor]):
    """
    Manages Executors by ensuring that Executors are created and reused efficiently based on their configurations.

    :param thread_pool:  threadpool to perform work on
    :param environment_manager: The VirtualEnvironmentManager responsible for managing the virtual environments
    """

    def __init__(self, thread_pool: ThreadPoolExecutor, environment_manager: VirtualEnvironmentManager):
        self.executor_map: dict[ExecutorId, MyExecutor] = {}
        self.environment_manager = environment_manager
        self.thread_pool = thread_pool
        self._locks: NamedLock = NamedLock()

    @abc.abstractmethod
    async def create_executor(self, venv: ExecutorVirtualEnvironment, executor_id: ExecutorId) -> MyExecutor:
        pass

    async def get_executor(self, agent_name: str, blueprint: ExecutorBlueprint) -> MyExecutor:
        """
        Retrieves an Executor based on the agent name and blueprint.
        If an Executor does not exist for the given configuration, a new one is created.

        :param agent_name: The name of the agent for which an Executor is being retrieved or created.
        :param blueprint: The ExecutorBlueprint defining the configuration for the Executor.
        :return: An Executor instance
        """
        executor_id = ExecutorId(agent_name, blueprint)
        if executor_id in self.executor_map:
            return self.executor_map[executor_id]
        # Acquire a lock based on the blueprint's hash
        async with self._locks.get(blueprint.generate_blueprint_hash()):
            if executor_id in self.executor_map:
                return self.executor_map[executor_id]
            blueprint = executor_id.blueprint
            env_blueprint = blueprint.to_env_blueprint()
            venv = await self.environment_manager.get_environment(env_blueprint, self.thread_pool)
            executor = await self.create_executor(venv, executor_id)
            self.executor_map[executor_id] = executor
            return executor

    async def execute(
        self,
        agent_name: str,
        blueprint: ExecutorBlueprint,
        resources: list[Resource],
    ) -> None:
        """
        Execute the given resources with the appropriate Executor.

        :param agent_name: The name of the agent under which the execution is performed.
        :param blueprint: The ExecutorBlueprint defining the configuration for the Executor.
        :param resources: A list of Resource instances to be deployed.
        """
        executor = await self.get_executor(agent_name, blueprint)
        executor.execute(resources)
