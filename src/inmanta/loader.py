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
import glob
import hashlib
import imp
import inspect
import logging
import os
import types
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pkg_resources

from inmanta import const
from inmanta.module import Project

VERSION_FILE = "version"
MODULE_DIR = "modules"

LOGGER = logging.getLogger(__name__)


class SourceNotFoundException(Exception):
    """ This exception is raised when the source of the provided type is not found
    """


class SourceInfo(object):
    """ This class is used to store information related to source code information
    """

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
        """ Get the sha1 hash of the file
        """
        if self._hash is None:
            sha1sum = hashlib.new("sha1")
            sha1sum.update(self.content.encode("utf-8"))
            self._hash = sha1sum.hexdigest()

        return self._hash

    @property
    def content(self) -> str:
        """ Get the content of the file
        """
        if self._content is None:
            with open(self.path, "r") as fd:
                self._content = fd.read()
        return self._content

    def _get_module_name(self) -> str:
        """Get the name of the inmanta module, derived from the python module name
        """
        module_parts = self.module_name.split(".")
        if module_parts[0] != const.PLUGINS_PACKAGE:
            raise Exception(
                "All instances from which the source is loaded, should be defined in the inmanta plugins package. "
                "%s does not match" % self.module_name
            )

        return module_parts[1]

    @property
    def requires(self) -> List[str]:
        """ List of python requirements associated with this source file
        """
        if self._requires is None:
            self._requires = Project.get().modules[self._get_module_name()].get_python_requirements_as_list()
        return self._requires


class CodeManager(object):
    """ This class is responsible for loading and packaging source code for types (resources, handlers, ...) that need to be
    available in a remote process (e.g. agent).
    """

    def __init__(self) -> None:
        self.__type_file: Dict[str, Set[str]] = {}
        self.__file_info: Dict[str, SourceInfo] = {}

    def register_code(self, type_name: str, instance: object) -> None:
        """ Register the given type_object under the type_name and register the source associated with this type object.

        :param type_name: The inmanta type name for which the source of type_object will be registered. For example std::File
        :param instance: An instance for which the code needs to be registered.
        """
        file_name = self.get_object_source(instance)
        if file_name is None:
            raise SourceNotFoundException("Unable to locate source code of instance %s for entity %s" % (inspect, type_name))

        if type_name not in self.__type_file:
            self.__type_file[type_name] = set()

        if file_name in self.__type_file[type_name]:
            return

        self.__type_file[type_name].add(file_name)

        if file_name not in self.__file_info:
            self.__file_info[file_name] = SourceInfo(file_name, instance.__module__)

    def get_object_source(self, instance: object) -> Optional[str]:
        """ Get the path of the source file in which type_object is defined
        """
        try:
            return inspect.getsourcefile(instance)
        except TypeError:
            return None

    def get_file_hashes(self) -> Iterable[str]:
        """ Return the hashes of all source files
        """
        return (info.hash for info in self.__file_info.values())

    def get_file_content(self, hash: str) -> str:
        """ Get the file content for the given hash
        """
        for info in self.__file_info.values():
            if info.hash == hash:
                return info.content

        raise KeyError("No file found with this hash")

    def get_types(self) -> Iterable[Tuple[str, List[SourceInfo]]]:
        """ Get a list of all registered types
        """
        return ((type_name, [self.__file_info[path] for path in files]) for type_name, files in self.__type_file.items())


class CodeLoader(object):
    """
        Class responsible for managing code loaded from modules received from the compiler

        :param code_dir: The directory where the code is stored
    """

    def __init__(self, code_dir: str) -> None:
        self.__code_dir = code_dir
        self.__modules: Dict[str, Tuple[str, types.ModuleType]] = {}  # A map with all modules we loaded, and its hv

        self.__check_dir()
        self.load_modules()

    def load_modules(self) -> None:
        """
            Load all existing modules
        """
        mod_dir = os.path.join(self.__code_dir, MODULE_DIR)
        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

        for py in glob.glob(os.path.join(mod_dir, "*.py")):
            if mod_dir in py:
                mod_name = py[len(mod_dir) + 1 : -3]
            else:
                mod_name = py[:-3]

            with open(py, "r") as fd:
                source_code = fd.read().encode("utf-8")

            sha1sum = hashlib.new("sha1")
            sha1sum.update(source_code)

            hv = sha1sum.hexdigest()

            self._load_module(mod_name, py, hv)

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

    def _load_module(self, mod_name: str, python_file: str, hv: str) -> None:
        """
            Load or reload a module
        """
        try:
            mod = imp.load_source(mod_name, python_file)
            self.__modules[mod_name] = (hv, mod)
            LOGGER.info("Loaded module %s" % mod_name)
        except ImportError:
            LOGGER.exception("Unable to load module %s" % mod_name)

    def deploy_version(self, hash_value: str, module_name: str, module_source: str) -> None:
        """ Deploy a new version of the modules
        """
        # if the module is new, or update
        if module_name not in self.__modules or hash_value != self.__modules[module_name][0]:
            LOGGER.info("Deploying code (hv=%s, module=%s)", hash_value, module_name)
            # write the new source
            source_file = os.path.join(self.__code_dir, MODULE_DIR, module_name + ".py")

            fd = open(source_file, "w+")
            fd.write(module_source)
            fd.close()

            # (re)load the new source
            self._load_module(module_name, source_file, hash_value)

        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()
