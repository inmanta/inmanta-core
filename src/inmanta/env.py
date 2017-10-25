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

import sys
import os
import subprocess
import tempfile
import hashlib
import logging
import re

import pkg_resources


LOGGER = logging.getLogger(__name__)


class VirtualEnv(object):
    """
        Creates and uses a virtual environment for this process
    """
    _egg_fragment_re = re.compile(r"#egg=(?P<name>[^&]*)")
    _at_fragment_re = re.compile(r"^(?P<name>[^@]+)@(?P<req>.+)")

    def __init__(self, env_path):
        LOGGER.info("Creating new virtual environment in %s", env_path)
        self.env_path = env_path
        self.virtual_python = None
        self.virtual_pip = None
        self.__cache_done = set()

        self._old = {}

    def init_env(self):
        """
            Init the virtual environment
        """
        python_exec = sys.executable
        python_name = os.path.basename(sys.executable)

        # check if the virtual env exists
        python_bin = os.path.join(self.env_path, "bin", python_name)

        if not os.path.exists(python_bin):
            venv_call = [python_exec, "-m", "virtualenv"]
            try:
                subprocess.check_output(venv_call + ["--version"])
            except subprocess.CalledProcessError:
                raise Exception("Virtualenv not installed for python %s" % python_exec)

            proc = subprocess.Popen(venv_call + ["-p", python_exec, self.env_path], env=os.environ.copy(),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()

            if proc.returncode == 0:
                LOGGER.debug("Created a new virtualenv at %s", self.env_path)
            else:
                LOGGER.error("Unable to create new virtualenv at %s (%s, %s)", self.env_path, out.decode(), err.decode())
                return False

        # set the path to the python and the pip executables
        self.virtual_python = python_bin
        self.virtual_pip = os.path.join(self.env_path, "bin", "pip")
        return True

    def use_virtual_env(self):
        """
            Use the virtual environment
        """
        if not self.init_env():
            raise Exception("Unable to init virtual environment")

        activate_file = os.path.join(self.env_path, "bin/activate_this.py")
        if os.path.exists(activate_file):
            with open(activate_file) as f:
                code = compile(f.read(), activate_file, 'exec')
                exec(code, {"__file__": activate_file})
        else:
            raise Exception("Unable to activate virtual environment because %s does not exist." % activate_file)

        # patch up pkg
        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

    def _parse_line(self, req_line: str) -> tuple:
        """
            Parse the requirement line
        """
        at = VirtualEnv._at_fragment_re.search(req_line)
        if at is not None:
            d = at.groupdict()
            return d["name"], d["req"] + "#egg=" + d["name"]

        egg = VirtualEnv._egg_fragment_re.search(req_line)
        if egg is not None:
            d = egg.groupdict()
            return d["name"], req_line

        return None, req_line

    def _gen_requirements_file(self, requirements_list) -> str:
        modules = {}
        for req in requirements_list:
            name, req_spec = self._parse_line(req)

            if name is None:
                name = req

            url = None
            version = None
            try:
                # this will fail is an url is supplied
                parsed_req = list(pkg_resources.parse_requirements(req_spec))
                if len(parsed_req) > 0:
                    item = parsed_req[0]
                    if hasattr(item, "name"):
                        name = item.name
                    elif hasattr(item, "unsafe_name"):
                        name = item.unsafe_name
                    version = item.specs
                    if hasattr(item, "url"):
                        url = item.url
            except pkg_resources.RequirementParseError:
                url = req_spec

            if name not in modules:
                modules[name] = {"name": name, "version": []}

            if version is not None:
                modules[name]["version"].extend(version)

            if url is not None:
                modules[name]["url"] = url

        requirements_file = ""
        for module, info in modules.items():
            version_spec = ""
            if len(info["version"]) > 0:
                version_spec = " " + (", ".join(["%s %s" % (a, b) for a, b in info["version"]]))

            if "url" in info:
                module = info["url"]

            requirements_file += module + version_spec + "\n"

        return requirements_file

    def _install(self, requirements_list: []) -> None:
        """
            Install requirements in the given requirements file
        """
        requirements_file = self._gen_requirements_file(requirements_list)

        try:
            fdnum, path = tempfile.mkstemp()
            fd = os.fdopen(fdnum, "w+")
            fd.write(requirements_file)
            fd.close()

            cmd = [self.virtual_pip, "install", "-r", path]
            output = b""
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            except Exception:
                LOGGER.debug("%s: %s", cmd, output.decode())
                LOGGER.debug("requirements: %s", requirements_file)
                raise
            else:
                LOGGER.debug("%s: %s", cmd, output.decode())

        finally:
            if os.path.exists(path):
                os.remove(path)

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

        self._install(requirements_list)
        self._set_current_requirements_hash(new_req_hash)
        for x in requirements_list:
            self.__cache_done.add(x)
