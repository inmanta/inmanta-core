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

import hashlib
import json
import logging
import os
import re
import site
import subprocess
import sys
import tempfile
import venv
from subprocess import CalledProcessError
from typing import Any, Dict, List, Optional, Set, Tuple

import pkg_resources

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from packaging.requirements import InvalidRequirement
else:
    from pkg_resources.extern.packaging.requirements import InvalidRequirement

LOGGER = logging.getLogger(__name__)


class VirtualEnv(object):
    """
    Creates and uses a virtual environment for this process
    """

    _egg_fragment_re = re.compile(r"#egg=(?P<name>[^&]*)")
    _at_fragment_re = re.compile(r"^(?P<name>[^@]+)@(?P<req>.+)")

    def __init__(self, env_path: str) -> None:
        LOGGER.info("Creating new virtual environment in %s", env_path)
        self.env_path: str = env_path
        self.virtual_python: Optional[str] = None
        self.__cache_done: Set[str] = set()
        self.__using_venv: bool = False
        self._parent_python: Optional[str] = None
        self._packages_installed_in_parent_env: Optional[Dict[str, str]] = None

        python_name = os.path.basename(sys.executable)

        if sys.platform == "win32":
            self.binpath = os.path.abspath(os.path.join(self.env_path, "Scripts"))
            site_package_relative_path = os.path.join("Lib", "site-packages")
        else:
            self.binpath = os.path.abspath(os.path.join(self.env_path, "bin"))
            site_package_relative_path = os.path.join(
                "lib", "python%s" % ".".join(str(digit) for digit in sys.version_info[:2]), "site-packages"
            )

        self.python_bin = os.path.join(self.binpath, python_name)
        self.base = os.path.dirname(self.binpath)
        self.site_packages = os.path.join(self.base, site_package_relative_path)

    def get_package_installed_in_parent_env(self) -> Optional[Dict[str, str]]:
        if self._packages_installed_in_parent_env is None:
            self._packages_installed_in_parent_env = self._get_installed_packages(self._parent_python)

        return self._packages_installed_in_parent_env

    def _init_env(self) -> bool:
        """
        Init the virtual environment
        """
        self._parent_python = sys.executable

        # check if the virtual env exists
        if os.path.isdir(self.env_path) and os.listdir(self.env_path):
            # make sure the venv hosts the same python version as the running process
            if sys.platform.startswith("linux"):
                # On linux distributions we can check the versions match because
                # the env's version is in the site-packages dir's path

                if not os.path.exists(self.site_packages):
                    raise VenvActivationFailedError(
                        msg=f"Unable to use virtualenv at {self.env_path} because its Python version "
                        "is different from the Python version of this process."
                    )

            else:
                # On other distributions a more costly check is required:
                # get version as a (major, minor) tuple for the venv and the running process
                venv_python_version = subprocess.check_output([self.python_bin, "--version"]).decode("utf-8").strip().split()[1]
                venv_python_version = tuple(map(int, venv_python_version.split(".")))[:2]

                running_process_python_version = sys.version_info[:2]

                if venv_python_version != running_process_python_version:
                    raise VenvActivationFailedError(
                        msg=f"Unable to use virtualenv at {self.env_path} because its Python version "
                        "is different from the Python version of this process."
                    )

        else:
            path = os.path.realpath(self.env_path)

            # --clear is required in python prior to 3.4 if the folder already exists
            try:
                venv.create(path, clear=True, with_pip=False)
            except CalledProcessError as e:
                LOGGER.exception("Unable to create new virtualenv at %s (%s)", self.env_path, e.stdout.decode())
                return False
            except Exception:
                LOGGER.exception("Unable to create new virtualenv at %s", self.env_path)
                return False
            LOGGER.debug("Created a new virtualenv at %s", self.env_path)

        # set the path to the python and the pip executables
        self.virtual_python = self.python_bin

        return True

    def use_virtual_env(self) -> None:
        """
        Use the virtual environment
        """
        if self.__using_venv:
            raise Exception(f"Already using venv {self.env_path}.")

        if not self._init_env():
            raise Exception("Unable to init virtual environment")

        self._activate_that()

        # patch up pkg
        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

        self.__using_venv = True

    def _activate_that(self) -> None:
        # adapted from https://github.com/pypa/virtualenv/blob/master/virtualenv_embedded/activate_this.py
        # MIT license
        # Copyright (c) 2007 Ian Bicking and Contributors
        # Copyright (c) 2009 Ian Bicking, The Open Planning Project
        # Copyright (c) 2011-2016 The virtualenv developers

        old_os_path = os.environ.get("PATH", "")
        os.environ["PATH"] = self.binpath + os.pathsep + old_os_path
        prev_sys_path = list(sys.path)

        site.addsitedir(self.site_packages)
        sys.real_prefix = sys.prefix
        sys.prefix = self.base
        # Move the added items to the front of the path:
        new_sys_path = []
        for item in list(sys.path):
            if item not in prev_sys_path:
                new_sys_path.append(item)
                sys.path.remove(item)
        sys.path[:0] = new_sys_path

        # Also set the python path environment variable for any subprocess
        os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)

        # write out a "stub" pip so that pip list works in the virtual env
        pip_path = os.path.join(self.env_path, "bin", "pip")

        with open(pip_path, "w") as fd:
            fd.write(
                f"""#!/bin/sh
source activate
export PYTHONPATH="{os.pathsep.join(sys.path)}"
python -m pip $@
            """
            )

        os.chmod(pip_path, 0o755)

    def _parse_line(self, req_line: str) -> Tuple[Optional[str], str]:
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

    def _gen_requirements_file(self, requirements_list: List[str]) -> str:
        """Generate a new requirements file based on the requirements list that was built from all the different modules.
        :param requirements_list:  A list of requirements from all the requirements files in all modules.
        :return: A string that can be written to a requirements file that pip understands.
        """
        modules: Dict[str, Any] = {}
        for req in requirements_list:
            parsed_name, req_spec = self._parse_line(req)

            if parsed_name is None:
                name = req
            else:
                name = parsed_name

            url = None
            version = None
            marker = None
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
                    marker = item.marker
                    if hasattr(item, "url"):
                        url = item.url
            except InvalidRequirement:
                url = req_spec

            if name not in modules:
                modules[name] = {"name": name, "version": [], "markers": []}

            if version is not None:
                modules[name]["version"].extend(version)

            if marker is not None:
                modules[name]["markers"].append(marker)

            if url is not None:
                modules[name]["url"] = url

        requirements_file = ""
        for module, info in modules.items():
            version_spec = ""
            markers: str = ""
            if len(info["version"]) > 0:
                version_spec = " " + (", ".join(["%s %s" % (a, b) for a, b in info["version"]]))

            if len(info["markers"]) > 0:
                markers = " ; " + (" and ".join(map(str, info["markers"])))

            if "url" in info:
                module = info["url"]

            requirements_file += module + version_spec + markers + "\n"

        return requirements_file

    def _install(self, requirements_list: List[str]) -> None:
        """
        Install requirements in the given requirements file
        """
        requirements_file = self._gen_requirements_file(requirements_list)

        path = ""
        try:
            fdnum, path = tempfile.mkstemp()
            fd = os.fdopen(fdnum, "w+", encoding="utf-8")
            fd.write(requirements_file)
            fd.close()

            assert self.virtual_python is not None
            cmd: List["str"] = [self.virtual_python, "-m", "pip", "install", "-r", path]
            output: bytes = b""  # Make sure the var is always defined in the except bodies
            try:
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            except CalledProcessError as e:
                LOGGER.error("%s: %s", cmd, e.output.decode())
                LOGGER.error("requirements: %s", requirements_file)
                raise
            except Exception:
                LOGGER.error("%s: %s", cmd, output.decode())
                LOGGER.error("requirements: %s", requirements_file)
                raise
            else:
                LOGGER.debug("%s: %s", cmd, output.decode())

        finally:
            if os.path.exists(path):
                os.remove(path)

        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

    def _read_current_requirements_hash(self) -> str:
        """
        Return the hash of the requirements file used to install the current environment
        """
        path = os.path.join(self.env_path, "requirements.sha1sum")
        if not os.path.exists(path):
            return ""

        with open(path, "r", encoding="utf-8") as fd:
            return fd.read().strip()

    def _set_current_requirements_hash(self, new_hash: str) -> None:
        """
        Set the current requirements hash
        """
        path = os.path.join(self.env_path, "requirements.sha1sum")
        with open(path, "w+", encoding="utf-8") as fd:
            fd.write(new_hash)

    def install_from_list(self, requirements_list: List[str], detailed_cache: bool = False, cache: bool = True) -> None:
        """
        Install requirements from a list of requirement strings
        """
        if not self.__using_venv:
            raise Exception(f"Not using venv {self.__using_venv}. use_virtual_env() should be called first.")

        if detailed_cache:
            requirements_list = sorted(list(set(requirements_list) - self.__cache_done))
            if len(requirements_list) == 0:
                return

        requirements_list = sorted(requirements_list)

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

    @classmethod
    def _get_installed_packages(cls, python_interpreter: str) -> Dict[str, str]:
        """Return a list of all installed packages in the site-packages of a python interpreter.
        :param python_interpreter: The python interpreter to get the packages for
        :return: A dict with package names as keys and versions as values
        """
        cmd = [python_interpreter, "-m", "pip", "list", "--format", "json"]
        output = b""
        try:
            environment = os.environ.copy()
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, env=environment)
        except CalledProcessError as e:
            LOGGER.error("%s: %s", cmd, e.output.decode())
            raise
        except Exception:
            LOGGER.error("%s: %s", cmd, output.decode())
            raise
        else:
            LOGGER.debug("%s: %s", cmd, output.decode())

        return {r["name"]: r["version"] for r in json.loads(output.decode())}


class VenvActivationFailedError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg
