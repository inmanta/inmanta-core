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
import base64
import hashlib
import importlib
import importlib.util
import inspect
import logging
import os
import pathlib
import sys
import types
from collections import abc
from dataclasses import dataclass
from importlib.abc import FileLoader, MetaPathFinder
from importlib.machinery import ModuleSpec, SourcelessFileLoader
from itertools import chain, starmap
from typing import TYPE_CHECKING, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

from inmanta import const, module
from inmanta.stable_api import stable_api
from inmanta.util import hash_file_streaming

if TYPE_CHECKING:
    from inmanta import protocol

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
        :param module_name: The fully qualified name of the Python module. Should be a module in the inmanta_plugins namespace.
        """
        self.path = path
        self._hash: Optional[str] = None
        self._content: Optional[bytes] = None
        self._requires: Optional[List[str]] = None
        self.module_name = module_name

    @property
    def hash(self) -> str:
        """Get the sha1 hash of the file"""
        if self._hash is None:
            sha1sum = hashlib.new("sha1")
            sha1sum.update(self.content)
            self._hash = sha1sum.hexdigest()

        return self._hash

    @property
    def content(self) -> bytes:
        """Get the content of the file"""
        if self._content is None:
            with open(self.path, "rb") as fd:
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
        return starmap(SourceInfo, module.Project.get().modules[self._get_module_name()].get_plugin_files())

    @property
    def requires(self) -> List[str]:
        """List of python requirements associated with this source file"""
        if self._requires is None:
            project: module.Project = module.Project.get()
            mod: module.Module = project.modules[self._get_module_name()]
            if project.metadata.agent_install_dependency_modules:
                self._requires = mod.get_all_python_requirements_as_list()
            else:
                self._requires = mod.get_strict_python_requirements_as_list()
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

    def get_file_content(self, hash: str) -> bytes:
        """Get the file content for the given hash"""
        for info in self.__file_info.values():
            if info.hash == hash:
                return info.content

        raise KeyError("No file found with this hash")

    def get_types(self) -> Iterable[Tuple[str, List[SourceInfo]]]:
        """Get a list of all registered types"""
        return ((type_name, [self.__file_info[path] for path in files]) for type_name, files in self.__type_file.items())


@dataclass(frozen=True)
class ModuleSource:
    """
    :param name: the name of the python module. e.g. inmanta_plugins.model.x
    :param is_byte_code: is this content python byte code or python source
    :param source: the content of the file
    :param _client: a protocol client, required when source is not set

    """

    name: str
    hash_value: str
    is_byte_code: bool
    source: Optional[bytes] = None
    _client: Optional["protocol.SyncClient"] = None

    def get_source_code(self) -> bytes:
        """Load the source code"""
        if self.source is not None:
            return self.source

        if self._client is None:
            raise Exception("_client should be set to use this method.")

        response: protocol.Result = self._client.get_file(self.hash_value)
        if response.code != 200 or response.result is None:
            raise Exception(f"Failed to fetch code for {self.name} with hash {self.hash_value}.")

        return base64.b64decode(response.result["content"])


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
        PluginModuleFinder.configure_module_finder(modulepaths=[mod_dir], prefer=True)

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
        except ImportError:
            LOGGER.exception("Unable to load module %s" % mod_name)

    def install_source(self, module_source: ModuleSource) -> bool:
        """
        :return: True if this module install requires a reload
        """
        # if the module is new, or update
        if module_source.name not in self.__modules or module_source.hash_value != self.__modules[module_source.name][0]:
            LOGGER.info("Deploying code (hv=%s, module=%s)", module_source.hash_value, module_source.name)

            all_modules_dir: str = os.path.join(self.__code_dir, MODULE_DIR)
            relative_module_path: str = convert_module_to_relative_path(module_source.name)
            # Treat all modules as a package for simplicity: module is a dir with source in __init__.py
            module_dir: str = os.path.join(all_modules_dir, relative_module_path)

            package_dir: str = os.path.normpath(
                os.path.join(all_modules_dir, pathlib.PurePath(pathlib.PurePath(relative_module_path).parts[0]))
            )

            if module_source.is_byte_code:
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
                if thehash == module_source.hash_value:
                    LOGGER.debug(
                        "Not deploying code (hv=%s, module=%s) because it is already on disk",
                        module_source.hash_value,
                        module_source.name,
                    )
                    # Force (re)load, because we have it on disk, but not on the in-memory cache
                    # We may have not loaded it
                    return True

            # write the new source
            source_code = module_source.get_source_code()
            with open(source_file, "wb+") as fd:
                fd.write(source_code)
            return True
        else:
            LOGGER.debug(
                "Not deploying code (hv=%s, module=%s) because of cache hit", module_source.hash_value, module_source.name
            )
            return False

    def deploy_version(self, module_sources: Iterable[ModuleSource]) -> None:
        to_reload: List[ModuleSource] = []

        sources = set(module_sources)
        for module_source in sources:
            is_changed = self.install_source(module_source)
            if is_changed:
                to_reload.append(module_source)

        if len(to_reload) > 0:
            importlib.invalidate_caches()
            for module_source in to_reload:
                # (re)load the new source
                self._load_module(module_source.name, module_source.hash_value)


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
            return "".encode("utf-8")
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
        if last == "__init__.py" or last == "__init__.pyc":
            return init
        if last.endswith(".py"):
            return list(chain(init, [last[:-3]]))
        if last.endswith(".pyc"):
            return list(chain(init, [last[:-4]]))
        return module

    top_level_inmanta_module: str = parts[0]
    inmanta_submodule: List[str] = parts[2:]

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

    def __init__(self, modulepaths: List[str]) -> None:
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
    def configure_module_finder(cls, modulepaths: List[str], *, prefer: bool = False) -> None:
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

    loaded_modules: List[str] = [mod_name for mod_name, mod in sys.modules.items() if module_in_prefix(mod, path)]
    for mod_name in loaded_modules:
        del sys.modules[mod_name]
    importlib.invalidate_caches()
