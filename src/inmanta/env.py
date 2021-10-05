"""
    Copyright 2021 Inmanta

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
import contextlib
import enum
import functools
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
from typing import Any, Dict, Iterator, List, Optional, Pattern, Set, Tuple, TypeVar, Union

import pkg_resources
from pkg_resources import DistInfoDistribution, Requirement

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


class PipListFormat(enum.Enum):
    """
    The different output formats that can be passed to the `pip list` command.
    """
    columns = "columns"
    freeze = "freeze"
    json = "json"


class PipCommandBuilder:
    """
    Class used to compose pip commands.
    """

    @classmethod
    def compose_install_command(
        cls,
        python_path: str,
        requirements: Optional[List[Requirement]] = None,
        paths: Optional[List[LocalPackagePath]] = None,
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
        constraints_files: Optional[List[str]] = None,
        requirements_files: Optional[List[str]] = None,
        reinstall: bool = False,
    ) -> List[str]:
        """
        Generate `pip install` command from the given arguments.

        :param python_path: The python interpreter to use in the command
        :param requirements: The requirements that should be installed
        :param paths: Paths to python projects on disk that should be installed in the venv.
        :param index_urls: The Python package repositories to use. When set to None, the system default will be used.
        :param upgrade: Upgrade the specified packages to the latest version.
        :param allow_pre_releases: Allow the installation of packages with pre-releases and development versions.
        :param constraints_files: Files that should be passed to pip using the `-c` option.
        :param requirements_files: Files that should be passed to pip using the `-r` option.
        :param reinstall: Reinstall previously installed packages. If not set, packages are not overridden.
        """
        requirements = requirements if requirements is not None else []
        paths = paths if paths is not None else []
        local_paths: Iterator[LocalPackagePath] = (
            # make sure we only try to install from a local source: add leading `./` and trailing `/` to explicitly tell pip
            # we're pointing to a local directory.
            LocalPackagePath(path=os.path.join(".", path.path, ""), editable=path.editable)
            for path in paths
        )
        index_args: List[str] = (
            []
            if index_urls is None
            else ["--index-url", index_urls[0], *chain.from_iterable(["--extra-index-url", url] for url in index_urls[1:])]
            if index_urls
            else ["--no-index"]
        )
        constraints_files = constraints_files if constraints_files is not None else []
        requirements_files = requirements_files if requirements_files is not None else []
        return [
            python_path,
            "-m",
            "pip",
            "install",
            *(["--ignore-installed"] if reinstall else []),
            *(["--upgrade"] if upgrade else []),
            *(["--pre"] if allow_pre_releases else []),
            *chain.from_iterable(["-c", f] for f in constraints_files),
            *chain.from_iterable(["-r", f] for f in requirements_files),
            *(str(requirement) for requirement in requirements),
            *chain.from_iterable(["-e", path.path] if path.editable else [path.path] for path in local_paths),
            *index_args,
        ]

    @classmethod
    def compose_list_command(
        cls, python_path: str, format: Optional[PipListFormat] = None, only_editable: bool = False
    ) -> List[str]:
        """
        Generate a `pip list` command for the given arguments.

        :param python_path: The python interpreter to use in the command.
        :param format: The output format to use.
        :param only_editable: Whether the output should only contain project installed in editable mode.
        """
        return [
            python_path,
            "-m",
            "pip",
            "list",
            *(["--format", format.value] if format else []),
            *(["--editable"] if only_editable else []),
        ]


class PythonEnvironment:
    """
    A generic Python environment.

    The implementation of this class is based on the invariant that the version of the inmanta-core and the
    Inmanta product packages doesn't change. This call will make sure that the version of these packages is
    never changed.
    """

    def __init__(self, *, env_path: Optional[str] = None, python_path: Optional[str] = None) -> None:
        if (env_path is None) == (python_path is None):
            raise ValueError("Exactly one of `env_path` and `python_path` needs to be specified")
        self.env_path: str
        self.python_path: str
        if env_path is not None:
            self.env_path = env_path
            self.python_path = self.get_python_path_for_env_path(self.env_path)
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

    @classmethod
    def get_python_path_for_env_path(cls, env_path: str) -> str:
        """
        For the given venv directory (`env_path`) return the path to the Python interpreter.
        """
        python_name: str = os.path.basename(sys.executable)
        return (
            os.path.join(env_path, "Scripts", python_name)
            if sys.platform == "win32"
            else os.path.join(env_path, "bin", python_name)
        )

    def get_installed_packages(self, only_editable: bool = False) -> Dict[str, version.Version]:
        """
        Return a list of all installed packages in the site-packages of a python interpreter.

        :param only_editable: List only packages installed in editable mode.
        :return: A dict with package names as keys and versions as values
        """
        cmd = PipCommandBuilder.compose_list_command(self.python_path, format=PipListFormat.json, only_editable=only_editable)
        output = self._run_command_and_log_output(cmd, stderr=subprocess.DEVNULL, env=os.environ.copy())
        return {r["name"]: version.Version(r["version"]) for r in json.loads(output)}

    def install_from_index(
        self,
        requirements: List[Requirement],
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
        constraint_files: Optional[List[str]] = None,
    ) -> None:
        if len(requirements) == 0:
            raise Exception("install_from_index requires at least one requirement to install")
        constraint_files = constraint_files if constraint_files is not None else []
        with requirements_txt_file(content=self._get_constraint_on_inmanta_package()) as filename:
            try:
                cmd: List[str] = PipCommandBuilder.compose_install_command(
                    python_path=self.python_path,
                    requirements=requirements,
                    index_urls=index_urls,
                    upgrade=upgrade,
                    allow_pre_releases=allow_pre_releases,
                    constraints_files=[*constraint_files, filename],
                )
                self._run_command_and_log_output(cmd, stderr=subprocess.PIPE)
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

    def install_from_source(
        self, paths: List[LocalPackagePath], constraint_files: Optional[List[str]] = None, *, reinstall: bool = False
    ) -> None:
        """
        Install one or more packages from source. Any path arguments should be local paths to a package directory or wheel.

        :param reinstall: reinstall previously installed packages. If not set, packages are not overridden.
        """
        if len(paths) == 0:
            raise Exception("install_from_source requires at least one package to install")
        constraint_files = constraint_files if constraint_files is not None else []
        with requirements_txt_file(content=self._get_constraint_on_inmanta_package()) as filename:
            cmd: List[str] = PipCommandBuilder.compose_install_command(
                python_path=self.python_path, paths=paths, constraints_files=[*constraint_files, filename], reinstall=reinstall
            )
            self._run_command_and_log_output(cmd, stderr=subprocess.PIPE)

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


@contextlib.contextmanager
def requirements_txt_file(content: str) -> Iterator[str]:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=True) as fd:
        fd.write(content)
        fd.flush()
        yield fd.name


req_list = TypeVar("req_list", List[str], List[Requirement])


class ActiveEnv(PythonEnvironment):
    """
    The active Python environment. Method implementations assume this environment is active when they're called.
    Activating another environment that inherits from this one is allowed.
    """

    _egg_fragment_re = re.compile(r"#egg=(?P<name>[^&]*)")
    _at_fragment_re = re.compile(r"^(?P<name>[^@]+)@(?P<req>.+)")

    def __init__(self, *, env_path: Optional[str] = None, python_path: Optional[str] = None) -> None:
        super(ActiveEnv, self).__init__(env_path=env_path, python_path=python_path)

    def is_using_virtual_env(self) -> bool:
        return True

    def use_virtual_env(self) -> None:
        """
        Activate the virtual environment.
        """
        return

    @classmethod
    def _get_as_requirements_type(cls, requirements: req_list) -> List[Requirement]:
        """
        Convert requirements from Union[List[str], List[Requirement]] to List[Requirement]
        """
        if isinstance(requirements[0], str):
            return [Requirement.parse(r) for r in requirements]
        else:
            return requirements

    def _are_installed(self, requirements: req_list) -> bool:
        """
        Return True iff the given requirements are installed in this venv.
        """
        if not requirements:
            return True
        reqs_as_requirements: List[Requirement] = self._get_as_requirements_type(requirements)
        installed_packages: Dict[str, version.Version] = self._get_installed_packages_from_working_set()
        return all(r.key in installed_packages and str(installed_packages[r.key]) in r for r in reqs_as_requirements)

    def install_from_index(
        self,
        requirements: List[Requirement],
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
        constraint_files: Optional[List[str]] = None,
    ) -> None:
        if not upgrade and self._are_installed(requirements):
            return
        try:
            super(ActiveEnv, self).install_from_index(requirements, index_urls, upgrade, allow_pre_releases, constraint_files)
        finally:
            self.notify_change()

    def install_from_source(
        self, paths: List[LocalPackagePath], constraint_files: Optional[List[str]] = None, *, reinstall: bool = False
    ) -> None:
        try:
            super().install_from_source(paths, constraint_files, reinstall=reinstall)
        finally:
            self.notify_change()

    @classmethod
    def _parse_line(cls, req_line: str) -> Tuple[Optional[str], str]:
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

    @classmethod
    def _gen_content_requirements_file(cls, requirements_list: List[str]) -> str:
        """Generate a new requirements file based on the requirements list.
        :param requirements_list:  A list of Python requirements as strings.
        :return: A string that can be written to a requirements file that pip understands.
        """
        modules: Dict[str, Any] = {}
        for req in requirements_list:
            parsed_name, req_spec = cls._parse_line(req)

            if parsed_name is None:
                name = req
            else:
                name = parsed_name

            url = None
            version = None
            marker = None
            try:
                # this will fail if an url is supplied
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

    def install_from_list(self, requirements_list: List[str]) -> None:
        """
        Install requirements from a list of requirement strings. This method uses the Python package repositories
        configured on the host.

        This method differs from the `_install_from_index()` method in the sense that it calls
        `_gen_content_requirements_file()`, which rewrites the requirements from pep440 format to a format that pip understands.
        This method is maintained for V1 modules only.
        """
        if self._are_installed(requirements_list):
            return
        try:
            self._install_from_list(requirements_list)
        finally:
            self.notify_change()

    def _install_from_list(self, requirements_list: List[str]) -> None:
        content_requirements_file = self._gen_content_requirements_file(requirements_list)
        with requirements_txt_file(content=content_requirements_file) as requirements_file:
            with requirements_txt_file(content=self._get_constraint_on_inmanta_package()) as constraint_file:
                cmd: List[str] = PipCommandBuilder.compose_install_command(
                    python_path=self.python_path,
                    requirements_files=[requirements_file],
                    constraints_files=[constraint_file],
                )
                try:
                    self._run_command_and_log_output(cmd, stderr=subprocess.STDOUT)
                except Exception:
                    LOGGER.error("requirements: %s", content_requirements_file)
                    raise

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

        installed_versions: Dict[str, version.Version] = cls._get_installed_packages_from_working_set()
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

    def init_namespace(self, namespace: str) -> None:
        """
        Make sure importer will be able to find the namespace packages for this namespace that will get installed in the
        process venv. This method needs to be called before the importer caches the search paths, so make sure to call it
        before calling get_module_file for this namespace.

        :param namespace: The namespace to initialize.
        """
        path: str = os.path.join(self.site_packages_dir, namespace)
        os.makedirs(path, exist_ok=True)
        spec: Optional[ModuleSpec] = importlib.util.find_spec(namespace)
        if spec is None or spec.submodule_search_locations is None or path not in spec.submodule_search_locations:
            raise Exception(
                "Invalid state: trying to init namespace after it has been loaded. Make sure to call this method before calling"
                " get_module_file for this namespace."
            )

    @classmethod
    def _get_installed_packages_from_working_set(cls) -> Dict[str, version.Version]:
        """
        Return all installed packages based on `pkg_resources.working_set`.
        """
        return {dist_info.key: version.Version(dist_info.version) for dist_info in pkg_resources.working_set}

    @functools.lru_cache(maxsize=1)
    def _get_constraint_on_inmanta_package(self) -> str:
        """
        Returns the content of the constraint file that should be supplied to each `pip install` invocation
        to make sure that no Inmanta packages gets overridden.
        """
        installed_packages = self._get_installed_packages_from_working_set()
        inmanta_packages = ["inmanta-service-orchestrator", "inmanta", "inmanta-core"]
        for pkg in inmanta_packages:
            if pkg in installed_packages:
                return f"{pkg}=={installed_packages[pkg]}"
        # No inmanta product or inmanta-core package installed -> Leave constraint empty
        return ""

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


process_env: ActiveEnv = ActiveEnv(python_path=sys.executable)
"""
Singleton representing the Python environment this process is running in.
"""


class VirtualEnv(ActiveEnv):
    """
    Creates and uses a virtual environment for this process. This virtualenv inherits from the previously active one.
    """

    def __init__(self, env_path: str) -> None:
        LOGGER.info("Creating new virtual environment in %s", env_path)
        super(VirtualEnv, self).__init__(env_path=env_path)
        self.env_path: str = env_path
        self.virtual_python: Optional[str] = None
        self.__using_venv: bool = False
        self._parent_python: Optional[str] = None
        self._path_sitecustomize_py = os.path.join(self.site_packages_dir, "sitecustomize.py")

    def exists(self) -> bool:
        """
        Returns True iff the venv exists on disk.
        """
        return os.path.exists(self.python_path) and os.path.exists(self._path_sitecustomize_py)

    def init_env(self) -> None:
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
                self._write_pip_binary()
                self._write_sitecustomize_py_file()
            except CalledProcessError as e:
                raise VenvCreationFailedError(msg=f"Unable to create new virtualenv at {self.env_path} ({e.stdout.decode()})")
            except Exception:
                raise VenvCreationFailedError(msg=f"Unable to create new virtualenv at {self.env_path}")
            LOGGER.debug("Created a new virtualenv at %s", self.env_path)
        elif not os.path.exists(self._path_sitecustomize_py):
            # Venv was created using an older version of Inmanta -> Update pip binary and set sitecustomize.py file
            self._write_pip_binary()
            self._write_sitecustomize_py_file()

        # set the path to the python and the pip executables
        self.virtual_python = self.python_path

    def is_using_virtual_env(self) -> bool:
        return self.__using_venv

    def use_virtual_env(self) -> None:
        """
        Activate the virtual environment.
        """
        if self.__using_venv:
            raise Exception(f"Already using venv {self.env_path}.")

        self.init_env()
        self._activate_that()

        # patch up pkg
        self.notify_change()

        self.__using_venv = True

    def _write_pip_binary(self) -> None:
        """
        write out a "stub" pip binary so that pip list works in the virtual env.
        """
        pip_path = os.path.join(self.env_path, "bin", "pip")

        with open(pip_path, "w", encoding="utf-8") as fd:
            fd.write(
                """#!/bin/bash
cd $(dirname "${BASH_SOURCE[0]}")
source activate
python -m pip $@
                """.strip()
            )
        os.chmod(pip_path, 0o755)

    def _write_sitecustomize_py_file(self) -> None:
        """
        Write a sitecustomize.py file to the venv to ensure that an activation of this venv will also activate
        the parent venv. The site directories of the parent venv should appear later in sys.path than the ones of this venv.
        """
        sys_path_as_python_strings = ['"' + p.replace('"', r'\"') + '"' for p in list(sys.path)]
        site_package_dir_as_python_string = '"' + self.site_packages_dir.replace('"', r'\"') + '"'
        script = f"""import sys
import os
import site
sys.path = [{', '.join(sys_path_as_python_strings)}]
previous_sys_path = list(sys.path)
site.addsitedir({site_package_dir_as_python_string})
# Move the added items to the front of the path
new_entries_sys_path = [e for e in sys.path if e not in previous_sys_path]
sys.path = [*new_entries_sys_path, *previous_sys_path]
# Also set the PYTHONPATH environment variable for any subprocess
os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)
"""
        with open(self._path_sitecustomize_py, "w", encoding="utf-8") as fd:
            fd.write(script)

    def _update_sys_path(self) -> None:
        """
        Updates sys.path by adding self.site_packages_dir. This method ensures
        that .pth files are processed.
        """
        prev_sys_path = list(sys.path)
        site.addsitedir(self.site_packages_dir)
        # Move the added items to the front of the path
        new_sys_path = [e for e in list(sys.path) if e not in prev_sys_path]
        new_sys_path.extend(prev_sys_path)
        # Set sys.path
        sys.path = new_sys_path

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

        sys.real_prefix = sys.prefix
        sys.prefix = base
        self._update_sys_path()

        # Also set the python path environment variable for any subprocess
        os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)

    def install_from_index(
        self,
        requirements: List[Requirement],
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
        constraint_files: Optional[List[str]] = None,
    ) -> None:
        if not self.__using_venv:
            raise Exception(f"Not using venv {self.env_path}. use_virtual_env() should be called first.")
        super(VirtualEnv, self).install_from_index(
            requirements,
            index_urls,
            upgrade,
            allow_pre_releases,
            constraint_files,
        )

    def install_from_source(
        self, paths: List[LocalPackagePath], constraint_files: Optional[List[str]] = None, *, reinstall: bool = False
    ) -> None:
        if not self.__using_venv:
            raise Exception(f"Not using venv {self.env_path}. use_virtual_env() should be called first.")
        super(VirtualEnv, self).install_from_source(paths, constraint_files, reinstall=reinstall)

    def install_from_list(self, requirements_list: List[str]) -> None:
        if not self.__using_venv:
            raise Exception(f"Not using venv {self.env_path}. use_virtual_env() should be called first.")
        super(VirtualEnv, self).install_from_list(requirements_list)


class VenvCreationFailedError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg
