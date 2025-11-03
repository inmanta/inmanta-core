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
import types
from collections import abc, defaultdict
from collections.abc import Iterable, Iterator, Sequence
from importlib.abc import FileLoader, MetaPathFinder
from importlib.machinery import ModuleSpec, SourcelessFileLoader
from itertools import chain
from typing import TYPE_CHECKING, Optional

from inmanta import const, module
from inmanta.data.model import InmantaModule, ModuleSource
from inmanta.stable_api import stable_api
from inmanta.util import hash_file_streaming

VERSION_FILE = "version"
MODULE_DIR = "modules"
PLUGIN_DIR = "plugins"

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inmanta.data.model import ModuleSourceMetadata
    from inmanta.resources import Id, Resource


def get_inmanta_module_name(python_module_name: str) -> str:
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
    """This class is responsible for loading and packaging source code for types (resources, handlers, ...) that need to be
    available in a remote process (e.g. agent).

    __file_info: Stores metadata about each individual source code file. The keys are file paths and the values
                 in this dictionary are ``ModuleSource`` objects.
    """

    def __init__(self) -> None:
        # Old implementation
        # Use by external code

        # Map of [path, ModuleSource]
        # To which python module do these python files belong
        self.__file_info: dict[str, ModuleSource] = {}

        self._types_to_agent: dict[str, set[str]] = defaultdict(set)

        # Map of [inmanta_module_name, inmanta module]
        self.module_version_info: dict[str, "InmantaModule"] = {}

    def build_agent_map(self, resources: dict["Id", "Resource"]) -> None:
        """
        Construct a map of which agents are registered to deploy which resource type.
        This map is later used to construct a map of which agents need to load
        which Inmanta module(s).
        """
        for id in resources:
            self._types_to_agent[id.entity_type].add(id.agent_name)

    def register_code(self, type_name: str, instance: object) -> None:
        """Register the given type_object under the type_name and register the source associated with this type object.
        This method assumes the build_agent_map method was called first.

        :param type_name: The inmanta type name for which the source of type_object will be registered.
            For example std::testing::NullResource
        :param instance: An instance for which the code needs to be registered.
        """
        file_name = self.get_object_source(instance)
        if file_name is None:
            raise SourceNotFoundException(f"Unable to locate source code of instance {instance} for entity {type_name}")

        # get the module
        module_name = get_inmanta_module_name(instance.__module__)
        loaded_modules = module.Project.get().modules

        if module_name not in loaded_modules:
            raise SourceNotFoundException(
                "Module %s is imported in plugin code but not in model code. Either remove the unused import, "
                "or make sure to import the module in model code." % module_name
            )

        self._register_inmanta_module(module_name, loaded_modules[module_name])

        registered_agents: set[str] = self._types_to_agent.get(type_name, set())
        self._update_agents_for_module(module_name, registered_agents)

    def _register_inmanta_module(self, inmanta_module_name: str, module: "module.Module") -> None:
        if inmanta_module_name in self.module_version_info:
            # This module was already registered
            return

        module_sources: list[ModuleSource] = []

        for absolute_path, fqn_module_name in module.get_plugin_files():
            source_info = ModuleSource.from_path(absolute_path=absolute_path, name=fqn_module_name)
            self.__file_info[absolute_path] = source_info
            module_sources.append(source_info)

        files_metadata = [module_source.metadata for module_source in module_sources]
        requirements = self.get_inmanta_module_requirements(inmanta_module_name)

        module_version = self.get_module_version(requirements, files_metadata)

        self.module_version_info[inmanta_module_name] = InmantaModule(
            name=inmanta_module_name,
            version=module_version,
            files_in_module=files_metadata,
            requirements=list(requirements),
            for_agents=[],
        )

    def _update_agents_for_module(self, inmanta_module_name: str, registered_agents: set[str]) -> None:
        """
        Helper method to add the given agents to the list of registered agents for the given Inmanta module.
        """
        old_set: set[str] = set(self.module_version_info[inmanta_module_name].for_agents)
        self.module_version_info[inmanta_module_name].for_agents = list(old_set.union(registered_agents))

    def get_object_source(self, instance: object) -> Optional[str]:
        """Get the path of the source file in which type_object is defined"""
        try:
            return inspect.getsourcefile(instance)
        except TypeError:
            return None

    def get_file_hashes(self) -> Iterable[str]:
        """Return the hashes of all source files"""
        return (info.metadata.hash_value for info in self.__file_info.values())

    def get_module_version_info(self) -> dict[str, "InmantaModule"]:
        """Return all module version info"""
        return self.module_version_info

    @staticmethod
    def get_inmanta_module_requirements(module_name: str) -> set[str]:
        """Get the list of python requirements associated with this inmanta module"""
        project: module.Project = module.Project.get()
        mod: module.Module = project.modules[module_name]

        if project.metadata.agent_install_dependency_modules:
            _requires = mod.get_all_python_requirements_as_list()
        else:
            _requires = mod.get_strict_python_requirements_as_list()

        return set(_requires)

    @staticmethod
    def get_module_version(requirements: set[str], module_sources: Sequence["ModuleSourceMetadata"]) -> str:
        module_version_hash = hashlib.new("sha1")

        for module_source in sorted(module_sources, key=lambda f: f.hash_value):
            module_version_hash.update(module_source.hash_value.encode())

        for requirement in sorted(requirements):
            module_version_hash.update(str(requirement).encode())

        return module_version_hash.hexdigest()

    def get_file_content(self, hash: str) -> bytes:
        """Get the file content for the given hash"""
        for info in self.__file_info.values():
            if info.metadata.hash_value == hash:
                return info.source

        raise KeyError("No file found with this hash")


class CodeLoader:
    """
    Class responsible for managing code loaded from modules received from the compiler

    :param code_dir: The directory where the code is stored
    """

    def __init__(self, code_dir: str, clean: bool = False) -> None:
        self.__code_dir = code_dir
        self.__modules: dict[str, tuple[str, types.ModuleType]] = {}  # A map with all modules we loaded, and its hv

        self.__check_dir(clean)

        self.mod_dir = os.path.join(self.__code_dir, MODULE_DIR)
        PluginModuleFinder.configure_module_finder(modulepaths=[self.mod_dir], prefer=True)

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

    def load_module(self, mod_name: str, hv: str) -> None:
        """
        Ensure the given module is loaded. Does not capture any import errors.

        :param mod_name: Name of the module to load
        :param hv: hash value of the content of the module

        :raises Exception: When the provided hash value is different from the one in the cache for this module.
        """

        # Importing a module -> only the first import loads the code
        # cache of loaded modules mechanism -> starts afresh when agent is restarted
        if mod_name in self.__modules:
            if hv != self.__modules[mod_name][0]:
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
