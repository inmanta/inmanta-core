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
from collections import abc
from dataclasses import dataclass
from functools import reduce
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from itertools import chain
from subprocess import CalledProcessError
from textwrap import indent
from typing import Any, Dict, Iterator, List, Mapping, NamedTuple, Optional, Pattern, Sequence, Set, Tuple, TypeVar

import pkg_resources
from pkg_resources import DistInfoDistribution, Distribution, Requirement

import inmanta.module
from inmanta import const
from inmanta.ast import CompilerException
from inmanta.server.bootloader import InmantaBootloader
from inmanta.stable_api import stable_api
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
LOGGER_PIP = logging.getLogger("inmanta.pip")  # Use this logger to log pip commands or data related to pip commands.


class PackageNotFound(Exception):
    pass


class PipInstallError(Exception):
    pass


@dataclass(eq=True, frozen=True)
class VersionConflict:
    """
    Represents a version conflict that exists in a Python environment.

    :param requirement: The requirement that is unsatisfied.
    :param installed_version: The version that is currently installed. None if the package is not installed.
    :param owner: The package from which the constraint originates
    """

    requirement: Requirement
    installed_version: Optional[version.Version] = None
    owner: Optional[str] = None

    def __str__(self) -> str:
        owner = ""
        if self.owner:
            # Cfr pip
            # Requirement already satisfied: certifi>=2017.4.17 in /[...]/site-packages
            # (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==7.0.0) (2022.6.15)
            owner = f" (from {self.owner})"
        if self.installed_version:
            return (
                f"Incompatibility between constraint {self.requirement} and installed version {self.installed_version}{owner}"
            )
        else:
            return f"Constraint {self.requirement} is not installed{owner}"


class ConflictingRequirements(CompilerException):
    """
    Conflict reporting

    Can be used in two ways:
    - if we don't know the exact conflicts (detected by e.g. pip), the messages is used
    - if we have detailed conflict info, the message is derived from it

    """

    def __init__(self, message: str, conflicts: Optional[Set[VersionConflict]] = None):

        CompilerException.__init__(self, msg=message)
        self.conflicts = conflicts

    def get_message(self) -> str:
        # The message has three potential parts
        # First the advices, derived from the conflicts, if present
        # Then the message, if present
        # Then the individual conflicts, if present
        out = []

        advices = self.get_advice()
        if advices:
            out.append(advices)

        if self.msg:
            out.append(self.msg)

        conflicts = self.get_conflicts_string()
        if conflicts:
            out.append(conflicts)

        return "\n".join(out)

    def get_conflicts_string(self) -> Optional[str]:
        if not self.conflicts:
            return None
        msg = ""
        for current_conflict in sorted(self.conflicts, key=lambda x: x.requirement.key):
            msg += f"\n\t* {current_conflict}"
        return msg

    def has_missing(self) -> bool:
        """Does the set of conflicts contain any missing dependency?"""
        if not self.conflicts:
            return False
        return any(conflict.installed_version is None for conflict in self.conflicts)

    def get_advice(self) -> Optional[str]:
        """
        Derive an end-user centric message from the conflicts
        """
        if self.conflicts is None:
            return None
        if self.has_missing():
            return "Not all required python packages are installed run 'inmanta project install' to resolve this"
        else:
            return (
                "A dependency conflict exists, this is either because some modules are stale, incompatible "
                "or because pip can not find a correct combination of packages. To resolve this, "
                "first try `inmanta project update` to ensure no modules are stale. "
                "Second, try adding additional constraints to the requirements.txt file of "
                "the inmanta project to help pip resolve this problem. After every change, run `inmanta project update`"
            )


req_list = TypeVar("req_list", Sequence[str], Sequence[Requirement])


class PythonWorkingSet:
    @classmethod
    def _get_as_requirements_type(cls, requirements: req_list) -> Sequence[Requirement]:
        """
        Convert requirements from Union[Sequence[str], Sequence[Requirement]] to Sequence[Requirement]
        """
        if isinstance(requirements[0], str):
            return [Requirement.parse(r) for r in requirements]
        else:
            return requirements

    @classmethod
    def are_installed(cls, requirements: req_list) -> bool:
        """
        Return True iff the given requirements are installed in this workingset.
        """
        if not requirements:
            return True
        installed_packages: Dict[str, version.Version] = cls.get_packages_in_working_set()

        def _are_installed_recursive(
            reqs: Sequence[Requirement],
            seen_requirements: Sequence[Requirement],
            contained_in_extra: Optional[str] = None,
        ) -> bool:
            """
            Recursively check the given reqs are installed in this working set

            :param reqs: The requirements that should be checked.
            :param seen_requirements: An accumulator that contains all the requirements that were check in
                                      previous iterators. It prevents infinite loops when the dependency
                                      graph contains circular dependencies.
            :param contained_in_extra: The name of the extra that trigger a new recursive call. On the first
                                       iteration of this method this value is None.
            """
            for r in reqs:
                if r in seen_requirements:
                    continue
                # Requirements created by the `Distribution.requires()` method have the extra, the Requirement was created from,
                # set as a marker. The line below makes sure that the "extra" marker matches. The marker is not set by
                # `Distribution.requires()` when the package is installed in editable mode, but setting it always doesn't make
                # the marker evaluation fail.
                environment_marker_evaluation = {"extra": contained_in_extra} if contained_in_extra else None
                if r.marker and not r.marker.evaluate(environment=environment_marker_evaluation):
                    # The marker of the requirement doesn't apply on this environment
                    continue
                if r.key not in installed_packages or str(installed_packages[r.key]) not in r:
                    return False
                if r.extras:
                    for extra in r.extras:
                        distribution: Optional[Distribution] = pkg_resources.working_set.find(r)
                        if distribution is None:
                            return False
                        pkgs_required_by_extra: Set[Requirement] = set(distribution.requires(extras=(extra,))) - set(
                            distribution.requires(extras=())
                        )
                        if not _are_installed_recursive(
                            reqs=list(pkgs_required_by_extra),
                            seen_requirements=list(seen_requirements) + list(reqs),
                            contained_in_extra=extra,
                        ):
                            return False
            return True

        reqs_as_requirements: Sequence[Requirement] = cls._get_as_requirements_type(requirements)
        return _are_installed_recursive(reqs_as_requirements, seen_requirements=[])

    @classmethod
    def get_packages_in_working_set(cls, inmanta_modules_only: bool = False) -> Dict[str, version.Version]:
        """
        Return all packages present in `pkg_resources.working_set` together with the version of the package.

        :param inmanta_modules_only: Only return inmanta modules from the working set
        """
        return {
            dist_info.key: version.Version(dist_info.version)
            for dist_info in pkg_resources.working_set
            if not inmanta_modules_only or dist_info.key.startswith(inmanta.module.ModuleV2.PKG_NAME_PREFIX)
        }

    @classmethod
    def rebuild_working_set(cls) -> None:
        pkg_resources.working_set = pkg_resources.WorkingSet._build_master()

    @classmethod
    def get_dependency_tree(cls, dists: abc.Iterable[str]) -> abc.Set[str]:
        """
        Returns the full set of all dependencies (both direct and transitive) for the given distributions. Includes the
        distributions themselves.
        If one of the distributions or its dependencies is not installed, it is still included in the set but its dependencies
        are not.

        :param dists: The keys for the distributions to get the dependency tree for.
        """
        # create dict for O(1) lookup
        installed_distributions: abc.Mapping[str, Distribution] = {
            dist_info.key: dist_info for dist_info in pkg_resources.working_set
        }

        def _get_tree_recursive(dists: abc.Iterable[str], acc: abc.Set[str] = frozenset()) -> abc.Set[str]:
            """
            :param acc: Accumulator for requirements that have already been recursed on.
            """
            return reduce(_get_tree_recursive_single, dists, acc)

        def _get_tree_recursive_single(acc: abc.Set[str], dist: str) -> abc.Set[str]:
            if dist in acc:
                return acc

            if dist not in installed_distributions:
                return acc | {dist}

            # recurse on direct dependencies
            return _get_tree_recursive(
                (requirement.key for requirement in installed_distributions[dist].requires()),
                acc=acc | {dist},
            )

        return _get_tree_recursive(dists)


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


class PipUpgradeStrategy(enum.Enum):
    """
    The upgrade strategy used by pip (`--upgrade-strategy` option). Determines upgrade behavior for dependencies of packages to
    upgrade.
    """

    EAGER = "eager"
    ONLY_IF_NEEDED = "only-if-needed"


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
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        allow_pre_releases: bool = False,
        constraints_files: Optional[List[str]] = None,
        requirements_files: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Generate `pip install` command from the given arguments.

        :param python_path: The python interpreter to use in the command
        :param requirements: The requirements that should be installed
        :param paths: Paths to python projects on disk that should be installed in the venv.
        :param index_urls: The Python package repositories to use. When set to None, the system default will be used.
        :param upgrade: Upgrade the specified packages to the latest version.
        :param upgrade_strategy: The upgrade strategy to use for requirements' dependencies.
        :param allow_pre_releases: Allow the installation of packages with pre-releases and development versions.
        :param constraints_files: Files that should be passed to pip using the `-c` option.
        :param requirements_files: Files that should be passed to pip using the `-r` option.
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
            *(["--upgrade", "--upgrade-strategy", upgrade_strategy.value] if upgrade else []),
            *(["--pre"] if allow_pre_releases else []),
            *chain.from_iterable(["-c", f] for f in constraints_files),
            *chain.from_iterable(["-r", f] for f in requirements_files),
            *(str(requirement) for requirement in requirements),
            *chain.from_iterable(["-e", path.path] if path.editable else [path.path] for path in local_paths),
            *index_args,
        ]

    @classmethod
    def compose_uninstall_command(cls, python_path: str, pkg_names: Sequence[str]) -> List[str]:
        """
        Return the pip command to uninstall the given python packages.

        :param python_path: The python interpreter to use in the command.
        :param pkg_names: The names of the python packages that should be uninstalled.
        """
        return [python_path, "-m", "pip", "uninstall", "-y", *pkg_names]

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
            # we disable pip-version check to prevent the json format from getting other output
            # deeply confusing issue: https://github.com/pypa/pip/issues/10715
            *(["--disable-pip-version-check", "--no-python-version-warning", "--format", format.value] if format else []),
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
            if not self.env_path:
                raise ValueError("The env_path cannot be an empty string.")
        else:
            assert python_path is not None
            self.python_path = python_path
            self.env_path = self.get_env_path_for_python_path(self.python_path)
            if not self.python_path:
                raise ValueError("The python_path cannot be an empty string.")
        self.site_packages_dir: str = self.get_site_dir_for_env_path(self.env_path)

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

    @classmethod
    def get_site_dir_for_env_path(cls, env_path: str) -> str:
        """
        Return the site directory for a given venv directory.
        """
        return (
            os.path.join(env_path, "Lib", "site-packages")
            if sys.platform == "win32"
            else os.path.join(
                env_path, "lib", "python%s" % ".".join(str(digit) for digit in sys.version_info[:2]), "site-packages"
            )
        )

    def _run_pip_install_command(
        self,
        python_path: str,
        requirements: Optional[List[Requirement]] = None,
        paths: Optional[List[LocalPackagePath]] = None,
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        allow_pre_releases: bool = False,
        constraints_files: Optional[List[str]] = None,
        requirements_files: Optional[List[str]] = None,
    ) -> None:
        cmd: List[str] = PipCommandBuilder.compose_install_command(
            python_path=python_path,
            requirements=requirements,
            paths=paths,
            index_urls=index_urls,
            upgrade=upgrade,
            upgrade_strategy=upgrade_strategy,
            allow_pre_releases=allow_pre_releases,
            constraints_files=constraints_files,
            requirements_files=requirements_files,
        )

        sub_env = os.environ.copy()

        # if index_urls are set, only use those. Otherwise, use the one from the environment
        if index_urls is not None:
            # setting this env_var to os.devnull disables the loading of all pip configuration files
            sub_env["PIP_CONFIG_FILE"] = os.devnull
        if index_urls is not None and "PIP_EXTRA_INDEX_URL" in sub_env:
            del sub_env["PIP_EXTRA_INDEX_URL"]
        if index_urls is not None and "PIP_INDEX_URL" in sub_env:
            del sub_env["PIP_INDEX_URL"]

        def create_log_content_files(title: str, files: List[str]) -> List[str]:
            """
            Log the content of a list of files with indentations in the following format:

            Content of [title]:
                [files[0]]:
                    line 1 in files[0]
                [files[1]]:
                    line 1 in files[1]
                    line 2 in files[1]
                    line 3 in files[1]
                    ...
                [files[2]]:
                ...

            this function will skip empty lines in files
            """
            log_msg: List[str] = [f"Content of {title}:\n"]
            indentation: str = "    "
            for file in files:
                log_msg.append(indent(file + ":\n", indentation))
                with open(file) as f:
                    for line in f:
                        if line.strip():
                            log_msg.append(indent(line.strip() + "\n", 2 * indentation))
            return log_msg

        log_msg: List[str] = []
        if requirements_files:
            log_msg.extend(create_log_content_files("requirements files", requirements_files))
        if constraints_files:
            log_msg.extend(create_log_content_files("constraints files", constraints_files))
        log_msg.append("Pip command: " + " ".join(cmd))
        LOGGER_PIP.debug("".join(log_msg).strip())
        return_code, full_output = CommandRunner(LOGGER_PIP).run_command_and_stream_output(cmd, env_vars=sub_env)

        if return_code != 0:
            not_found: List[str] = []
            conflicts: List[str] = []
            for line in full_output:
                m = re.search(r"No matching distribution found for ([\S]+)", line)
                if m:
                    # Add missing package name to not_found list
                    not_found.append(m.group(1))

                if "versions have conflicting dependencies" in line:
                    conflicts.append(line)
            if not_found:
                raise PackageNotFound("Packages %s were not found in the given indexes." % ", ".join(not_found))
            if conflicts:
                raise ConflictingRequirements("\n".join(conflicts))
            raise PipInstallError(
                f"Process {cmd} exited with return code {return_code}. "
                "Increase the verbosity level with the -v option for more information."
            )

    @classmethod
    def get_env_path_for_python_path(cls, python_path: str) -> str:
        """
        For a given path to a python binary, return the path to the venv directory.
        """
        return os.path.dirname(os.path.dirname(python_path))

    def get_installed_packages(self, only_editable: bool = False) -> Dict[str, version.Version]:
        """
        Return a list of all installed packages in the site-packages of a python interpreter.

        :param only_editable: List only packages installed in editable mode.
        :return: A dict with package names as keys and versions as values
        """
        cmd = PipCommandBuilder.compose_list_command(self.python_path, format=PipListFormat.json, only_editable=only_editable)
        output = CommandRunner(LOGGER_PIP).run_command_and_log_output(cmd, stderr=subprocess.DEVNULL, env=os.environ.copy())
        return {r["name"]: version.Version(r["version"]) for r in json.loads(output)}

    def install_from_index(
        self,
        requirements: List[Requirement],
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
        constraint_files: Optional[List[str]] = None,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
    ) -> None:
        if len(requirements) == 0:
            raise Exception("install_from_index requires at least one requirement to install")
        constraint_files = constraint_files if constraint_files is not None else []
        inmanta_requirements = self._get_requirements_on_inmanta_package()
        self._run_pip_install_command(
            python_path=self.python_path,
            requirements=[*requirements, *inmanta_requirements],
            index_urls=index_urls,
            upgrade=upgrade,
            allow_pre_releases=allow_pre_releases,
            constraints_files=[*constraint_files],
            upgrade_strategy=upgrade_strategy,
        )

    def install_from_source(self, paths: List[LocalPackagePath], constraint_files: Optional[List[str]] = None) -> None:
        """
        Install one or more packages from source. Any path arguments should be local paths to a package directory or wheel.
        """
        if len(paths) == 0:
            raise Exception("install_from_source requires at least one package to install")
        constraint_files = constraint_files if constraint_files is not None else []
        inmanta_requirements = self._get_requirements_on_inmanta_package()
        self._run_pip_install_command(
            python_path=self.python_path,
            paths=paths,
            constraints_files=constraint_files,
            requirements=inmanta_requirements,
        )

    @classmethod
    def get_protected_inmanta_packages(cls) -> List[str]:
        """
        Returns the list of packages that should not be installed/updated by any operation on a Python environment.
        """
        return [
            # Protect product packages
            "inmanta",
            "inmanta-service-orchestrator",
            # Protect all server extensions
            *(f"inmanta-{ext_name}" for ext_name in InmantaBootloader.get_available_extensions().keys()),
        ]

    @classmethod
    def _get_requirements_on_inmanta_package(cls) -> Sequence[Requirement]:
        """
        Returns the content of the requirement file that should be supplied to each `pip install` invocation
        to make sure that no Inmanta packages gets overridden.
        """
        protected_inmanta_packages: List[str] = cls.get_protected_inmanta_packages()
        workingset: Dict[str, version.Version] = PythonWorkingSet.get_packages_in_working_set()
        return [Requirement.parse(f"{pkg}=={workingset[pkg]}") for pkg in workingset if pkg in protected_inmanta_packages]


class CommandRunner:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def run_command_and_log_output(
        self, cmd: List[str], env: Optional[Dict[str, str]] = None, stderr: Optional[int] = None
    ) -> str:
        output: bytes = b""  # Make sure the var is always defined in the except bodies
        try:
            output = subprocess.check_output(cmd, stderr=stderr, env=env)
        except CalledProcessError as e:
            if e.stderr:
                msg = e.stderr.decode()
            elif e.output:
                msg = e.output.decode()
            else:
                msg = ""
            self.logger.error("%s: %s", cmd, msg)
            raise
        except Exception:
            self.logger.error("%s: %s", cmd, output.decode())
            raise
        else:
            self.logger.debug("%s: %s", cmd, output.decode())
            return output.decode()

    def run_command_and_stream_output(
        self,
        cmd: List[str],
        shell: bool = False,
        timeout: float = 10,
        env_vars: Optional[Mapping[str, str]] = None,
    ) -> Tuple[int, List[str]]:
        """
        Similar to the _run_command_and_log_output method, but here, the output is logged on the fly instead of at the end
        of the sub-process.
        """
        full_output: List[str] = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=shell,
            env=env_vars,
        )
        assert process.stdout is not None  # Make mypy happy
        try:
            for line in process.stdout:
                # Eagerly consume the buffer to avoid a deadlock in case the subprocess fills it entirely.
                output = line.decode().strip()
                full_output.append(output)
                self.logger.debug(output)
        finally:
            process.stdout.close()

        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            return -1, full_output
        else:
            return return_code, full_output


@contextlib.contextmanager
def requirements_txt_file(content: str) -> Iterator[str]:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=True) as fd:
        fd.write(content)
        fd.flush()
        yield fd.name


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

    def are_installed(self, requirements: req_list) -> bool:
        """
        Return True iff the given requirements are installed in this environment.
        """
        return PythonWorkingSet.are_installed(requirements)

    def install_from_index(
        self,
        requirements: List[Requirement],
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
        constraint_files: Optional[List[str]] = None,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
    ) -> None:
        if not upgrade and self.are_installed(requirements):
            return
        try:
            super(ActiveEnv, self).install_from_index(
                requirements, index_urls, upgrade, allow_pre_releases, constraint_files, upgrade_strategy
            )
        finally:
            self.notify_change()

    def install_from_source(self, paths: List[LocalPackagePath], constraint_files: Optional[List[str]] = None) -> None:
        try:
            super().install_from_source(paths, constraint_files)
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
    def _gen_content_requirements_file(cls, requirements_list: Sequence[str]) -> str:
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
            extras = None
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
                    if hasattr(item, "extras") and len(item.extras) > 0:
                        extras = sorted(item.extras)
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

            if extras is not None:
                modules[name]["extras"] = extras

        requirements_file = ""
        for module, info in modules.items():
            version_spec = ""
            markers: str = ""
            extras_spec: str = ""
            if len(info["version"]) > 0:
                version_spec = " " + (", ".join(["%s %s" % (a, b) for a, b in info["version"]]))

            if len(info["markers"]) > 0:
                markers = " ; " + (" and ".join(map(str, info["markers"])))

            if "url" in info:
                module = info["url"]

            if "extras" in info:
                extras_spec = f"[{','.join(info['extras'])}]"

            requirements_file += module + extras_spec + version_spec + markers + "\n"

        return requirements_file

    def install_from_list(
        self,
        requirements_list: Sequence[str],
        *,
        upgrade: bool = False,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
    ) -> None:
        """
        Install requirements from a list of requirement strings. This method uses the Python package repositories
        configured on the host.

        :param requirements_list: List of requirement strings to install.
        :param upgrade: Upgrade requirements to the latest compatible version.
        :param upgrade_strategy: The upgrade strategy to use for requirements' dependencies.
        """
        if not upgrade and self.are_installed(requirements_list):
            # don't fork subprocess if requirements are already met
            return
        try:
            self._install_from_list(requirements_list, upgrade=upgrade, upgrade_strategy=upgrade_strategy)
        finally:
            self.notify_change()

    def _install_from_list(
        self,
        requirements_list: Sequence[str],
        *,
        upgrade: bool = False,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
    ) -> None:
        """
        This method differs from the `install_from_index()` method in the sense that it calls
        `_gen_content_requirements_file()`, which rewrites the requirements from pep440 format to a format that pip understands.
        This method is maintained for V1 modules only: V2 modules do not require this conversion. It is currently used for both
        v1 and v2 for consistency but it can be substituted by `install_from_index` once V1 support is removed.
        """
        content_requirements_file = self._gen_content_requirements_file(requirements_list)
        with requirements_txt_file(content=content_requirements_file) as requirements_file:
            inmanta_requirements = self._get_requirements_on_inmanta_package()
            try:
                self._run_pip_install_command(
                    python_path=self.python_path,
                    requirements_files=[requirements_file],
                    requirements=inmanta_requirements,
                    upgrade=upgrade,
                    upgrade_strategy=upgrade_strategy,
                )
            except Exception:
                LOGGER.info("requirements:\n%s", content_requirements_file)
                raise

    @classmethod
    def get_constraint_violations_for_check(
        cls,
        strict_scope: Optional[Pattern[str]] = None,
        constraints: Optional[List[Requirement]] = None,
    ) -> Tuple[Set[VersionConflict], Set[VersionConflict]]:
        """
        Return the constraint violations that exist in this venv. Returns a tuple of non-strict and strict violations,
        in that order.
        """

        class OwnedRequirement(NamedTuple):
            requirement: Requirement
            owner: Optional[str] = None

            def is_owned_by(self, owners: abc.Set[str]) -> bool:
                return self.owner is None or self.owner in owners

        # all requirements of all packages installed in this environment
        installed_constraints: abc.Set[OwnedRequirement] = frozenset(
            OwnedRequirement(requirement, dist_info.key)
            for dist_info in pkg_resources.working_set
            for requirement in dist_info.requires()
        )
        inmanta_constraints: abc.Set[OwnedRequirement] = frozenset(
            OwnedRequirement(r, owner="inmanta-core") for r in cls._get_requirements_on_inmanta_package()
        )
        extra_constraints: abc.Set[OwnedRequirement] = frozenset(
            (OwnedRequirement(r) for r in constraints) if constraints is not None else []
        )

        all_constraints: abc.Set[OwnedRequirement] = installed_constraints | inmanta_constraints | extra_constraints

        full_strict_scope: abc.Set[str] = PythonWorkingSet.get_dependency_tree(
            chain(
                (
                    []
                    if strict_scope is None
                    else (dist_info.key for dist_info in pkg_resources.working_set if strict_scope.fullmatch(dist_info.key))
                ),
                (requirement.requirement.key for requirement in inmanta_constraints),
                (requirement.requirement.key for requirement in extra_constraints),
            )
        )

        installed_versions: Dict[str, version.Version] = PythonWorkingSet.get_packages_in_working_set()

        constraint_violations: set[VersionConflict] = set()
        constraint_violations_strict: set[VersionConflict] = set()
        for c in all_constraints:
            requirement = c.requirement
            if (requirement.key not in installed_versions or str(installed_versions[requirement.key]) not in requirement) and (
                not requirement.marker or (requirement.marker and requirement.marker.evaluate())
            ):
                version_conflict = VersionConflict(
                    requirement=requirement,
                    installed_version=installed_versions.get(requirement.key, None),
                    owner=c.owner,
                )
                if c.is_owned_by(full_strict_scope):
                    constraint_violations_strict.add(version_conflict)
                else:
                    constraint_violations.add(version_conflict)

        return constraint_violations, constraint_violations_strict

    @classmethod
    def check(
        cls,
        strict_scope: Optional[Pattern[str]] = None,
        constraints: Optional[List[Requirement]] = None,
    ) -> None:
        """
        Check this Python environment for incompatible dependencies in installed packages.

        :param strict_scope: A full pattern representing the package names that are considered in scope for the installed
            packages compatibility check. strict_scope packages' dependencies will also be considered for conflicts.
            Any conflicts for packages that do not match this pattern will only raise a warning.
            The pattern is matched against an all-lowercase package name.
        :param constraints: In addition to checking for compatibility within the environment, also verify that the environment's
            packages meet the given constraints. All listed packages are expected to be installed.
        """
        constraint_violations, constraint_violations_strict = cls.get_constraint_violations_for_check(strict_scope, constraints)

        if len(constraint_violations_strict) != 0:
            raise ConflictingRequirements(
                "",  # The exception has a detailed list of constraint_violations, so it can make its own message
                constraint_violations_strict,
            )

        for violation in constraint_violations:
            LOGGER.warning("%s", violation)

    @classmethod
    def check_legacy(cls, in_scope: Pattern[str], constraints: Optional[List[Requirement]] = None) -> bool:
        """
        Check this Python environment for incompatible dependencies in installed packages. This method is a legacy method
        in the sense that it has been replaced with a more correct check defined in self.check(). This method is invoked
        when the `--no-strict-deps-check` commandline option is provided.

        :param in_scope: A full pattern representing the package names that are considered in scope for the installed packages'
            compatibility check. Only in scope packages' dependencies will be considered for conflicts. The pattern is matched
            against an all-lowercase package name.
        :param constraints: In addition to checking for compatibility within the environment, also verify that the environment's
            packages meet the given constraints. All listed packages are expected to be installed.
        :return: True iff the check succeeds.
        """
        constraint_violations_non_strict, constraint_violations_strict = cls.get_constraint_violations_for_check(
            in_scope, constraints
        )

        dist_info: DistInfoDistribution
        # add all requirements of all in scope packages installed in this environment
        all_constraints: Set[Requirement] = set(constraints if constraints is not None else []).union(
            requirement
            for dist_info in pkg_resources.working_set
            if in_scope.fullmatch(dist_info.key)
            for requirement in dist_info.requires()
        )

        installed_versions: Dict[str, version.Version] = PythonWorkingSet.get_packages_in_working_set()
        constraint_violations: Set[VersionConflict] = set(
            VersionConflict(constraint, installed_versions.get(constraint.key, None))
            for constraint in all_constraints
            if constraint.key not in installed_versions or str(installed_versions[constraint.key]) not in constraint
        )

        all_violations = constraint_violations_non_strict | constraint_violations_strict | constraint_violations
        for violation in all_violations:
            LOGGER.warning("%s", violation)

        return len(constraint_violations) == 0

    @classmethod
    def get_module_file(cls, module: str) -> Optional[Tuple[Optional[str], Loader]]:
        """
        Get the location of the init file for a Python module within the active environment. Returns the file path as observed
        by Python. For editable installs, this may or may not be a symlink to the actual location (see implementation
        mechanisms in setuptools docs: https://setuptools.pypa.io/en/latest/userguide/development_mode.html).

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
                    """
                    A V2 module was installed in this virtual environment, but the inmanta_plugins package was already
                    loaded before this venv was activated. Reload the inmanta_plugins package to ensure that all V2 modules
                    installed in this virtual environment are discovered correctly.

                    This is required to cover the following scenario:

                        * Two venvs are stacked on top of each other. The parent venv contains the inmanta-core package and
                          the subvenv is empty.
                        * The inmanta_plugins package gets loaded before a V2 module is installed in the subvenv. This way,
                          the module object in sys.modules, doesn't have the site dir of the subvenv in its
                          submodule_search_locations. This field caches where the loader should look for the namespace packages
                          that are part of the inmanta_plugins namespace.
                        * When a V2 module gets installed in the subvenv now, the loader will not find the newly installed V2
                          module, because it's not considering the site dir of the subvenv.

                    The above-mentioned scenario can only be triggered by test cases, because:
                        1) The compiler venv was removed. As such, no new venv are activated on the fly by production code
                           paths.
                        2) The compiler service creates a new subvenv for each inmanta environment, but the inmanta commands
                           are executed in a subprocess.
                    """
                    importlib.reload(mod)
        PythonWorkingSet.rebuild_working_set()


process_env: ActiveEnv = ActiveEnv(python_path=sys.executable)
"""
Singleton representing the Python environment this process is running in.
"""


@stable_api
def mock_process_env(*, python_path: Optional[str] = None, env_path: Optional[str] = None) -> None:
    """
    Overrides the process environment information. This forcefully sets the environment that is recognized as the outer Python
    environment. This function should only be called when a Python environment has been set up dynamically and this environment
    should be treated as if this process was spawned from it, and even then with great care.

    :param python_path: The path to the python binary. Only one of `python_path` and `env_path` should be set.
    :param env_path: The path to the python environment directory. Only one of `python_path` and `env_path` should be set.
    """
    process_env.__init__(python_path=python_path, env_path=env_path)  # type: ignore


@stable_api
class VirtualEnv(ActiveEnv):
    """
    Creates and uses a virtual environment for this process. This virtualenv inherits from the previously active one.
    """

    def __init__(self, env_path: str) -> None:
        super(VirtualEnv, self).__init__(env_path=env_path)
        self.env_path: str = env_path
        self.virtual_python: Optional[str] = None
        self._using_venv: bool = False
        self._parent_python: Optional[str] = None
        self._path_pth_file = os.path.join(self.site_packages_dir, "inmanta-inherit-from-parent-venv.pth")

    def exists(self) -> bool:
        """
        Returns True iff the venv exists on disk.
        """
        return os.path.exists(self.python_path) and os.path.exists(self._path_pth_file)

    def init_env(self) -> None:
        """
        Initialize the virtual environment.
        """
        self._parent_python = sys.executable
        LOGGER.info("Using virtual environment at %s", self.env_path)

        # check if the virtual env exists
        if os.path.isdir(self.env_path) and os.listdir(self.env_path):
            # Make sure the venv hosts the same python version as the running process
            if sys.platform.startswith("linux"):
                # Check if the python binary exists in the environment's bin directory
                if not os.path.exists(self.python_path):
                    raise VenvActivationFailedError(
                        msg=f"Unable to use virtualenv at {self.env_path} as no Python installation exists."
                    )
                # On linux based systems, the python version is in the path to the site packages dir:
                if not os.path.exists(self.site_packages_dir):
                    raise VenvActivationFailedError(
                        msg=f"Unable to use virtualenv at {self.env_path} because its Python version "
                        "is different from the Python version of this process."
                    )
            else:
                # On other distributions a more costly check is required:
                # Get version as a (major, minor) tuple for the venv and the running process
                venv_python_version = (
                    subprocess.check_output([self.python_path, "--version"]).decode("utf-8").strip().split()[1]
                )
                venv_python_version = tuple(map(int, venv_python_version.split(".")))[:2]

                running_process_python_version = sys.version_info[:2]

                if venv_python_version != running_process_python_version:
                    raise VenvActivationFailedError(
                        msg=f"Unable to use virtualenv at {self.env_path} because its Python version "
                        "is different from the Python version of this process."
                    )

        else:
            path = os.path.realpath(self.env_path)
            try:
                venv.create(path, clear=True, with_pip=False)
                self._write_pip_binary()
                self._write_pth_file()
            except CalledProcessError as e:
                raise VenvCreationFailedError(msg=f"Unable to create new virtualenv at {self.env_path} ({e.stdout.decode()})")
            except Exception:
                raise VenvCreationFailedError(msg=f"Unable to create new virtualenv at {self.env_path}")
            LOGGER.debug("Created a new virtualenv at %s", self.env_path)

        if not os.path.exists(self._path_pth_file):
            # Venv was created using an older version of Inmanta -> Update pip binary and set sitecustomize.py file
            self._write_pip_binary()
            self._write_pth_file()

        # set the path to the python and the pip executables
        self.virtual_python = self.python_path

    def is_using_virtual_env(self) -> bool:
        return self._using_venv

    def use_virtual_env(self) -> None:
        """
        Activate the virtual environment.
        """
        if self._using_venv:
            raise Exception(f"Already using venv {self.env_path}.")
        if not self.env_path:
            raise Exception("The env_path cannot be an empty string.")

        self.init_env()
        self._activate_that()
        mock_process_env(python_path=self.python_path)

        # patch up pkg
        self.notify_change()

        self._using_venv = True

    def _write_pip_binary(self) -> None:
        """
        write out a "stub" pip binary so that pip list works in the virtual env.
        """
        pip_path = os.path.join(self.env_path, "bin", "pip")

        with open(pip_path, "w", encoding="utf-8") as fd:
            fd.write(
                """#!/usr/bin/env bash
source "$(dirname "$0")/activate"
python -m pip $@
                """.strip()
            )
        os.chmod(pip_path, 0o755)

    def _write_pth_file(self) -> None:
        """
        Write an inmanta-inherit-from-parent-venv.pth file to the venv to ensure that an activation of this venv will also
        activate the parent venv. The site directories of the parent venv should appear later in sys.path than the ones of
        this venv.
        """
        site_dir_strings: List[str] = ['"' + p.replace('"', r"\"") + '"' for p in list(sys.path)]
        add_site_dir_statements: str = "\n".join(
            [f"site.addsitedir({p}) if {p} not in sys.path else None" for p in site_dir_strings]
        )
        script = f"""
import os
import site
import sys


# Ensure inheritance from all parent venvs + process their .pth files
{add_site_dir_statements}
        """
        script_as_oneliner = "; ".join(
            [line for line in script.split("\n") if line.strip() and not line.strip().startswith("#")]
        )
        with open(self._path_pth_file, "w", encoding="utf-8") as fd:
            fd.write(script_as_oneliner)

    def _update_sys_path(self) -> None:
        """
        Updates sys.path by adding self.site_packages_dir. This method ensures
        that .pth files are processed.
        """
        prev_sys_path = list(sys.path)
        site.addsitedir(self.site_packages_dir)
        # Move the added items to the front of the path
        new_sys_path = [e for e in list(sys.path) if e not in prev_sys_path]
        new_sys_path += prev_sys_path
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

    def install_from_index(
        self,
        requirements: List[Requirement],
        index_urls: Optional[List[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
        constraint_files: Optional[List[str]] = None,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
    ) -> None:
        if not self._using_venv:
            raise Exception(f"Not using venv {self.env_path}. use_virtual_env() should be called first.")
        super(VirtualEnv, self).install_from_index(
            requirements, index_urls, upgrade, allow_pre_releases, constraint_files, upgrade_strategy
        )

    def install_from_source(self, paths: List[LocalPackagePath], constraint_files: Optional[List[str]] = None) -> None:
        if not self._using_venv:
            raise Exception(f"Not using venv {self.env_path}. use_virtual_env() should be called first.")
        super(VirtualEnv, self).install_from_source(paths, constraint_files)

    def install_from_list(
        self,
        requirements_list: Sequence[str],
        *,
        upgrade: bool = False,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
    ) -> None:
        if not self._using_venv:
            raise Exception(f"Not using venv {self.env_path}. use_virtual_env() should be called first.")
        super(VirtualEnv, self).install_from_list(requirements_list, upgrade=upgrade, upgrade_strategy=upgrade_strategy)


class VenvCreationFailedError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg


class VenvActivationFailedError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg
