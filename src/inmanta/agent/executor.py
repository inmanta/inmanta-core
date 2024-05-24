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
import contextlib
import dataclasses
import functools
import hashlib
import json
import logging
import os
import types
import typing
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import pkg_resources

import inmanta.types
from inmanta.agent import config as cfg
from inmanta.data.model import PipConfig, ResourceIdStr, ResourceVersionIdStr
from inmanta.env import PythonEnvironment
from inmanta.loader import ModuleSource
from inmanta.resources import Id
from inmanta.types import JsonType
from inmanta.util import NamedLock

LOGGER = logging.getLogger(__name__)

FailedResourcesSet: typing.TypeAlias = set[str]


class AgentInstance(abc.ABC):
    eventloop: asyncio.AbstractEventLoop
    sessionid: uuid.UUID
    environment: uuid.UUID
    uri: str

    @abc.abstractmethod
    def is_stopped(self) -> bool:
        pass


class ResourceDetails:
    """
    In memory representation of the desired state of a resource
    """

    id: Id
    rid: ResourceIdStr
    rvid: ResourceVersionIdStr
    env_id: uuid.UUID
    model_version: int
    requires: Sequence[Id]
    attributes: dict[str, object]

    def __init__(self, resource_dict: JsonType) -> None:
        self.attributes = resource_dict["attributes"]
        self.attributes["id"] = resource_dict["id"]
        self.id = Id.parse_id(resource_dict["id"])
        self.rid = self.id.resource_str()
        self.rvid = self.id.resource_version_str()
        self.env_id = resource_dict["environment"]
        self.requires = [Id.parse_id(resource_id) for resource_id in resource_dict["attributes"]["requires"]]
        self.model_version = resource_dict["model"]


@dataclasses.dataclass
class EnvBlueprint:
    """Represents a blueprint for creating virtual environments with specific pip configurations and requirements."""

    pip_config: PipConfig
    requirements: Sequence[str]
    _hash_cache: Optional[str] = dataclasses.field(default=None, init=False, repr=False)

    def blueprint_hash(self) -> str:
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
        return (self.pip_config, set(self.requirements)) == (other.pip_config, set(other.requirements))

    def __hash__(self) -> int:
        return int(self.blueprint_hash(), 16)

    def __str__(self) -> str:
        req = ",".join(str(req) for req in self.requirements)
        return f"EnvBlueprint(requirements=[{str(req)}], pip={self.pip_config}]"


@dataclasses.dataclass
class ExecutorBlueprint(EnvBlueprint):
    """Extends EnvBlueprint to include sources for the executor environment."""

    sources: Sequence[ModuleSource]
    _hash_cache: Optional[str] = dataclasses.field(default=None, init=False, repr=False)

    @classmethod
    def from_specs(cls, code: typing.Collection["ResourceInstallSpec"]) -> "ExecutorBlueprint":
        sources = list({source for cd in code for source in cd.blueprint.sources})
        requirements = list({req for cd in code for req in cd.blueprint.requirements})
        pip_configs = [cd.blueprint.pip_config for cd in code]
        if not pip_configs:
            raise Exception("No Pip config available, aborting")
        base_pip = pip_configs[0]
        for pip_config in pip_configs:
            assert pip_config == base_pip, f"One agent is using multiple pip configs: {base_pip} {pip_config}"
        return ExecutorBlueprint(
            pip_config=base_pip,
            sources=sources,
            requirements=requirements,
        )

    def blueprint_hash(self) -> str:
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
        return (self.pip_config, set(self.requirements), sorted(self.sources)) == (
            other.pip_config,
            set(other.requirements),
            sorted(other.sources),
        )


@dataclasses.dataclass
class ExecutorId:
    """Identifies an executor with an agent name and its blueprint configuration."""

    agent_name: str
    agent_uri: str
    blueprint: ExecutorBlueprint

    def __hash__(self) -> int:
        combined_str = self.identity()
        hash_obj = hashlib.md5(combined_str.encode("utf-8"))
        return int(hash_obj.hexdigest(), 16)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExecutorId):
            return False
        return (
            self.agent_name == other.agent_name
            and self.agent_uri == other.agent_uri
            and self.blueprint.blueprint_hash() == other.blueprint.blueprint_hash()
        )

    def identity(self) -> str:
        return self.agent_name + self.agent_uri + self.blueprint.blueprint_hash()


@dataclass(frozen=True)
class ResourceInstallSpec:
    """
    This class encapsulates the requirements for a specific resource type for a specific model version.

    :ivar resource_type: fully qualified name for this resource type e.g. std::testing::NullResource
    :ivar model_version: the version of the model to use
    :ivar blueprint: the associate install blueprint

    """

    resource_type: str
    model_version: int
    blueprint: ExecutorBlueprint


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
        env_dir_name: str = blueprint.blueprint_hash()
        env_dir: str = os.path.join(self.envs_dir, env_dir_name)

        # Check if the directory already exists and create it if not
        if not os.path.exists(env_dir):
            os.makedirs(env_dir)
            return env_dir, True  # Returning the path and True for newly created directory
        else:
            LOGGER.debug(
                "Found existing venv for content %s at %s, content hash: %s",
                str(blueprint),
                env_dir,
                blueprint.blueprint_hash(),
            )
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
            LOGGER.info("Creating venv for content %s, content hash: %s", str(blueprint), blueprint.blueprint_hash())
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
            LOGGER.debug(
                "Found existing virtual environment for content %s, content hash: %s",
                str(blueprint),
                blueprint.blueprint_hash(),
            )
            return self._environment_map[blueprint]
        # Acquire a lock based on the blueprint's hash
        async with self._locks.get(blueprint.blueprint_hash()):
            if blueprint in self._environment_map:
                LOGGER.debug(
                    "Found existing virtual environment for content %s, content hash: %s",
                    str(blueprint),
                    blueprint.blueprint_hash(),
                )
                return self._environment_map[blueprint]
            return await self.create_environment(blueprint, threadpool)


class CacheVersionContext(contextlib.AbstractAsyncContextManager[None]):
    """
    A context manager to ensure the cache version is properly closed
    """

    def __init__(self, executor: "Executor", version: int) -> None:
        self.version = version
        self.executor = executor

    async def __aenter__(self) -> None:
        await self.executor.open_version(self.version)

    async def __aexit__(
        self,
        __exc_type: typing.Type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: types.TracebackType | None,
    ) -> None:
        await self.executor.close_version(self.version)
        return None


class Executor(abc.ABC):
    """
    Represents an executor responsible for deploying resources within a specified virtual environment.
    It is identified by an ExecutorId and operates within the context of a given ExecutorVirtualEnvironment.

    :param executor_id: Unique identifier for the executor, encapsulating the agent name and its configuration blueprint.
    :param executor_virtual_env: The virtual environment in which this executor operates
    :param storage: File system path to where the executor's resources are stored.
    """

    failed_resource_types: FailedResourcesSet

    def cache(self, model_version: int) -> CacheVersionContext:
        """
        Context manager responsible for opening and closing the handler cache
        for the given model_version during deployment.
        """
        return CacheVersionContext(self, model_version)

    @abc.abstractmethod
    async def execute(
        self,
        gid: uuid.UUID,
        resource_details: ResourceDetails,
        reason: str,
    ) -> None:
        """
        Perform the actual deployment of the resource by calling the loaded handler code

        :param gid: unique id for this deploy
        :param resource_details: desired state for this resource as a ResourceDetails
        :param reason: textual reason for this deploy
        """
        pass

    @abc.abstractmethod
    async def dry_run(
        self,
        resources: Sequence[ResourceDetails],
        dry_run_id: uuid.UUID,
    ) -> None:
        """
        Perform a dryrun for the given resources

        :param resources: Sequence of resources for which to perform a dryrun.
        :param dry_run_id: id for this dryrun
        """
        pass

    @abc.abstractmethod
    async def dry_run_one(
        self,
        resource: ResourceDetails,
        dry_run_id: uuid.UUID,
    ) -> None:
        """
        Perform a dryrun for the given resource

        :param resource: resource for which to perform a dryrun.
        :param dry_run_id: id for this dryrun
        """
        pass

    @abc.abstractmethod
    async def get_facts(self, resource: ResourceDetails) -> inmanta.types.Apireturn:
        """
        Get facts for a given resource
        :param resource: The resource for which to get facts.
        """
        pass

    @abc.abstractmethod
    async def open_version(self, version: int) -> None:
        """
        Open a version on the cache
        """
        pass

    @abc.abstractmethod
    async def close_version(self, version: int) -> None:
        """
        Close a version on the cache
        """
        pass


E = typing.TypeVar("E", bound=Executor, covariant=True)


class ExecutorManager(abc.ABC, typing.Generic[E]):
    """
    Manages Executors by ensuring that Executors are created and reused efficiently based on their configurations.

    :param thread_pool:  threadpool to perform work on
    :param environment_manager: The VirtualEnvironmentManager responsible for managing the virtual environments
    """

    @abc.abstractmethod
    async def get_executor(self, agent_name: str, agent_uri: str, code: typing.Collection[ResourceInstallSpec]) -> E:
        """
        Retrieves an Executor based on the agent name and blueprint.
        If an Executor does not exist for the given configuration, a new one is created.

        :param agent_name: The name of the agent for which an Executor is being retrieved or created.
        :param blueprint: The ExecutorBlueprint defining the configuration for the Executor.
        :return: An Executor instance
        """
        pass

    @abc.abstractmethod
    async def stop_for_agent(self, agent_name: str) -> list[E]:
        """
        Indicate that all executors for this agent can be stopped.

        This is considered to be a hint , the manager can choose to follow or not

        If executors are stopped, they are returned
        """
        pass

    @abc.abstractmethod
    async def stop(self) -> None:
        """
        Stop all executors.

        Don't wait for them to terminate
        """
        pass

    @abc.abstractmethod
    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor], timeout: float) -> None:
        """
        Wait for all executors to terminate.

        Any threadpools that need to be closed can be handed of to the parent via thread_pool_finalizer
        """
        pass
