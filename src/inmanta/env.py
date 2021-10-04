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
import importlib.util
import json
import logging
import os
import re
import site
import subprocess
import sys
import tempfile
import venv
from dataclasses import dataclass
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from itertools import chain
from subprocess import CalledProcessError
from typing import Any, Dict, Iterator, List, Optional, Pattern, Set, Tuple

import pkg_resources
from pkg_resources import DistInfoDistribution, Requirement

from inmanta import const
from packaging import version

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from packaging.requirements import InvalidRequirement
else:
    from pkg_resources.extern.packaging.requirements import InvalidRequirement

LOGGER = logging.getLogger(__name__)


class PackageNotFound(Exception):
    pass


@dataclass
class LocalPackagePath:
    path: str
    editable: bool = False


class PythonEnvironment:
    """
    A generic Python environment.
    """

    def __init__(self, *, env_path: Optional[str] = None, python_path: Optional[str] = None) -> None:
        if (env_path is None) == (python_path is None):
            raise ValueError("Exactly one of `env_path` and `python_path` needs to be specified")
        self.env_path: str
        self.python_path: str
        if env_path is not None:
            python_name: str = os.path.basename(sys.executable)
            self.env_path = env_path
            self.python_path = (
                os.path.join(self.env_path, "Scripts", python_name)
                if sys.platform == "win32"
                else os.path.join(self.env_path, "bin", python_name)
            )
        else:
            assert python_path is not None
            self.python_path = python_path
            self.env_path = os.path.dirname(os.path.dirname(self.python_path))
        self.site_packages_dir: str = (
            os.path.join(self.env_path, "Lib", "site-packages")
            if sys.platform == "win32"
            else os.path.join(
                self.env_path, "lib", "python%s" % ".".join(str(digit) for digit in sys.version_info[:2]), "site-packages"
            )
        )

    def get_installed_packages(self, only_editable: bool = False) -> Dict[str, version.Version]:
        """
        Return a list of all installed packages in the site-packages of a python interpreter.

        :param only_editable: List only packages installed in editable mode.
        :return: A dict with package names as keys and versions as values
        """
        cmd = [self.python_path, "-m", "pip", "list", "--format", "json", *(["--editable"] if only_editable else [])]
        output = self._run_command_and_log_output(cmd, stderr=subprocess.DEVNULL, env=os.environ.copy())
        return {r["name"]: version.Version(r["version"]) for r in json.loads(output)}

    def install_from_index(
        self,
        requirements: List[Requirement],
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
    ) -> None:
        index_args: List[str] = (
            []
            if index_urls is None
            else ["--index-url", index_urls[0], *chain.from_iterable(["--extra-index-url", url] for url in index_urls[1:])]
            if index_urls
            else ["--no-index"]
        )
        try:
            self._run_command_and_log_output(
                [
                    self.python_path,
                    "-m",
                    "pip",
                    "install",
                    *(["--upgrade"] if upgrade else []),
                    *(["--pre"] if allow_pre_releases else []),
                    *(str(requirement) for requirement in requirements),
                    *index_args,
                ],
                stderr=subprocess.PIPE,
            )
        except CalledProcessError as e:
            stderr: str = e.stderr.decode()
            not_found: List[str] = [
                requirement.project_name
                for requirement in requirements
                if f"No matching distribution found for {requirement.project_name}" in stderr
            ]
            if not_found:
                raise PackageNotFound("Packages %s were not found in the given indexes." % ", ".join(not_found))
            raise e

    def install_from_source(self, paths: List[LocalPackagePath], *, reinstall: bool = False) -> None:
        """
        Install one or more packages from source. Any path arguments should be local paths to a package directory or wheel.

        :param reinstall: reinstall previously installed packages. If not set, packages are not overridden.
        """
        if len(paths) == 0:
            raise Exception("install_from_source requires at least one package to install")
        explicit_paths: Iterator[LocalPackagePath] = (
            # make sure we only try to install from a local source: add leading `./` to explicitly tell pip we're pointing to a
            # local directory.
            LocalPackagePath(path=os.path.join(".", path.path), editable=path.editable)
            for path in paths
        )
        self._run_command_and_log_output(
            [
                self.python_path,
                "-m",
                "pip",
                "install",
                *(["--ignore-installed"] if reinstall else []),
                *chain.from_iterable(["-e", path.path] if path.editable else [path.path] for path in explicit_paths),
            ],
            stderr=subprocess.PIPE,
        )

    @classmethod
    def _run_command_and_log_output(
        cls, cmd: List[str], env: Optional[Dict[str, str]] = None, stderr: Optional[int] = None
    ) -> str:
        output: bytes = b""  # Make sure the var is always defined in the except bodies
        try:
            output = subprocess.check_output(cmd, stderr=stderr, env=env)
        except CalledProcessError as e:
            LOGGER.error("%s: %s", cmd, e.output.decode())
            raise
        except Exception:
            LOGGER.error("%s: %s", cmd, output.decode())
            raise
        else:
            LOGGER.debug("%s: %s", cmd, output.decode())
            return output.decode()


class ActiveEnv(PythonEnvironment):
    """
    The active Python environment. Method implementations assume this environment is active when they're called.
    Activating another environment that inherits from this one is allowed.
    """

    def install_from_index(
        self,
        requirements: List[Requirement],
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
    ) -> None:
        super().install_from_index(requirements, index_urls, upgrade, allow_pre_releases)
        self.notify_change()

    def install_from_source(self, paths: List[LocalPackagePath], *, reinstall: bool = False) -> None:
        super().install_from_source(paths, reinstall=reinstall)
        self.notify_change()

    @classmethod
    def check(cls, in_scope: Pattern[str], constraints: Optional[List[Requirement]] = None) -> bool:
        """
        Check this Python environment for incompatible dependencies in installed packages.

        :param in_scope: A full pattern representing the package names that are considered in scope for the installed packages'
            compatibility check. Only in scope packages' dependencies will be considered for conflicts. The pattern is matched
            against an all-lowercase package name.
        :param constraints: In addition to checking for compatibility within the environment, also verify that the environment's
            packages meet the given constraints. All listed packages are expected to be installed.
        :return: True iff the check succeeds.
        """

        dist_info: DistInfoDistribution
        # add all requirements of all in scope packages installed in this environment
        all_constraints: Set[Requirement] = set(constraints if constraints is not None else []).union(
            requirement
            for dist_info in pkg_resources.working_set
            if in_scope.fullmatch(dist_info.key)
            for requirement in dist_info.requires()
        )

        installed_versions: Dict[str, version.Version] = {
            dist_info.key: version.Version(dist_info.version) for dist_info in pkg_resources.working_set
        }
        constraint_violations: List[Tuple[Requirement, Optional[version.Version]]] = [
            (constraint, installed_versions.get(constraint.key, None))
            for constraint in all_constraints
            if constraint.key not in installed_versions or str(installed_versions[constraint.key]) not in constraint
        ]

        for constraint, v in constraint_violations:
            LOGGER.warning("Incompatibility between constraint %s and installed version %s", constraint, v)
        return len(constraint_violations) == 0

    @classmethod
    def get_module_file(cls, module: str) -> Optional[Tuple[Optional[str], Loader]]:
        """
        Get the location of the init file for a Python module within the active environment.

        :return: A tuple of the path and the associated loader, if the module is found.
        """
        spec: Optional[ModuleSpec]
        try:
            spec = importlib.util.find_spec(module)
        # inmanta.loader.PluginModuleLoader raises ImportError if module is not found
        except (ImportError, ModuleNotFoundError):
            spec = None
        return (spec.origin, spec.loader) if spec is not None else None

    def notify_change(self) -> None:
        """
        This method must be called when a package is installed or removed from the environment in order for Python to detect
        the change. Namespace packages installed in editable mode in particular require this method to allow them to be found by
        get_module_file().
        """
        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()
        # Make sure that the .pth files in the site-packages directory are processed.
        # This is required to make editable installs work.
        site.addsitedir(self.site_packages_dir)
        importlib.invalidate_caches()

        if const.PLUGINS_PACKAGE in sys.modules:
            mod = sys.modules[const.PLUGINS_PACKAGE]
            if mod is not None:
                # Make mypy happy
                assert mod.__spec__.submodule_search_locations is not None
                if self.site_packages_dir not in mod.__spec__.submodule_search_locations and os.path.exists(
                    os.path.join(self.site_packages_dir, const.PLUGINS_PACKAGE)
                ):
                    # A V2 module was installed in this virtual environment, but the inmanta_plugins package was already
                    # loaded before this venv was activated. As such, the site_packages_dir of this virtual environment
                    # doesn't appear in the submodule_search_locations of the loaded module. Reload the inmanta_plugins package
                    # to ensure that all V2 modules installed in this virtual environment are discovered correctly.
                    importlib.reload(mod)


process_env: ActiveEnv = ActiveEnv(python_path=sys.executable)
"""
Singleton representing the Python environment this process is running in.
"""


class VirtualEnv(ActiveEnv):
    """
    Creates and uses a virtual environment for this process. This virtualenv inherits from the previously active one.
    """

    _egg_fragment_re = re.compile(r"#egg=(?P<name>[^&]*)")
    _at_fragment_re = re.compile(r"^(?P<name>[^@]+)@(?P<req>.+)")

    def __init__(self, env_path: str) -> None:
        LOGGER.info("Creating new virtual environment in %s", env_path)
        super().__init__(env_path=env_path)
        self.env_path: str = env_path
        self.virtual_python: Optional[str] = None
        self.__cache_done: Set[str] = set()
        self.__using_venv: bool = False
        self._parent_python: Optional[str] = None
        self._packages_installed_in_parent_env: Optional[Dict[str, str]] = None

    def _init_env(self) -> bool:
        """
        Init the virtual environment
        """
        self._parent_python = sys.executable

        # check if the virtual env exists
        if not os.path.exists(self.python_path):
            # venv requires some care when the .env folder already exists
            # https://docs.python.org/3/library/venv.html
            if not os.path.exists(self.env_path):
                path = self.env_path
            else:
                # venv has problems with symlinks
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
        self.virtual_python = self.python_path

        return True

    def is_using_virtual_env(self) -> bool:
        return self.__using_venv

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
        self.notify_change()

        self.__using_venv = True

    def _activate_that(self) -> None:
        # adapted from https://github.com/pypa/virtualenv/blob/master/virtualenv_embedded/activate_this.py
        # MIT license
        # Copyright (c) 2007 Ian Bicking and Contributors
        # Copyright (c) 2009 Ian Bicking, The Open Planning Project
        # Copyright (c) 2011-2016 The virtualenv developers

        binpath: str = os.path.dirname(self.python_path)
        base: str = os.path.dirname(binpath)
        old_os_path = os.environ.get("PATH", "")
        os.environ["PATH"] = binpath + os.pathsep + old_os_path
        prev_sys_path = list(sys.path)

        site.addsitedir(self.site_packages_dir)
        sys.real_prefix = sys.prefix
        sys.prefix = base
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
            try:
                self._run_command_and_log_output(cmd, stderr=subprocess.STDOUT)
            except Exception:
                LOGGER.error("requirements: %s", requirements_file)
                raise
        finally:
            if os.path.exists(path):
                os.remove(path)

        self.notify_change()

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

    def install(self, path: str, editable: bool) -> None:
        """
        Install a package in the virtual environment.

        This call by-passes the cache. It's only used by the tests via the `snippetcompiler*` fixtures.
        """
        if not self.__using_venv:
            raise Exception(f"Not using venv {self.__using_venv}. use_virtual_env() should be called first.")
        if editable and not os.path.isdir(path):
            raise Exception(f"An editable install was requested, but {path} is not a source directory")

        # Make mypy happy
        assert self.virtual_python is not None

        cmd_base: List["str"] = [self.virtual_python, "-m", "pip", "install"]
        if editable:
            cmd = cmd_base + ["-e", path]
        else:
            cmd = cmd_base + [path]

        self._run_command_and_log_output(cmd, stderr=subprocess.STDOUT)
        self.notify_change()
