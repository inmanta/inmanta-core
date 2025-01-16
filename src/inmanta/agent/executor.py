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
import concurrent.futures
import dataclasses
import datetime
import hashlib
import json
import logging
import os
import pathlib
import shutil
import typing
import uuid
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, cast
from uuid import UUID

import packaging.requirements
from inmanta import const
from inmanta.agent import config as cfg
from inmanta.agent import resourcepool
from inmanta.agent.handler import HandlerContext
from inmanta.const import Change
from inmanta.data import LogLine
from inmanta.data.model import AttributeStateChange, PipConfig
from inmanta.env import PythonEnvironment
from inmanta.loader import ModuleSource
from inmanta.resources import Id
from inmanta.types import JsonType, ResourceIdStr, ResourceType, ResourceVersionIdStr

LOGGER = logging.getLogger(__name__)


FailedResources: typing.TypeAlias = dict[ResourceType, Exception]


class AgentInstance(abc.ABC):
    eventloop: asyncio.AbstractEventLoop
    sessionid: uuid.UUID
    environment: uuid.UUID
    uri: str

    @abc.abstractmethod
    def is_stopped(self) -> bool:
        pass


@dataclass
class DryrunReport:
    rvid: ResourceVersionIdStr
    dryrun_id: uuid.UUID
    changes: dict[str, AttributeStateChange]
    started: datetime.datetime
    finished: datetime.datetime
    messages: list[LogLine]
    resource_state: Optional[const.ResourceState] = None


class ResourceDetails:
    """
    In memory representation of the desired state of a resource
    """

    id: Id
    rid: ResourceIdStr
    rvid: ResourceVersionIdStr
    model_version: int
    requires: Sequence[Id]
    attributes: dict[str, object]

    def __init__(self, id: ResourceIdStr, version: int, attributes: Mapping[str, object]) -> None:
        self.attributes = dict(attributes)
        self.id = Id.parse_id(id).copy(version=version)
        self.rid = self.id.resource_str()
        self.rvid = self.id.resource_version_str()
        self.attributes["id"] = self.rvid
        self.model_version = version
        self.requires = [Id.parse_id(resource_id) for resource_id in cast(list[ResourceIdStr], attributes["requires"])]

    @classmethod
    def from_json(cls, resource_dict: JsonType) -> "ResourceDetails":
        return ResourceDetails(resource_dict["id"], resource_dict["model"], resource_dict["attributes"])


@dataclasses.dataclass
class EnvBlueprint:
    """Represents a blueprint for creating virtual environments with specific pip configurations and requirements."""

    pip_config: PipConfig
    requirements: Sequence[str]
    _hash_cache: Optional[str] = dataclasses.field(default=None, init=False, repr=False)
    python_version: tuple[int, int]

    def __post_init__(self) -> None:
        # remove duplicates and make uniform
        self.requirements = sorted(set(self.requirements))

    def blueprint_hash(self) -> str:
        """
        Generate a stable hash for an EnvBlueprint instance by serializing its pip_config
        and requirements in a sorted, consistent manner. This ensures that the hash value is
        independent of the order of requirements and consistent across interpreter sessions.
        Also cache the hash to only compute it once.
        """
        if self._hash_cache is None:
            blueprint_dict: Dict[str, Any] = {
                "pip_config": self.pip_config.model_dump(),
                "requirements": self.requirements,
                "python_version": self.python_version,
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
        return (self.pip_config, set(self.requirements), self.python_version) == (
            other.pip_config,
            set(other.requirements),
            other.python_version,
        )

    def __hash__(self) -> int:
        return int(self.blueprint_hash(), 16)

    def __str__(self) -> str:
        req = ",".join(str(req) for req in self.requirements)
        return f"EnvBlueprint(requirements=[{str(req)}], pip={self.pip_config}, python_version={self.python_version}]"


@dataclasses.dataclass
class ExecutorBlueprint(EnvBlueprint):
    """Extends EnvBlueprint to include sources for the executor environment."""

    sources: Sequence[ModuleSource]
    _hash_cache: Optional[str] = dataclasses.field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        # remove duplicates and make uniform
        self.sources = sorted(set(self.sources))

    @classmethod
    def from_specs(cls, code: typing.Collection["ResourceInstallSpec"]) -> "ExecutorBlueprint":
        """
        Create a single ExecutorBlueprint by combining the blueprint(s) of several
        ResourceInstallSpec by merging respectively their module sources and their
        requirements and making sure they all share the same pip config.
        """

        if not code:
            raise ValueError("from_specs expects at least one resource install spec")
        sources = list({source for cd in code for source in cd.blueprint.sources})
        requirements = list({req for cd in code for req in cd.blueprint.requirements})
        pip_configs = [cd.blueprint.pip_config for cd in code]
        python_versions = [cd.blueprint.python_version for cd in code]
        if not pip_configs:
            raise Exception("No Pip config available, aborting")
        if not python_versions:
            raise Exception("No Python versions found, aborting")
        base_pip = pip_configs[0]
        for pip_config in pip_configs:
            assert pip_config == base_pip, f"One agent is using multiple pip configs: {base_pip} {pip_config}"
        base_python_version = python_versions[0]
        for python_version in python_versions:
            assert (
                python_version == base_python_version
            ), f"One agent is using multiple python versions: {base_python_version} {python_version}"
        return ExecutorBlueprint(
            pip_config=base_pip,
            sources=sources,
            requirements=requirements,
            python_version=base_python_version,
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
                "pip_config": self.pip_config.model_dump(),
                "requirements": self.requirements,
                # Use the hash values and name to create a stable identity
                "sources": [[source.hash_value, source.name, source.is_byte_code] for source in self.sources],
                "python_version": self.python_version,
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
        return EnvBlueprint(pip_config=self.pip_config, requirements=self.requirements, python_version=self.python_version)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExecutorBlueprint):
            return False
        return (self.pip_config, self.requirements, self.sources, self.python_version) == (
            other.pip_config,
            other.requirements,
            other.sources,
            other.python_version,
        )

    def __hash__(self) -> int:
        return hash(self.blueprint_hash())


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

    resource_type: ResourceType
    model_version: int
    blueprint: ExecutorBlueprint


class ExecutorVirtualEnvironment(PythonEnvironment, resourcepool.PoolMember[str]):
    """
    Manages a single virtual environment for an executor,
    including the creation and installation of packages based on a blueprint.

    :param env_path: The file system path where the virtual environment should be created or exists.
    """

    def __init__(self, env_path: str, io_threadpool: ThreadPoolExecutor):
        PythonEnvironment.__init__(self, env_path=env_path)
        resourcepool.PoolMember.__init__(self, my_id=os.path.basename(env_path))
        self.inmanta_venv_status_file: pathlib.Path = pathlib.Path(self.env_path) / const.INMANTA_VENV_STATUS_FILENAME
        self.folder_name: str = pathlib.Path(self.env_path).name
        self.io_threadpool = io_threadpool

    async def create_and_install_environment(self, blueprint: EnvBlueprint) -> None:
        """
        Creates and configures the virtual environment according to the provided blueprint.

        :param blueprint: An instance of EnvBlueprint containing the configuration for
            the pip installation and the requirements to install.
        """
        req: list[str] = list(blueprint.requirements)
        await asyncio.get_running_loop().run_in_executor(self.io_threadpool, self.init_env)
        if len(req):  # install_for_config expects at least 1 requirement or a path to install
            await self.async_install_for_config(
                requirements=[packaging.requirements.Requirement(requirement_string=e) for e in req],
                config=blueprint.pip_config,
            )

        self.touch()

    def is_correctly_initialized(self) -> bool:
        """
        Was the venv correctly initialized: the inmanta status file exists
        """
        return self.inmanta_venv_status_file.exists()

    def touch(self) -> None:
        """
        Touch the inmanta status file
        """
        self.inmanta_venv_status_file.touch()

    @property
    def last_used(self) -> datetime.datetime:
        """
        Retrieve the last modified timestamp of the inmanta status file
        """
        if not self.is_correctly_initialized():
            return const.DATETIME_MIN_UTC
        return datetime.datetime.fromtimestamp(self.inmanta_venv_status_file.stat().st_mtime).astimezone()

    async def request_shutdown(self) -> None:
        """
        Remove the venv of the executor through the thread pool.
        This method is supposed to be used by the VirtualEnvironmentManager with the lock associated to this executor!
        """
        await super().request_shutdown()
        await asyncio.get_running_loop().run_in_executor(self.io_threadpool, self.remove_venv)
        await self.set_shutdown()

    def remove_venv(self) -> None:
        """
        Remove the venv of the executor
        """
        try:
            LOGGER.debug("Removing venv %s", self.env_path)
            shutil.rmtree(self.env_path)
        except Exception:
            LOGGER.exception(
                "An error occurred while removing the venv located %s",
                self.env_path,
            )

    def reset(self) -> None:
        """
        Remove the venv of the executor and recreate the directory of the venv
        """
        self.remove_venv()
        os.makedirs(self.env_path)


class VirtualEnvironmentManager(resourcepool.TimeBasedPoolManager[EnvBlueprint, str, ExecutorVirtualEnvironment]):
    """
    Manages virtual environments to ensure efficient reuse.
    This manager handles the creation of new environments based on specific blueprints and maintains a directory
    for storing these environments.
    """

    def __init__(self, envs_dir: str, thread_pool: concurrent.futures.thread.ThreadPoolExecutor) -> None:
        # We rely on a Named lock (`self._locks`, inherited from PoolManager) to be able to lock specific entries of the
        # `_environment_map` dict. This allows us to prevent creating and deleting the same venv at a given time. The keys of
        # this named lock are the hash of venv
        super().__init__(
            retention_time=cfg.executor_venv_retention_time.get(),
        )
        self.envs_dir: pathlib.Path = pathlib.Path(envs_dir).absolute()
        self.thread_pool = thread_pool

    async def start(self) -> None:
        await self.init_environment_map()
        await super().start()

    def my_name(self) -> str:
        return "EnvironmentManager"

    def member_name(self, member: ExecutorVirtualEnvironment) -> str:
        return f"venv with hash: {member.get_id()}"

    def render_id(self, member: EnvBlueprint) -> str:
        return f"venv with hash: {member.blueprint_hash()}"

    def _id_to_internal(self, ext_id: EnvBlueprint) -> str:
        return ext_id.blueprint_hash()

    def get_lock_name_for(self, member_id: str) -> str:
        return member_id

    async def init_environment_map(self) -> None:
        """
        Initialize the environment map of the VirtualEnvironmentManager: It will read everything on disk to reconstruct a
        complete view of existing Venvs
        """
        folders = [file for file in self.envs_dir.iterdir() if file.is_dir()]
        for folder in folders:
            # No lock here, singe shot prior to start
            current_folder = self.envs_dir / folder
            self.pool[folder.name] = ExecutorVirtualEnvironment(env_path=str(current_folder), io_threadpool=self.thread_pool)

    async def get_environment(self, blueprint: EnvBlueprint) -> ExecutorVirtualEnvironment:
        """
        Retrieves an existing virtual environment that matches the given blueprint or creates a new one if no match is found.
        Utilizes NamedLock to ensure thread-safe operations for each unique blueprint.
        """
        return await self.get(blueprint)

    async def create_member(self, member_id: EnvBlueprint) -> ExecutorVirtualEnvironment:
        """
        Creates a new virtual environment based on the provided blueprint or reuses an existing one if suitable.
        This involves setting up the virtual environment and installing any required packages as specified in the blueprint.
        This method must execute under the self._locks.get(<blueprint-hash>) lock to ensure thread-safe operations for each
        unique blueprint.

        :param member_id: The blueprint specifying the configuration for the new virtual environment.
        :return: An instance of ExecutorVirtualEnvironment representing the created or reused environment.
        """
        internal_id = member_id.blueprint_hash()
        env_dir_name: str = internal_id
        env_dir: str = os.path.join(self.envs_dir, env_dir_name)

        # Check if the directory already exists and create it if not
        if not os.path.exists(env_dir):
            os.makedirs(env_dir)
            is_new = True
        else:
            LOGGER.debug(
                "Found existing venv for content %s at %s, content hash: %s",
                str(member_id),
                env_dir,
                internal_id,
            )
            is_new = False  # Returning the path and False for existing directory

        process_environment = ExecutorVirtualEnvironment(env_dir, self.thread_pool)

        loop = asyncio.get_running_loop()

        if not is_new and not process_environment.is_correctly_initialized():
            LOGGER.info(
                "Venv is already present but it was not correctly initialized. Re-creating it for content %s, "
                "content hash: %s located in %s",
                str(member_id),
                internal_id,
                env_dir,
            )
            await loop.run_in_executor(self.thread_pool, process_environment.reset)
            is_new = True

        if is_new:
            LOGGER.info("Creating venv for content %s, content hash: %s", str(member_id), internal_id)
            await process_environment.create_and_install_environment(member_id)
        return process_environment


@dataclass
class GetFactReport:
    resource_id: ResourceVersionIdStr
    # Failed fact checks may have empty action_id
    action_id: Optional[uuid.UUID]
    started: datetime.datetime
    finished: datetime.datetime
    success: bool
    parameters: list[dict[str, Any]]
    messages: list[LogLine]
    error_msg: Optional[str] = None
    resource_state: Optional[const.ResourceState] = None


@dataclass
class DeployReport:
    rvid: ResourceVersionIdStr
    resource_id: ResourceIdStr = dataclasses.field(init=False)
    action_id: uuid.UUID
    resource_state: const.HandlerResourceState
    messages: list[LogLine]
    changes: dict[str, AttributeStateChange]
    change: Optional[Change]

    def __post_init__(self) -> None:
        if self.status in {*const.TRANSIENT_STATES, *const.UNDEPLOYABLE_STATES, const.ResourceState.dry}:
            raise ValueError(f"Resource state {self.status} is not a valid state for a deployment result.")
        self.resource_id = Id.parse_id(self.rvid).resource_str()

    @property
    def status(self) -> const.ResourceState:
        """
        Translates the new HandlerResourceState to the const.ResourceState that some of the code still uses
        (mainly parts of the code that communicate with the server)
        """
        if self.resource_state is const.HandlerResourceState.skipped_for_dependency:
            return const.ResourceState.skipped
        return const.ResourceState(self.resource_state)

    @classmethod
    def from_ctx(cls, rvid: ResourceVersionIdStr, ctx: HandlerContext) -> "DeployReport":
        if ctx.status is None:
            ctx.warning("Deploy status field is None, failing!")
            ctx.set_resource_state(const.HandlerResourceState.failed)
        # Make mypy happy
        assert ctx.resource_state is not None
        return DeployReport(
            rvid=rvid,
            action_id=ctx.action_id,
            resource_state=ctx.resource_state or const.HandlerResourceState.failed,
            messages=ctx.logs,
            changes=ctx.changes,
            change=ctx.change,
        )

    @classmethod
    def undeployable(cls, rvid: ResourceVersionIdStr, action_id: UUID, message: LogLine) -> "DeployReport":
        return DeployReport(
            rvid=rvid,
            action_id=action_id,
            resource_state=const.HandlerResourceState.unavailable,
            messages=[message],
            changes={},
            change=Change.nochange,
        )


class Executor(abc.ABC):
    """
    Represents an executor responsible for deploying resources within a specified virtual environment.
    It is identified by an ExecutorId and operates within the context of a given ExecutorVirtualEnvironment.

    :param executor_id: Unique identifier for the executor, encapsulating the agent name and its configuration blueprint.
    :param executor_virtual_env: The virtual environment in which this executor operates
    :param storage: File system path to where the executor's resources are stored.
    """

    failed_resources: FailedResources

    @abc.abstractmethod
    async def execute(
        self,
        action_id: uuid.UUID,
        gid: uuid.UUID,
        resource_details: ResourceDetails,
        reason: str,
        requires: Mapping[ResourceIdStr, const.ResourceState],
    ) -> DeployReport:
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
        resource: ResourceDetails,
        dry_run_id: uuid.UUID,
    ) -> DryrunReport:
        """
        Perform a dryrun for the given resources

        :param resource: Resource for which to perform a dryrun.
        :param dry_run_id: id for this dryrun
        """
        pass

    @abc.abstractmethod
    async def get_facts(self, resource: ResourceDetails) -> GetFactReport:
        """
        Get facts for a given resource
        :param resource: The resource for which to get facts.
        """
        pass

    @abc.abstractmethod
    async def join(self) -> None:
        """Wait for shutdown to be completed"""
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
        Retrieves an Executor for a given agent with the relevant handler code loaded in its venv.
        If an Executor does not exist for the given configuration, a new one is created.

        :param agent_name: The name of the agent for which an Executor is being retrieved or created.
        :param agent_uri: The name of the host on which the agent is running.
        :param code: Collection of ResourceInstallSpec defining the configuration for the Executor i.e.
            which resource types it can act on and all necessary information to install the relevant
            handler code in its venv.
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
    async def start(self) -> None:
        """
        Start the manager.
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
    async def join(self, thread_pool_finalizer: list[concurrent.futures.ThreadPoolExecutor], timeout: float) -> None:
        """
        Wait for all executors to terminate.

        Any threadpools that need to be closed can be handed of to the parent via thread_pool_finalizer
        """
        pass
