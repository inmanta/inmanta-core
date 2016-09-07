"""
    Copyright 2016 Inmanta

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

import sys
import os
import subprocess
import tempfile
import hashlib
import logging

import pkg_resources


LOGGER = logging.getLogger(__name__)


class VirtualEnv(object):
    """
        Creates and uses a virtual environment for this process
    """

    def __init__(self, env_path):
        self.env_path = env_path
        self.virtual_python = None
        self.virtual_pip = None
        self.__cache_done = set()

    def init_env(self):
        """
            Init the virtual environment
        """
        python_exec = sys.executable
        python_name = os.path.basename(sys.executable)

        # check if the virtual env exists
        python_bin = os.path.join(self.env_path, "bin", python_name)

        if not os.path.exists(python_bin):
            virtualenv_path = os.path.join(os.path.dirname(python_exec), "virtualenv")
            if not os.path.exists(virtualenv_path):
                raise Exception("Unable to find virtualenv script (%s does not exist)" % virtualenv_path)

            proc = subprocess.Popen([virtualenv_path, "-p", python_exec, self.env_path], env=os.environ.copy(),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()

            if proc.returncode == 0:
                LOGGER.debug("Created a new virtualenv at %s", self.env_path)
            else:
                LOGGER.error("Unable to create new virtualenv at %s (%s, %s)", self.env_path, out.decode(), err.decode())

        # set the path to the python and the pip executables
        self.virtual_python = python_bin
        self.virtual_pip = os.path.join(self.env_path, "bin", "pip")

    def use_virtual_env(self):
        """
            Use the virtual environment
        """
        self.init_env()

        activate_file = os.path.join(self.env_path, "bin/activate_this.py")
        if os.path.exists(activate_file):
            with open(activate_file) as f:
                code = compile(f.read(), activate_file, 'exec')
                exec(code, {"__file__": activate_file})
        else:
            raise Exception("Unable to activate virtual environment because %s does not exist." % activate_file)

        # patch up pkg
        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

    def install(self, requirements):
        """
            Install the given list of requirements in the virtual environment
        """
        cmd = [self.virtual_pip, "install"]
        for require in requirements:
            cmd.append(require)

        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        LOGGER.debug("%s: %s", cmd, output)
        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

    def install_from_file(self, requirements_file: str) -> None:
        """
            Install requirements in the given requirements file
        """
        if os.path.exists(requirements_file):
            cmd = [self.virtual_pip, "install", "-r", requirements_file]
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            except Exception as e:
                LOGGER.debug("%s: %s", cmd, e.output.decode())
                raise
            else:
                LOGGER.debug("%s: %s", cmd, output)

        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

    def _read_current_requirements_hash(self):
        """
            Return the hash of the requirements file used to install the current environment
        """
        path = os.path.join(self.env_path, "requirements.sha1sum")
        if not os.path.exists(path):
            return ""

        with open(path, "r") as fd:
            return fd.read().strip()

    def _set_current_requirements_hash(self, new_hash):
        """
            Set the current requirements hahs
        """
        path = os.path.join(self.env_path, "requirements.sha1sum")
        with open(path, "w+") as fd:
            fd.write(new_hash)

    def install_from_list(self, requirements_list: list, detailed_cache=False, cache=True) -> None:
        """
            Install requirements from a list of requirement strings
        """
        requirements_list = sorted(requirements_list)

        if detailed_cache:
            requirements_list = sorted(list(set(requirements_list) - self.__cache_done))
            if len(requirements_list) == 0:
                return

        # hash it
        sha1sum = hashlib.sha1()
        sha1sum.update("\n".join(requirements_list).encode())
        new_req_hash = sha1sum.hexdigest()

        current_hash = self._read_current_requirements_hash()

        if new_req_hash == current_hash and cache:
            return

        try:
            # create requirements file
            requirements_file = tempfile.mktemp()
            with open(requirements_file, "w+") as fd:
                fd.write("\n".join(requirements_list))
                fd.close()

            self.install_from_file(requirements_file)
            self._set_current_requirements_hash(new_req_hash)
            for x in requirements_list:
                self.__cache_done.add(x)
        finally:
            os.remove(requirements_file)
