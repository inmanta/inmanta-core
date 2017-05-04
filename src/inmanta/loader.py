"""
    Copyright 2017 Inmanta

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

import os
import glob
import imp
import hashlib
import json
import logging

import pkg_resources

VERSION_FILE = "version"
MODULE_DIR = "modules"
PERSIST_FILE = "modules.json"

LOGGER = logging.getLogger(__name__)


class CodeLoader(object):
    """
        Class responsible for managing code loaded from modules received from the compiler

        :param code_dir The directory where the code is stored
    """

    def __init__(self, code_dir):
        self.__code_dir = code_dir
        self.__modules = {}
        self.__current_version = 0

        self.__check_dir()
        self.load_modules()

    def load_modules(self):
        """
            Load all existing modules
        """
        mod_dir = os.path.join(self.__code_dir, MODULE_DIR)

        if os.path.exists(os.path.join(self.__code_dir, VERSION_FILE)):
            fd = open(os.path.join(self.__code_dir, VERSION_FILE), "r")
            self.__current_version = int(fd.read())
            fd.close()

        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

        for py in glob.glob(os.path.join(mod_dir, "*.py")):
            if mod_dir in py:
                mod_name = py[len(mod_dir) + 1:-3]
            else:
                mod_name = py[:-3]

            source_code = ""
            with open(py, "r") as fd:
                source_code = fd.read().encode("utf-8")

            sha1sum = hashlib.new("sha1")
            sha1sum.update(source_code)

            hv = sha1sum.hexdigest()

            self._load_module(mod_name, py, hv)

    def __check_dir(self):
        """
            Check if the code directory
        """
        # check for the code dir
        if not os.path.exists(self.__code_dir):
            os.makedirs(self.__code_dir, exist_ok=True)

        # check for modules subdir
        if not os.path.exists(os.path.join(self.__code_dir, MODULE_DIR)):
            os.makedirs(os.path.join(self.__code_dir, MODULE_DIR), exist_ok=True)

    def _load_module(self, mod_name, python_file, hv):
        """
            Load or reload a module
        """
        try:
            mod = imp.load_source(mod_name, python_file)
            self.__modules[mod_name] = (hv, mod)
            LOGGER.info("Loaded module %s" % mod_name)
        except ImportError:
            LOGGER.exception("Unable to load module %s" % mod_name)

    def deploy_version(self, key, mod, persist=False):
        """
            Deploy a new version of the modules

            :param version The version of the deployed modules
            :modules modules A list of module names and the hashes of the code files
        """
        LOGGER.info("Deploying code (key=%s)" % key)
        # deploy the new code
        name = mod[1]
        source_code = mod[2]

        # if the module is new, or update
        if name not in self.__modules or key != self.__modules[name][0]:
            # write the new source
            source_file = os.path.join(self.__code_dir, MODULE_DIR, name + ".py")

            fd = open(source_file, "w+")
            fd.write(source_code)
            fd.close()

            # (re)load the new source
            self._load_module(name, source_file, key)

        if persist:
            with open(os.path.join(self.__code_dir, PERSIST_FILE), "w+") as fd:
                json.dump(mod, fd)

        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

    def get_module_payload(self):
        """
            Get the lastest module code payload in json formatted string
        """
        with open(os.path.join(self.__code_dir, PERSIST_FILE), "w+") as fd:
            return fd.read()
