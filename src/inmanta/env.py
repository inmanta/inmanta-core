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

import asyncio
import enum
import importlib.metadata
import importlib.util
import json
import logging
import os
import re
import site
import subprocess
import sys
import tempfile
import typing
import venv
from collections import abc
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import reduce
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from importlib.metadata import Distribution, distribution, distributions
from itertools import chain
from subprocess import CalledProcessError
from textwrap import indent
from typing import Callable, Optional, Tuple, TypeVar

import inmanta.util
import packaging.requirements
import packaging.utils
import packaging.version
from inmanta import const
from inmanta.ast import CompilerException
from inmanta.data.model import LEGACY_PIP_DEFAULT, PipConfig
from inmanta.server.bootloader import InmantaBootloader
from inmanta.stable_api import stable_api
from inmanta.util import parse_requirement, strtobool
from packaging.utils import NormalizedName, canonicalize_name

LOGGER = logging.getLogger(__name__)
LOGGER_PIP = logging.getLogger("inmanta.pip")  # Use this logger to log pip commands or data related to pip commands.

if typing.TYPE_CHECKING:
    from _typeshed.importlib import MetaPathFinderProtocol, PathEntryFinderProtocol


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

    requirement: inmanta.util.CanonicalRequirement
    installed_version: Optional[packaging.version.Version] = None
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

    def __init__(self, message: str, conflicts: Optional[set[VersionConflict]] = None):
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
        for current_conflict in sorted(self.conflicts, key=lambda x: x.requirement.name):
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


req_list = TypeVar("req_list", Sequence[str], Sequence[inmanta.util.CanonicalRequirement])


class PythonWorkingSet:
    @classmethod
    def _get_as_requirements_type(cls, requirements: req_list) -> Sequence[inmanta.util.CanonicalRequirement]:
        """
        Convert requirements from Union[Sequence[str], Sequence[Requirement]] to Sequence[Requirement]
        """
        if isinstance(requirements[0], str):
            return inmanta.util.parse_requirements(requirements)
        else:
            return requirements

    @classmethod
    def are_installed(cls, requirements: req_list) -> bool:
        """
        Return True iff the given requirements are installed in this workingset.
        """
        if not requirements:
            return True
        installed_packages: dict[NormalizedName, packaging.version.Version] = cls.get_packages_in_working_set()

        # All thing to do, requirement + extra if added via extra
        worklist: list[Tuple[inmanta.util.CanonicalRequirement, Optional[str]]] = []
        seen_requirements: set[inmanta.util.CanonicalRequirement] = set()

        reqs_as_requirements: Sequence[inmanta.util.CanonicalRequirement] = cls._get_as_requirements_type(requirements)
        for r in reqs_as_requirements:
            worklist.append((r, None))

        while worklist:
            r, contained_in_extra = worklist.pop()

            if r in seen_requirements:
                continue
            seen_requirements.add(r)

            # Requirements created by the `Distribution.requires()` method have the extra, the Requirement was created
            # from,
            # set as a marker. The line below makes sure that the "extra" marker matches. The marker is not set by
            # `Distribution.requires()` when the package is installed in editable mode, but setting it always doesn't make
            # the marker evaluation fail.
            environment_marker_evaluation = {"extra": contained_in_extra} if contained_in_extra else None
            if r.marker and not r.marker.evaluate(environment=environment_marker_evaluation):
                # The marker of the requirement doesn't apply on this environment
                continue

            name = NormalizedName(r.name)  # requirement is normalized
            if name not in installed_packages or not r.specifier.contains(installed_packages[name], prereleases=True):
                return False

            if r.extras:
                # if we have extr'as these may not have been installed!
                # We have to recurse for them!
                for extra in r.extras:
                    found_distribution: Optional[Distribution] = distribution(name)
                    if found_distribution is None:
                        return False

                    environment_marker_evaluation = {"extra": extra}
                    all_requires: list[inmanta.util.CanonicalRequirement] = [
                        inmanta.util.parse_requirement(requirement) for requirement in (found_distribution.requires or [])
                    ]
                    pkgs_required_by_extra: list[inmanta.util.CanonicalRequirement] = [
                        requirement
                        for requirement in all_requires
                        if requirement.marker and requirement.marker.evaluate(environment_marker_evaluation)
                    ]
                    for req in pkgs_required_by_extra:
                        worklist.append((req, extra))
        return True

    @classmethod
    def get_packages_in_working_set(cls, inmanta_modules_only: bool = False) -> dict[NormalizedName, packaging.version.Version]:
        """
        Return all package names (under the canonicalized form) present on the sys.path with their version

        :param inmanta_modules_only: Only return inmanta modules from the working set
        """
        return {
            name: packaging.version.Version(dist_info.version)
            for name, dist_info in cls.get_dist_in_working_set().items()
            if not inmanta_modules_only or name.startswith(const.MODULE_PKG_NAME_PREFIX)
        }

    @classmethod
    def get_dist_in_working_set(cls) -> dict[NormalizedName, Distribution]:
        """
        Return all packages (with the canonicalized name) present on the sys.path
        """
        return {
            packaging.utils.canonicalize_name(dist_info.name): dist_info
            for dist_info in reversed(list(distributions()))  # make sure we get the first entry for every name
        }

    @classmethod
    def get_dependency_tree(cls, dists: abc.Iterable[NormalizedName]) -> abc.Set[NormalizedName]:
        """
        Returns the full set of all dependencies (both direct and transitive) for the given distributions. Includes the
        distributions themselves.
        If one of the distributions or its dependencies is not installed, it is still included in the set but its dependencies
        are not.

        extras are ignored

        :param dists: The keys for the distributions to get the dependency tree for.
        """
        # create dict for O(1) lookup
        installed_distributions: abc.Mapping[NormalizedName, Distribution] = PythonWorkingSet.get_dist_in_working_set()

        def _get_tree_recursive(
            dists: abc.Iterable[NormalizedName], acc: abc.Set[NormalizedName] = frozenset()
        ) -> abc.Set[NormalizedName]:
            """
            :param acc: Accumulator for requirements that have already been recursed on.
            """
            return reduce(_get_tree_recursive_single, dists, acc)

        def _get_tree_recursive_single(acc: abc.Set[NormalizedName], dist: NormalizedName) -> abc.Set[NormalizedName]:
            if dist in acc:
                return acc

            if dist not in installed_distributions:
                return acc | {dist}

            # recurse on direct dependencies
            return _get_tree_recursive(
                (
                    requirement.name
                    for requirement in (
                        parse_requirement(raw_requirement) for raw_requirement in (installed_distributions[dist].requires or [])
                    )
                    if (requirement.marker is None or requirement.marker.evaluate())
                ),
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


def assert_pip_has_source(pip_config: PipConfig, reason: str) -> None:
    """Ensure this index has a valid package source, otherwise raise exception"""
    # placed here and not in pip_config to avoid import loop
    if not pip_config.has_source():
        raise PackageNotFound(
            f"Attempting to install {reason} but pip is not configured. Add the relevant pip "
            f"indexes to the project config file. e.g. to set PyPi as pip index, add the following "
            "to `project.yml`:"
            "\npip:"
            "\n  index_url: https://pypi.org/simple"
            "\nAnother option is to set `pip.use_system_config = true` to use the system's pip config."
        )


class PipCommandBuilder:
    """
    Class used to compose pip commands.
    """

    @classmethod
    def compose_uninstall_command(cls, python_path: str, pkg_names: Sequence[str]) -> list[str]:
        """
        Return the pip command to uninstall the given python packages.

        :param python_path: The python interpreter to use in the command.
        :param pkg_names: The names of the python packages that should be uninstalled.
        """
        return [python_path, "-m", "pip", "uninstall", "-y", *pkg_names]

    @classmethod
    def compose_list_command(
        cls, python_path: str, format: Optional[PipListFormat] = None, only_editable: bool = False
    ) -> list[str]:
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
            *(["--disable-pip-version-check", "--format", format.value] if format else []),
            *(["--editable"] if only_editable else []),
        ]


class Pip(PipCommandBuilder):
    """Class to handle interactions with pip"""

    @classmethod
    def run_pip_install_command_from_config(
        cls,
        python_path: str,
        config: PipConfig,
        requirements: Optional[Sequence[packaging.requirements.Requirement]] = None,
        requirements_files: Optional[list[str]] = None,
        upgrade: bool = False,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        constraints_files: Optional[list[str]] = None,
        paths: Optional[list[LocalPackagePath]] = None,
    ) -> None:
        """
        Perform a pip install according to the given config

        :param python_path: the python path to use
        :param config: the pip config to use

        :param requirements: which requirements to install
        :param requirements_files: which requirements_files to install (-r)
        :param paths: which paths to install

        :param constraints_files: pass along the following constraint files

        :param upgrade: make pip do an upgrade
        :param upgrade_strategy: what upgrade strategy to use
        """

        cmd, constraints_files_clean, requirements_files_clean, sub_env = cls._prepare_pip_install_command(
            python_path,
            config,
            requirements,
            requirements_files,
            upgrade,
            upgrade_strategy,
            constraints_files,
            paths,
        )

        cls.run_pip(cmd, sub_env, constraints_files_clean, requirements_files_clean)

    @classmethod
    async def async_run_pip_install_command_from_config(
        cls,
        python_path: str,
        config: PipConfig,
        requirements: Optional[Sequence[packaging.requirements.Requirement]] = None,
        requirements_files: Optional[list[str]] = None,
        upgrade: bool = False,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        constraints_files: Optional[list[str]] = None,
        paths: Optional[list[LocalPackagePath]] = None,
    ) -> None:
        """
        Perform a pip install according to the given config

        :param python_path: the python path to use
        :param config: the pip config to use

        :param requirements: which requirements to install
        :param requirements_files: which requirements_files to install (-r)
        :param paths: which paths to install

        :param constraints_files: pass along the following constraint files

        :param upgrade: make pip do an upgrade
        :param upgrade_strategy: what upgrade strategy to use
        """

        cmd, constraints_files_clean, requirements_files_clean, sub_env = cls._prepare_pip_install_command(
            python_path,
            config,
            requirements,
            requirements_files,
            upgrade,
            upgrade_strategy,
            constraints_files,
            paths,
        )
        await cls.async_run_pip(cmd, sub_env, constraints_files_clean, requirements_files_clean)

    @classmethod
    def run_pip_download_command(
        cls,
        python_path: str,
        dependencies: Sequence[inmanta.util.CanonicalRequirement],
        output_dir: str,
        constraints: Sequence[inmanta.util.CanonicalRequirement] | None = None,
        pip_config: PipConfig | None = None,
        no_deps: bool = False,
        no_binary: str | None = None,
    ) -> None:
        if not dependencies:
            return

        index_args: list[str]
        env_vars: dict[str, str]
        if pip_config:
            index_args = pip_config.get_index_args()
            env_vars = pip_config.get_environment_variables()
        else:
            index_args = []
            env_vars = os.environ.copy()

        cmd = [python_path, "-m", "pip", "download"]
        if index_args:
            cmd.extend(index_args)
        if no_deps:
            cmd.append("--no-deps")
        if no_binary:
            cmd.extend(["--no-binary", no_binary])
        with tempfile.NamedTemporaryFile() as fd:
            if constraints:
                fd.write("\n".join(str(c) for c in constraints).encode())
                fd.seek(0)
                cmd.extend(["-c", fd.name])
            if dependencies:
                cmd.extend([str(r) for r in dependencies])
            cls.run_pip(cmd, env=env_vars, cwd=output_dir, constraints_files=[fd.name])

    @classmethod
    def _prepare_pip_install_command(
        cls,
        python_path: str,
        config: PipConfig,
        requirements: Optional[Sequence[packaging.requirements.Requirement]] = None,
        requirements_files: Optional[list[str]] = None,
        upgrade: bool = False,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        constraints_files: Optional[list[str]] = None,
        paths: Optional[list[LocalPackagePath]] = None,
    ) -> Tuple[list[str], list[str], list[str], dict[str, str]]:
        # What
        requirements = requirements if requirements is not None else []
        clean_requirements_files = requirements_files if requirements_files is not None else []
        paths = paths if paths is not None else []
        local_paths: Iterator[LocalPackagePath] = (
            # make sure we only try to install from a local source: add leading `./` and trailing `/` to explicitly tell pip
            # we're pointing to a local directory.
            LocalPackagePath(path=os.path.join(".", path.path, ""), editable=path.editable)
            for path in paths
        )
        install_args = [
            *(str(requirement) for requirement in requirements),
            *chain.from_iterable(["-r", f] for f in clean_requirements_files),
            *chain.from_iterable(["-e", path.path] if path.editable else [path.path] for path in local_paths),
        ]
        # From where
        if paths:
            # For local installs, we allow not having an index set.
            pass
        else:
            # All others need an index
            assert_pip_has_source(config, "'" + " ".join(install_args) + "'")
        index_args: list[str] = config.get_index_args()
        clean_constraints_files = constraints_files if constraints_files is not None else []
        # Command
        cmd = [
            python_path,
            "-m",
            "pip",
            "install",
            *(["--upgrade", "--upgrade-strategy", upgrade_strategy.value] if upgrade else []),
            *(["--pre"] if config.pre else []),
            *chain.from_iterable(["-c", f] for f in clean_constraints_files),
            *install_args,
            *index_args,
        ]
        # ISOLATION!
        sub_env = config.get_environment_variables()
        return cmd, clean_constraints_files, clean_requirements_files, sub_env

    @classmethod
    def run_pip(
        cls,
        cmd: list[str],
        env: dict[str, str],
        constraints_files: list[str] | None = None,
        requirements_files: list[str] | None = None,
        cwd: str | None = None,
    ) -> None:
        if constraints_files is None:
            constraints_files = []
        if requirements_files is None:
            requirements_files = []
        cls._log_before_run(cmd, constraints_files, requirements_files)
        return_code, full_output = CommandRunner(LOGGER_PIP).run_command_and_stream_output(cmd, env_vars=env, cwd=cwd)
        cls._process_return(cmd, env, full_output, return_code)

    @classmethod
    async def async_run_pip(
        cls, cmd: list[str], env: dict[str, str], constraints_files: list[str], requirements_files: list[str]
    ) -> None:
        cls._log_before_run(cmd, constraints_files, requirements_files)
        return_code, full_output = await CommandRunner(LOGGER_PIP).async_run_command_and_stream_output(cmd, env_vars=env)
        cls._process_return(cmd, env, full_output, return_code)

    @classmethod
    def _log_before_run(cls, cmd: list[str], constraints_files: list[str], requirements_files: list[str]) -> None:
        def create_log_content_files(title: str, files: list[str]) -> list[str]:
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
            log_msg: list[str] = [f"Content of {title}:\n"]
            indentation: str = "    "
            for file in files:
                log_msg.append(indent(file + ":\n", indentation))
                with open(file) as f:
                    for line in f:
                        if line.strip():
                            log_msg.append(indent(line.strip() + "\n", 2 * indentation))
            return log_msg

        log_msg: list[str] = []
        if requirements_files:
            log_msg.extend(create_log_content_files("requirements files", requirements_files))
        if constraints_files:
            log_msg.extend(create_log_content_files("constraints files", constraints_files))
        log_msg.append("Pip command: " + " ".join(cmd))
        LOGGER_PIP.debug("".join(log_msg).strip())

    @classmethod
    def _process_return(cls, cmd: list[str], env: dict[str, str], full_output: list[str], return_code: int) -> None:
        if return_code != 0:
            not_found: list[str] = []
            conflicts: list[str] = []
            indexes: str = ""
            for line in full_output:
                m = re.search(r"No matching distribution found for ([\S]+)", line)
                if m:
                    # Add missing package name to not_found list
                    not_found.append(m.group(1))

                if "versions have conflicting dependencies" in line:
                    conflicts.append(line)
                # Get the indexes line from full_output
                # This is not printed when not using any index or when only using PyPi
                if "Looking in indexes:" in line:
                    indexes = line
            if not_found:
                no_index: bool = "--no-index" in cmd or strtobool(env.get("PIP_NO_INDEX", "false"))
                if no_index:
                    msg = "Packages %s were not found. No indexes were used." % ", ".join(not_found)
                elif indexes:
                    msg = "Packages %s were not found in the given indexes. (%s)" % (", ".join(not_found), indexes)
                else:
                    msg = "Packages %s were not found at PyPI." % ", ".join(not_found)
                raise PackageNotFound(msg)
            if conflicts:
                raise ConflictingRequirements("\n".join(conflicts))
            raise PipInstallError(
                f"Process {cmd} exited with return code {return_code}. "
                "Increase the verbosity level with the -v option for more information."
            )


class PythonEnvironment:
    """
    A generic Python environment.

    The implementation of this class is based on the invariant that the version of the inmanta-core and the
    Inmanta product packages don't change.
    """

    _invalid_chars_in_path_re = re.compile(r'["$`]')

    def __init__(self, *, env_path: Optional[str] = None, python_path: Optional[str] = None) -> None:
        if (env_path is None) == (python_path is None):
            raise ValueError("Exactly one of `env_path` and `python_path` needs to be specified")
        self.env_path: str
        self.python_path: str
        self._parent_python: Optional[str] = None
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
        self.validate_path(self.env_path)
        self.site_packages_dir: str = self.get_site_dir_for_env_path(self.env_path)
        self._path_pth_file = os.path.join(self.site_packages_dir, "inmanta-inherit-from-parent-venv.pth")

    def validate_path(self, path: str) -> None:
        """
        The given path is used in the `./bin/activate` file of the created venv without escaping any special characters.
        As such, we refuse all special characters here that might cause the given path to be interpreted incorrectly:

            * $: Character used for variable expansion in bash strings.
            * `: Character used to perform command substitution in bash strings.
            * ": Character that will be interpreted incorrectly as the end of the string.

        :param path: Path to validate.
        """
        if not path:
            raise ValueError("Cannot create virtual environment because the provided path is an empty string.")

        match = PythonEnvironment._invalid_chars_in_path_re.search(path)
        if match:
            raise ValueError(
                f"Cannot create virtual environment because the provided path `{path}` contains an"
                f" invalid character (`{match.group()}`)."
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

    @classmethod
    def get_env_path_for_python_path(cls, python_path: str) -> str:
        """
        For a given path to a python binary, return the path to the venv directory.
        """
        return os.path.dirname(os.path.dirname(python_path))

    def init_env(self) -> None:
        """
        Initialize the virtual environment.
        """
        self._parent_python = sys.executable
        LOGGER.info("Initializing virtual environment at %s", self.env_path)

        # check if the virtual env exists
        if os.path.isdir(self.env_path) and os.listdir(self.env_path):
            self.can_activate()
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

    def can_activate(self) -> None:
        """
        Can this venv be activated with this current python version?

        raises a VenvActivationFailedError exception if this is not the case
        """
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
            venv_python_version = subprocess.check_output([self.python_path, "--version"]).decode("utf-8").strip().split()[1]
            venv_python_version = tuple(map(int, venv_python_version.split(".")))[:2]

            running_process_python_version = sys.version_info[:2]

            if venv_python_version != running_process_python_version:
                raise VenvActivationFailedError(
                    msg=f"Unable to use virtualenv at {self.env_path} because its Python version "
                    "is different from the Python version of this process."
                )

    def _write_pip_binary(self) -> None:
        """
        write out a "stub" pip binary so that pip list works in the virtual env.
        """
        pip_path = os.path.join(self.env_path, "bin", "pip")

        with open(pip_path, "w", encoding="utf-8") as fd:
            fd.write("""#!/bin/sh
"$(dirname "$0")/python" -m pip $@
                """.strip())
        os.chmod(pip_path, 0o755)

    def _write_pth_file(self) -> None:
        """
        Write an inmanta-inherit-from-parent-venv.pth file to the venv to ensure that an activation of this venv will also
        activate the parent venv. The site directories of the parent venv should appear later in sys.path than the ones of
        this venv.
        """
        site_dir_strings: list[str] = ['"' + p.replace('"', r"\"") + '"' for p in list(sys.path)]
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

    def get_installed_packages(self, only_editable: bool = False) -> dict[NormalizedName, packaging.version.Version]:
        """
        Return a list of all installed packages in the site-packages of a python interpreter.

        :param only_editable: List only packages installed in editable mode.
        :return: A dict with package names as keys and versions as values
        """
        cmd = PipCommandBuilder.compose_list_command(self.python_path, format=PipListFormat.json, only_editable=only_editable)
        output = CommandRunner(LOGGER_PIP).run_command_and_log_output(cmd, stderr=subprocess.DEVNULL, env=os.environ.copy())
        return {canonicalize_name(r["name"]): packaging.version.Version(r["version"]) for r in json.loads(output)}

    def download_distributions(
        self,
        output_directory: str,
        pip_config: PipConfig | None,
        dependencies: Sequence[inmanta.util.CanonicalRequirement],
        constraints: Sequence[inmanta.util.CanonicalRequirement] | None = None,
        no_binary: str | None = None,
        no_deps: bool = False,
    ) -> None:
        """
        Download the python distribution packages that satisfy the given requirements.
        """
        if not dependencies:
            return
        Pip.run_pip_download_command(
            python_path=self.python_path,
            output_dir=output_directory,
            pip_config=pip_config,
            dependencies=dependencies,
            constraints=constraints,
            no_deps=no_deps,
            no_binary=no_binary,
        )

    def install_for_config(
        self,
        requirements: Sequence[inmanta.util.CanonicalRequirement],
        config: PipConfig,
        upgrade: bool = False,
        constraint_files: Optional[list[str]] = None,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        paths: list[LocalPackagePath] = [],
        add_inmanta_requires: bool = True,
        constraints: Sequence[inmanta.util.CanonicalRequirement] | None = None,
    ) -> None:
        """
        Perform a pip install in this environment, according to the given config

        :param requirements: which requirements to install
        :param paths: which paths to install
        :param config: the pip config to use
        :param constraint_files: pass along the following constraint files
        :param upgrade: make pip do an upgrade
        :param upgrade_strategy: what upgrade strategy to use

        limitation:
         - When upgrade is false, if requirements are already installed constraints from constraint files may not be verified.
        """
        if len(requirements) == 0 and len(paths) == 0:
            raise Exception("install_for_config requires at least one requirement or path to install")
        constraint_files = constraint_files if constraint_files is not None else []
        if add_inmanta_requires:
            inmanta_requirements = self._get_requirements_on_inmanta_package()
        else:
            inmanta_requirements = []

        with tempfile.NamedTemporaryFile() as fd:
            if constraints:
                fd.write("\n".join(str(c) for c in constraints).encode())
                fd.seek(0)
            Pip.run_pip_install_command_from_config(
                python_path=self.python_path,
                config=config,
                requirements=[*requirements, *inmanta_requirements],
                constraints_files=[*constraint_files, fd.name],
                upgrade=upgrade,
                upgrade_strategy=upgrade_strategy,
                paths=paths,
            )

    async def async_install_for_config(
        self,
        requirements: list[packaging.requirements.Requirement],
        config: PipConfig,
        upgrade: bool = False,
        constraint_files: Optional[list[str]] = None,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        paths: list[LocalPackagePath] = [],
    ) -> None:
        """
        Perform a pip install in this environment, according to the given config

        :param requirements: which requirements to install
        :param config: the pip config to use
        :param upgrade: make pip do an upgrade
        :param constraint_files: pass along the following constraint files
        :param upgrade_strategy: what upgrade strategy to use
        :param paths: which paths to install

        limitation:
         - When upgrade is false, if requirements are already installed constraints from constraint files may not be verified.
        """
        if len(requirements) == 0 and len(paths) == 0:
            raise Exception("install_for_config requires at least one requirement or path to install")
        constraint_files = constraint_files if constraint_files is not None else []
        inmanta_requirements = self._get_requirements_on_inmanta_package()

        await Pip.async_run_pip_install_command_from_config(
            python_path=self.python_path,
            config=config,
            requirements=[*requirements, *inmanta_requirements],
            constraints_files=constraint_files,
            upgrade=upgrade,
            upgrade_strategy=upgrade_strategy,
            paths=paths,
        )

    def install_from_index(
        self,
        requirements: list[inmanta.util.CanonicalRequirement],
        index_urls: Optional[list[str]] = None,
        upgrade: bool = False,
        allow_pre_releases: bool = False,
        constraint_files: Optional[list[str]] = None,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        use_pip_config: Optional[bool] = False,
    ) -> None:
        """This method provides backward compatibility with ISO6"""
        if len(requirements) == 0:
            raise Exception("install_from_index requires at least one requirement to install")

        if not index_urls:
            index_url = None
            extra_index_url = []
        else:
            index_url = index_urls[0]
            extra_index_url = index_urls[1:]

        self.install_for_config(
            requirements=requirements,
            config=PipConfig(
                index_url=index_url,
                extra_index_url=extra_index_url,
                pre=allow_pre_releases,
                use_system_config=use_pip_config if use_pip_config is not None else True,
            ),
            upgrade=upgrade,
            constraint_files=constraint_files,
            upgrade_strategy=upgrade_strategy,
        )

    def install_from_source(
        self,
        paths: list[LocalPackagePath],
        constraint_files: Optional[list[str]] = None,
    ) -> None:
        """
        Install one or more packages from source. Any path arguments should be local paths to a package directory or wheel.

        This method provides backward compatibility with ISO6
        """
        if len(paths) == 0:
            raise Exception("install_from_source requires at least one package to install")
        self.install_for_config(
            requirements=[],
            paths=paths,
            config=LEGACY_PIP_DEFAULT,
            constraint_files=constraint_files,
        )

    def install_from_list(
        self,
        requirements_list: Sequence[str],
        *,
        upgrade: bool = False,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        use_pip_config: Optional[bool] = False,
    ) -> None:
        """
        Install requirements from a list of requirement strings. This method uses the Python package repositories
        configured on the host.
        :param requirements_list: List of requirement strings to install.
        :param upgrade: Upgrade requirements to the latest compatible version.
        :param upgrade_strategy: The upgrade strategy to use for requirements' dependencies.
        :param use_pip_config: ignored

        This method provides backward compatibility with ISO6
        use_pip_config was ignored on ISO6 and it still is
        """
        self.install_from_index(
            requirements=inmanta.util.parse_requirements(requirements_list),
            upgrade=upgrade,
            upgrade_strategy=upgrade_strategy,
            use_pip_config=True,
        )

    @classmethod
    def get_protected_inmanta_packages(cls) -> list[str]:
        """
        Returns the list of packages that should not be installed/updated by any operation on a Python environment.
        This list of packages will be under the canonical form.
        """
        return [
            # Protect product packages
            packaging.utils.canonicalize_name("inmanta"),
            packaging.utils.canonicalize_name("inmanta-service-orchestrator"),
            # Protect all server extensions
            *(
                packaging.utils.canonicalize_name(f"inmanta-{ext_name}")
                for ext_name in InmantaBootloader.get_available_extensions().keys()
            ),
        ]

    @classmethod
    def _get_requirements_on_inmanta_package(cls) -> Sequence[inmanta.util.CanonicalRequirement]:
        """
        Returns the content of the requirement file that should be supplied to each `pip install` invocation
        to make sure that no Inmanta packages gets overridden.
        """
        protected_inmanta_packages: list[str] = cls.get_protected_inmanta_packages()
        workingset: dict[NormalizedName, packaging.version.Version] = PythonWorkingSet.get_packages_in_working_set()
        return [
            inmanta.util.parse_requirement(requirement=f"{pkg}=={workingset[pkg]}")
            for pkg in workingset
            if pkg in protected_inmanta_packages
        ]


class CommandRunner:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def run_command_and_log_output(
        self, cmd: list[str], env: Optional[dict[str, str]] = None, stderr: Optional[int] = None, cwd: Optional[str] = None
    ) -> str:
        output: bytes = b""  # Make sure the var is always defined in the except bodies
        try:
            output = subprocess.check_output(cmd, stderr=stderr, env=env, cwd=cwd)
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
        cmd: list[str],
        timeout: float = 10,
        env_vars: Optional[Mapping[str, str]] = None,
        cwd: str | None = None,
    ) -> tuple[int, list[str]]:
        """
        Similar to the _run_command_and_log_output method, but here, the output is logged on the fly instead of at the end
        of the sub-process.
        """
        full_output: list[str] = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env_vars,
            cwd=cwd,
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

    async def async_run_command_and_stream_output(
        self,
        cmd: list[str],
        timeout: float = 10,
        env_vars: Optional[Mapping[str, str]] = None,
    ) -> tuple[int, list[str]]:
        """
        Similar to the _run_command_and_log_output method, but here, the output is logged on the fly instead of at the end
        of the sub-process.
        """
        full_output = []
        # We use close_fds here to avoid
        # the bug https://github.com/python/cpython/issues/103911#issuecomment-2333963137
        # We attempt to get on the code path that uses _posix_spawn instead of _fork_exec
        # Subprocess shell did not work to prevent it
        # Improved escaping (shlex.quote) to prevent `>` from leaking did not help
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env_vars, close_fds=False
        )
        assert process.stdout is not None  # Make mypy happy
        async for line in process.stdout:
            # Eagerly consume the buffer to avoid a deadlock in case the subprocess fills it entirely.
            output = line.decode().strip()
            full_output.append(output)
            self.logger.debug(output)

        try:
            return_code = await asyncio.wait_for(process.wait(), timeout=timeout)
        except TimeoutError:
            process.kill()
            return -1, full_output
        else:
            return return_code, full_output


class ActiveEnv(PythonEnvironment):
    """
    The active Python environment. Method implementations assume this environment is active when they're called.
    Activating another environment that inherits from this one is allowed.
    """

    _egg_fragment_re = re.compile(r"#egg=(?P<name>[^&]*)")
    _at_fragment_re = re.compile(r"^(?P<name>[^@]+)@(?P<req>.+)")

    def __init__(self, *, env_path: Optional[str] = None, python_path: Optional[str] = None) -> None:
        super().__init__(env_path=env_path, python_path=python_path)

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
        assert self.is_using_virtual_env()
        return PythonWorkingSet.are_installed(requirements)

    def install_for_config(
        self,
        requirements: Sequence[inmanta.util.CanonicalRequirement],
        config: PipConfig,
        upgrade: bool = False,
        constraint_files: Optional[list[str]] = None,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        paths: list[LocalPackagePath] = [],
        add_inmanta_requires: bool = True,
        constraints: Sequence[inmanta.util.CanonicalRequirement] | None = None,
    ) -> None:
        if (not upgrade and self.are_installed(requirements)) and not paths:
            return
        try:
            super().install_for_config(
                requirements,
                config,
                upgrade,
                constraint_files,
                upgrade_strategy,
                paths,
                add_inmanta_requires,
                constraints=constraints,
            )
        finally:
            self.notify_change()

    @classmethod
    def get_module_file(cls, module: str) -> Optional[tuple[Optional[str], Loader]]:
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

    def get_installed_packages(self, only_editable: bool = False) -> dict[NormalizedName, packaging.version.Version]:
        """
        Return a list of all installed packages in the site-packages of a python interpreter.

        :param only_editable: List only packages installed in editable mode.
        :return: A dict with package names as keys and versions as values
        """
        if self.is_using_virtual_env() and not only_editable:
            return PythonWorkingSet.get_packages_in_working_set()
        return super().get_installed_packages(only_editable=only_editable)

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


process_env: ActiveEnv = ActiveEnv(python_path=sys.executable)
"""
Singleton representing the Python environment this process is running in.

Should not be imported directly, as it can be updated
"""


@stable_api
def mock_process_env(*, python_path: Optional[str] = None, env_path: Optional[str] = None) -> None:
    """
    Overrides the process environment information. This forcefully sets the environment that is recognized as the outer Python
    environment. This function should only be called when a Python environment has been set up dynamically and this environment
    should be treated as if this process was spawned from it, and even then with great care.
    :param python_path: The path to the python binary. Only one of `python_path` and `env_path` should be set.
    :param env_path: The path to the python environment directory. Only one of `python_path` and `env_path` should be set.

    When using this method in a fixture to set and reset virtualenv, it is preferable to use `store_venv()`
    """
    process_env.__init__(python_path=python_path, env_path=env_path)  # type: ignore


def swap_process_env(env: ActiveEnv) -> ActiveEnv:
    """
    Overrides the process environment information.

    Returns the old active env

    For use in testing. Test as expected to swap the old process env back in place
    """
    global process_env
    old_env = process_env
    process_env = env
    return old_env


@stable_api
class VirtualEnv(ActiveEnv):
    """
    Creates and uses a virtual environment for this process. This virtualenv inherits from the previously active one.
    """

    def __init__(self, env_path: str) -> None:
        super().__init__(env_path=env_path)
        self.env_path: str = env_path
        self.virtual_python: Optional[str] = None
        self._using_venv: bool = False

    def exists(self) -> bool:
        """
        Returns True iff the venv exists on disk.
        """
        return os.path.exists(self.python_path)

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
        mock_process_env(python_path=self.python_path)

        self._activate_that()

        self._using_venv = True

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

        is_change = sys.prefix != base
        sys.real_prefix = sys.prefix
        sys.prefix = base
        self._update_sys_path()
        if is_change:
            self.notify_change()

    def install_for_config(
        self,
        requirements: Sequence[inmanta.util.CanonicalRequirement],
        config: PipConfig,
        upgrade: bool = False,
        constraint_files: Optional[list[str]] = None,
        upgrade_strategy: PipUpgradeStrategy = PipUpgradeStrategy.ONLY_IF_NEEDED,
        paths: list[LocalPackagePath] = [],
        add_inmanta_requires: bool = True,
        constraints: Sequence[inmanta.util.CanonicalRequirement] | None = None,
    ) -> None:
        if not self._using_venv:
            raise Exception(f"Not using venv {self.env_path}. use_virtual_env() should be called first.")
        super().install_for_config(
            requirements,
            config,
            upgrade,
            constraint_files,
            upgrade_strategy,
            paths,
            add_inmanta_requires,
            constraints=constraints,
        )


class VenvCreationFailedError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg


class VenvActivationFailedError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg


@dataclass
class VenvSnapshot:
    old_os_path: str
    old_prefix: str
    old_path: list[str]
    old_meta_path: "list[MetaPathFinderProtocol]"
    old_path_hooks: "list[Callable[[str], PathEntryFinderProtocol]]"
    old_pythonpath: Optional[str]
    old_os_venv: Optional[str]
    old_process_env_path: str
    old_process_env: ActiveEnv

    def restore(self) -> None:
        if sys.prefix != self.old_prefix:
            # only reset on folder change
            os.environ["PATH"] = self.old_os_path
            sys.prefix = self.old_prefix
            sys.path = self.old_path
            # reset sys.meta_path because it might contain finders for editable installs, make sure to keep the same object
            sys.meta_path.clear()
            sys.meta_path.extend(self.old_meta_path)
            sys.path_hooks.clear()
            sys.path_hooks.extend(self.old_path_hooks)
            # Clear cache for sys.path_hooks
            sys.path_importer_cache.clear()
            # Restore PYTHONPATH
            if self.old_pythonpath is not None:
                os.environ["PYTHONPATH"] = self.old_pythonpath
            elif "PYTHONPATH" in os.environ:
                del os.environ["PYTHONPATH"]
            # Restore VIRTUAL_ENV
            if self.old_os_venv is not None:
                os.environ["VIRTUAL_ENV"] = self.old_os_venv
            elif "VIRTUAL_ENV" in os.environ:
                del os.environ["VIRTUAL_ENV"]

        # We reset the process_env both ways: we put the reference back and we do an in_place update
        swap_process_env(self.old_process_env)
        mock_process_env(env_path=self.old_process_env_path)


def store_venv() -> VenvSnapshot:
    """
    Create a snapshot of the venv environment, for use in testing, to resest the test
    """

    self = VenvSnapshot(
        old_os_path=os.environ.get("PATH", ""),
        old_prefix=sys.prefix,
        old_path=list(sys.path),
        old_meta_path=sys.meta_path.copy(),
        old_path_hooks=sys.path_hooks.copy(),
        old_pythonpath=os.environ.get("PYTHONPATH", None),
        old_os_venv=os.environ.get("VIRTUAL_ENV", None),
        old_process_env=process_env,
        old_process_env_path=process_env.env_path,
    )
    return self
