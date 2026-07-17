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
import platform
import shutil
import typing
import uuid
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, cast
from uuid import UUID

import packaging.requirements
from inmanta import const, loader, module
from inmanta.agent import config as cfg
from inmanta.agent import resourcepool
from inmanta.agent.handler import HandlerContext
from inmanta.const import Change
from inmanta.data import LogLine
from inmanta.data.model import AttributeStateChange, ExecutorModuleSource, ModuleSource, PipConfig
from inmanta.env import LocalPackagePath, PythonEnvironment
from inmanta.resources import Id
from inmanta.types import FailedInmantaModules, JsonType, ResourceIdStr, ResourceVersionIdStr

LOGGER = logging.getLogger(__name__)


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


def get_libc_version() -> str:
    """
    Return a string of the form "{lib}:{version}", where lib is the name
    of the c library and the version its version number. Return an empty
    string if the libc version cannot be determined. That can happen on
    operating systems that don't rely on libc.
    """
    lib, version = platform.libc_ver()
    if not lib or not version:
        return ""
    return f"{lib}:{version}"


@dataclasses.dataclass
class EditableModuleInstall:
    """
    An inmanta module that was installed in editable mode in the compiler venv and must therefore be reconstructed
    as an installable python package and pip-installed in editable mode in the executor's venv.

    :param name: the inmanta module name (e.g. "std").
    :param version: the module's content-hash version. Together with the name, this constitutes the module's
        contribution to the identity of the venv it is installed in: any change to the module's files or python
        requirements yields a different version and hence a different venv.
    :param python_module_sources: the python files composing this module's inmanta_plugins package.
    :param setup_cfg: content of the module's setup.cfg file, or None if it has none.
    :param pyproject_toml: content of the module's pyproject.toml file, or None if it has none.
    """

    name: str
    version: str
    python_module_sources: Sequence[ModuleSource]
    setup_cfg: bytes | None
    pyproject_toml: bytes | None

    def identity(self) -> tuple[str, str]:
        """The (name, version) pair that fully identifies this editable module for venv pooling purposes."""
        return (self.name, self.version)


@dataclasses.dataclass
class EnvBlueprint:
    """Represents a blueprint for creating virtual environments
    with specific pip configurations, requirements and constraints."""

    environment_id: uuid.UUID
    pip_config: PipConfig
    requirements: Sequence[str]
    _hash_cache: str | None = dataclasses.field(default=None, init=False, repr=False)
    python_version: tuple[int, int]
    project_constraints: str | None = dataclasses.field(default=None, kw_only=True)
    # The libc version determines which python packages are compatible with the machine they run on.
    # If this version is updated, pip might select different packages.
    libc_version: str = dataclasses.field(default_factory=get_libc_version, kw_only=True)
    # Inmanta modules that were installed in editable mode in the compiler venv. They are reconstructed as
    # installable python packages and pip-installed in editable mode when the venv is created. They are part
    # of the venv identity (through their (name, version) pair): a change in an editable module yields a new
    # venv rather than mutating an existing (potentially shared) one.
    editable_modules: Sequence[EditableModuleInstall] = dataclasses.field(default=(), kw_only=True)

    def __post_init__(self) -> None:
        # remove duplicates and make uniform
        self.requirements = sorted(set(self.requirements))

    def blueprint_hash(self) -> str:
        """
        Generate a stable hash for an EnvBlueprint instance by serializing its pip_config, requirements
        and project constraints in a sorted, consistent manner. This ensures that the hash value is
        independent of the order of requirements/constraints and consistent across interpreter sessions.
        Also cache the hash to only compute it once.
        """
        if self._hash_cache is None:
            blueprint_dict: Dict[str, Any] = {
                "environment_id": str(self.environment_id),
                "pip_config": self.pip_config.model_dump(),
                "requirements": self.requirements,
                "python_version": self.python_version,
                "project_constraints": self.project_constraints,
                "libc_version": self.libc_version,
                # Only the (name, version) identity of each editable module matters: the version is a content
                # hash, so it already reflects any change in the module's files or requirements.
                "editable_modules": sorted(editable_module.identity() for editable_module in self.editable_modules),
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
        return (
            self.environment_id,
            self.pip_config,
            set(self.requirements),
            self.python_version,
            self.project_constraints,
            self.libc_version,
            sorted(editable_module.identity() for editable_module in self.editable_modules),
        ) == (
            other.environment_id,
            other.pip_config,
            set(other.requirements),
            other.python_version,
            other.project_constraints,
            other.libc_version,
            sorted(editable_module.identity() for editable_module in other.editable_modules),
        )

    def __hash__(self) -> int:
        return int(self.blueprint_hash(), 16)

    def __str__(self) -> str:
        req = ",".join(str(req) for req in self.requirements)
        constraints = ",".join(self.project_constraints.split("\n")) if self.project_constraints else ""
        editable = ",".join(m.name for m in self.editable_modules)
        return (
            f"EnvBlueprint(environment_id={self.environment_id}, requirements=[{str(req)}], "
            f"constraints=[{constraints}], pip={self.pip_config}, python_version={self.python_version}, "
            f"libc_version={self.libc_version}, editable_modules=[{editable}])"
        )


@dataclasses.dataclass
class ExecutorBlueprint(EnvBlueprint):
    """Extends EnvBlueprint to include sources for the executor environment."""

    sources: Sequence[ExecutorModuleSource]
    _hash_cache: Optional[str] = dataclasses.field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        # remove duplicates and make uniform
        self.sources = sorted(set(self.sources), key=lambda source: source.sort_key())

    @classmethod
    def from_specs(cls, code: typing.Collection["InmantaModuleInstallSpec"]) -> "ExecutorBlueprint":
        """
        Create a single ExecutorBlueprint by combining the blueprint(s) of several
        InmantaModuleInstallSpec by merging respectively their module sources and their
        requirements and making sure they all share the same pip config.
        """

        if not code:
            raise ValueError("from_specs expects at least one resource install spec")
        env_ids = {cd.blueprint.environment_id for cd in code}
        assert len(env_ids) == 1
        sources: set[ExecutorModuleSource] = set()
        requirements: set[str] = set()
        editable_modules: list[EditableModuleInstall] = []
        all_constraints: set[str | None] = set()
        pip_configs: list[PipConfig] = []
        python_versions: list[tuple[int, int]] = []

        for module_install_spec in code:
            # An install spec describes a single inmanta module, which always ships at least one python file.
            # We rely on this below to derive the install mode from its sources.
            if not module_install_spec.blueprint.sources:
                raise ValueError(f"Install spec for module {module_install_spec.module_name} has no sources")

            # Gather all sources (both for editable and package install). During code installation on the agent,
            # we rely on these to know which python modules to load (import) for this executor.
            sources.update(module_install_spec.blueprint.sources)

            # Gather all editable modules. These are reconstructed as installable python packages and pip-installed
            # in editable mode when the venv is created (see ExecutorVirtualEnvironment). This is a no-op for a spec
            # that describes a package install (its blueprint carries no editable modules).
            editable_modules.extend(module_install_spec.blueprint.editable_modules)

            all_constraints.add(module_install_spec.blueprint.project_constraints)

            pip_configs.append(module_install_spec.blueprint.pip_config)

            python_versions.append(module_install_spec.blueprint.python_version)

            # All sources of a single module share the same install mode, so the first one is representative.
            editable_install: bool | None = module_install_spec.blueprint.sources[0].install_on_disk

            if editable_install is None:
                # Compatibility layer for model versions that were exported using iso<10 that are now
                # being deployed / dry-ran. We need to use the "old style" agent code install.
                # This layer can be removed in iso11.

                # install the requirements first, and then the source from the database
                requirements.update(module_install_spec.blueprint.requirements)

            else:
                # We're deploying a model version that was exported using iso>=10
                # We will let pip handle the dependencies when installing the module:
                #  - For editable installs, the module itself is reconstructed and pip-installed in
                #    editable mode. Pip will fetch dependencies from setup.cfg (install_requires)
                #  - For package installs, add the module itself as a requirement:
                if not editable_install:
                    requirements.add(
                        (
                            f"{module.ModuleV2Source.get_package_name_for(module_install_spec.module_name)}=="
                            f"{module_install_spec.module_version}"
                        )
                    )

        # Check that constraints set at the project level are consistent across all modules
        assert len(all_constraints) == 1
        constraints = all_constraints.pop()

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
            environment_id=env_ids.pop(),
            pip_config=base_pip,
            sources=list(sources),
            requirements=list(requirements),
            python_version=base_python_version,
            project_constraints=constraints,
            editable_modules=editable_modules,
        )

    def blueprint_hash(self) -> str:
        """
        Generate a stable hash for an ExecutorBlueprint instance by serializing its pip_config, sources,
        requirements and constraints in a sorted, consistent manner. This ensures that the hash value is
        independent of the order of requirements and consistent across interpreter sessions.
        Also cache the hash to only compute it once.
        """
        if self._hash_cache is None:
            blueprint_dict = {
                "environment_id": str(self.environment_id),
                "pip_config": self.pip_config.model_dump(),
                "requirements": self.requirements,
                # Use the hash values and name to create a stable identity. The install_on_disk and load_module flags
                # are part of the identity as well: two blueprints that ship the same source files but install/load a
                # different subset of them produce different executors. Otherwise they would collide on a single shared
                # executor process, whose loaded modules would depend on which agent won the creation race.
                "sources": [
                    [
                        source.metadata.hash_value,
                        source.metadata.name,
                        source.metadata.is_byte_code,
                        source.install_on_disk,
                        source.load_module,
                    ]
                    for source in self.sources
                ],
                "python_version": self.python_version,
                "project_constraints": self.project_constraints,
                "libc_version": self.libc_version,
                # Fold in the editable modules' identity as well. It is already implied by the sources for a
                # change in the python files, but not for a change limited to the packaging files (setup.cfg,
                # pyproject.toml), which the version hash does capture. Keeping this consistent with the venv
                # identity (EnvBlueprint) guarantees an executor process is never reused across differing venvs.
                "editable_modules": sorted(editable_module.identity() for editable_module in self.editable_modules),
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
        return EnvBlueprint(
            environment_id=self.environment_id,
            pip_config=self.pip_config,
            requirements=self.requirements,
            python_version=self.python_version,
            project_constraints=self.project_constraints,
            libc_version=self.libc_version,
            editable_modules=self.editable_modules,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExecutorBlueprint):
            return False
        return (
            self.environment_id,
            self.pip_config,
            self.requirements,
            self.sources,
            self.python_version,
            self.project_constraints,
            self.libc_version,
            sorted(editable_module.identity() for editable_module in self.editable_modules),
        ) == (
            other.environment_id,
            other.pip_config,
            other.requirements,
            other.sources,
            other.python_version,
            other.project_constraints,
            other.libc_version,
            sorted(editable_module.identity() for editable_module in other.editable_modules),
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
class InmantaModuleInstallSpec:
    """
    This class encapsulates the requirements for a specific (inmanta_module_name, inmanta_module_version).

    :ivar module_name: fully qualified name for this Inmanta module
    :ivar module_version: the version of the module to use
    :ivar blueprint: the associated install blueprint

    """

    module_name: str
    module_version: str
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

        # The .inmanta dir contains
        #   - a status file for bookkeeping. Its presence indicates the successful creation
        #     of the ExecutorVirtualEnvironment and its age determines if this env can be cleaned up.
        #   - (Optionally) a requirements.txt file. It holds the python package constraints
        #     set at the project level enforced on the agent when installing code.
        #   - (Optionally) an editable/ dir. It holds the reconstructed source trees of the editable
        #     inmanta modules that are pip-installed in editable mode in this venv.
        self.inmanta_storage: pathlib.Path = pathlib.Path(self.env_path) / ".inmanta"

        self.inmanta_venv_status_file: pathlib.Path = self.inmanta_storage / const.INMANTA_VENV_STATUS_FILENAME

        # Directory holding the reconstructed source trees of the editable modules installed in this venv. It lives
        # inside the venv so its lifetime is tied to the venv: it is removed together with the venv (remove_venv).
        self.inmanta_editable_dir: pathlib.Path = self.inmanta_storage / "editable"

        self.io_threadpool = io_threadpool

    def ensure_disk_layout_backwards_compatibility(self) -> None:
        """
        Backwards compatibility helper: move files that used to live in the
        top-level dir of the venv into the dedicated storage dir.

        This upgrades from the layout prior to september 2025

        it should be called under the lock of the VirtualEnvironmentManager
        """
        created_storage = False

        for file_name in ["requirements.txt", const.INMANTA_VENV_STATUS_FILENAME]:
            legacy_path: pathlib.Path = pathlib.Path(self.env_path) / file_name
            if legacy_path.exists():
                new_path: pathlib.Path = pathlib.Path(self.inmanta_storage) / file_name
                if not new_path.exists():
                    if not created_storage:
                        os.makedirs(self.inmanta_storage, exist_ok=True)
                        created_storage = True
                    # Use copy2 to preserve last access time metadata (for the status file).
                    shutil.copy2(src=legacy_path, dst=new_path)
                os.remove(legacy_path)

    def _write_constraint_file(self, blueprint: EnvBlueprint) -> str | None:
        """
        Write the constraint file defined in the blueprint to disk and return the path
        to it, or None if no such constraint file is defined.
        """
        if blueprint.project_constraints is not None:
            constraint_file_path = self.inmanta_storage / "requirements.txt"
            with constraint_file_path.open("w") as f:
                f.write(blueprint.project_constraints)
            return str(constraint_file_path)

        return None

    def _reconstruct_editable_module(self, editable_module: EditableModuleInstall) -> str:
        """
        Reconstruct the given editable inmanta module as an installable python package on disk, in this venv's
        storage directory, and return the path to its root (suitable for a pip editable install).

        Each python module is materialized as a package (a directory with an __init__ file), following the layout
        expected by the ``packages=find_namespace:`` build config of V2 modules. In particular, no __init__ file
        is created for the top-level ``inmanta_plugins`` namespace package, so that editable installs of several
        inmanta modules can all contribute to it.
        """
        module_root: pathlib.Path = self.inmanta_editable_dir / editable_module.name
        module_root.mkdir(parents=True, exist_ok=True)
        for module_source in editable_module.python_module_sources:
            relative_path: str = loader.convert_module_to_editable_relative_path(
                module_source.metadata.name, is_byte_code=module_source.metadata.is_byte_code
            )
            target: pathlib.Path = module_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(module_source.source)

        if editable_module.setup_cfg is not None:
            (module_root / module.ModuleV2.MODULE_FILE).write_bytes(editable_module.setup_cfg)
        if editable_module.pyproject_toml is not None:
            (module_root / module.ModuleV2.PYPROJECT_FILE).write_bytes(editable_module.pyproject_toml)

        return str(module_root)

    async def _create_and_install_environment(self, blueprint: EnvBlueprint) -> None:
        """
        Creates and configures the virtual environment according to the provided blueprint.

        :param blueprint: An instance of EnvBlueprint containing the configuration for
            the pip installation and the requirements to install.
        """
        req: list[str] = list(blueprint.requirements)
        await asyncio.get_running_loop().run_in_executor(self.io_threadpool, self.init_env)
        # Ensure our storage folder exists
        os.makedirs(self.inmanta_storage, exist_ok=True)

        constraint_file: str | None = self._write_constraint_file(blueprint)

        # Reconstruct the editable modules on disk and install them in editable mode alongside the requirements.
        editable_paths: list[LocalPackagePath] = [
            LocalPackagePath(path=self._reconstruct_editable_module(editable_module), editable=True)
            for editable_module in blueprint.editable_modules
        ]

        if req or editable_paths:  # install_for_config expects at least 1 requirement or a path to install
            await self.async_install_for_config(
                requirements=[packaging.requirements.Requirement(requirement_string=e) for e in req],
                config=blueprint.pip_config,
                constraint_files=[constraint_file] if constraint_file else None,
                paths=editable_paths,
            )

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
        Remove the venv of the executor.

        This method must be called on a threadpool to not block the ioloop.
        """
        try:
            # Remove the status file first. Like this we will rebuild the venv on use
            # if the rmtree() call was interrupted because of a system failure.
            os.remove(self.inmanta_venv_status_file)
        except Exception:
            pass
        try:
            LOGGER.debug("Removing venv %s", self.env_path)
            # Will also delete .inmanta storage dir
            shutil.rmtree(self.env_path)
        except Exception:
            LOGGER.exception(
                "An error occurred while removing the venv located %s",
                self.env_path,
            )

    def reset(self) -> None:
        """
        Remove the venv of the executor and recreate the directory of the venv.

        This method must be called on a threadpool to not block the ioloop.
        """
        self.remove_venv()


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

    async def remove_all_venvs(self) -> None:
        """
        Removes all the venvs from disk. It's the responsibility of the caller
        to make sure the venvs are no longer used.
        """
        folders = [file for file in self.envs_dir.iterdir() if file.is_dir()]
        for folder in folders:
            if folder.name in self.pool:
                # The ExecutorVirtualEnvironment is managed by this VirtualEnvironmentManager.
                # Rely on the normal shutdown flow to clean up all datastructures correctly.
                virtual_environment = self.pool[folder.name]
                future: asyncio.Future[None] = asyncio.Future()

                async def venv_cleanup_is_done(exec_virt_env: resourcepool.PoolMember[resourcepool.TPoolID]) -> None:
                    future.set_result(None)

                virtual_environment.termination_listeners.append(venv_cleanup_is_done)
                await virtual_environment.request_shutdown()
                await future
            else:
                # This should normally not happen, unless somebody added a directory manually
                # to the venv directory while the server was running. Let's clean it up anyway.
                fq_path = os.path.join(self.envs_dir, folder.name)
                try:
                    await asyncio.get_running_loop().run_in_executor(self.thread_pool, shutil.rmtree, fq_path)
                except Exception:
                    LOGGER.exception("An error occurred while removing the venv located %s", fq_path)

    async def init_environment_map(self) -> None:
        """
        Initialize the environment map of the VirtualEnvironmentManager: It will read everything on disk to reconstruct a
        complete view of existing Venvs
        """
        folders = [file for file in self.envs_dir.iterdir() if file.is_dir()]
        for folder in folders:
            # No lock here, singe shot prior to start
            virtual_environment = ExecutorVirtualEnvironment(env_path=str(folder), io_threadpool=self.thread_pool)
            virtual_environment.ensure_disk_layout_backwards_compatibility()
            if virtual_environment.is_correctly_initialized():
                self.pool[folder.name] = virtual_environment
            else:
                await asyncio.get_running_loop().run_in_executor(self.thread_pool, virtual_environment.remove_venv)

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
            is_new = False

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
            await process_environment._create_and_install_environment(member_id)

        process_environment.touch()
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
    async def get_executor(self, agent_name: str, agent_uri: str, code: typing.Collection[InmantaModuleInstallSpec]) -> E:
        """
        Retrieves an Executor for a given agent with the relevant handler code loaded in its venv.
        If an Executor does not exist for the given configuration, a new one is created.

        :param agent_name: The name of the agent for which an Executor is being retrieved or created.
        :param agent_uri: The name of the host on which the agent is running.
        :param code: Collection of InmantaModuleInstallSpec defining the configuration for the Executor i.e.
            which resource types it can act on and all necessary information to install the relevant
            handler code in its venv. Must have at least one element.
        :return: An Executor instance
        """

    @abc.abstractmethod
    def get_environment_manager(self) -> VirtualEnvironmentManager | None:
        """
        Returns the VirtualEnvironmentManager used by this ExecutorManager or None if this
        ExecutorManager doesn't have a VirtualEnvironmentManager.
        """

    @abc.abstractmethod
    async def stop_all_executors(self) -> list[E]:
        """
        Stop all executors started by the ExecutorManager.
        """
        pass

    @abc.abstractmethod
    async def stop_for_agent(self, agent_name: str) -> list[E]:
        """
        Indicate that all executors for this agent can be stopped.

        Because multiple agents can run on the same executor, this method only stops the executor if no more
        agents are running on it.

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


class ModuleLoadingException(Exception):
    """
    This exception is raised when some Inmanta modules couldn't be loaded on a given agent.
    """

    def __init__(self, failed_modules: FailedInmantaModules) -> None:
        """
        :param failed_modules: Data for all module loading errors as a nested map of
            inmanta module name -> python module name -> Exception.
        """
        self.failed_modules = failed_modules

    def _format_module_loading_errors(self) -> str:
        """
        Helper method to display module loading failures.
        """
        formatted_module_loading_errors = ""
        N_FAILURES = sum(len(v) for v in self.failed_modules.values())
        failure_index = 1

        for _, failed_modules_data in self.failed_modules.items():
            for python_module, exception in failed_modules_data.items():
                formatted_module_loading_errors += f"Error {failure_index}/{N_FAILURES}:\n"
                formatted_module_loading_errors += f"In module {python_module}:\n"
                formatted_module_loading_errors += str(exception)
                failure_index += 1

        return formatted_module_loading_errors

    def create_log_line_for_failed_modules(
        self, agent: str, level: int = logging.ERROR, *, verbose_message: bool = False
    ) -> LogLine:
        """
        Helper method to convert this Exception into a LogLine.

        :param agent: Name of the agent for which module loading was unsuccessful
        :param level: The log level for the resulting LogLine
        :param verbose_message: Whether to include the full formatted error output in the LogLine message.
            When displayed on the webconsole, the full formatted error output will be displayed in its own section
            regardless of this flag's value.

        """
        message = "Agent %s failed to load the following modules: %s." % (
            agent,
            ", ".join(self.failed_modules.keys()),
        )

        formatted_module_loading_errors = self._format_module_loading_errors()

        if verbose_message:
            message += f"\n{formatted_module_loading_errors}"
        return LogLine.log(
            level=level,
            msg=message,
            timestamp=None,
            errors=formatted_module_loading_errors,
        )

    def log_resource_action_to_scheduler_log(
        self, agent: str, rid: ResourceVersionIdStr, *, include_exception_info: bool
    ) -> None:
        """
        Helper method to log module loading failures to the scheduler's resource action log.

        This method does not write anything to the 'resourceaction' table, which is what is ultimately displayed in the
        'Logs' tab of the 'Resource Details' page in the web console. Therefore, the caller is responsible
        for making sure that the scheduler's resource action log and the web console logs remain somewhat in sync.

        """
        log_line = self.create_log_line_for_failed_modules(agent=agent, verbose_message=True)
        log_line.write_to_logger_for_resource(agent=agent, resource_version_string=rid, exc_info=include_exception_info)
