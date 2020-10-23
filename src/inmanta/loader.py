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
import inspect
import logging
import os
import pathlib
import sys
import traceback
import types
from dataclasses import dataclass
from importlib.abc import FileLoader, Finder
from itertools import chain, starmap
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple

import more_itertools

from inmanta import const

VERSION_FILE = "version"
MODULE_DIR = "modules"
PLUGIN_DIR = "plugins"

LOGGER = logging.getLogger(__name__)


class SourceNotFoundException(Exception):
    """This exception is raised when the source of the provided type is not found"""


class SourceInfo(object):
    """This class is used to store information related to source code information"""

    def __init__(self, path: str, module_name: str) -> None:
        """
        :param path: The path of the source code file
        :param path: The name of the inmanta module
        """
        self.path = path
        self._hash: Optional[str] = None
        self._content: Optional[str] = None
        self._requires: Optional[List[str]] = None
        self.module_name = module_name

    @property
    def hash(self) -> str:
        """Get the sha1 hash of the file"""
        if self._hash is None:
            sha1sum = hashlib.new("sha1")
            sha1sum.update(self.content.encode("utf-8"))
            self._hash = sha1sum.hexdigest()

        return self._hash

    @property
    def content(self) -> str:
        """Get the content of the file"""
        if self._content is None:
            with open(self.path, "r", encoding="utf-8") as fd:
                self._content = fd.read()
        return self._content

    def _get_module_name(self) -> str:
        """Get the name of the inmanta module, derived from the python module name"""
        module_parts = self.module_name.split(".")
        if module_parts[0] != const.PLUGINS_PACKAGE:
            raise Exception(
                "All instances from which the source is loaded, should be defined in the inmanta plugins package. "
                "%s does not match" % self.module_name
            )

        return module_parts[1]

    def get_siblings(self) -> Iterator["SourceInfo"]:
        """
        Returns an iterator over SourceInfo objects for all plugin source files in this Inmanta module (including this one).
        """
        from inmanta.module import Project

        return starmap(SourceInfo, Project.get().modules[self._get_module_name()].get_plugin_files())

    @property
    def requires(self) -> List[str]:
        """List of python requirements associated with this source file"""
        from inmanta.module import Project

        if self._requires is None:
            self._requires = Project.get().modules[self._get_module_name()].get_python_requirements_as_list()
        return self._requires


class CodeManager(object):
    """This class is responsible for loading and packaging source code for types (resources, handlers, ...) that need to be
    available in a remote process (e.g. agent).
    """

    def __init__(self) -> None:
        self.__type_file: Dict[str, Set[str]] = {}
        self.__file_info: Dict[str, SourceInfo] = {}

    def register_code(self, type_name: str, instance: object) -> None:
        """Register the given type_object under the type_name and register the source associated with this type object.

        :param type_name: The inmanta type name for which the source of type_object will be registered. For example std::File
        :param instance: An instance for which the code needs to be registered.
        """
        file_name = self.get_object_source(instance)
        if file_name is None:
            raise SourceNotFoundException("Unable to locate source code of instance %s for entity %s" % (inspect, type_name))

        if type_name not in self.__type_file:
            self.__type_file[type_name] = set()

        # if file_name is in there, all plugin files should be in there => return
        if file_name in self.__type_file[type_name]:
            return

        # don't just store this file, but all plugin files in its Inmanta module to allow for importing helper modules
        all_plugin_files: List[SourceInfo] = list(SourceInfo(file_name, instance.__module__).get_siblings())
        self.__type_file[type_name].update(source_info.path for source_info in all_plugin_files)

        if file_name in self.__file_info:
            return

        for file_info in all_plugin_files:
            self.__file_info[file_info.path] = file_info

    def get_object_source(self, instance: object) -> Optional[str]:
        """Get the path of the source file in which type_object is defined"""
        try:
            return inspect.getsourcefile(instance)
        except TypeError:
            return None

    def get_file_hashes(self) -> Iterable[str]:
        """Return the hashes of all source files"""
        return (info.hash for info in self.__file_info.values())

    def get_file_content(self, hash: str) -> str:
        """Get the file content for the given hash"""
        for info in self.__file_info.values():
            if info.hash == hash:
                return info.content

        raise KeyError("No file found with this hash")

    def get_types(self) -> Iterable[Tuple[str, List[SourceInfo]]]:
        """Get a list of all registered types"""
        return ((type_name, [self.__file_info[path] for path in files]) for type_name, files in self.__type_file.items())


@dataclass
class ModuleSource:
    name: str
    source: str
    hash_value: str


class CodeLoader(object):
    """
    Class responsible for managing code loaded from modules received from the compiler

    :param code_dir: The directory where the code is stored
    """

    def __init__(self, code_dir: str) -> None:
        self.__code_dir = code_dir
        self.__modules: Dict[str, Tuple[str, types.ModuleType]] = {}  # A map with all modules we loaded, and its hv

        self.__check_dir()

        mod_dir = os.path.join(self.__code_dir, MODULE_DIR)
        configure_module_finder([mod_dir])

    def __check_dir(self) -> None:
        """
        Check if the code directory
        """
        # check for the code dir
        if not os.path.exists(self.__code_dir):
            os.makedirs(self.__code_dir, exist_ok=True)

        # check for modules subdir
        if not os.path.exists(os.path.join(self.__code_dir, MODULE_DIR)):
            os.makedirs(os.path.join(self.__code_dir, MODULE_DIR), exist_ok=True)

    def _load_module(self, mod_name: str, hv: str) -> None:
        """
        Load or reload a module
        """
        try:
            if mod_name in self.__modules:
                mod = importlib.reload(self.__modules[mod_name][1])
            else:
                mod = importlib.import_module(mod_name)
            self.__modules[mod_name] = (hv, mod)
            LOGGER.info("Loaded module %s" % mod_name)
        except (ImportError, PluginModuleLoadException):
            LOGGER.exception("Unable to load module %s" % mod_name)

    def deploy_version(self, module_sources: Iterable[ModuleSource]) -> None:
        to_reload: List[ModuleSource] = []

        for module_source in module_sources:
            # if the module is new, or update
            if module_source.name not in self.__modules or module_source.hash_value != self.__modules[module_source.name][0]:
                LOGGER.info("Deploying code (hv=%s, module=%s)", module_source.hash_value, module_source.name)

                all_modules_dir: str = os.path.join(self.__code_dir, MODULE_DIR)
                relative_module_path: str = PluginModuleLoader.convert_module_to_relative_path(module_source.name)
                # Treat all modules as a package for simplicity: module is a dir with source in __init__.py
                module_dir: str = os.path.join(all_modules_dir, relative_module_path)

                package_dir: str = os.path.normpath(
                    os.path.join(all_modules_dir, pathlib.PurePath(pathlib.PurePath(relative_module_path).parts[0]))
                )

                def touch_inits(directory: str) -> None:
                    """
                    Make sure __init__.py files exist for this package and all parent packages. Required for compatibility
                    with pre-2020.4 inmanta clients because they don't necessarily upload the whole package.
                    """
                    normdir: str = os.path.normpath(directory)
                    if normdir == package_dir:
                        return
                    pathlib.Path(os.path.join(normdir, "__init__.py")).touch()
                    touch_inits(os.path.dirname(normdir))

                # ensure correct package structure
                os.makedirs(module_dir, exist_ok=True)
                touch_inits(os.path.dirname(module_dir))
                source_file = os.path.join(module_dir, "__init__.py")

                # write the new source
                with open(source_file, "w+", encoding="utf-8") as fd:
                    fd.write(module_source.source)

                to_reload.append(module_source)

        if len(to_reload) > 0:
            importlib.invalidate_caches()
            for module_source in to_reload:
                # (re)load the new source
                self._load_module(module_source.name, module_source.hash_value)


class PluginModuleLoadException(Exception):
    """
    Wrapper exception raised when an exception occurs during plugin module loading.
    """

    def __init__(self, cause: Exception, module: str, path: str, lineno: Optional[int]) -> None:
        self.cause: Exception = cause
        self.module: str = module
        self.path: str = path
        self.lineno: Optional[int] = lineno
        lineno_suffix = f":{self.lineno}" if self.lineno is not None else ""
        super().__init__(
            "%s while loading plugin module %s at %s: %s"
            % (
                self.get_cause_type_name(),
                self.module,
                f"{self.path}{lineno_suffix}",
                self.cause,
            )
        )

    def get_cause_type_name(self) -> str:
        module: Optional[str] = type(self.cause).__module__
        name: str = type(self.cause).__qualname__
        return name if module is None or module == "builtins" else "%s.%s" % (module, name)


class PluginModuleLoader(FileLoader):
    """
    A custom module loader which imports the modules in the inmanta_plugins package.
    """

    def __init__(self, modulepaths: List[str], fullname: str) -> None:
        self._modulepaths = modulepaths
        path_to_module = self._get_path_to_module(fullname)
        super(PluginModuleLoader, self).__init__(fullname, path_to_module)
        self.path: str

    def exec_module(self, module: types.ModuleType) -> None:
        try:
            return super().exec_module(module)
        except Exception as e:
            # attach module, file name and line number
            tb: Optional[types.TracebackType] = sys.exc_info()[2]
            stack: traceback.StackSummary = traceback.extract_tb(tb)
            lineno: Optional[int] = more_itertools.first(
                (frame.lineno for frame in reversed(stack) if frame.filename == self.path), None
            )
            raise PluginModuleLoadException(e, self.name, self.path, lineno)

    def get_source(self, fullname: str) -> bytes:
        # No __init__.py exists for top level package
        if self._loading_top_level_package():
            return "".encode("utf-8")
        with open(self.path, "r", encoding="utf-8") as fd:
            return fd.read().encode("utf-8")

    def is_package(self, fullname: str) -> bool:
        if self._loading_top_level_package():
            return True
        return os.path.basename(self.path) == "__init__.py"

    @classmethod
    def convert_relative_path_to_module(cls, path: str) -> str:
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

        parts: List[str] = list(split(path))

        if parts == []:
            return const.PLUGINS_PACKAGE

        if len(parts) == 1 or parts[1] != PLUGIN_DIR:
            raise Exception("Error parsing module path: expected 'some_module/%s/some_submodule', got %s" % (PLUGIN_DIR, path))

        def strip_py(module: List[str]) -> List[str]:
            """
            Strip __init__.py or .py file extension from module parts.
            """
            if module == []:
                return []
            init, last = module[:-1], module[-1]
            if last == "__init__.py":
                return init
            if last.endswith(".py"):
                return list(chain(init, [last[:-3]]))
            return module

        top_level_inmanta_module: str = parts[0]
        inmanta_submodule: List[str] = parts[2:]

        # my_mod/plugins/tail -> inmanta_plugins.my_mod.tail
        return ".".join(chain([const.PLUGINS_PACKAGE, top_level_inmanta_module], strip_py(inmanta_submodule)))

    @classmethod
    def convert_module_to_relative_path(cls, full_mod_name: str) -> str:
        """
        Returns path to the module, relative to the module directory. Does not differentiate between modules and packages.
        For example convert_module_to_relative_path("inmanta_plugins.my_mod.my_submod") == "my_mod/plugins/my_submod".
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

    def _get_path_to_module(self, fullname: str) -> str:
        relative_path: str = self.convert_module_to_relative_path(fullname)
        # special case: top-level package
        if relative_path == "":
            return ""
        for module_path in self._modulepaths:
            path_to_module = os.path.join(module_path, relative_path)
            if os.path.exists(f"{path_to_module}.py"):
                return f"{path_to_module}.py"
            if os.path.isdir(path_to_module):
                path_to_module = os.path.join(path_to_module, "__init__.py")
                if os.path.exists(path_to_module):
                    return path_to_module

        raise ImportError(f"Cannot find module {fullname} in {self._modulepaths}")

    def _loading_top_level_package(self):
        return self.path == ""


class PluginModuleFinder(Finder):
    """
    Custom module finder which handles all the imports for the package inmanta_plugins.
    """

    def __init__(self, modulepaths: List[str]) -> None:
        self._modulepaths = modulepaths

    def add_module_paths(self, paths: List[str]) -> None:
        for p in paths:
            if p not in self._modulepaths:
                self._modulepaths.append(p)

    def find_module(self, fullname: str, path: Optional[str] = None) -> Optional[PluginModuleLoader]:
        if fullname == const.PLUGINS_PACKAGE or fullname.startswith(f"{const.PLUGINS_PACKAGE}."):
            LOGGER.debug("Loading module: %s", fullname)
            return PluginModuleLoader(self._modulepaths, fullname)
        return None


def configure_module_finder(modulepaths: List[str]) -> None:
    """
    Setup a custom module loader to handle imports in .py files of the modules.
    """
    for finder in sys.meta_path:
        # PluginModuleFinder already present in sys.meta_path.
        if isinstance(finder, PluginModuleFinder):
            finder.add_module_paths(modulepaths)
            return

    # PluginModuleFinder not yet present in sys.meta_path.
    module_finder = PluginModuleFinder(modulepaths)
    sys.meta_path.insert(0, module_finder)


def unload_inmanta_plugins():
    """
    Unload the inmanta_plugins package.
    """
    loaded_modules = sys.modules.keys()
    modules_to_unload = [k for k in loaded_modules if k == const.PLUGINS_PACKAGE or k.startswith(f"{const.PLUGINS_PACKAGE}.")]
    for k in modules_to_unload:
        del sys.modules[k]
