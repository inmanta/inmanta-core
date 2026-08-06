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

import hashlib
import importlib
import importlib.util
import inspect
import logging
import os
import pathlib
import shutil
import sys
import traceback
import types
from collections import abc, defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from importlib.abc import FileLoader, MetaPathFinder
from importlib.machinery import ModuleSpec, SourcelessFileLoader
from itertools import chain
from typing import TYPE_CHECKING, Optional

from inmanta import const, module
from inmanta.data.model import AgentName, ExecutorModuleSource, InmantaModule, InmantaModuleName, ModuleSource
from inmanta.stable_api import stable_api
from inmanta.types import FailedInmantaModules, FailedPythonModules
from inmanta.util import hash_file_streaming

VERSION_FILE = "version"
MODULE_DIR = "modules"
PLUGIN_DIR = "plugins"

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inmanta.data.model import ModuleSourceMetadata
    from inmanta.resources import Id


def get_inmanta_module_name(python_module_name: str) -> InmantaModuleName:
    """Small utility to convert python module into inmanta module"""
    module_parts = python_module_name.split(".")
    if module_parts[0] != const.PLUGINS_PACKAGE:
        raise Exception(
            "All instances from which the source is loaded, should be defined in the inmanta plugins package. "
            "%s does not match" % python_module_name
        )
    return module_parts[1]


class SourceNotFoundException(Exception):
    """This exception is raised when module source is not found"""


class CodeManager:
    """
    This class is responsible for collecting source code for types (resources, handlers, ...) that need to be
    available in a remote process (e.g. agent).

    At initialization, uses the collection of all resources to determine for each agent which resource types
    it is responsible for.

    ``register_code()`` is the main entrypoint for registering code. It will populate internal state.
    Finally, ``get_module_version_info()``, ``get_file_hashes()`` and ``get_file_content()`` can be used to
    retrieve the module sources with appropriate metadata.

    __file_info: Stores metadata about each individual source code file. The keys are file paths and the values
                 in this dictionary are ``ModuleSource`` objects.
    """

    def __init__(self, resources: Collection["Id"]) -> None:
        """
        :param resources: Collection of all resources present in the current compile run.
        """
        # Map of [path, ModuleSource]
        # To which python module do these python files belong
        self.__file_info: dict[str, ModuleSource] = {}

        # Content of non-python-module files that must be uploaded to the server as well, keyed by content hash.
        # These are the packaging files (setup.cfg, pyproject.toml) of editable modules.
        self.__packaging_files_content: dict[str, bytes] = {}

        self._types_to_agent: dict[str, set[AgentName]] = defaultdict(set)

        for id in resources:
            self._types_to_agent[id.entity_type].add(id.agent_name)

        project = module.Project.get()

        # A map of {module_name: module} containing all modules that were loaded
        # in the venv of the compiler. Keys are 'raw' Inmanta module names e.g. "std".
        self._loaded_modules: Mapping[InmantaModuleName, "module.Module[module.ModuleMetadata]"] = project.modules
        # The collection of modules installed in editable mode
        # in the venv of the compiler. The Inmanta module name is used e.g. "std".
        self._editable_installed_modules: frozenset[InmantaModuleName] = frozenset(
            project.get_editable_installed_inmanta_modules()
        )

        # Map of [inmanta_module_name, inmanta module]
        self.module_version_info: dict[InmantaModuleName, "InmantaModule"] = {}

    def register_code(self, resource_entity_type: str, class_definition: type[object]) -> None:
        """
        Register a type that is required for proper management of the given resource type.
        Derives the object's inmanta module, as well as which agents require it, based on the resource type to agent mapping.

        :param resource_entity_type: The inmanta type name (e.g. std::testing::NullResource) for which the source
            code of class_definition will be registered.
        :param class_definition: Definition of either a resource, a handler, a reference or a mutator class
            for which the code needs to be registered. This is the actual decorated (e.g. by @resource) class defined
            inside a plugin.
        """
        file_name = self.get_object_source(class_definition)
        if file_name is None:
            raise SourceNotFoundException(
                f"Unable to locate source code of definition {class_definition} for entity {resource_entity_type}"
            )

        # get the module
        module_name = get_inmanta_module_name(class_definition.__module__)

        if module_name not in self._loaded_modules:
            raise SourceNotFoundException(
                "Module %s is imported in plugin code but not in model code. Either remove the unused import, "
                "or make sure to import the module in model code." % module_name
            )

        editable_install = module_name in self._editable_installed_modules

        registered_agents: set[AgentName] = self._types_to_agent.get(resource_entity_type, set())

        # Register this module, or extend its agent sets if we have seen it before
        self._register_inmanta_module(
            module_name,
            self._loaded_modules[module_name],
            editable_install=editable_install,
            registered_agents=registered_agents,
        )

    def _register_inmanta_module(
        self,
        inmanta_module_name: InmantaModuleName,
        mod: "module.Module[module.ModuleMetadata]",
        *,
        editable_install: bool,
        registered_agents: set[AgentName],
    ) -> None:
        """
        Register the metadata of the given Inmanta module, or, if it was already registered for another resource type,
        extend the sets of agents that load and install it.

        :param editable_install: Whether this module was installed in editable mode in the compiler venv.
        :param registered_agents: The agents that manage the resource type for which this module is being registered.
        """
        registered_module: Optional[InmantaModule] = self.module_version_info.get(inmanta_module_name)
        if registered_module is not None:
            registered_module.load_module_on_agents = list({*registered_module.load_module_on_agents, *registered_agents})
            return

        if editable_install:
            # [editable install mode] (editable installs are always V2 modules) # TODO handle v1 modules
            # We need to store the relevant files in the db to recreate this module as an installable python
            # package on the agent side, i.e.:
            #    - python code in the inmanta_plugins dir (plugin_files_metadata, gathered above)
            #    - the packaging metadata files (setup.cfg, pyproject.toml)
            module_sources: list[ModuleSource] = []

            for absolute_path, fqn_module_name in mod.get_plugin_files():
                source_info = ModuleSource.from_path(absolute_path=absolute_path, name=fqn_module_name)
                self.__file_info[absolute_path] = source_info
                module_sources.append(source_info)

            plugin_files_metadata = [module_source.metadata for module_source in module_sources]
            requirements = self.get_inmanta_module_requirements(inmanta_module_name)

            # Content hash per packaging file, keyed by file name. The content itself is staged for upload in
            # __packaging_files_content so that it gets uploaded to the server alongside the plugin sources.
            packaging_file_hashes: dict[str, str] = {}
            for (
                packaging_file_path,
                packaging_file_name,
            ) in mod.get_metadata_files():  # TODO v1: add a get_metadata_files  method ?
                with open(packaging_file_path, "rb") as fd:
                    content = fd.read()
                content_hash = hashlib.new("sha1", content).hexdigest()
                self.__packaging_files_content[content_hash] = content
                packaging_file_hashes[packaging_file_name] = content_hash

            module_version = self.get_module_version(requirements, plugin_files_metadata, list(packaging_file_hashes.values()))

            self.module_version_info[inmanta_module_name] = InmantaModule(
                name=inmanta_module_name,
                version=module_version,
                python_files_metadata=plugin_files_metadata,
                requirements=list(requirements),
                setup_cfg_hash=packaging_file_hashes.get(module.ModuleV2.MODULE_FILE),  # TODO v1 modules as well
                pyproject_toml_hash=packaging_file_hashes.get(module.ModuleV2.PYPROJECT_FILE),  # TODO v1 modules as well
                load_module_on_agents=list(registered_agents),
                editable_install=True,
            )
        else:
            # [package install mode]
            # Store the pep 440 version of the module in the db. Neither the python files that make up this module nor
            # its python requirements are stored: the agent installs the module with pip, which resolves the
            # requirements, and discovers the python files in its venv.
            self.module_version_info[inmanta_module_name] = InmantaModule(
                name=inmanta_module_name,
                version=str(mod.version),
                python_files_metadata=None,
                requirements=None,
                load_module_on_agents=list(registered_agents),
                editable_install=False,
            )

    def get_object_source(self, instance: object) -> Optional[str]:
        """Get the path of the source file in which type_object is defined"""
        try:
            return inspect.getsourcefile(instance)
        except TypeError:
            return None

    def get_file_hashes(self) -> Iterable[str]:
        """Return the hashes of all files that must be uploaded (python module sources and packaging files)"""
        return chain((info.metadata.hash_value for info in self.__file_info.values()), self.__packaging_files_content.keys())

    def get_module_version_info(self) -> Mapping[InmantaModuleName, "InmantaModule"]:
        """Return all module version info"""
        return self.module_version_info

    @staticmethod
    def get_inmanta_module_requirements(module_name: InmantaModuleName) -> set[str]:
        """Get the list of python requirements associated with this inmanta module"""
        project: module.Project = module.Project.get()
        mod: module.Module[module.ModuleMetadata] = project.modules[module_name]
        return set(mod.get_all_python_requirements_as_list())

    @staticmethod
    def get_module_version(
        requirements: set[str],
        module_sources: Sequence["ModuleSourceMetadata"],
        metadata_file_hashes: Sequence[str],
    ) -> str:
        module_version_hash = hashlib.new("sha1")

        for module_source in sorted(module_sources, key=lambda f: f.hash_value):
            module_version_hash.update(module_source.hash_value.encode())

        for metadata_file_hash in sorted(metadata_file_hashes):
            module_version_hash.update(metadata_file_hash.encode())

        for requirement in sorted(requirements):
            module_version_hash.update(str(requirement).encode())

        return module_version_hash.hexdigest()

    def get_file_content(self, hash: str) -> bytes:
        """Get the file content for the given hash"""
        for info in self.__file_info.values():
            if info.metadata.hash_value == hash:
                return info.source

        if hash in self.__packaging_files_content:
            return self.__packaging_files_content[hash]

        raise KeyError("No file found with this hash")


class ModuleImportException(Exception):
    """Raised when a python module could not be imported during agent code loading."""

    def __init__(self, base_exception: Exception, module_name: str):
        self.message = f"Failed to import module source {module_name}:\n{str(base_exception)}.\n"
        self.tb = "".join(traceback.format_tb(base_exception.__traceback__))
        self.__cause__ = base_exception

    def __str__(self) -> str:
        return self.message + self.tb + "\n"


class CodeLoader:
    """
    Class responsible for managing code loaded from modules received from the compiler

    :param code_dir: The directory where the code is stored
    """

    def __init__(self, code_dir: str, clean: bool = False) -> None:
        self.__code_dir = code_dir
        # A map with all modules we loaded, and its hv (None for modules whose content is not transported)
        self.__modules: dict[str, tuple[Optional[str], types.ModuleType]] = {}

        self.__check_dir(clean)

        self.mod_dir = os.path.join(self.__code_dir, MODULE_DIR)

    def __check_dir(self, clean: bool = False) -> None:
        """
        Check if the code directory
        """
        if clean and os.path.exists(self.__code_dir):
            shutil.rmtree(self.__code_dir)

        # check for the code dir
        if not os.path.exists(self.__code_dir):
            os.makedirs(self.__code_dir, exist_ok=True)

        # check for modules subdir
        if not os.path.exists(os.path.join(self.__code_dir, MODULE_DIR)):
            os.makedirs(os.path.join(self.__code_dir, MODULE_DIR), exist_ok=True)

    def load_module(self, mod_name: str, hv: Optional[str] = None) -> None:
        """
        Ensure the given module is loaded. Does not capture any import errors.

        :param mod_name: Name of the module to load
        :param hv: hash value of the content of the module, if it is known. Package installed modules pass None: their
            content is not transported but pinned by the version installed in this executor's venv.

        :raises Exception: When the provided hash value is different from the one in the cache for this module.
        """

        # Importing a module -> only the first import loads the code
        # cache of loaded modules mechanism -> starts afresh when agent is restarted
        if mod_name in self.__modules:
            if hv is not None and hv != self.__modules[mod_name][0]:
                raise Exception(f"The content of module {mod_name} changed since it was last imported.")
            LOGGER.debug("Module %s is already loaded", mod_name)
            return
        else:
            mod = importlib.import_module(mod_name)
        self.__modules[mod_name] = (hv, mod)
        LOGGER.info("Loaded module %s", mod_name)

    def install_source(self, module_source: ModuleSource) -> None:
        """
        Ensure the given module source is available on disk.
        """
        # Modules written to disk here are only importable through the PluginModuleFinder: mod_dir is never added to
        # sys.path. Configure it lazily on this old-style (iso9 / in-process) install path so the new-style (iso10) load
        # path, which imports modules straight from the venv, never installs the finder. The call is idempotent, so it is
        # cheap to run per source. The finder can be dropped altogether once iso9 support is removed (iso11, #10592).
        PluginModuleFinder.configure_module_finder(modulepaths=[self.mod_dir], prefer=True)
        # if the module is new, or update
        if (
            module_source.metadata.name not in self.__modules
            or module_source.metadata.hash_value != self.__modules[module_source.metadata.name][0]
        ):
            LOGGER.info("Deploying code (hv=%s, module=%s)", module_source.metadata.hash_value, module_source.metadata.name)

            all_modules_dir: str = os.path.join(self.__code_dir, MODULE_DIR)
            relative_module_path: str = convert_module_to_relative_path(module_source.metadata.name)
            # Treat all modules as a package for simplicity: module is a dir with source in __init__.py
            module_dir: str = os.path.join(all_modules_dir, relative_module_path)

            package_dir: str = os.path.normpath(
                os.path.join(all_modules_dir, pathlib.PurePath(pathlib.PurePath(relative_module_path).parts[0]))
            )

            if module_source.metadata.is_byte_code:
                init_file = "__init__.pyc"
                alternate_file = "__init__.py"
            else:
                init_file = "__init__.py"
                alternate_file = "__init__.pyc"

            def touch_inits(directory: str) -> None:
                """
                Make sure __init__.py files exist for this package and all parent packages. Required for compatibility
                with pre-2020.4 inmanta clients because they don't necessarily upload the whole package.
                """
                normdir: str = os.path.normpath(directory)
                if normdir == package_dir:
                    return
                if not os.path.exists(os.path.join(normdir, "__init__.py")) and not os.path.exists(
                    os.path.join(normdir, "__init__.pyc")
                ):
                    pathlib.Path(os.path.join(normdir, "__init__.py")).touch()
                touch_inits(os.path.dirname(normdir))

            # ensure correct package structure
            os.makedirs(module_dir, exist_ok=True)
            touch_inits(os.path.dirname(module_dir))
            source_file = os.path.join(module_dir, init_file)

            if os.path.exists(os.path.join(module_dir, alternate_file)):
                # A file of the other type exists, we should clean it up
                os.remove(os.path.join(module_dir, alternate_file))

            if os.path.exists(source_file):
                with open(source_file, "rb") as fh:
                    thehash = hash_file_streaming(fh)
                if thehash == module_source.metadata.hash_value:
                    LOGGER.debug(
                        "Not deploying code (hv=%s, module=%s) because it is already on disk",
                        module_source.metadata.hash_value,
                        module_source.metadata.name,
                    )
                    return

            # write the new source
            with open(source_file, "wb+") as fd:
                fd.write(module_source.source)
        else:
            LOGGER.debug(
                "Not deploying code (hv=%s, module=%s) because of cache hit",
                module_source.metadata.hash_value,
                module_source.metadata.name,
            )

    def deploy_version(self, module_sources: Iterable[ModuleSource]) -> None:
        """
        Ensure the given module sources are available on disk.
        """
        sources = set(module_sources)
        for module_source in sources:
            self.install_source(module_source)

    def deploy_and_load(
        self,
        module_sources: Sequence[ExecutorModuleSource],
        inmanta_modules_to_load: Sequence[InmantaModuleName],
        logger: logging.Logger,
    ) -> FailedInmantaModules:
        """
        Install the given module sources on disk and import the ones registered for this executor. Additionally import
        the code of the given package installed inmanta modules, which is already present in this executor's venv.

        :param module_sources: The module sources destined for this executor.
        :param inmanta_modules_to_load: The names of the inmanta modules that were installed as a python package in this
            executor's venv and whose python code has to be imported. Their python files are not transported, they are
            discovered in the venv.
        :param logger: The executor-scoped logger to use when reporting install and import failures.
        :return: The python modules that could not be installed or imported, grouped by inmanta module.
        """

        def deploy_and_load_modules_iso9(module_sources: Sequence[ExecutorModuleSource]) -> FailedInmantaModules:
            """
            Compatibility layer method that install and loads the given module_sources using the "old-style" (iso<10) of
            code install on the agent:
                - Agents that "directly" require an Inmanta module (i.e. agents that were registered to
                  use some of its handler code and/or references the module defines) will install these modules from source.
                - "Indirect" Inmanta module requirements (e.g. to reuse a method defined in a plugin) will already have been
                  installed via pip during the executor venv creation along with other regular python requirements.
                - We will only attempt to load modules that were successfully installed from source.

            This compatibility layer method can be dropped in iso11.
            :return: The python modules that could not be installed or imported, grouped by inmanta module.
            """
            failed: FailedInmantaModules = defaultdict(dict)

            in_place: list[ExecutorModuleSource] = []
            # First put all files on disk
            for module_source in module_sources:
                fq_module_name = module_source.get_fq_module_name()
                try:
                    self.install_source(module_source)
                    in_place.append(module_source)
                except Exception as e:
                    logger.info("Failed to load source on disk: %s", fq_module_name, exc_info=True)
                    inmanta_module_name = module_source.get_inmanta_module_name()
                    failed[inmanta_module_name][fq_module_name] = e

            # then try to import them
            for module_source in in_place:
                fq_module_name = module_source.get_fq_module_name()
                try:
                    self.load_module(fq_module_name, module_source.metadata.hash_value)
                except Exception as e:
                    logger.info("Failed to import source: %s", fq_module_name, exc_info=True)
                    inmanta_module_name = module_source.get_inmanta_module_name()
                    failed[inmanta_module_name][fq_module_name] = ModuleImportException(e, fq_module_name)

            return failed

        def load_modules_iso10(
            module_sources: Sequence[ExecutorModuleSource], inmanta_modules_to_load: Sequence[InmantaModuleName]
        ) -> FailedInmantaModules:
            """
            Compatibility layer method that loads the given module_sources using the "new-style" (iso10+) of
            code install on the agent:
              - Modules installed in editable mode in the compiler venv will have been reconstructed as installable
                python packages and pip-installed in editable mode during the executor venv creation.
              - Modules installed in package mode in the compiler venv will already have been
                installed on the agent via pip during the executor venv creation along with other regular python requirements.
                Their python files are not transported: they are discovered in the venv.
              - Either way, the code already lives in the venv, so this method only has to import the modules registered
                for this agent (the sources flagged with load_module), regardless of the install mode.

            This compatibility layer method can be dropped in iso11 and its code moved to the parent deploy_and_load method.

            Failures are collected per module and returned rather than raised, so that a single broken module does not
            prevent the others from being loaded.

            :return: The python modules that could not be imported, grouped by inmanta module.
            """
            failed: FailedInmantaModules = defaultdict(dict)

            for module_source in module_sources:
                assert module_source.load_module is not None

                if module_source.load_module:
                    fq_module_name = module_source.get_fq_module_name()
                    try:
                        self.load_module(fq_module_name, module_source.metadata.hash_value)
                    except Exception as e:
                        logger.info("Failed to import source: %s", fq_module_name, exc_info=True)
                        failed[module_source.get_inmanta_module_name()][fq_module_name] = ModuleImportException(
                            e, module_source.metadata.name
                        )

            for inmanta_module_name in inmanta_modules_to_load:
                failed_python_modules = self.load_installed_inmanta_module(inmanta_module_name, logger)
                if failed_python_modules:
                    failed[inmanta_module_name].update(failed_python_modules)

            return failed

        # Compatibility layer: use the first source to determine if we should use new style (>iso10) or old
        # style (<iso10) of code install. This value should be consistent across all module sources (e.g. either set to None
        # for all of them or set to a proper bool value)
        # An executor without any source can only be a new style one: old style code install always transports the source
        # of every module registered for the agent.
        # This compatibility layer can be removed in iso11 once we no longer need to deploy / dry-run versions using module
        # sources for which the install_on_disk and load_module is None (because it cannot be determined unless a full
        # compile is ran)

        if module_sources and module_sources[0].install_on_disk is None:
            return deploy_and_load_modules_iso9(module_sources)
        else:
            return load_modules_iso10(module_sources, inmanta_modules_to_load)

    def load_installed_inmanta_module(
        self, inmanta_module_name: InmantaModuleName, logger: logging.Logger
    ) -> FailedPythonModules:
        """
        Import all the python files of an inmanta module that was installed as a python package in this executor's venv.
        Because the source of such a module is not transported, the files that make it up are discovered in the venv.

        :param inmanta_module_name: The name of the inmanta module to load, e.g. "std".
        :param logger: The executor-scoped logger to use when reporting discovery and import failures.
        :return: The python modules that could not be discovered or imported.
        """
        failed: FailedPythonModules = {}
        top_level_module_name = f"{const.PLUGINS_PACKAGE}.{inmanta_module_name}"

        try:
            plugin_dir = get_installed_plugin_dir(inmanta_module_name)
            plugin_files = list(discover_plugin_files(plugin_dir, inmanta_module_name))
        except Exception as e:
            logger.info("Failed to discover the python files of module %s", inmanta_module_name, exc_info=True)
            return {top_level_module_name: e}

        for _, fq_module_name in plugin_files:
            try:
                self.load_module(fq_module_name)
            except Exception as e:
                logger.info("Failed to import source: %s", fq_module_name, exc_info=True)
                failed[fq_module_name] = ModuleImportException(e, fq_module_name)

        return failed


class PluginModuleLoader(FileLoader):
    """
    A custom module loader which imports the V1 modules in the inmanta_plugins namespace package.
    V2 modules are loaded using the standard Python loader.
    """

    def __init__(self, fullname: str, path_to_module: str) -> None:
        """
        :param fullname: A fully qualified import path to the module or package to be imported
        :param path_to_module: Path to the file on disk that belongs to the import `fullname`. This should be an empty
                               string when the top-level package inmanta_plugins is imported.
        """
        super().__init__(fullname, path_to_module)
        self.path: str

    def exec_module(self, module: types.ModuleType) -> None:
        return super().exec_module(module)

    def get_source(self, fullname: str) -> bytes:
        # No __init__.py exists for top level package
        if self._loading_top_level_package():
            return b""
        with open(self.path, "rb") as fd:
            return fd.read()

    def is_package(self, fullname: str) -> bool:
        if self._loading_top_level_package():
            return True
        return os.path.basename(self.path) == "__init__.py"

    def _loading_top_level_package(self) -> bool:
        return self.path == ""


class ByteCodePluginModuleLoader(SourcelessFileLoader):
    def is_package(self, fullname: str) -> bool:
        if self._loading_top_level_package():
            return True
        return os.path.basename(self.path) == "__init__.pyc"

    def _loading_top_level_package(self) -> bool:
        return self.path == ""


def strip_py(module: list[str]) -> list[str]:
    """
    Strip __init__.py or .py file extension from module parts.
    """
    if module == []:
        return []
    init, last = module[:-1], module[-1]
    if last == "__init__.py" or last == "__init__.pyc":
        return init
    if last.endswith(".py"):
        return list(chain(init, [last[:-3]]))
    if last.endswith(".pyc"):
        return list(chain(init, [last[:-4]]))
    return module


def split(path: str) -> Iterator[str]:
    """
    Returns an iterator over path's parts.
    """
    if path == "":
        return iter(())
    init, last = os.path.split(path)
    yield from split(init)
    if last != "":
        yield last


def convert_relative_path_to_module(path: str) -> str:
    """
    Returns the fully qualified module name given a path, relative to the module directory.
    For example
        convert_relative_path_to_module("my_mod/plugins/my_submod")
        == convert_relative_path_to_module("my_mod/plugins/my_submod.py")
        == convert_relative_path_to_module("my_mod/plugins/my_submod/__init__.py")
        == "inmanta_plugins.my_mod.my_submod".
    """
    if path.startswith("/"):
        raise Exception("Error parsing module path: expected relative path, got %s" % path)

    parts: list[str] = list(split(path))

    if parts == []:
        return const.PLUGINS_PACKAGE

    if len(parts) == 1 or parts[1] != PLUGIN_DIR:
        raise Exception(f"Error parsing module path: expected 'some_module/{PLUGIN_DIR}/some_submodule', got {path}")

    top_level_inmanta_module: str = parts[0]
    inmanta_submodule: list[str] = parts[2:]

    # my_mod/plugins/tail -> inmanta_plugins.my_mod.tail
    return ".".join(chain([const.PLUGINS_PACKAGE, top_level_inmanta_module], strip_py(inmanta_submodule)))


def convert_module_to_editable_relative_path(full_mod_name: str, *, is_byte_code: bool) -> str:
    """
    Returns the path, relative to the reconstructed module root, at which the python module `full_mod_name` should be
    written when reconstructing an editable inmanta module as an installable python package.

    Each python module is materialized as a package (a directory with an __init__ file), following the layout expected by
    the ``packages=find_namespace:`` build config of V2 modules. No __init__ file is created for the top-level
    ``inmanta_plugins`` namespace package itself, so that editable installs of several inmanta modules can all contribute
    to it. For example convert_module_to_editable_relative_path("inmanta_plugins.my_mod.my_submod", is_byte_code=False)
    == "inmanta_plugins/my_mod/my_submod/__init__.py".
    """
    parts: list[str] = full_mod_name.split(".")
    if parts[0] != const.PLUGINS_PACKAGE:
        raise Exception(
            f"Module {full_mod_name} is not part of the {const.PLUGINS_PACKAGE} package.",
        )
    init_file: str = "__init__.pyc" if is_byte_code else "__init__.py"
    return os.path.join(*parts, init_file)


def convert_module_to_relative_path(full_mod_name: str) -> str:
    """
    Returns path to the module, relative to the module directory. Does not differentiate between modules and packages.
    For example convert_module_to_relative_path("inmanta_plugins.my_mod.my_submod") == "my_mod/plugins/my_submod".
    An empty string is returned when `full_mod_name` equals `inmanta_plugins`.
    """
    full_module_parts = full_mod_name.split(".")
    if full_module_parts[0] != const.PLUGINS_PACKAGE:
        raise Exception(
            "PluginModuleLoader is a loader for the inmanta_plugins package."
            " Module %s is not part of the inmanta_plugins package." % full_mod_name,
        )
    module_parts = full_module_parts[1:]
    # No __init__.py exists for top level package
    if len(module_parts) == 0:
        return ""

    module_parts.insert(1, PLUGIN_DIR)

    if module_parts[-1] == "__init__":
        module_parts = module_parts[:-1]

    return os.path.join(*module_parts)


def list_python_files(plugin_dir: str) -> list[str]:
    """
    Return the path of every python file in the given plugin directory. This method prioritizes .pyc files over .py
    files, includes namespace packages and excludes the `model`, `files` and `templates` directories, which a V2 module
    ships inside its python package.

    :param plugin_dir: The directory that holds the python code of a single inmanta module.
    """
    # Map of [path without extension, path] to prioritize .pyc files over .py files
    files: dict[str, str] = {}

    for dirpath, dirnames, filenames in os.walk(plugin_dir, topdown=True):
        if dirpath == plugin_dir:
            # A V2 module ships these directories inside its python package. Modify dirnames in-place to stop os.walk
            # from descending into them. Only the top level ones are excluded: a nested directory with such a name is a
            # regular python package.
            dirnames[:] = [dir_name for dir_name in dirnames if dir_name not in ("model", "files", "templates")]

        for filename in filenames:
            file_path = os.path.join(dirpath, filename)

            # Skip files in the default cache directory
            if "__pycache__" in file_path:
                continue

            base_file_path, extension = os.path.splitext(file_path)

            if extension == ".pyc":
                files[base_file_path] = file_path
            elif extension == ".py" and base_file_path not in files:
                files[base_file_path] = file_path

    return list(files.values())


def discover_plugin_files(plugin_dir: str, inmanta_module_name: InmantaModuleName) -> Iterator[tuple[str, str]]:
    """
    Return a tuple (absolute_path, fq_python_module_name) for every python file in the given plugin directory.

    :param plugin_dir: The directory that holds the python code of the given inmanta module.
    :param inmanta_module_name: The name of the inmanta module the plugin directory belongs to, e.g. "std".
    """
    for file_path in list_python_files(plugin_dir):
        relative_path = os.path.relpath(file_path, start=plugin_dir)
        yield (
            file_path,
            convert_relative_path_to_module(os.path.join(inmanta_module_name, PLUGIN_DIR, relative_path)),
        )


def get_installed_plugin_dir(inmanta_module_name: InmantaModuleName) -> str:
    """
    Return the directory that holds the python code of the given inmanta module, as installed in the active python
    environment.

    :param inmanta_module_name: The name of the inmanta module to look up, e.g. "std".
    :raises SourceNotFoundException: When the module is not installed in the active python environment.
    """
    package_name = f"{const.PLUGINS_PACKAGE}.{inmanta_module_name}"
    try:
        spec: Optional[ModuleSpec] = importlib.util.find_spec(package_name)
    except (ImportError, ModuleNotFoundError):
        # The inmanta_plugins namespace package itself doesn't exist
        spec = None

    if spec is None or spec.origin is None:
        raise SourceNotFoundException(f"Python package {package_name} is not installed in {sys.prefix}")

    return os.path.dirname(os.path.realpath(spec.origin))


@stable_api
class PluginModuleFinder(MetaPathFinder):
    """
    Custom module finder which handles V1 Inmanta modules. V2 modules are handled using the standard Python finder. This
    finder is stored as the last entry in `meta_path`, as such that the default Python Finders detect V2 modules first.
    """

    MODULE_FINDER: "PluginModuleFinder" = None

    def __init__(self, modulepaths: list[str]) -> None:
        """
        :param modulepaths: The module paths for the inmanta project.
        """
        self._modulepaths = list(modulepaths)

    @classmethod
    def get_module_finder(cls) -> "PluginModuleFinder":
        if cls.MODULE_FINDER is not None:
            return cls.MODULE_FINDER
        raise Exception("No PluginModuleFinder configured. Call configure_module_finder() first.")

    @classmethod
    def reset(cls) -> None:
        """
        Remove the PluginModuleFinder from sys.meta_path.
        """
        if cls.MODULE_FINDER is not None and cls.MODULE_FINDER in sys.meta_path:
            sys.meta_path.remove(cls.MODULE_FINDER)
        cls.MODULE_FINDER = None

    @classmethod
    def configure_module_finder(cls, modulepaths: list[str], *, prefer: bool = False) -> None:
        """
        Setup a custom module loader to handle imports in .py files of the modules. This finder will be stored
        as the last finder in sys.meta_path, unless prefer is True. If the custom module loader has already been
        set up, does nothing (i.e. it is not moved to the front or the back of sys.meta_path).

        :param modulepaths: The directories where the module finder should look for modules.
        :param prefer: Prefer this module finder over others, putting it first in sys.meta_path.
        """
        if cls.MODULE_FINDER is not None:
            # PluginModuleFinder already present in sys.meta_path
            cls.MODULE_FINDER._modulepaths = list(modulepaths)
            return

        # PluginModuleFinder not yet present in sys.meta_path.
        module_finder = PluginModuleFinder(modulepaths)
        if prefer:
            sys.meta_path.insert(0, module_finder)
        else:
            sys.meta_path.append(module_finder)
        cls.MODULE_FINDER = module_finder

    def find_spec(
        self, fullname: str, path: Optional[abc.Sequence[str]], target: Optional[types.ModuleType] = None
    ) -> Optional[ModuleSpec]:
        """
        :param fullname: A fully qualified import path to the module or package to be imported.
        """
        if self._should_handle_import(fullname):
            LOGGER.debug("Loading module: %s", fullname)
            path_to_module = self._get_path_to_module(fullname)
            if path_to_module is not None:
                if path_to_module[-4:] == ".pyc":
                    return importlib.util.spec_from_loader(fullname, ByteCodePluginModuleLoader(fullname, path_to_module))
                return importlib.util.spec_from_loader(fullname, PluginModuleLoader(fullname, path_to_module))
            else:
                # The given module is not present in self.modulepath.
                return None
        return None

    def _should_handle_import(self, fq_import_path: str) -> bool:
        if fq_import_path == const.PLUGINS_PACKAGE:
            return False
        return fq_import_path.startswith(f"{const.PLUGINS_PACKAGE}.")

    def _get_path_to_module(self, fullname: str) -> Optional[str]:
        """
        Return the path to the file in the module path that belongs to the module given by `fullname`.
        None is returned when the given module is not present in the module path.

        :param fullname: A fully-qualified import path to a module.
        """

        def find_module(module_path: str, extension: str = "py") -> Optional[str]:
            path_to_module = os.path.join(module_path, relative_path)
            if os.path.exists(f"{path_to_module}.{extension}"):
                return f"{path_to_module}.{extension}"
            if os.path.isdir(path_to_module):
                path_to_module = os.path.join(path_to_module, f"__init__.{extension}")
                if os.path.exists(path_to_module):
                    return path_to_module

            return None

        relative_path: str = convert_module_to_relative_path(fullname)
        # special case: top-level package
        if relative_path == "":
            return ""
        for module_path in self._modulepaths:
            path_to_module = find_module(module_path, extension="pyc")

            if path_to_module is not None:
                return path_to_module

            # try the byte code only version
            path_to_module = find_module(module_path, extension="py")

            if path_to_module is not None:
                return path_to_module

        return None


@stable_api
def unload_inmanta_plugins(inmanta_module: Optional[str] = None) -> None:
    """
    Unloads Python modules associated with inmanta modules (`inmanta_plugins` submodules).

    :param inmanta_module: Unload the Python modules for a specific inmanta module. If omitted, unloads the Python modules for
        all inmanta modules.
    """
    top_level_pkg: str = f"{const.PLUGINS_PACKAGE}.{inmanta_module}" if inmanta_module is not None else const.PLUGINS_PACKAGE
    # module created by setuptools for custom Finder
    prefix_editable_installed_pkg = "__editable___inmanta_module_"
    if inmanta_module is not None:
        prefix_editable_installed_pkg = f"{prefix_editable_installed_pkg}{inmanta_module.replace('-', '_')}"

    def should_unload(key_in_sys_modules_dct: str) -> bool:
        if key_in_sys_modules_dct == top_level_pkg or key_in_sys_modules_dct.startswith(f"{top_level_pkg}."):
            return True
        if key_in_sys_modules_dct.startswith(prefix_editable_installed_pkg):
            return True
        return False

    loaded_modules: abc.KeysView[str] = sys.modules.keys()
    modules_to_unload: Sequence[str] = [fq_name for fq_name in loaded_modules if should_unload(fq_name)]
    for k in modules_to_unload:
        del sys.modules[k]
    if modules_to_unload:
        importlib.invalidate_caches()


def unload_modules_for_path(path: str) -> None:
    """
    Unload any modules that are loaded from a given path (site-packages dir).
    """

    def module_in_prefix(module: types.ModuleType, prefix: str) -> bool:
        file: Optional[str] = getattr(module, "__file__", None)
        return file.startswith(prefix) if file is not None else False

    loaded_modules: list[str] = [mod_name for mod_name, mod in sys.modules.items() if module_in_prefix(mod, path)]
    for mod_name in loaded_modules:
        del sys.modules[mod_name]
    importlib.invalidate_caches()
