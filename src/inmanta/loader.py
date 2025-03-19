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
import functools
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
from dataclasses import dataclass
from functools import cached_property
from importlib.abc import FileLoader, MetaPathFinder
from importlib.machinery import ModuleSpec, SourcelessFileLoader
from itertools import chain
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, computed_field

from inmanta import const, module
from inmanta.stable_api import stable_api
from inmanta.util import hash_file_streaming

if TYPE_CHECKING:
    from inmanta import protocol

VERSION_FILE = "version"
MODULE_DIR = "modules"
PLUGIN_DIR = "plugins"

LOGGER = logging.getLogger(__name__)


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
    """This exception is raised when the source of the provided type is not found"""


class CodeManager:
    """This class is responsible for loading and packaging source code for types (resources, handlers, ...) that need to be
    available in a remote process (e.g. agent).

    __type_file: Maps Inmanta type names (e.g., ``std::testing::NullResource``, ``mymodule::Mytype``)
                 to sets of filenames containing
                 the necessary source code (all plugin files in the module).
    __file_info: Stores metadata about each individual source code file. The keys are file paths and the values
                 in this dictionary are ``SourceInfo`` objects.
    """

    def __init__(self) -> None:
        # Old implementation
        # Use by external code

        # Map of [Union[resouce_type, handler_type], set[path]]
        # Which python files are required by each type
        self.__type_file: dict[str, set[str]] = {}

        # Map of [path, SourceInfo]
        # To which python module do these python files belong
        self.__file_info: dict[str, SourceInfo] = {}

        # Map of [Union[resouce_type, handler_type], str]
        # Maps a type to the module it lives in
        self.__type_to_module: dict[str, list[str]] = defaultdict(list)

        # Cache of module to source info
        self.__module_to_source_info: dict[str, list[SourceInfo]] = {}

        self.__modules_data: dict[str, "PythonModule"] = {}

    def register_code(self, type_name: str, instance: object) -> None:
        """Register the given type_object under the type_name and register the source associated with this type object.

        :param type_name: The inmanta type name for which the source of type_object will be registered.
            For example std::testing::NullResource
        :param instance: An instance for which the code needs to be registered.
        """
        file_name = self.get_object_source(instance)
        if file_name is None:
            raise SourceNotFoundException(f"Unable to locate source code of instance {instance} for entity {type_name}")

        if type_name not in self.__type_file:
            self.__type_file[type_name] = set()

        # if file_name is in there, all plugin files should be in there => return
        if file_name in self.__type_file[type_name]:
            return

        # get the module
        module_name = get_inmanta_module_name(instance.__module__)

        all_plugin_files: list[SourceInfo] = self._get_source_info_for_module(module_name)
        LOGGER.debug(f"Registering {type_name=} from {instance=} in {module_name=} {all_plugin_files=}")
        # fqn_module_name = next(module.Project.get().modules[module_name].get_plugin_files())[0]
        self.__type_to_module[type_name].append(module_name)

        self.__type_file[type_name].update(source_info.path for source_info in all_plugin_files)

    def _get_source_info_for_module(self, inmanta_module_name: str) -> list["SourceInfo"]:
        if inmanta_module_name in self.__module_to_source_info:
            return self.__module_to_source_info[inmanta_module_name]

        sources = [
            SourceInfo(path=absolute_path, module_name=fqn_module_name)
            for absolute_path, fqn_module_name in module.Project.get().modules[inmanta_module_name].get_plugin_files()
        ]

        self.__module_to_source_info[inmanta_module_name] = sources

        # Register files
        for file_info in sources:
            self.__file_info[file_info.path] = file_info

        return sources

    def get_object_source(self, instance: object) -> Optional[str]:
        """Get the path of the source file in which type_object is defined"""
        try:
            return inspect.getsourcefile(instance)
        except TypeError:
            return None

    def get_file_hashes(self) -> Iterable[str]:
        """Return the hashes of all source files"""
        return (info.hash for info in self.__file_info.values())

    def get_module_source_info(self) -> dict[str, list["SourceInfo"]]:
        """Return all module source info"""
        return self.__module_to_source_info

    def get_modules_data(self) -> dict[str, "PythonModule"]:
        if self.__modules_data:
            return self.__modules_data

        source_info = self.get_module_source_info()

        modules_data = {}
        for module_name, files_in_module in source_info.items():
            all_files_hashes = [file.hash for file in sorted(files_in_module, key=lambda f: f.hash)]

            module_version_hash = hashlib.new("sha1")
            for file_hash in all_files_hashes:
                module_version_hash.update(file_hash.encode())

            module_version = module_version_hash.hexdigest()
            modules_data[module_name] = PythonModule(
                name=module_name,
                version=module_version,
                files_in_module=files_in_module,
            )
        self.__modules_data = modules_data

        return self.__modules_data

    def get_module_version_info(self) -> dict[str, "PythonModule"]:
        """Return all module version info"""
        return self.get_modules_data()
        # return {module_data.name: module_data.version for module_data in self.get_modules_data().values()}

    def get_type_to_module(self) -> dict[str, list[str]]:
        """Return all module source info"""
        return self.__type_to_module

    def get_file_content(self, hash: str) -> bytes:
        """Get the file content for the given hash"""
        for info in self.__file_info.values():
            if info.hash == hash:
                return info.content

        raise KeyError("No file found with this hash")

    def get_types(self) -> Iterable[tuple[str, list["SourceInfo"]]]:
        """Get a list of all registered types"""
        return ((type_name, [self.__file_info[path] for path in files]) for type_name, files in self.__type_file.items())


@dataclass(frozen=True)
@functools.total_ordering
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

    def __lt__(self, other):
        if not isinstance(other, ModuleSource):
            return NotImplemented
        return (self.name, self.hash_value, self.is_byte_code) < (other.name, other.hash_value, other.is_byte_code)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleSource):
            return False
        return (self.name, self.hash_value, self.is_byte_code) == (other.name, other.hash_value, other.is_byte_code)

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

    def for_transport(self) -> "ModuleSource":
        return ModuleSource(name=self.name, hash_value=self.hash_value, is_byte_code=self.is_byte_code, source=self.source)

    def with_client(self, client: "protocol.SyncClient") -> "ModuleSource":
        return ModuleSource(
            name=self.name, hash_value=self.hash_value, is_byte_code=self.is_byte_code, source=self.source, _client=client
        )


@dataclass(frozen=True)
class FailedModuleSource:
    module_source: ModuleSource
    exception: Exception


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
            LOGGER.debug("Trying to import %s", mod_name)
            import os

            cwd = os.getcwd()
            LOGGER.debug(f"In {cwd=}")
            mod = importlib.import_module(mod_name)
        self.__modules[mod_name] = (hv, mod)
        LOGGER.info("Loaded module %s", mod_name)

    def install_source(self, module_source: ModuleSource) -> None:
        """
        Ensure the given module source is available on disk.
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
                # LOGGER.debug("BP1")
                # LOGGER.debug(f"{directory=}")
                # LOGGER.debug(f"{normdir=}")
                # LOGGER.debug(f"{package_dir=}")
                if normdir == package_dir:
                    return
                if not os.path.exists(os.path.join(normdir, "__init__.py")) and not os.path.exists(
                    os.path.join(normdir, "__init__.pyc")
                ):
                    pathlib.Path(os.path.join(normdir, "__init__.py")).touch()
                touch_inits(os.path.dirname(normdir))

            # ensure correct package structure
            os.makedirs(module_dir, exist_ok=True)
            LOGGER.debug(f"touch inists {module_dir=}")
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
                    return

            # write the new source
            source_code = module_source.get_source_code()
            with open(source_file, "wb+") as fd:
                LOGGER.debug(f"writing source to {source_file}")
                fd.write(source_code)
        else:
            LOGGER.debug(
                "Not deploying code (hv=%s, module=%s) because of cache hit", module_source.hash_value, module_source.name
            )

    def deploy_version(self, module_sources: Iterable[ModuleSource], module_name: str) -> None:
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

    parts: list[str] = list(split(path))

    if parts == []:
        return const.PLUGINS_PACKAGE

    if len(parts) == 1 or parts[1] != PLUGIN_DIR:
        raise Exception(f"Error parsing module path: expected 'some_module/{PLUGIN_DIR}/some_submodule', got {path}")

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

    # if module_parts[-1] == "__init__":
    #     module_parts = module_parts[:-1]

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


@dataclass(frozen=True)
class PythonModule:
    name: str
    version: str
    files_in_module: list["SourceInfo"]


class SourceInfo(BaseModel):
    """This class is used to store information related to source code information"""

    path: str
    module_name: str

    # def __str__(self):
    #     return f"SourceInfo ({self.path=}, {self.module_name=}"
    #
    # def __repr__(self):
    #     return f"SourceInfo ({self.path=}, {self.module_name=}"

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def hash(self) -> str:
        """Get the sha1 hash of the file"""
        sha1sum = hashlib.new("sha1")
        sha1sum.update(self.content)
        return sha1sum.hexdigest()

    @cached_property
    def content(self) -> bytes:
        """Get the content of the file"""
        with open(self.path, "rb") as fd:
            _content = fd.read()
        return _content

    def _get_module_name(self) -> str:
        """Get the name of the inmanta module, derived from the python module name"""
        return get_inmanta_module_name(self.module_name)

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def requires(self) -> list[str]:
        """List of python requirements associated with this source file"""
        project: module.Project = module.Project.get()
        mod: module.Module = project.modules[self._get_module_name()]
        if project.metadata.agent_install_dependency_modules:
            _requires = mod.get_all_python_requirements_as_list()
        else:
            _requires = mod.get_strict_python_requirements_as_list()
        return _requires
