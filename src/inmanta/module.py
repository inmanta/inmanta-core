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

import configparser
import enum
import glob
import importlib
import logging
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import traceback
import types
import warnings
from abc import ABC, abstractmethod
from collections import abc, defaultdict
from configparser import ConfigParser
from dataclasses import dataclass
from importlib.abc import Loader
from io import BytesIO, TextIOBase
from itertools import chain
from subprocess import CalledProcessError
from tarfile import TarFile
from time import time
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Mapping,
    NewType,
    Optional,
    Sequence,
    Set,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import more_itertools
import pkg_resources
import yaml
from pkg_resources import Distribution, DistributionNotFound, Requirement, parse_requirements, parse_version
from pydantic import BaseModel, Field, NameEmail, ValidationError, constr, validator
from pydantic.error_wrappers import display_errors

import packaging.version
from inmanta import RUNNING_TESTS, const, env, loader, plugins
from inmanta.ast import CompilerException, LocatableString, Location, Namespace, Range, WrappingRuntimeException
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.statements import BiStatement, DefinitionStatement, DynamicStatement, Statement
from inmanta.ast.statements.define import DefineImport
from inmanta.file_parser import PreservativeYamlParser, RequirementsTxtParser
from inmanta.parser import plyInmantaParser
from inmanta.parser.plyInmantaParser import cache_manager
from inmanta.stable_api import stable_api
from inmanta.util import get_compiler_version
from inmanta.warnings import InmantaWarning
from packaging import version
from ruamel.yaml.comments import CommentedMap

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


LOGGER = logging.getLogger(__name__)

Path = NewType("Path", str)
ModuleName = NewType("ModuleName", str)

T = TypeVar("T")
TModule = TypeVar("TModule", bound="Module")
TProject = TypeVar("TProject", bound="Project")
TInmantaModuleRequirement = TypeVar("TInmantaModuleRequirement", bound="InmantaModuleRequirement")


@stable_api
class InmantaModuleRequirement:
    """
    Represents a requirement on an inmanta module. This is a wrapper around Requirement. This class is provided for the
    following reasons:
        1. Work around some particulars of Requirement's semantics with respect to naming conventions.
        2. Improve readability and clarity of purpose where a requirement on either a Python package or an inmanta module is
            used by distinguishing the two on a type level.
    """

    def __init__(self, requirement: Requirement) -> None:
        if requirement.project_name.startswith(ModuleV2.PKG_NAME_PREFIX):
            raise ValueError("InmantaModuleRequirement instances work with inmanta module names, not python package names.")
        self._requirement: Requirement = requirement

    @property
    def project_name(self) -> str:
        # Requirement converts all "_" to "-". Inmanta modules use "_"
        return self._requirement.project_name.replace("-", "_")

    @property
    def key(self) -> str:
        # Requirement converts all "_" to "-". Inmanta modules use "_"
        return self._requirement.key.replace("-", "_")

    @property
    def specifier(self) -> str:
        return self._requirement.specifier

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InmantaModuleRequirement):
            return NotImplemented
        return self._requirement == other._requirement

    def __contains__(self, version: str) -> bool:
        return version in self._requirement

    def __str__(self) -> str:
        return str(self._requirement).replace("-", "_")

    def __hash__(self) -> int:
        return self._requirement.__hash__()

    @property
    def specs(self) -> Sequence[Tuple[str, str]]:
        return self._requirement.specs

    def version_spec_str(self) -> str:
        """
        Returns a string representation of this module requirement's version spec. Includes only the version part.
        """
        return ",".join("".join(spec) for spec in self.specs)

    @classmethod
    def parse(cls: Type[TInmantaModuleRequirement], spec: str) -> TInmantaModuleRequirement:
        if spec.startswith(ModuleV2.PKG_NAME_PREFIX):
            raise ValueError(
                "Invalid Inmanta module requirement: Use the Inmanta module name instead of the Python package name"
            )
        if "-" in spec:
            raise ValueError("Invalid Inmanta module requirement: Inmanta module names use '_', not '-'.")
        return cls(Requirement.parse(spec))

    def get_python_package_requirement(self) -> Requirement:
        """
        Return a Requirement with the name of the Python distribution package for this module requirement.
        """
        module_name = self.project_name
        pkg_name = ModuleV2Source.get_package_name_for(module_name)
        pkg_req_str = str(self).replace(module_name, pkg_name, 1)  # Replace max 1 occurrence
        return Requirement.parse(pkg_req_str)


class CompilerExceptionWithExtendedTrace(CompilerException):
    """
    A compiler exception that adds additional information about the cause of this exception
    to the formatted trace.
    """

    def format_trace(self, indent: str = "", indent_level: int = 0) -> str:
        """Make a representation of this exception and its causes"""
        # can have a cause of any type
        out = indent * indent_level + self.format()

        if self.__cause__ is not None:
            part = traceback.format_exception_only(self.__cause__.__class__, self.__cause__)
            out += "\n" + indent * indent_level + "caused by:\n"
            for line in part:
                out += indent * (indent_level + 1) + line

        return out


@stable_api
class InvalidModuleException(CompilerExceptionWithExtendedTrace):
    """
    This exception is raised if a module is invalid.
    """


class ModuleNotFoundException(CompilerExceptionWithExtendedTrace):
    """
    This exception is raised if a module is not found in any of the repositories.
    """


class ModuleLoadingException(WrappingRuntimeException):
    """
    Wrapper around an InvalidModuleException or a ModuleNotFoundException that contains extra information
    about the specific DefinedImport statement that cannot not be processed correctly.
    """

    def __init__(
        self,
        name: str,
        stmt: "DefineImport",
        cause: Union[InvalidModuleException, ModuleNotFoundException],
        msg: Optional[str] = None,
    ) -> None:
        """
        :param name: The name of the module that could not be loaded.
        :param stmt: The DefinedImport statement that triggered the failure
        :param cause: The InvalidModuleException or ModuleNotFoundException that was raised
        :param msg: A description of the error.
        """
        if msg is None:
            msg = "Failed to load module %s" % name
        WrappingRuntimeException.__init__(self, stmt, msg, cause)
        self.name = name

    def importantance(self) -> int:
        return 5


class ModuleMetadataFileNotFound(InvalidModuleException):
    pass


class ModuleV2InV1PathException(InvalidModuleException):
    def __init__(self, project: Optional["Project"], module: "ModuleV2", msg: str) -> None:
        super().__init__(msg)
        self.project: Optional[Project] = project
        self.module: ModuleV2 = module


@stable_api
class InvalidMetadata(CompilerException):
    """
    This exception is raised if the metadata file of a project or module is invalid.
    """

    def __init__(self, msg: str, validation_error: Optional[ValidationError] = None) -> None:
        if validation_error is not None:
            msg = self._extend_msg_with_validation_information(msg, validation_error)
        super(InvalidMetadata, self).__init__(msg=msg)

    @classmethod
    def _extend_msg_with_validation_information(cls, msg: str, validation_error: ValidationError) -> str:
        errors = validation_error.errors()
        if errors:
            msg += "\n" + textwrap.indent(display_errors(errors), " " * 2)
        return msg


class ModuleDeprecationWarning(InmantaWarning):
    pass


@stable_api
class ProjectNotFoundException(CompilerException):
    """
    This exception is raised when inmanta is unable to find a valid project
    """


class PluginModuleLoadException(Exception):
    """
    Exception representing an error during plugin module loading.
    """

    def __init__(self, cause: Exception, module: str, fq_import: str, path: str, lineno: Optional[int]) -> None:
        """
        :param cause: The exception raised by the import.
        :param module: The name of the Inmanta module.
        :param fq_import: The fully qualified import to the Python module for which the loading failed.
        :param path: The path to the file on disk that belongs to `fq_import`.
        :param lineno: Optionally, the line number in `path` that causes the loading issue.
        """
        self.cause: Exception = cause
        self.module: str = module
        self.fq_import: str = fq_import
        self.path: str = path
        self.lineno: Optional[int] = lineno
        lineno_suffix = f":{self.lineno}" if self.lineno is not None else ""
        super().__init__(
            "%s while loading plugin module %s at %s: %s"
            % (
                self.get_cause_type_name(),
                self.module,
                f"{self.path}{lineno_suffix}",
                self.cause,
            )
        )

    def get_cause_type_name(self) -> str:
        module: Optional[str] = type(self.cause).__module__
        name: str = type(self.cause).__qualname__
        return name if module is None or module == "builtins" else "%s.%s" % (module, name)

    def to_compiler_exception(self) -> CompilerException:
        module: Optional[str] = type(self.cause).__module__
        name: str = type(self.cause).__qualname__
        cause_type_name = name if module is None or module == "builtins" else "%s.%s" % (module, name)

        exception = CompilerException(
            f"Unable to load all plug-ins for module {self.module}:"
            f"\n\t{cause_type_name} while loading plugin module {self.fq_import}: {self.cause}"
        )
        exception.set_location(Location(self.path, self.lineno if self.lineno is not None else 0))
        return exception


class UntrackedFilesMode(enum.Enum):
    """
    The different options that can be passed to the --untracked-files option of the `git status` command.
    """

    ALL = "all"
    NORMAL = "normal"
    NO = "no"


class GitProvider(object):
    def clone(self, src: str, dest: str) -> None:
        pass

    def fetch(self, repo: str) -> None:
        pass

    def status(self, repo: str, untracked_files_mode: Optional[UntrackedFilesMode] = None) -> str:
        pass

    def get_all_tags(self, repo: str) -> List[str]:
        pass

    def get_version_tags(self, repo: str, only_return_stable_versions: bool = False) -> list[version.Version]:
        pass

    def get_file_for_version(self, repo: str, tag: str, file: str) -> str:
        pass

    def checkout_tag(self, repo: str, tag: str) -> None:
        pass

    def commit(
        self,
        repo: str,
        message: str,
        commit_all: bool,
        add: Optional[abc.Sequence[str]] = None,
        raise_exc_when_nothing_to_commit: bool = True,
    ) -> None:
        pass

    def tag(self, repo: str, tag: str) -> None:
        pass

    def push(self, repo: str) -> str:
        pass

    def pull(self, repo: str) -> str:
        pass

    def get_remote(self, repo: str) -> Optional[str]:
        pass

    def is_git_repository(self, repo: str) -> bool:
        pass

    def git_init(self, repo: str) -> None:
        pass

    def add(self, repo: str, files: list[str]) -> None:
        pass


class CLIGitProvider(GitProvider):
    def clone(self, src: str, dest: str) -> None:
        process_env = os.environ.copy()
        process_env["GIT_ASKPASS"] = "true"
        cmd = ["git", "clone", src, dest]

        return_code, _ = env.CommandRunner(LOGGER).run_command_and_stream_output(cmd, env_vars=process_env)

        if return_code != 0:
            raise Exception(f"An unexpected error occurred while cloning into {dest} from {src}.")

    def fetch(self, repo: str) -> None:
        env = os.environ.copy()
        env["GIT_ASKPASS"] = "true"
        subprocess.check_call(
            ["git", "fetch", "--tags"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
        )

    def status(self, repo: str, untracked_files_mode: Optional[UntrackedFilesMode] = None) -> str:
        """
        Return the output of the `git status --porcelain` command.

        :param repo: The path to the directory that contains the git repository on which the git command should be executed.
        :param untracked_files_mode: If provided, the --untracked-files option will be passed to `git status` command.
        """
        extra_args = []
        if untracked_files_mode:
            extra_args.append(f"--untracked-files={untracked_files_mode.value}")
        return subprocess.check_output(["git", "status", "--porcelain", *extra_args], cwd=repo).decode("utf-8")

    def get_all_tags(self, repo: str) -> List[str]:
        return subprocess.check_output(["git", "tag"], cwd=repo).decode("utf-8").splitlines()

    def get_version_tags(self, repo: str, only_return_stable_versions: bool = False) -> list[version.Version]:
        """
        Return the Git tags that represent version numbers as version.Version objects. Only PEP440 compliant
        versions will be returned.

        :param repo: The path to the directory that contains the git repository on which the git command should be executed.
        :param only_return_stable_versions: Return only version for stable releases.
        """
        result = []
        all_tags: List[str] = sorted(self.get_all_tags(repo))
        for tag in all_tags:
            try:
                parsed_version: version.Version = version.Version(tag)
            except version.InvalidVersion:
                continue
            if not only_return_stable_versions or not parsed_version.is_prerelease:
                result.append(parsed_version)
        return sorted(result)

    def checkout_tag(self, repo: str, tag: str) -> None:
        subprocess.check_call(["git", "checkout", tag], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def commit(
        self,
        repo: str,
        message: str,
        commit_all: bool,
        add: Optional[abc.Sequence[str]] = None,
        raise_exc_when_nothing_to_commit: bool = True,
    ) -> None:
        """
        Execute the `git commit` command.

        :param repo: The path to the directory that contains the git repository on which the git command should be executed.
        :param message: The commit message.
        :param commit_all: Commit changes to all tracked files using the `-a` option.
        :param add: Paths to files that have to be staged for the commit.
        :param raise_exc_when_nothing_to_commit: True iff there are no changes to commit.
        """
        if add is None:
            add = []
        self.add(repo=repo, files=add)
        if (
            not raise_exc_when_nothing_to_commit
            and not self.status(repo=repo, untracked_files_mode=UntrackedFilesMode.NO).strip()
        ):
            # Nothing to commit
            return
        if not commit_all:
            subprocess.check_call(
                ["git", "commit", "-m", message], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        else:
            subprocess.check_call(
                ["git", "commit", "-a", "-m", message], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

    def tag(self, repo: str, tag: str) -> None:
        subprocess.check_call(
            ["git", "tag", "-a", "-m", "auto tag by module tool", tag],
            cwd=repo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def pull(self, repo: str) -> str:
        return subprocess.check_output(["git", "pull"], cwd=repo, stderr=subprocess.DEVNULL).decode("utf-8")

    def get_remote(self, repo: str) -> Optional[str]:
        """
        Returns the remote tracking repo given a local repo or None if the remote is not yet configured
        """
        try:
            remote = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"], cwd=repo, stderr=subprocess.DEVNULL
            ).decode("utf-8")
        except CalledProcessError:
            remote = None
        return remote

    def push(self, repo: str) -> str:
        return subprocess.check_output(
            ["git", "push", "--follow-tags", "--porcelain"], cwd=repo, stderr=subprocess.DEVNULL
        ).decode("utf-8")

    def get_file_for_version(self, repo: str, tag: str, file: str) -> str:
        data = subprocess.check_output(["git", "archive", "--format=tar", tag, file], cwd=repo, stderr=subprocess.DEVNULL)
        tf = TarFile(fileobj=BytesIO(data))
        tfile = tf.next()
        assert tfile is not None
        b = tf.extractfile(tfile)
        assert b is not None
        return b.read().decode("utf-8")

    def is_git_repository(self, repo: str) -> bool:
        """
        Return True iff the given directory is a git repository.
        """
        try:
            self.status(repo=repo)
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    def git_init(self, repo: str) -> None:
        """
        Execute `git init` in the given repository.
        """
        subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def add(self, repo: str, files: abc.Sequence[str]) -> None:
        if files:
            subprocess.check_call(["git", "add", *files], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


gitprovider = CLIGitProvider()


class ModuleSource(Generic[TModule]):
    def get_installed_module(self, project: Optional["Project"], module_name: str) -> Optional[TModule]:
        """
        Returns a module object for a module if it is installed.

        :param project: The project associated with the module.
        :param module_name: The name of the module.
        """
        path: Optional[str] = self.path_for(module_name)
        return self.from_path(project, module_name, path) if path is not None else None

    def get_module(
        self, project: "Project", module_spec: List[InmantaModuleRequirement], install: bool = False
    ) -> Optional[TModule]:
        """
        Returns the appropriate module instance for a given module spec.

        :param project: The project associated with the module.
        :param module_spec: The module specification including any constraints on its version. In this case,
                            the project is responsible for verifying constraint compatibility.
        :param install: Whether to attempt to install the module if it hasn't been installed yet.
        """
        module_name: str = self._get_module_name(module_spec)
        installed: Optional[TModule] = self.get_installed_module(project, module_name)

        def _should_install_module() -> bool:
            """
            Return True iff the given module should get installed
            """
            if not install:
                # No install was requested
                return False
            if installed is None:
                # Package is not installed
                return True
            if isinstance(installed, ModuleV2):
                python_pkg_req = [r.get_python_package_requirement() for r in module_spec]
                if not project.virtualenv.are_installed(python_pkg_req):
                    # Package could define an extra that is not installed yet
                    return True
            # Already installed
            return False

        if _should_install_module():
            return self.install(project, module_spec)
        return installed

    def _format_constraints(self, module_name: str, module_spec: List[InmantaModuleRequirement]) -> str:
        """
        Returns the constraints on a given inmanta module as a string.

        :param module_name: The name of the module.
        :param module_spec: List of inmanta requirements in which to look for the module.
        """
        constraints_on_module: List[str] = [str(req) for req in module_spec if module_name == req.key and req.specs]
        if constraints_on_module:
            from_constraints = f"(with constraints {' '.join(constraints_on_module)})"
        else:
            from_constraints = "(with no version constraints)"
        return from_constraints

    @abstractmethod
    def log_pre_install_information(self, module_name: str, module_spec: List[InmantaModuleRequirement]) -> None:
        """
        Display information about this module's installation before the actual installation.

        :param module_name: The module's name.
        """
        raise NotImplementedError("Abstract method")

    def _log_version_snapshot(self, header: Optional[str], version_snapshot: Dict[str, version.Version]) -> None:
        if version_snapshot:
            out = [header] if header is not None else []
            out.extend(f"{mod}: {version}" for mod, version in version_snapshot.items())
            LOGGER.debug("\n".join(out))

    def _log_snapshot_difference(
        self, version_snapshot: Dict[str, version.Version], previous_snapshot: Dict[str, version.Version], header: Optional[str]
    ) -> None:
        set_pre_install: Set[tuple[str, version.Version]] = set(previous_snapshot.items())
        set_post_install: Set[tuple[str, version.Version]] = set(version_snapshot.items())
        updates_and_additions: Set[tuple[str, version.Version]] = set_post_install - set_pre_install

        if version_snapshot:
            out = [header] if header is not None else []
            for inmanta_module_name, package_version in sorted(version_snapshot.items()):
                if inmanta_module_name not in previous_snapshot.keys():
                    # new module that wasn't previously installed
                    out.append("+ " + inmanta_module_name + ": " + str(package_version))
                elif inmanta_module_name in [elmt[0] for elmt in updates_and_additions]:
                    # module has a different version
                    out.append("+ " + inmanta_module_name + ": " + str(package_version))
                    out.append("- " + inmanta_module_name + ": " + str(previous_snapshot[inmanta_module_name]))

            LOGGER.debug("\n".join(out))

    @abstractmethod
    def install(self, project: "Project", module_spec: List[InmantaModuleRequirement]) -> Optional[TModule]:
        """
        Attempt to install a module given a module spec. Updates a module that is already installed only if it does not match
        the constraints.

        :param project: The project associated with the module.
        :param module_spec: The module specification including any constraints on its version.
        :return: The module object when the module was installed. When the module could not be found, None is returned.
        """
        raise NotImplementedError("Abstract method")

    @abstractmethod
    def path_for(self, name: str) -> Optional[str]:
        """
        Returns the path to the module root directory. Should be called prior to configuring the module finder for v1 modules.
        """
        raise NotImplementedError("Abstract method")

    @classmethod
    @abstractmethod
    def from_path(cls, project: Optional["Project"], module_name: str, path: str) -> TModule:
        """
        Returns a module instance given a path to it.
        """
        raise NotImplementedError("Abstract method")

    def _get_module_name(self, module_spec: List[InmantaModuleRequirement]) -> str:
        module_names: Set[str] = {req.project_name for req in module_spec}
        module_name: str = more_itertools.one(
            module_names,
            too_short=ValueError("module_spec should contain at least one requirement"),
            too_long=ValueError("module_spec should contain requirements for exactly one module"),
        )
        return module_name


@stable_api
class ModuleV2Source(ModuleSource["ModuleV2"]):
    def __init__(self, urls: List[str]) -> None:
        self.urls: List[str] = [url if not os.path.exists(url) else os.path.abspath(url) for url in urls]

    @classmethod
    def get_installed_version(cls, module_name: str) -> Optional[version.Version]:
        """
        Returns the version for a module if it is installed.
        """
        if module_name.startswith(ModuleV2.PKG_NAME_PREFIX):
            raise ValueError("PythonRepo instances work with inmanta module names, not Python package names.")
        try:
            dist: Distribution = pkg_resources.get_distribution(ModuleV2Source.get_package_name_for(module_name))
            return version.Version(dist.version)
        except DistributionNotFound:
            return None
        except version.InvalidVersion:
            raise InvalidModuleException(f"Package {dist.project_name} was installed but it has no valid version.")

    @classmethod
    def get_inmanta_module_name(cls, python_package_name: str) -> str:
        if not python_package_name.startswith(ModuleV2.PKG_NAME_PREFIX):
            raise ValueError(f"Invalid python package name: should start with {ModuleV2.PKG_NAME_PREFIX}")
        result: str = python_package_name[len(ModuleV2.PKG_NAME_PREFIX) :].replace("-", "_")
        if not result:
            raise ValueError("Invalid python package name: empty module name part.")
        return result

    @classmethod
    def get_package_name_for(cls, module_name: str) -> str:
        module_name = module_name.replace("_", "-")
        return f"{ModuleV2.PKG_NAME_PREFIX}{module_name}"

    @classmethod
    def get_namespace_package_name(cls, module_name: str) -> str:
        return f"{const.PLUGINS_PACKAGE}.{module_name}"

    def install(self, project: "Project", module_spec: List[InmantaModuleRequirement]) -> Optional["ModuleV2"]:
        module_name: str = self._get_module_name(module_spec)
        if not self.urls:
            raise Exception(
                f"Attempting to install a v2 module {module_name} but no v2 module source is configured. Add at least one "
                'repo of type "package" to the project config file. e.g. to add PyPi as a module source, add the following to '
                "the `repo` section of the project's `project.yml`:"
                "\n\t- type: package"
                "\n\t  url: https://pypi.org/simple"
            )
        requirements: List[Requirement] = [req.get_python_package_requirement() for req in module_spec]
        allow_pre_releases = project is not None and project.install_mode in {InstallMode.prerelease, InstallMode.master}
        preinstalled: Optional[ModuleV2] = self.get_installed_module(project, module_name)

        # Get known requires and add them to prevent invalidating constraints through updates
        # These could be constraints (-c) as well, but that requires additional sanitation
        # Because for pip not every valid -r is a valid -c
        current_requires = project.get_strict_python_requirements_as_list()
        requirements += [Requirement.parse(r) for r in current_requires]

        if preinstalled is not None:
            # log warning if preinstalled version does not match constraints
            preinstalled_version: str = str(preinstalled.version)
            if not all(preinstalled_version in constraint for constraint in module_spec):
                LOGGER.warning(
                    "Currently installed %s-%s does not match constraint %s: updating to compatible version.",
                    module_name,
                    preinstalled_version,
                    ",".join(constraint.version_spec_str() for constraint in module_spec if constraint.specs),
                )
        try:
            self.log_pre_install_information(module_name, module_spec)
            modules_pre_install = self.take_v2_modules_snapshot(header="Modules versions before installation:")
            env.process_env.install_from_index(requirements, self.urls, allow_pre_releases=allow_pre_releases)

            self.log_post_install_information(module_name)
            self.log_snapshot_difference_v2_modules(modules_pre_install, header="Modules versions after installation:")
        except env.PackageNotFound:
            return None
        path: Optional[str] = self.path_for(module_name)
        if path is None:
            python_package: str = ModuleV2Source.get_package_name_for(module_name)
            namespace_package: str = self.get_namespace_package_name(module_name)
            raise InvalidModuleException(f"{python_package} does not contain a {namespace_package} module.")
        return self.from_path(project, module_name, path)

    def log_pre_install_information(self, module_name: str, module_spec: List[InmantaModuleRequirement]) -> None:
        LOGGER.debug("Installing module %s (v2) %s.", module_name, super()._format_constraints(module_name, module_spec))

    def take_v2_modules_snapshot(self, header: Optional[str] = None) -> Dict[str, version.Version]:
        """
        Log and return a dictionary containing currently installed v2 modules and their versions.

        :param header: Optional text to be displayed before logging the modules and their versions
        """
        packages = env.PythonWorkingSet.get_packages_in_working_set(inmanta_modules_only=True)
        version_snapshot = {self.get_inmanta_module_name(mod): version for mod, version in packages.items()}
        super()._log_version_snapshot(header, version_snapshot)
        return version_snapshot

    def log_snapshot_difference_v2_modules(
        self, previous_snapshot: Dict[str, version.Version], header: Optional[str] = None
    ) -> None:
        """
        Logs a diff view of v2 inmanta modules currently installed (in alphabetical order) and their version.

        :param previous_snapshot: Mapping of inmanta module names to their respective versions. This is the baseline against
        which the currently installed versions will be compared.
        :param header: Optional text to be displayed before logging the diff view
        """
        packages = env.PythonWorkingSet.get_packages_in_working_set(inmanta_modules_only=True)
        version_snapshot = {self.get_inmanta_module_name(mod): version for mod, version in packages.items()}

        super()._log_snapshot_difference(version_snapshot, previous_snapshot, header)

    def log_post_install_information(self, module_name: str) -> None:
        """
        Display information about this module's installation after the actual installation.

        :param module_name: The module's name.
        """
        installed_version: Optional[version.Version] = self.get_installed_version(module_name)
        LOGGER.debug("Successfully installed module %s (v2) version %s", module_name, installed_version)

    def path_for(self, name: str) -> Optional[str]:
        """
        Returns the path to the module root directory. Should be called prior to configuring the module finder for v1 modules.
        """
        if name.startswith(ModuleV2.PKG_NAME_PREFIX):
            raise ValueError("PythonRepo instances work with inmanta module names, not Python package names.")
        package: str = self.get_namespace_package_name(name)
        mod_spec: Optional[Tuple[Optional[str], Loader]] = env.ActiveEnv.get_module_file(package)
        if mod_spec is None:
            return None
        init, mod_loader = mod_spec
        if isinstance(mod_loader, loader.PluginModuleLoader):
            # Module was found in the environment but it is associated with the v1 module loader. Since the v2 loader has
            # precedence, we can conclude the module has not been installed in v2 mode. If it were, the module could never
            # be associated with the v1 loader.
            return None
        if init is None:
            raise InvalidModuleException(f"Package {package} was installed but no __init__.py file could be found.")
        # In case of editable installs the path may contain symlinks to actual location (see
        # PythonEnvironment.get_module_file docstring). Since modules contain non-Python files (of which setuptools may not be
        # aware, therefore they may not exist in the link structure), we need the real path.
        pkg_installation_dir = os.path.dirname(os.path.realpath(init))
        if os.path.exists(os.path.join(pkg_installation_dir, ModuleV2.MODULE_FILE)):
            # normal install: __init__.py is in module root
            return pkg_installation_dir
        else:
            # editable install: __init__.py is in `inmanta_plugins/<mod_name>`
            module_root_dir = os.path.normpath(os.path.join(pkg_installation_dir, os.pardir, os.pardir))
            if os.path.exists(os.path.join(module_root_dir, ModuleV2.MODULE_FILE)):
                return module_root_dir
        raise InvalidModuleException(
            f"Invalid module at {pkg_installation_dir}: found module package but it has no {ModuleV2.MODULE_FILE}. "
            "This occurs when you install or build modules from source incorrectly. "
            "Always use the `inmanta module install` and `inmanta module build` commands to "
            "respectively install and build modules from source. Make sure to uninstall the broken package first."
        )

    @classmethod
    def from_path(cls, project: Optional["Project"], module_name: str, path: str) -> "ModuleV2":
        return ModuleV2(
            project,
            path,
            is_editable_install=os.path.exists(os.path.join(path, const.PLUGINS_PACKAGE)),
            installed_version=cls.get_installed_version(module_name),
        )

    def _get_module_name(self, module_spec: List[InmantaModuleRequirement]) -> str:
        module_name: str = super()._get_module_name(module_spec)
        if module_name.startswith(ModuleV2.PKG_NAME_PREFIX.replace("-", "_")):
            raise ValueError("PythonRepo instances work with inmanta module names, not Python package names.")
        return module_name


class ModuleV1Source(ModuleSource["ModuleV1"]):
    def __init__(self, local_repo: "ModuleRepo", remote_repo: "ModuleRepo") -> None:
        self.local_repo: ModuleRepo = local_repo
        self.remote_repo: ModuleRepo = remote_repo

    def log_pre_install_information(self, module_name: str, module_spec: List[InmantaModuleRequirement]) -> None:
        LOGGER.debug("Installing module %s (v1) %s.", module_name, super()._format_constraints(module_name, module_spec))

    def take_modules_snapshot(self, project: "Project", header: Optional[str] = None) -> Dict[str, version.Version]:
        """
        Log and return a dictionary containing currently loaded modules and their versions.

        :param header: Optional text to be displayed before logging the modules and their versions
        """

        version_snapshot = {module_name: module.version for module_name, module in project.modules.items()}
        super()._log_version_snapshot(header, version_snapshot)
        return version_snapshot

    def log_snapshot_difference_v1_modules(
        self, project: "Project", previous_snapshot: Dict[str, version.Version], header: Optional[str] = None
    ) -> None:
        """
        Logs a diff view on inmanta modules (both v1 and v2) currently loaded (in alphabetical order) and their version.

        :param project: The currently active project.
        :param previous_snapshot: Mapping of inmanta module names to their respective versions. This is the baseline against
        which the currently installed versions will be compared.
        :param header: Optional text to be displayed before logging the diff view.
        """
        version_snapshot = {module_name: module.version for module_name, module in project.modules.items()}
        super()._log_snapshot_difference(version_snapshot, previous_snapshot, header)

    def log_post_install_information(self, module: TModule) -> None:
        """
        Display information about this module's installation after the actual installation.

        :param module: The module.
        """
        local_repo = module.path
        remote_repo = gitprovider.get_remote(local_repo)
        remote_repo = f" from {remote_repo.strip()}" if remote_repo is not None else ""

        LOGGER.debug(
            "Successfully installed module %s (v1) version %s in %s%s.",
            module.name,
            module.version,
            module.path,
            remote_repo,
        )

    def install(self, project: "Project", module_spec: List[InmantaModuleRequirement]) -> Optional["ModuleV1"]:
        module_name: str = self._get_module_name(module_spec)
        preinstalled: Optional[ModuleV1] = self.get_installed_module(project, module_name)
        if preinstalled is not None:
            preinstalled_version: str = str(preinstalled.version)
            if all(preinstalled_version in constraint for constraint in module_spec):
                return preinstalled
            else:
                LOGGER.warning(
                    "Currently installed %s-%s does not match constraint %s: updating to compatible version.",
                    module_name,
                    preinstalled_version,
                    ",".join(constraint.version_spec_str() for constraint in module_spec if constraint.specs),
                )
                self.log_pre_install_information(module_name, module_spec)
                modules_pre_install = self.take_modules_snapshot(project, header="Modules versions before installation:")
                module = ModuleV1.update(
                    project, module_name, module_spec, preinstalled.path, fetch=False, install_mode=project.install_mode
                )
                self.log_snapshot_difference_v1_modules(
                    project, modules_pre_install, header="Modules versions after installation:"
                )
                self.log_post_install_information(module)
                return module
        else:
            if project.downloadpath is None:
                raise CompilerException(
                    f"Can not install module {module_name} because 'downloadpath' is not set in {project.PROJECT_FILE}"
                )
            download_path: str = os.path.join(project.downloadpath, module_name)
            result = self.remote_repo.clone(module_name, project.downloadpath)
            if not result:
                return None

            self.log_pre_install_information(module_name, module_spec)
            modules_pre_install = self.take_modules_snapshot(project, header="Modules versions before installation:")
            module = ModuleV1.update(
                project, module_name, module_spec, download_path, fetch=False, install_mode=project.install_mode
            )
            self.log_snapshot_difference_v1_modules(project, modules_pre_install, header="Modules versions after installation:")
            self.log_post_install_information(module)

            return module

    def path_for(self, name: str) -> Optional[str]:
        return self.local_repo.path_for(name)

    @classmethod
    def from_path(cls, project: Optional["Project"], module_name: str, path: str) -> "ModuleV1":
        return ModuleV1(project, path)


class ModuleRepo:
    def clone(self, name: str, dest: str) -> bool:
        raise NotImplementedError("Abstract method")

    def path_for(self, name: str) -> Optional[str]:
        # same class is used for search path and remote repos, perhaps not optimal
        raise NotImplementedError("Abstract method")


class CompositeModuleRepo(ModuleRepo):
    def __init__(self, children: List[ModuleRepo]) -> None:
        self.children = children

    def clone(self, name: str, dest: str) -> bool:
        for child in self.children:
            if child.clone(name, dest):
                return True
        return False

    def path_for(self, name: str) -> Optional[str]:
        for child in self.children:
            result = child.path_for(name)
            if result is not None:
                return result
        return None


class LocalFileRepo(ModuleRepo):
    def __init__(self, root: str, parent_root: Optional[str] = None) -> None:
        if parent_root is None:
            self.root = os.path.abspath(root)
        else:
            self.root = os.path.join(parent_root, root)

    def clone(self, name: str, dest: str) -> bool:
        try:
            gitprovider.clone(os.path.join(self.root, name), os.path.join(dest, name))
            return True
        except Exception:
            LOGGER.debug("could not clone repo", exc_info=True)
            return False

    def path_for(self, name: str) -> Optional[str]:
        path = os.path.join(self.root, name)
        if os.path.exists(path):
            return path
        return None


class RemoteRepo(ModuleRepo):
    def __init__(self, baseurl: str) -> None:
        self.baseurl = baseurl

    def clone(self, name: str, dest: str) -> bool:
        url, nbr_substitutions = re.subn(r"{}", name, self.baseurl)
        if nbr_substitutions > 1:
            raise InvalidMetadata(msg=f"Wrong repo path at {self.baseurl} : should only contain at most one {{}} pair")
        elif nbr_substitutions == 0:
            url = self.baseurl + name
        try:
            gitprovider.clone(url, os.path.join(dest, name))
            return True
        except Exception:
            LOGGER.debug("could not clone repo", exc_info=True)
            return False

    def path_for(self, name: str) -> Optional[str]:
        raise NotImplementedError("Should only be called on local repos")


def make_repo(path: str, root: Optional[str] = None) -> Union[LocalFileRepo, RemoteRepo]:
    """
    Returns the appropriate `ModuleRepo` instance (v1) for the given path.
    """
    # check that the second char is not a colon (windows)
    if ":" in path and path[1] != ":":
        return RemoteRepo(path)
    else:
        return LocalFileRepo(path, parent_root=root)


def merge_specs(mainspec: "Dict[str, List[InmantaModuleRequirement]]", new: "List[InmantaModuleRequirement]") -> None:
    """Merge two maps str->[TMetadata] by concatting their lists."""
    for req in new:
        key = req.project_name
        if key not in mainspec:
            mainspec[key] = [req]
        else:
            mainspec[key] = mainspec[key] + [req]


@stable_api
class InstallMode(str, enum.Enum):
    """
    The module install mode determines what version of a module should be selected when a module is downloaded.
    """

    release = "release"
    """
    Only use a released version that is compatible with the current compiler and any version constraints defined in the
    ``requires`` lists for the project or any other modules (see :class:`ProjectMetadata`, :class:`ModuleV1Metadata` and
    :class:`ModuleV2Metadata`).

    A module is considered released in the following situations:
      * For V1 modules: There is a tag on a commit. This tag is a valid, pep440 compliant version identifier and it's not a
                        prelease version.
      * For V2 modules: The python package was published on a Python package repository, the version identifier is pep440
                        compliant and is not a prerelease version.
    """

    prerelease = "prerelease"
    """
    Similar to :attr:`InstallMode.release` but prerelease versions are allowed as well.
    """

    master = "master"
    """
    For V1 modules: Use the module's master branch.
    For V2 modules: Equivalent to :attr:`InstallMode.prerelease`
    """


INSTALL_OPTS: List[str] = [mode.value for mode in InstallMode]  # Part of the stable API
"""
List of possible module install modes, kept for backwards compatibility. New code should use :class:`InstallMode` instead.
"""


@stable_api
class FreezeOperator(str, enum.Enum):
    eq = "=="
    compatible = "~="
    ge = ">="

    @classmethod
    def get_regex_for_validation(cls) -> str:
        all_values = [re.escape(o.value) for o in cls]
        return f"^({'|'.join(all_values)})$"


class RawParser(ABC):
    @classmethod
    @abstractmethod
    def parse(cls, source: Union[str, TextIO]) -> Mapping[str, object]:
        raise NotImplementedError()


class YamlParser(RawParser):
    @classmethod
    def parse(cls, source: Union[str, TextIO]) -> Mapping[str, object]:
        try:
            return yaml.safe_load(source)
        except yaml.YAMLError as e:
            if isinstance(source, TextIOBase):
                raise InvalidMetadata(msg=f"Invalid yaml syntax in {source.name}:\n{str(e)}") from e
            else:
                raise InvalidMetadata(msg=str(e)) from e


class CfgParser(RawParser):
    @classmethod
    def parse(cls, source: Union[str, TextIO]) -> Mapping[str, object]:
        try:
            config: configparser.ConfigParser = configparser.ConfigParser()
            config.read_string(source if isinstance(source, str) else source.read())
            if config.has_option("options", "install_requires"):
                install_requires = [r for r in config.get("options", "install_requires").split("\n") if r]
            else:
                install_requires = []
            version_tag: str = config.get("egg_info", "tag_build", fallback="")
            return {**config["metadata"], "install_requires": install_requires, "version_tag": version_tag}
        except configparser.Error as e:
            if isinstance(source, TextIOBase):
                raise InvalidMetadata(msg=f"Invalid syntax in {source.name}:\n{str(e)}") from e
            else:
                raise InvalidMetadata(msg=str(e)) from e
        except KeyError as e:
            if isinstance(source, TextIOBase):
                raise InvalidMetadata(msg=f"Metadata file {source.name} doesn't have a metadata section.") from e
            else:
                raise InvalidMetadata(msg="Metadata file doesn't have a metadata section.") from e


class RequirementsTxtFile:
    """
    This class caches the requirements specified in the requirements.txt file in memory.
    As such, this class will miss any updated applied after the object is constructed.
    """

    def __init__(self, filename: str, create_file_if_not_exists: bool = False) -> None:
        self._filename = filename
        if not os.path.exists(self._filename):
            if create_file_if_not_exists:
                with open(self._filename, "w", encoding="utf-8"):
                    pass
            else:
                raise FileNotFoundError(f"File {filename} does not exist")
        self._requirements = RequirementsTxtParser.parse(filename)

    def has_requirement_for(self, pkg_name: str) -> bool:
        """
        Returns True iff this requirements.txt file contains the given package name. The given `pkg_name` is matched
        case insensitive against the requirements in this RequirementsTxtFile.
        """
        return any(r.key == pkg_name.lower() for r in self._requirements)

    def set_requirement_and_write(self, requirement: Requirement) -> None:
        """
        Add the given requirement to the requirements.txt file and update the file on disk, replacing any existing constraints
        on this package.
        """
        new_content_file = RequirementsTxtParser.get_content_with_dep_removed(self._filename, remove_dep_on_pkg=requirement.key)
        new_content_file = new_content_file.rstrip()
        if new_content_file:
            new_content_file = f"{new_content_file}\n{requirement}"
        else:
            new_content_file = str(requirement)
        self._write(new_content_file)

    def remove_requirement_and_write(self, pkg_name: str) -> None:
        """
        Remove the dependency on the given package and update the file on disk.
        """
        if not self.has_requirement_for(pkg_name):
            return
        new_content_file = RequirementsTxtParser.get_content_with_dep_removed(self._filename, remove_dep_on_pkg=pkg_name)
        self._write(new_content_file)

    def _write(self, new_content_file: str) -> None:
        """
        Write the file to disk.
        """
        with open(self._filename, "w", encoding="utf-8") as fd:
            fd.write(new_content_file)
        self._requirements = RequirementsTxtParser.parse(self._filename)


TMetadata = TypeVar("TMetadata", bound="Metadata")


@stable_api
class Metadata(BaseModel):
    name: str
    description: Optional[str] = None
    freeze_recursive: bool = False
    freeze_operator: str = Field(default="~=", regex=FreezeOperator.get_regex_for_validation())

    _raw_parser: Type[RawParser]

    @classmethod
    def parse(cls: Type[TMetadata], source: Union[str, TextIO]) -> TMetadata:
        raw: Mapping[str, object] = cls._raw_parser.parse(source)
        try:
            return cls(**raw)
        except ValidationError as e:
            if isinstance(source, TextIOBase):
                raise InvalidMetadata(msg=f"Metadata defined in {source.name} is invalid:", validation_error=e) from e
            else:
                raise InvalidMetadata(msg=str(e), validation_error=e) from e


class MetadataFieldRequires(BaseModel):
    requires: List[str] = []

    @classmethod
    def to_list(cls, v: object) -> List[object]:
        if v is None:
            return []
        if not isinstance(v, list):
            return [v]
        return v

    @validator("requires", pre=True)
    @classmethod
    def requires_to_list(cls, v: object) -> object:
        return cls.to_list(v)


TModuleMetadata = TypeVar("TModuleMetadata", bound="ModuleMetadata")


@stable_api
class ModuleMetadata(ABC, Metadata):
    version: str
    license: str
    deprecated: Optional[bool]

    @validator("version")
    @classmethod
    def is_pep440_version(cls, v: str) -> str:
        try:
            version.Version(v)
        except version.InvalidVersion as e:
            raise ValueError(f"Version {v} is not PEP440 compliant") from e
        return v

    @classmethod
    def rewrite_version(
        cls: Type[TModuleMetadata], source: str, new_version: str, version_tag: str = ""
    ) -> Tuple[str, TModuleMetadata]:
        """
        Returns the source text with the version replaced by the new version.
        """
        metadata: TModuleMetadata = cls.parse(source)
        current_version = metadata.version
        if current_version == new_version:
            LOGGER.debug("Current version is the same as the new version: %s", current_version)

        result: str = cls._substitute_version(source, new_version, version_tag)

        try:
            new_metadata = cls.parse(result)
        except Exception:
            raise Exception("Unable to rewrite module definition.")

        # Validate whether the version and version_tag field was updated correctly in metadata file
        full_version_in_meta_data: packaging.version.Version = new_metadata.get_full_version()
        expected_full_version: packaging.version.Version = cls._compose_full_version(new_version, version_tag)
        if full_version_in_meta_data != expected_full_version:
            raise Exception(
                "Unable to write version and version tag information to the module metadata file.\n"
                "\t* For a V1 module: Does the module.yml file contain a syntax error near the version field?\n"
                "\t* For a V2 module: Does the setup.cfg file contain a syntax error near the metadata.version or "
                "the egg_info.tag_build field?"
            )

        return result, new_metadata

    @classmethod
    @abstractmethod
    def _substitute_version(cls: Type[TModuleMetadata], source: str, new_version: str, version_tag: str = "") -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_full_version(self) -> packaging.version.Version:
        """
        Return the full version (version + version tag) of this module.
        """
        raise NotImplementedError()

    @classmethod
    def _compose_full_version(cls, v: str, version_tag: str) -> packaging.version.Version:
        if not version_tag:
            return version.Version(v)
        normalized_tag: str = version_tag.lstrip(".")
        return version.Version(f"{v}.{normalized_tag}")


@stable_api
class ModuleV1Metadata(ModuleMetadata, MetadataFieldRequires):
    """
    :param name: The name of the module.
    :param description: (Optional) The description of the module
    :param version: The version of the inmanta module.
    :param license: The license for this module
    :param compiler_version: (Optional) The minimal compiler version required to compile this module.
    :param requires: (Optional) Model files import other modules. These imports do not determine a version, this
      is based on the install_mode setting of the project. Modules and projects can constrain a version in the
      requires setting. Similar to the module, version constraints are defined using
      `PEP440 syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.
    :param freeze_recursive: (Optional) This key determined if the freeze command will behave recursively or not. If
      freeze_recursive is set to false or not set, the current version of all modules imported directly in any submodule of
      this module will be set in module.yml. If it is set to true, all modules imported in any of those modules will also be
      set.
    :param freeze_operator: (Optional) This key determines the comparison operator used by the freeze command.
      Valid values are [==, ~=, >=]. *Default is '~='*
    """

    compiler_version: Optional[str] = None

    _raw_parser: Type[YamlParser] = YamlParser

    @validator("compiler_version")
    @classmethod
    def is_pep440_version_v1(cls, v: str) -> str:
        return cls.is_pep440_version(v)

    @classmethod
    def _substitute_version(cls: Type[TModuleMetadata], source: str, new_version: str, version_tag: str = "") -> str:
        new_version_obj: version.Version = cls._compose_full_version(new_version, version_tag)
        return re.sub(r"([\s]version\s*:\s*['\"\s]?)[^\"'}\s]+(['\"]?)", rf"\g<1>{new_version_obj}\g<2>", source)

    def get_full_version(self) -> packaging.version.Version:
        return version.Version(self.version)

    def to_v2(self) -> "ModuleV2Metadata":
        values = self.dict()
        if values["description"] is not None:
            values["description"] = values["description"].replace("\n", " ")
        del values["compiler_version"]
        install_requires = [ModuleV2Source.get_package_name_for(r) for r in values["requires"]]
        del values["requires"]
        values["name"] = ModuleV2Source.get_package_name_for(values["name"])
        values["version"], values["version_tag"] = ModuleV2Metadata.split_version(version.Version(values["version"]))
        return ModuleV2Metadata(**values, install_requires=install_requires)


@stable_api
class ModuleV2Metadata(ModuleMetadata):
    """
    :param name: The name of the python package that is generated when packaging this module.
                 This name should follow the format "inmanta-module-<module-name>"
    :param description: (Optional) The description of the module
    :param version: The version of the inmanta module. Should not contain build tag.
    :param version_tag: The build tag for this module version, i.e. "dev0"
    :param license: The license for this module
    :param freeze_recursive: (Optional) This key determined if the freeze command will behave recursively or not. If
      freeze_recursive is set to false or not set, the current version of all modules imported directly in any submodule of
      this module will be set in setup.cfg. If it is set to true, all modules imported in any of those modules will also be
      set.
    :param freeze_operator: (Optional) This key determines the comparison operator used by the freeze command.
      Valid values are [==, ~=, >=]. *Default is '~='*
    :param install_requires: The Python packages this module depends on.
    """

    install_requires: List[str]
    version_tag: str = ""

    _raw_parser: Type[CfgParser] = CfgParser

    @validator("version")
    @classmethod
    def is_base_version(cls, v: str) -> str:
        version_obj: version.Version = version.Version(v)
        if str(version_obj) != version_obj.base_version:
            raise ValueError(
                "setup.cfg version should be a base version without tag. Use egg_info.tag_build to configure a tag"
            )
        return v

    @classmethod
    def split_version(cls, v: packaging.version.Version) -> tuple[str, str]:
        """
        Splits a full version in a base version and a tag.
        """

        def get_version_tag(v: packaging.version.Version) -> str:
            if v.is_devrelease:
                return f"dev{v.dev}"
            if v.is_prerelease:
                # e.g. rc
                assert v.pre is not None
                return "%s%s" % (v.pre[0], v.pre[1])
            if v.is_postrelease:
                return f"post{v.post}"
            return ""

        return v.base_version, get_version_tag(v)

    @validator("version_tag")
    @classmethod
    def is_valid_version_tag(cls, v: str) -> str:
        try:
            cls._compose_full_version("1.0.0", v)
        except version.InvalidVersion as e:
            raise ValueError(f"Version tag {v} is not PEP440 compliant") from e
        return v

    @validator("name")
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        """
        The name field of a V2 module should follow the format "inmanta-module-<module-name>"
        """
        if not v.startswith(ModuleV2.PKG_NAME_PREFIX) or not len(v) > len(ModuleV2.PKG_NAME_PREFIX):
            raise ValueError(f'The name field should follow the format "{ModuleV2.PKG_NAME_PREFIX}<module-name>"')
        if "_" in v:
            raise ValueError("Module names should not contain underscores, use '-' instead.")
        return v

    def get_full_version(self) -> packaging.version.Version:
        return self._compose_full_version(self.version, self.version_tag)

    @classmethod
    def _substitute_version(cls: Type[TModuleMetadata], source: str, new_version: str, version_tag: str = "") -> str:
        result = re.sub(
            r"(\[metadata\][^\[]*[ \t\f\v]*version[ \t\f\v]*=[ \t\f\v]*)[\S]+(\n|$)",
            rf"\g<1>{new_version}\n",
            source,
        )
        if "[egg_info]" not in result:
            result = f"{result}\n[egg_info]\ntag_build = {version_tag}"
        elif "tag_build" not in result:
            result = result.replace("[egg_info]", f"[egg_info]\ntag_build = {version_tag}")
        else:
            result = re.sub(
                r"(\[egg_info\][^\[]*[ \t\f\v]*tag_build[ \t\f\v]*=)[ \t\f\v]*[\S]*(\n|$)",
                rf"\g<1> {version_tag}\n",
                result,
            )
        return result

    def to_config(self, inp: Optional[configparser.ConfigParser] = None) -> configparser.ConfigParser:
        if inp:
            out = inp
        else:
            out = configparser.ConfigParser()

        if not out.has_section("metadata"):
            out.add_section("metadata")
        for k, v in self.dict(exclude_none=True, exclude={"install_requires"}).items():
            out.set("metadata", k, str(v))

        if self.version_tag:
            if not out.has_section("egg_info"):
                out.add_section("egg_info")
            out.set("egg_info", "tag_build", self.version_tag)

        return out


@stable_api
class ModuleRepoType(enum.Enum):
    git = "git"
    package = "package"


@stable_api
class ModuleRepoInfo(BaseModel):
    url: str
    type: ModuleRepoType = ModuleRepoType.git


@dataclass(frozen=True)
class RelationPrecedenceRule:
    """
    Represents a rule defined in the relation precedence policy of the project.yml file.
    Indicates that list `first_type.first_relation_name` should be frozen
    before `then_type.then_relation_name`.
    """

    first_type: str
    first_relation_name: str
    then_type: str
    then_relation_name: str

    @classmethod
    def from_string(cls, rule: str) -> "RelationPrecedenceRule":
        """
        Create a RelationPrecedencePolicy object from its string representation.
        """
        match: Optional[re.Match[str]] = ProjectMetadata._re_relation_precedence_rule_compiled.fullmatch(rule.strip())
        if not match:
            raise Exception(
                f"Invalid rule in relation precedence policy: {rule}. "
                f"Expected syntax: '<entity-type>.<relation-name> before <entity-type>.<relation-name>'"
            )
        group_dict = match.groupdict()
        return cls(
            first_type=group_dict["ft"],
            first_relation_name=group_dict["fr"],
            then_type=group_dict["tt"],
            then_relation_name=group_dict["tr"],
        )

    def __str__(self) -> str:
        return f"{self.first_type}.{self.first_relation_name} before {self.then_type}.{self.then_relation_name}"


@stable_api
class ProjectMetadata(Metadata, MetadataFieldRequires):
    """
    :param name: The name of the project.
    :param description: (Optional) An optional description of the project
    :param author: (Optional) The author of the project
    :param author_email: (Optional) The contact email address of author
    :param license: (Optional) License the project is released under
    :param copyright: (Optional) Copyright holder name and date.
    :param modulepath: (Optional) This value is a list of paths where Inmanta should search for modules.
    :param downloadpath: (Optional) This value determines the path where Inmanta should download modules from
        repositories. This path is not automatically included in the modulepath!
    :param install_mode: (Optional) This key determines what version of a module should be selected when a module
        is downloaded. For more information see :class:`InstallMode`.
    :param repo: (Optional) A list (a yaml list) of repositories where Inmanta can find modules. Inmanta tries each repository
        in the order they appear in the list. Each element of this list requires a ``type`` and a ``url`` field. The type field
        can have the following values:

        * git: When the type is set to git, the url field should contain a template of the Git repo URL. Inmanta creates the
          git repo url by formatting {} or {0} with the name of the module. If no formatter is present it appends the name
          of the module to the URL.
        * package: When the type is set to package, the URL field should contain the URL of the Python package repository.
          The repository should be `PEP 503 <https://www.python.org/dev/peps/pep-0503/>`_ (the simple repository API)
          compliant.

        The old syntax, which only defines a Git URL per list entry is maintained for backward compatibility.
    :param requires: (Optional) This key can contain a list (a yaml list) of version constraints for modules used in this
        project. Similar to the module, version constraints are defined using
        `PEP440 syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.
    :param freeze_recursive: (Optional) This key determined if the freeze command will behave recursively or not. If
        freeze_recursive is set to false or not set, the current version of all modules imported directly in the main.cf file
        will be set in project.yml. If it is set to true, the versions of all modules used in this project will set in
        project.yml.
    :param freeze_operator: (Optional) This key determines the comparison operator used by the freeze command.
        Valid values are [==, ~=, >=]. *Default is '~='*
    :param relation_precedence_policy: [EXPERIMENTAL FEATURE] A list of rules that indicate the order in which the compiler
        should freeze lists. The following syntax should be used to specify a rule
        `<first-type>.<relation-name> before <then-type>.<relation-name>`. With this rule in
        place, the compiler will first freeze `first-type.relation-name` and only then `then-type.relation-name`.
    :param strict_deps_check: Determines whether the compiler or inmanta tools that install/update module dependencies,
        should check the virtual environment for version conflicts in a strict way or not.
        A strict check means that all transitive dependencies will be checked for version conflicts and that any violation will
        result in an error.
        When a non-strict check is done, only version conflicts in a direct dependency will result in an error.
        All other violations will only result in a warning message.
    :param agent_install_dependency_modules: [EXPERIMENTAL FEATURE] If true, when a module declares Python dependencies on
        other (v2) modules, the agent will install these dependency modules with pip. This option should only be enabled
        if the agent is configured with the appropriate pip related environment variables. The option allows to an extent
        for inter-module dependencies within handler code, even if the dependency module doesn't have any handlers that
        would otherwise be considered relevant for this agent.

        Care should still be taken when you use inter-module imports. The current code loading mechanism does not explicitly
        order reloads. A general guideline is to use qualified imports where you can (import the module rather than objects
        from the module). When this is not feasible, you should be aware of
        `Python's reload semantics <https://docs.python.org/3/library/importlib.html#importlib.reload>`_ and take this into
        account when making changes to handler code.

        Another caveat is that if the dependency module does contain code that is relevant for the agent, it will be loaded
        like any other handler code and it will be this code that is imported by any dependent modules (though depending on
        the load order the very first import may use the version installed by pip). If at some point this dependency module's
        handlers cease to be relevant for this agent, its code will remain stale. Therefore this feature should not be depended
        on in transient scenarios like this.
    """

    _raw_parser: Type[YamlParser] = YamlParser
    _re_relation_precedence_rule: str = r"^(?P<ft>[^\s.]+)\.(?P<fr>[^\s.]+)\s+before\s+(?P<tt>[^\s.]+)\.(?P<tr>[^\s.]+)$"
    _re_relation_precedence_rule_compiled: re.Pattern[str] = re.compile(_re_relation_precedence_rule)

    author: Optional[str] = None
    author_email: Optional[NameEmail] = None
    license: Optional[str] = None
    copyright: Optional[str] = None
    modulepath: List[str] = []
    repo: List[ModuleRepoInfo] = []
    downloadpath: Optional[str] = None
    install_mode: InstallMode = InstallMode.release
    requires: List[str] = []
    relation_precedence_policy: List[constr(strip_whitespace=True, regex=_re_relation_precedence_rule, min_length=1)] = []
    strict_deps_check: bool = True
    agent_install_dependency_modules: bool = False

    @validator("modulepath", pre=True)
    @classmethod
    def modulepath_to_list(cls, v: object) -> object:
        return cls.to_list(v)

    @validator("repo", pre=True)
    @classmethod
    def validate_repo_field(cls, v: object) -> List[Dict[Any, Any]]:
        v_as_list = cls.to_list(v)
        result = []
        for elem in v_as_list:
            if isinstance(elem, str):
                # Ensure backward compatibility with the version of Inmanta that didn't have support for the type field.
                result.append({"url": elem, "type": ModuleRepoType.git})
            elif isinstance(elem, dict):
                result.append(elem)
            else:
                raise ValueError(f"Value should be either a string of a dict, got {elem}")
        return result

    def get_relation_precedence_rules(self) -> List[RelationPrecedenceRule]:
        """
        Return all RelationPrecedenceRules defined in the project.yml file.
        """
        return [RelationPrecedenceRule.from_string(rule_as_str) for rule_as_str in self.relation_precedence_policy]

    def get_index_urls(self) -> List[str]:
        return [repo.url for repo in self.repo if repo.type == ModuleRepoType.package]


@stable_api
class ModuleLike(ABC, Generic[TMetadata]):
    """
    Commons superclass for projects and modules, which are both versioned by git

    :ivar name: The name for this module like instance, in the context of the Inmanta DSL.
    """

    def __init__(self, path: str) -> None:
        """
        :param path: root git directory
        """
        self._path = path
        self._metadata = self._get_metadata_from_disk()
        self.name = self.get_name_from_metadata(self._metadata)

    @classmethod
    @abstractmethod
    # Union[Project, ModuleV1, ModuleV2] would be more strict than ModuleLike[Any] but very restrictive with potential stable
    # API extension in mind.
    def from_path(cls, path: str) -> Optional["ModuleLike"]:
        """
        Get a concrete module like instance from a path. Returns None when no project or module is present at the given path.
        """
        subs: Tuple[Type[ModuleLike], ...] = (Project, Module)
        for sub in subs:
            instance: Optional[ModuleLike] = sub.from_path(path)
            if instance is not None:
                return instance
        return None

    @classmethod
    def get_first_directory_containing_file(cls, cur_dir: str, filename: str) -> str:
        """
        Travel up in the directory structure until a file with the given name is found.
        """
        fq_path_to_filename = os.path.join(cur_dir, filename)

        if os.path.exists(fq_path_to_filename):
            return cur_dir

        parent_dir = os.path.abspath(os.path.join(cur_dir, os.pardir))
        if parent_dir == cur_dir:
            raise FileNotFoundError(f"No file with name {filename} exists in any of the parent directories")

        return cls.get_first_directory_containing_file(parent_dir, filename)

    def _get_metadata_from_disk(self) -> TMetadata:
        metadata_file_path = self.get_metadata_file_path()

        if not os.path.exists(metadata_file_path):
            raise ModuleMetadataFileNotFound(f"Metadata file {metadata_file_path} does not exist")

        with open(metadata_file_path, "r", encoding="utf-8") as fd:
            return self.get_metadata_from_source(source=fd)

    def get_metadata_from_source(self, source: Union[str, TextIO]) -> TMetadata:
        """
        :param source: Either the yaml content as a string or an input stream from the yaml file
        """
        metadata_type: Type[TMetadata] = self.get_metadata_file_schema_type()
        return metadata_type.parse(source)

    @property
    def path(self) -> str:
        return self._path

    @property
    def metadata(self) -> TMetadata:
        return self._metadata

    @property
    def freeze_recursive(self) -> bool:
        return self._metadata.freeze_recursive

    @property
    def freeze_operator(self) -> str:
        return self._metadata.freeze_operator

    @abstractmethod
    def get_metadata_file_path(self) -> str:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def get_metadata_file_schema_type(cls) -> Type[TMetadata]:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def get_name_from_metadata(cls, metadata: TMetadata) -> str:
        raise NotImplementedError()

    @abstractmethod
    def add_module_requirement_persistent(self, requirement: InmantaModuleRequirement, add_as_v1_module: bool) -> None:
        """
        Add a new module requirement to the files that define requirements on other modules. This could include the
        requirements.txt file next to the metadata file of the project or module. This method updates the files on disk.

        This operation may make this object invalid or outdated if the persisted metadata has been updated since creating this
        instance.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_module_requirements(self) -> List[str]:
        """
        Returns all requirements this module has on other modules, regardless of module generation. Requirements should be on
        inmanta module names, not Python package names.
        """
        raise NotImplementedError()

    def has_module_requirement(self, module_name: str) -> bool:
        """
        :param module_name: The module name in lower cases.
        :returns: True iff the module defines a dependency on the given module in one of the files that
                  declare dependencies module dependencies. This could include the requirements.txt file
                  next to the metadata file of the project or module.
        """
        return any(module_name == InmantaModuleRequirement.parse(req).key for req in self.get_module_requirements())

    def _load_file(self, ns: Namespace, file: str) -> Tuple[List[Statement], BasicBlock]:
        ns.location = Location(file, 1)
        statements = []  # type: List[Statement]
        stmts = plyInmantaParser.parse(ns, file)
        block = BasicBlock(ns)
        for s in stmts:
            if isinstance(s, BiStatement):
                statements.append(s)
                block.add(s)
            elif isinstance(s, DefinitionStatement):
                statements.append(s)
                block.add_definition(s)
            elif isinstance(s, str) or isinstance(s, LocatableString):
                pass
            else:
                assert isinstance(s, DynamicStatement)
                block.add(s)
        return (statements, block)

    def _get_requirements_txt_as_list(self) -> List[str]:
        """
        Returns the contents of the requirements.txt file as a list of requirements, if it exists.
        """
        file = os.path.join(self._path, "requirements.txt")
        if os.path.exists(file):
            return RequirementsTxtParser.parse_requirements_as_strs(file)
        else:
            return []

    @abstractmethod
    def get_all_python_requirements_as_list(self) -> List[str]:
        """
        Returns all Python requirements specified by this module like, including requirements on V2 modules.
        """
        raise NotImplementedError()

    def get_strict_python_requirements_as_list(self) -> List[str]:
        """
        Returns the strict python requirements specified by this module like, meaning all Python requirements excluding those on
        inmanta modules.
        """
        return [req for req in self.get_all_python_requirements_as_list() if not req.startswith(ModuleV2.PKG_NAME_PREFIX)]

    def get_module_v2_requirements(self) -> List[InmantaModuleRequirement]:
        """
        Returns all requirements this module like has on v2 modules.
        """
        return [
            InmantaModuleRequirement.parse(ModuleV2Source.get_inmanta_module_name(req))
            for req in self.get_all_python_requirements_as_list()
            if req.startswith(ModuleV2.PKG_NAME_PREFIX)
        ]


class ModuleLikeWithYmlMetadataFile(ABC):
    @abstractmethod
    def get_metadata_file_path(self) -> str:
        raise NotImplementedError()

    def add_module_requirement_to_requires_and_write(self, requirement: InmantaModuleRequirement) -> None:
        """
        Updates the metadata file of the given project or V1 module by adding the given requirement the `requires` section.

        :param requirement: The requirement to add.
        """
        # Parse cfg file
        content: CommentedMap = PreservativeYamlParser.parse(self.get_metadata_file_path())
        # Update requires
        if "requires" in content:
            existing_matching_reqs: List[str] = [
                r for r in content["requires"] if InmantaModuleRequirement.parse(r).key == requirement.key
            ]
            for r in existing_matching_reqs:
                content["requires"].remove(r)
            content["requires"].append(str(requirement))
        else:
            content["requires"] = [str(requirement)]
        # Write file back to disk
        PreservativeYamlParser.dump(self.get_metadata_file_path(), content)

    def has_module_requirement_in_requires(self, module_name: str) -> bool:
        """
        Returns true iff the given module is present in the `requires` list of the given project or module metadata file.
        """
        content: CommentedMap = PreservativeYamlParser.parse(self.get_metadata_file_path())
        if "requires" not in content:
            return False
        return any(r for r in content["requires"] if InmantaModuleRequirement.parse(r).key == module_name)

    def remove_module_requirement_from_requires_and_write(self, module_name: str) -> None:
        """
        Updates the metadata file of the given project or module by removing the given requirement frm the `requires` section.

        :param module_name: The Inmanta module name is lower case.
        """
        if not self.has_module_requirement_in_requires(module_name):
            return
        content: CommentedMap = PreservativeYamlParser.parse(self.get_metadata_file_path())
        content["requires"] = [r for r in content["requires"] if InmantaModuleRequirement.parse(r).key != module_name]
        PreservativeYamlParser.dump(self.get_metadata_file_path(), content)


@stable_api
class Project(ModuleLike[ProjectMetadata], ModuleLikeWithYmlMetadataFile):
    """
    An inmanta project

    :ivar modules: The collection of loaded modules for this project.
    :ivar module_source: The v2 module source for this project.
    """

    PROJECT_FILE = "project.yml"
    _project = None

    def __init__(
        self,
        path: str,
        autostd: bool = True,
        main_file: str = "main.cf",
        venv_path: Optional[Union[str, "env.VirtualEnv"]] = None,
        attach_cf_cache: bool = True,
        strict_deps_check: Optional[bool] = None,
    ) -> None:
        """
        Initialize the project, this includes
         * Loading the project.yaml (into self._metadata)
         * Setting paths from project.yaml
         * Loading all modules in the module path (into self.modules)
        It does not include
         * verify if project.yml corresponds to the modules in self.modules

        Instances of this class can be created by in two different ways:
        1) Via the Project.get() method
        2) Via the constructor: Always call the Project.set() method after the constructor call.
                                Project instances should only be created via the constructor in test cases.

        :param path: The directory where the project is located
        :param venv_path: Path to the directory that will contain the Python virtualenv.
                          This can be an existing or a non-existing directory.
        :param strict_deps_check: Overrides the strict_deps_check configuration option from the project.yml file if the
                                  provided value is different from None.
        """
        if not os.path.exists(path):
            raise ProjectNotFoundException(f"Directory {path} doesn't exist")
        super().__init__(path)
        self.project_path = path
        self.main_file = main_file

        self._ast_cache: Optional[Tuple[List[Statement], BasicBlock]] = None  # Cache for expensive method calls
        self._metadata.modulepath = [os.path.abspath(os.path.join(path, x)) for x in self._metadata.modulepath]
        self.module_source: ModuleV2Source = ModuleV2Source(self.metadata.get_index_urls())
        self.module_source_v1: ModuleV1Source = ModuleV1Source(
            local_repo=CompositeModuleRepo([make_repo(x) for x in self.modulepath]),
            remote_repo=CompositeModuleRepo(
                [make_repo(repo.url, root=path) for repo in self._metadata.repo if repo.type == ModuleRepoType.git]
            ),
        )

        if self._metadata.downloadpath is not None:
            self._metadata.downloadpath = os.path.abspath(os.path.join(path, self._metadata.downloadpath))
            if self._metadata.downloadpath not in self._metadata.modulepath:
                LOGGER.warning("Downloadpath is not in module path! Module install will not work as expected")

            if not os.path.exists(self._metadata.downloadpath):
                os.mkdir(self._metadata.downloadpath)

        self.virtualenv: env.ActiveEnv
        if venv_path is None:
            self.virtualenv = env.process_env
        else:
            if isinstance(venv_path, env.VirtualEnv):
                self.virtualenv = venv_path
            else:
                venv_path = os.path.abspath(venv_path)
                self.virtualenv = env.VirtualEnv(venv_path)

        self.loaded = False
        self.modules: Dict[str, Module] = {}
        self.root_ns = Namespace("__root__")
        self.autostd = autostd
        if attach_cf_cache:
            cache_manager.attach_to_project(path)

        if strict_deps_check is not None:
            self.strict_deps_check = strict_deps_check
        else:
            self.strict_deps_check = self._metadata.strict_deps_check

    def get_relation_precedence_policy(self) -> List[RelationPrecedenceRule]:
        return self._metadata.get_relation_precedence_rules()

    @classmethod
    def from_path(cls: Type[TProject], path: str) -> Optional[TProject]:
        return cls(path=path) if os.path.exists(os.path.join(path, cls.PROJECT_FILE)) else None

    def install_module(self, module_req: InmantaModuleRequirement, install_as_v1_module: bool) -> None:
        """
        Install the given module. If attempting to as v2, this method implicitly trusts any Python package with the
        corresponding name.
        Does not reinstall if the given module requirement is already met.
        """
        installed_module: Optional[Module]
        if install_as_v1_module:
            installed_module = self.module_source_v1.install(self, module_spec=[module_req])
        else:
            installed_module = self.module_source.install(self, module_spec=[module_req])
        if not installed_module:
            raise ModuleNotFoundException(
                f"Failed to install module {module_req} as {'V1' if install_as_v1_module else 'V2'} module"
            )
        self.modules[installed_module.name] = installed_module

    @classmethod
    def get_name_from_metadata(cls, metadata: ProjectMetadata) -> str:
        return metadata.name

    @property
    def install_mode(self) -> InstallMode:
        return self._metadata.install_mode

    @property
    def modulepath(self) -> List[str]:
        return self._metadata.modulepath

    @property
    def downloadpath(self) -> Optional[str]:
        return self._metadata.downloadpath

    def get_metadata_file_path(self) -> str:
        return os.path.join(self._path, Project.PROJECT_FILE)

    @classmethod
    def get_metadata_file_schema_type(cls) -> Type[ProjectMetadata]:
        return ProjectMetadata

    @classmethod
    def get_project_dir(cls, cur_dir: str) -> str:
        """
        Find the project directory where we are working in. Traverse up until we find Project.PROJECT_FILE or reach /
        """
        try:
            return cls.get_first_directory_containing_file(cur_dir, Project.PROJECT_FILE)
        except FileNotFoundError:
            raise ProjectNotFoundException("Unable to find an inmanta project (project.yml expected)")

    @classmethod
    def get(cls, main_file: str = "main.cf", strict_deps_check: Optional[bool] = None) -> "Project":
        """
        Get the instance of the project
        """
        if cls._project is None:
            cls._project = Project(cls.get_project_dir(os.curdir), main_file=main_file, strict_deps_check=strict_deps_check)

        return cls._project

    @classmethod
    def set(cls, project: "Project", *, clean: bool = True) -> None:
        """
        Set the instance of the project.

        :param clean: Clean up all side effects of any previously loaded projects. Clears the registered plugins and loaded
            Python plugins packages.
        """
        cls._project = project
        os.chdir(project._path)
        if clean:
            plugins.PluginMeta.clear()
            loader.unload_inmanta_plugins()
        loader.PluginModuleFinder.reset()

    def install_modules(self, *, bypass_module_cache: bool = False, update_dependencies: bool = False) -> None:
        """
        Installs all modules, both v1 and v2.

        :param bypass_module_cache: Fetch the module data from disk even if a cache entry exists.
        :param update_dependencies: Update all Python dependencies (recursive) to their latest versions.
        """
        if not self.is_using_virtual_env():
            self.use_virtual_env()

        self.load_module_recursive(install=True, bypass_module_cache=bypass_module_cache)

        indexes_urls: List[str] = self.metadata.get_index_urls()
        # Verify non-python part
        self.verify_modules_cache()
        self.verify_module_version_compatibility()

        # do python install
        pyreq: List[Requirement] = [Requirement.parse(x) for x in self.collect_python_requirements()]

        if len(pyreq) > 0:
            # upgrade both direct and transitive module dependencies: eager upgrade strategy
            self.virtualenv.install_from_index(
                pyreq,
                upgrade=update_dependencies,
                index_urls=indexes_urls if indexes_urls else None,
                upgrade_strategy=env.PipUpgradeStrategy.EAGER,
            )

        self.verify()

    def load(self, install: bool = False) -> None:
        """
        Load this project's AST and plugins.

        :param install: Whether to install the project's modules before attempting to load it.
        """
        if not self.loaded:
            if not self.is_using_virtual_env():
                self.use_virtual_env()
            if install:
                self.install_modules()
            self.get_complete_ast()
            self.loaded = True
            self.verify()
            self.load_plugins()

    def invalidate_state(self, module: Optional[str] = None) -> None:
        """
        Invalidate this project's state, forcing a reload next time load is called.

        :param module: Invalidate the state for a single module. If omitted, invalidates the state for all modules.
        """
        if module is not None:
            if module in self.modules:
                del self.modules[module]
        else:
            self.modules = {}
        self.loaded = False

    def get_ast(self) -> Tuple[List[Statement], BasicBlock]:
        if self._ast_cache is None:
            self._ast_cache = self.__load_ast()
        return self._ast_cache

    def get_imports(self) -> List[DefineImport]:
        (statements, _) = self.get_ast()
        imports = [x for x in statements if isinstance(x, DefineImport)]
        if self.autostd:
            std_locatable = LocatableString("std", Range("__internal__", 1, 1, 1, 1), -1, self.root_ns)
            imp = DefineImport(std_locatable, std_locatable)
            imp.location = std_locatable.location
            imports.insert(0, imp)
        return imports

    def get_complete_ast(self) -> Tuple[List[Statement], List[BasicBlock]]:
        start = time()
        # load ast
        (statements, block) = self.get_ast()
        blocks = [block]
        statements = [x for x in statements]

        for _, nstmt, nb in self.load_module_recursive():
            statements.extend(nstmt)
            blocks.append(nb)

        end = time()
        LOGGER.debug("Parsing took %f seconds", end - start)
        cache_manager.log_stats()
        return (statements, blocks)

    def __load_ast(self) -> Tuple[List[Statement], BasicBlock]:
        main_ns = Namespace("__config__", self.root_ns)
        return self._load_file(main_ns, os.path.join(self.project_path, self.main_file))

    def get_modules(self) -> Dict[str, "Module"]:
        self.load()
        return self.modules

    def get_module(
        self,
        full_module_name: str,
        *,
        allow_v1: bool = False,
        install_v1: bool = False,
        install_v2: bool = False,
        bypass_module_cache: bool = False,
    ) -> "Module":
        """
        Get a module instance for a given module name. Caches modules by top level name for later access. The install parameters
        allow to install the module if it has not been installed yet. If both install parameters are False, the module is
        expected to be preinstalled.

        :param full_module_name: The full name of the module. If this is a submodule, the corresponding top level module is
            used.
        :param allow_v1: Allow this module to be loaded as v1.
        :param install_v1: Allow installing this module as v1 if it has not yet been installed. This option is ignored if
            allow_v1=False.
        :param install_v2: Allow installing this module as v2 if it has not yet been installed, implicitly trusting any Python
            package with the corresponding name.
        :param bypass_module_cache: Fetch the module data from disk even if a cache entry exists.
        """
        parts = full_module_name.split("::")
        module_name = parts[0]

        def use_module_cache() -> bool:
            if bypass_module_cache:
                return False
            if module_name not in self.modules:
                return False
            if not allow_v1 and not isinstance(self.modules[module_name], ModuleV2):
                # Reload module because it was loaded as a V1 module, while it should be loaded as a V2 module
                return False
            return True

        if use_module_cache():
            return self.modules[module_name]
        return self.load_module(module_name, allow_v1=allow_v1, install_v1=install_v1, install_v2=install_v2)

    def load_module_recursive(
        self, install: bool = False, bypass_module_cache: bool = False
    ) -> List[Tuple[str, List[Statement], BasicBlock]]:
        """
        Loads this project's modules and submodules by recursively following import statements starting from the project's main
        file.

        For each imported submodule, return a triple of name, statements, basicblock

        :param install: Run in install mode, installing any modules that have not yet been installed. If install is False,
            all modules are expected to be preinstalled. For security reasons installation of v2 modules is based on explicit
            Python requirements rather than on imports.
        :param bypass_module_cache: Fetch the module data from disk even if a cache entry exists.
        """
        ast_by_top_level_mod: Dict[str, List[Tuple[str, List[Statement], BasicBlock]]] = defaultdict(list)

        # List of imports that still have to be loaded.
        # get imports: don't use a set because this collection is used to drive control flow and we want to keep control flow as
        # deterministic as possible
        imports: List[DefineImport] = [x for x in self.get_imports()]

        # All imports of the entire project
        all_imports: Set[DefineImport] = set(imports)

        v2_modules: Set[str] = set()
        """
        Set of modules that should be loaded as a V2 module.
        """
        set_up: Set[str] = set()
        """
        Set of top level modules that have been set up (setup_module()).
        """
        done: Dict[str, Dict[str, DefineImport]] = defaultdict(dict)
        """
        Submodules, grouped by top level that have been fully loaded: AST has been loaded into ast_by_top_level_mod and its
        imports have been added to the queue (load_sub_module()).
        """

        def require_v2(module_name: str) -> None:
            """
            Ensure that the module with the given name gets loaded as a V2 module in a next iteration.
            """
            if module_name in v2_modules:
                # already v2
                return
            v2_modules.add(module_name)
            if module_name in set_up:
                set_up.remove(module_name)
            if module_name in done:
                # some submodules already loaded as v1 => reload
                add_imports_to_be_loaded(done[module_name].values())
                del done[module_name]
                if module_name in ast_by_top_level_mod:
                    del ast_by_top_level_mod[module_name]

        def load_module_v2_requirements(module_like: ModuleLike) -> None:
            """
            Loads all v2 modules explicitly required by the supplied module like instance, installing them if install=True. If
            any of these requirements have already been loaded as v1, queues them for reload.
            """
            for requirement in module_like.get_module_v2_requirements():
                # load module
                self.get_module(
                    requirement.key,
                    allow_v1=False,
                    install_v2=install,
                    bypass_module_cache=bypass_module_cache,
                )
                # queue AST reload
                require_v2(requirement.key)

        def setup_module(module: Module) -> None:
            """
            Sets up a top level module, making sure all its v2 requirements are loaded correctly. V2 modules do not support
            import-based installation because of security reasons (it would mean we implicitly trust any `inmanta-module-x`
            package for the module we're trying to load). As a result we need to make sure all required v2 modules are present
            in a set up stage.
            """
            if module.name in set_up:
                # already set up
                return
            if isinstance(module, ModuleV2):
                # register it as a v2 module so that any subsequent require_v2 calls
                require_v2(module.name)
            load_module_v2_requirements(module)
            set_up.add(module.name)

        def load_sub_module(module: Module, imp: DefineImport) -> None:
            """
            Loads a submodule's AST and processes its imports. Enforces dependency generation directionality (v1 can depend on
            v2 but not the other way around). If any modules have already been loaded with an incompatible generation, queues
            them for reload.
            Does not install any v2 modules.
            """
            parts: List[str] = imp.name.split("::")
            for i in range(1, len(parts) + 1):
                subs = "::".join(parts[0:i])
                if subs in done[module.name]:
                    continue
                (nstmt, nb) = module.get_ast(subs)

                done[module.name][subs] = imp
                ast_by_top_level_mod[module.name].append((subs, nstmt, nb))

                # get imports and add to list
                subs_imports: List[DefineImport] = module.get_imports(subs)
                add_imports_to_be_loaded(subs_imports)
                if isinstance(module, ModuleV2):
                    # A V2 module can only depend on V2 modules. Ensure that all dependencies
                    # of this module will be loaded as a V2 module.
                    for dep_module_name in (subs_imp.name.split("::")[0] for subs_imp in subs_imports):
                        require_v2(dep_module_name)

        def add_imports_to_be_loaded(new_imports: Iterable[DefineImport]) -> None:
            imports.extend(new_imports)
            all_imports.update(new_imports)

        # load this project's v2 requirements
        load_module_v2_requirements(self)

        # Loop over imports. For each import:
        # 1. Load the top level module. For v1, install if install=True, for v2 import-based installation is disabled for
        #   security reasons. v2 modules installation is done in step 2.
        # 2. Set up top level module if it has not been set up yet, loading v2 requirements and installing them if install=True.
        # 3. Load AST for imported submodule and its parent modules, queueing any transitive imports.
        while len(imports) > 0:
            imp: DefineImport = imports.pop()
            ns: str = imp.name

            module_name: str = ns.split("::")[0]

            if ns in done[module_name]:
                continue

            try:
                # get module
                module: Module = self.get_module(
                    module_name,
                    allow_v1=module_name not in v2_modules,
                    install_v1=install,
                    install_v2=False,
                    bypass_module_cache=bypass_module_cache,
                )
                setup_module(module)
                load_sub_module(module, imp)
            except (InvalidModuleException, ModuleNotFoundException) as e:
                raise ModuleLoadingException(ns, imp, e)

        # Remove modules from self.modules that were not part of an import statement.
        # This happens when a module or a project defines a V2 module requirement in
        # its dependencies, but the requirement is never imported anywhere.
        loaded_modules: Set[str] = set(self.modules.keys())
        imported_modules: Set[str] = set(i.name.split("::")[0] for i in all_imports)
        for module_to_unload in loaded_modules - imported_modules:
            self.invalidate_state(module_to_unload)

        return list(chain.from_iterable(ast_by_top_level_mod.values()))

    def load_module(
        self,
        module_name: str,
        *,
        allow_v1: bool = False,
        install_v1: bool = False,
        install_v2: bool = False,
    ) -> "Module":
        """
        Get a module instance for a given module name. The install parameters allow to install the module if it has not been
        installed yet. If both install parameters are False, the module is expected to be preinstalled.

        :param module_name: The name of the module.
        :param allow_v1: Allow this module to be loaded as v1.
        :param install_v1: Allow installing this module as v1 if it has not yet been installed. This option is ignored if
            allow_v1=False.
        :param install_v2: Allow installing this module as v2 if it has not yet been installed, implicitly trusting any Python
            package with the corresponding name.
        """
        if not self.is_using_virtual_env():
            self.use_virtual_env()
        reqs: Mapping[str, List[InmantaModuleRequirement]] = self.collect_requirements()
        module_reqs: List[InmantaModuleRequirement] = (
            list(reqs[module_name]) if module_name in reqs else [InmantaModuleRequirement.parse(module_name)]
        )

        module: Optional[Union[ModuleV1, ModuleV2]]
        try:
            module = self.module_source.get_module(self, module_reqs, install=install_v2)
            if module is not None and self.module_source_v1.path_for(module_name) is not None:
                LOGGER.warning("Module %s is installed as a V1 module and a V2 module: V1 will be ignored.", module_name)
            if module is None and allow_v1:
                module = self.module_source_v1.get_module(self, module_reqs, install=install_v1)
        except InvalidModuleException:
            raise
        except env.ConflictingRequirements:
            raise
        except Exception as e:
            raise InvalidModuleException(f"Could not load module {module_name}") from e

        if module is None:
            raise ModuleNotFoundException(
                f"Could not find module {module_name}. Please make sure to add any module v2 requirements with"
                " `inmanta module add --v2` and to install all the project's dependencies with `inmanta project install`."
            )
        if isinstance(module, ModuleV1):
            warnings.warn(
                InmantaWarning(
                    (
                        f"Loaded V1 module {module.name}. The use of V1 modules is deprecated."
                        " Use the equivalent V2 module instead."
                    )
                )
            )
        self.modules[module_name] = module
        return module

    def load_plugins(self) -> None:
        """
        Load all plug-ins
        """
        if not self.loaded:
            LOGGER.warning("loading plugins on project that has not been loaded completely")

        # ensure the loader is properly configured
        loader.PluginModuleFinder.configure_module_finder(self.modulepath)

        for module in self.modules.values():
            module.load_plugins()

    def verify(self) -> None:
        """
        Verifies the integrity of the loaded project, with respect to both inter-module requirements and the Python environment.
        """
        LOGGER.info("verifying project")
        self.verify_modules_cache()
        self.verify_module_version_compatibility()
        self.verify_python_requires()

    def verify_python_environment(self) -> None:
        """
        Verifies the integrity of the loaded project with respect to the Python environment, over which the project has no
        direct control.
        """
        self.verify_modules_cache()
        self.verify_python_requires()

    def verify_modules_cache(self) -> None:
        if not self._modules_cache_is_valid():
            raise CompilerException(
                "Not all modules were loaded correctly as a result of transitive dependencies. A recompile should load them"
                " correctly."
            )

    def verify_module_version_compatibility(self) -> None:
        """
        Check if all the required modules for this module have been loaded. Assumes the modules cache is valid and up to date.

        :raises CompilerException: When one or more of the requirements of the project is not satisfied.
        """
        requirements: Dict[str, List[InmantaModuleRequirement]] = self.collect_requirements()

        exc_message = ""
        for name, spec in requirements.items():
            if name not in self.modules:
                # the module is in the project requirements but it is not part of the loaded AST so there is no need to verify
                # its compatibility
                LOGGER.warning("Module %s is present in requires but it is not used by the model.", name)
                continue
            module = self.modules[name]
            version = parse_version(str(module.version))
            for r in spec:
                if version not in r:
                    exc_message += f"\n\t* requirement {r} on module {name} not fulfilled, now at version {version}."

        if exc_message:
            exc_message = f"The following requirements were not satisfied:{exc_message}"
            if self.metadata.install_mode == InstallMode.master:
                exc_message += (
                    "\nThe release type of the project is set to 'master'. Set it to a value that is "
                    "appropriate for the version constraint or remove the version constraint. After that, "
                    "run `inmanta project update` to resolve this issue."
                )
            else:
                exc_message += "\nRun `inmanta project update` to resolve this."
            raise CompilerException(exc_message)

    def verify_python_requires(self) -> None:
        """
        Verifies no incompatibilities exist within the Python environment with respect to installed module v2 requirements.
        """
        if self.strict_deps_check:
            constraints: List[Requirement] = [Requirement.parse(item) for item in self.collect_python_requirements()]
            env.ActiveEnv.check(strict_scope=re.compile(f"{ModuleV2.PKG_NAME_PREFIX}.*"), constraints=constraints)
        else:
            if not env.ActiveEnv.check_legacy(in_scope=re.compile(f"{ModuleV2.PKG_NAME_PREFIX}.*")):
                raise CompilerException(
                    "Not all installed modules are compatible: requirements conflicts were found. Please resolve any conflicts"
                    " before attempting another compile. Run `pip check` to check for any incompatibilities."
                )

    def _modules_cache_is_valid(self) -> bool:
        """
        Verify the modules cache after changes have been made to the Python environment. Returns False if any modules
        somehow got installed as another generation or with another version as the one that has been loaded into the AST.

        When this situation occurs, the compiler state is invalid and the compile needs to either abort or attempt recovery.
        The modules cache, from which the AST was loaded, is out of date, therefore at least a partial AST regeneration
        would be required to recover.

        Scenario's that could trigger this state:
            1.
                - latest v2 mod a is installed
                - some v1 mod depends on v2 mod b, which depends on a<2
                - during loading, after a has been loaded, mod b is installed
                - Python downgrades transitive dependency a to a<2
            2.
                - latest v2 mod a is installed
                - some v1 (or even v2 when in install mode) mod depends on a<2
                - after loading, during plugin requirements install, `pip install a<2` is run
                - Python downgrades direct dependency a to a<2
        In both cases, a<2 might be a valid version, but since it was installed transitively after the compiler has loaded
        module a, steps would need to be taken to take this change into account.
        """
        result: bool = True
        for name, module in self.modules.items():
            installed: Optional[ModuleV2] = self.module_source.get_installed_module(self, name)
            if installed is None:
                if module.GENERATION == ModuleGeneration.V1:
                    # Loaded module as V1 and no installed V2 module found: no issues with this module
                    continue
                raise CompilerException(
                    f"Invalid state: compiler has loaded module {name} as v2 but it is nowhere to be found."
                )
            else:
                if module.GENERATION == ModuleGeneration.V1:
                    LOGGER.warning(
                        "Compiler has loaded module %s as v1 but it has later been installed as v2 as a side effect.", name
                    )
                    result = False
                elif installed.version != module.version:
                    LOGGER.warning(
                        "Compiler has loaded module %s==%s but %s==%s has later been installed as a side effect.",
                        name,
                        module.version,
                        name,
                        installed.version,
                    )
                    result = False
        return result

    def is_using_virtual_env(self) -> bool:
        return self.virtualenv.is_using_virtual_env()

    def use_virtual_env(self) -> None:
        """
        Use the virtual environment. This activates the environment for the current process.
        """
        self.virtualenv.use_virtual_env()

    def sorted_modules(self) -> List["Module"]:
        """
        Return a list of all modules, sorted on their name
        """
        names = list(self.modules.keys())
        names = sorted(names)

        mod_list = []
        for name in names:
            mod_list.append(self.modules[name])

        return mod_list

    def log_installed_modules(self) -> None:
        """
        Log the name, version and generation (v1 or v2) of all installed modules.
        """
        LOGGER.info("The following modules are currently installed:")

        sorted_modules: List["Module"] = self.sorted_modules()

        def get_modules_with_gen(gen: ModuleGeneration) -> Sequence["Module"]:
            return list(filter(lambda mod: mod.GENERATION == gen, sorted_modules))

        v1_modules: Sequence["ModuleV1"] = cast(list["ModuleV1"], get_modules_with_gen(ModuleGeneration.V1))
        v2_modules: Sequence["ModuleV2"] = cast(list["ModuleV2"], get_modules_with_gen(ModuleGeneration.V2))

        if v2_modules:
            LOGGER.info("V2 modules:")
            for v2_mod in v2_modules:
                path = f" ({v2_mod.path})" if v2_mod._is_editable_install else ""
                LOGGER.info(f"  {v2_mod.name}: {v2_mod.version}{path}")
        if v1_modules:
            LOGGER.info("V1 modules:")
            for v1_mod in v1_modules:
                LOGGER.info(f"  {v1_mod.name}: {v1_mod.version}")

    def add_module_requirement_persistent(self, requirement: InmantaModuleRequirement, add_as_v1_module: bool) -> None:
        # Add requirement to metadata file
        if add_as_v1_module:
            self.add_module_requirement_to_requires_and_write(requirement)
            # Refresh in-memory metadata
            with open(self.get_metadata_file_path(), "r", encoding="utf-8") as fd:
                self._metadata = ProjectMetadata.parse(fd)
        # Update requirements.txt file
        requirements_txt_file_path = os.path.join(self._path, "requirements.txt")
        if not add_as_v1_module:
            requirements_txt_file = RequirementsTxtFile(requirements_txt_file_path, create_file_if_not_exists=True)
            requirements_txt_file.set_requirement_and_write(requirement.get_python_package_requirement())
        elif os.path.exists(requirements_txt_file_path):
            requirements_txt_file = RequirementsTxtFile(requirements_txt_file_path)
            requirements_txt_file.remove_requirement_and_write(requirement.get_python_package_requirement().key)

    def get_module_requirements(self) -> List[str]:
        return [*self.metadata.requires, *(str(req) for req in self.get_module_v2_requirements())]

    def requires(self) -> "List[InmantaModuleRequirement]":
        """
        Get the requires for this project
        """
        # filter on import stmt
        reqs = []
        for spec in self._metadata.requires:
            req = [x for x in parse_requirements(spec)]
            if len(req) > 1:
                print("Module file for %s has bad line in requirements specification %s" % (self._path, spec))
            reqe = InmantaModuleRequirement(req[0])
            reqs.append(reqe)
        return [*reqs, *self.get_module_v2_requirements()]

    def collect_requirements(self) -> "Dict[str, List[InmantaModuleRequirement]]":
        """
        Collect the list of all module requirements of all modules in the project.
        """
        specs: Dict[str, List[InmantaModuleRequirement]] = {}
        merge_specs(specs, self.requires())
        for module in self.modules.values():
            reqs = module.requires()
            merge_specs(specs, reqs)
        return specs

    def collect_imported_requirements(self) -> "Dict[str, List[InmantaModuleRequirement]]":
        imports = set([x.name.split("::")[0] for x in self.get_complete_ast()[0] if isinstance(x, DefineImport)])
        if self.autostd:
            imports.add("std")
        specs: Dict[str, List[InmantaModuleRequirement]] = self.collect_requirements()

        def get_spec(name: str) -> "List[InmantaModuleRequirement]":
            if name in specs:
                return specs[name]
            return [InmantaModuleRequirement.parse(name)]

        return {name: get_spec(name) for name in imports}

    def collect_python_requirements(self) -> List[str]:
        """
        Collect the list of all python requirements of all modules in this project, excluding those on inmanta modules.
        """
        reqs = chain(
            chain.from_iterable([mod.get_strict_python_requirements_as_list() for mod in self.modules.values()]),
            self.get_strict_python_requirements_as_list(),
        )
        return list(set(reqs))

    def get_root_namespace(self) -> Namespace:
        return self.root_ns

    def get_freeze(self, mode: str = "==", recursive: bool = False) -> Dict[str, str]:
        # collect in scope modules
        if not recursive:
            modules = {m.name: m for m in (self.get_module(imp.name, allow_v1=True) for imp in self.get_imports())}
        else:
            modules = self.get_modules()

        out = {}
        for name, mod in modules.items():
            version = str(mod.version)
            out[name] = mode + " " + version

        return out

    def get_all_python_requirements_as_list(self) -> List[str]:
        return self._get_requirements_txt_as_list()

    def module_v2_source_configured(self) -> bool:
        """
        Returns True iff this project has one or more module v2 sources configured.
        """
        return any(True for repo in self._metadata.repo if repo.type == ModuleRepoType.package)


@stable_api
class DummyProject(Project):
    """Placeholder project that does nothing"""

    def __init__(self, autostd: bool = True) -> None:
        super().__init__(tempfile.gettempdir(), autostd=autostd, attach_cf_cache=False)

    def _get_metadata_from_disk(self) -> ProjectMetadata:
        return ProjectMetadata(name="DUMMY")


@stable_api
class ModuleGeneration(enum.Enum):
    """
    The generation of a module. This might affect the on-disk structure of a module as well as how it's distributed.
    """

    V1: int = 1
    V2: int = 2


@stable_api
class Module(ModuleLike[TModuleMetadata], ABC):
    """
    This class models an inmanta configuration module
    """

    MODEL_DIR = "model"
    MODULE_FILE: str
    GENERATION: ModuleGeneration

    def __init__(self, project: Optional[Project], path: str) -> None:
        """
        Create a new configuration module

        :param project: A reference to the project this module belongs to.
        :param path: Where is the module stored
        """
        if not os.path.exists(path):
            raise InvalidModuleException(f"Directory {path} doesn't exist")
        super().__init__(path)

        if self.metadata.deprecated:
            warnings.warn(ModuleDeprecationWarning(f"Module {self.name} has been deprecated"))
        self._project: Optional[Project] = project
        self.ensure_versioned()
        self.model_dir = os.path.join(self.path, Module.MODEL_DIR)

        self._ast_cache: Dict[str, Tuple[List[Statement], BasicBlock]] = {}  # Cache for expensive method calls
        self._import_cache: Dict[str, List[DefineImport]] = {}  # Cache for expensive method calls

    @classmethod
    @abstractmethod
    def from_path(cls, path: str) -> Optional["Module"]:
        subs: Tuple[Type[Module], ...] = (ModuleV1, ModuleV2)
        for sub in subs:
            instance: Optional[Module] = sub.from_path(path)
            if instance is not None:
                return instance
        return None

    def requires(self) -> "List[InmantaModuleRequirement]":
        """
        Return all requirements this module has to other modules as a list of requirements.
        """
        reqs = []
        for spec in self.get_module_requirements():
            req = [x for x in parse_requirements(spec)]
            if len(req) > 1:
                print(f"Module file for {self._path} has bad line in requirements specification {spec}")
            reqe = InmantaModuleRequirement(req[0])
            reqs.append(reqe)
        return reqs

    @classmethod
    def get_module_dir(cls, module_subdirectory: str) -> str:
        """
        Find the top level module from the given subdirectory of a module.
        """
        try:
            return cls.get_first_directory_containing_file(module_subdirectory, cls.MODULE_FILE)
        except FileNotFoundError:
            raise InvalidModuleException(f"Directory {module_subdirectory} is not part of a valid {cls.GENERATION.name} module")

    def rewrite_version(self, new_version: str, version_tag: str = "") -> None:
        new_version = str(new_version)  # make sure it is a string!
        with open(self.get_metadata_file_path(), "r", encoding="utf-8") as fd:
            module_def = fd.read()
        new_module_def, new_metadata = self.get_metadata_file_schema_type().rewrite_version(
            module_def, new_version, version_tag
        )
        with open(self.get_metadata_file_path(), "w+", encoding="utf-8") as fd:
            fd.write(new_module_def)
        self._metadata = new_metadata

    def get_version(self) -> version.Version:
        """
        Return the version of this module. This is the actually installed version, which might differ from the version declared
        in its metadata (e.g. by a .dev0 tag).
        """
        return version.Version(self._metadata.version)

    version = property(get_version)

    def ensure_versioned(self) -> None:
        """
        Check if this module is versioned using Git. If not a warning is logged.
        """
        if not os.path.exists(os.path.join(self.path, ".git")):
            LOGGER.warning("Module %s is not version controlled, we recommend you do this as soon as possible.", self.name)

    def get_ast(self, name: str) -> Tuple[List[Statement], BasicBlock]:
        if self._project is None:
            raise ValueError("Can only get module's AST in the context of a project.")

        # Check local cache
        hit = self._ast_cache.get(name, None)
        if hit is not None:
            return hit

        if name == self.name:
            file = os.path.join(self.model_dir, "_init.cf")
        else:
            parts = name.split("::")
            parts = parts[1:]
            if os.path.isdir(os.path.join(self.model_dir, *parts)):
                path_elements = [self.model_dir] + parts + ["_init.cf"]
            else:
                path_elements = [self.model_dir] + parts[:-1] + [parts[-1] + ".cf"]
            file = os.path.join(*path_elements)

        ns = self._project.get_root_namespace().get_ns_or_create(name)

        try:
            out = self._load_file(ns, file)
            # Set local cache before returning
            self._ast_cache[name] = out
            return out
        except FileNotFoundError as e:
            raise InvalidModuleException("could not locate module with name: %s" % name) from e

    def get_freeze(self, submodule: str, recursive: bool = False, mode: str = ">=") -> Dict[str, str]:
        if self._project is None:
            raise ValueError("Can only get module's freeze in the context of a project.")

        imports = [statement.name for statement in self.get_imports(submodule)]

        out: Dict[str, str] = {}

        todo: List[str] = imports

        for impor in todo:
            if impor not in out:
                v1_mode: bool = self.GENERATION == ModuleGeneration.V1
                mainmod = self._project.get_module(impor, install_v1=v1_mode, allow_v1=v1_mode)
                vers: version.Version = mainmod.version
                # track submodules for cycle avoidance
                out[impor] = mode + " " + str(vers)
                if recursive:
                    todo.extend([statement.name for statement in mainmod.get_imports(impor)])

        # drop submodules
        return {x: v for x, v in out.items() if "::" not in x}

    def get_imports(self, name: str) -> List[DefineImport]:
        # Check local cache
        hit = self._import_cache.get(name, None)
        if hit is not None:
            return hit

        if self._project is None:
            raise ValueError("Can only get module's imports in the context of a project.")

        (statements, block) = self.get_ast(name)
        imports = [x for x in statements if isinstance(x, DefineImport)]
        if self.name != "std" and self._project.autostd:
            std_locatable = LocatableString("std", Range("__internal__", 1, 1, 1, 1), -1, block.namespace)
            imp = DefineImport(std_locatable, std_locatable)
            imp.location = std_locatable.location
            imports.insert(0, imp)

        # Set local cache before returning
        self._import_cache[name] = imports
        return imports

    def _get_model_files(self, curdir: str) -> List[str]:
        files: List[str] = []
        init_cf = os.path.join(curdir, "_init.cf")
        if not os.path.exists(init_cf):
            return files

        for entry in os.listdir(curdir):
            entry = os.path.join(curdir, entry)
            if os.path.isdir(entry):
                files.extend(self._get_model_files(entry))

            elif entry[-3:] == ".cf":
                files.append(entry)

        return files

    def get_all_submodules(self) -> List[str]:
        """
        Get all submodules of this module
        """
        modules = []
        files = self._get_model_files(self.model_dir)

        for f in files:
            name = f[len(self.model_dir) + 1 : -3]
            parts = name.split("/")
            if parts[-1] == "_init":
                parts = parts[:-1]

            parts.insert(0, self.name)
            name = "::".join(parts)

            modules.append(name)

        return modules

    @abstractmethod
    def get_plugin_dir(self) -> Optional[str]:
        """
        Return directory containing the python files which define handlers and plugins.
        If no such directory is defined, this method returns None.
        """
        raise NotImplementedError()

    def _list_python_files(self, plugin_dir: str) -> list[str]:
        """Generate a list of all python files"""
        files: Dict[str, str] = {}

        for file_name in glob.iglob(os.path.join(plugin_dir, "**", "*.pyc"), recursive=True):
            # Filter out pyc files in the default cache dir. Only support our compiled pyc files.
            if "__pycache__" not in file_name:
                files[file_name[:-3]] = file_name

        for file_name in glob.iglob(os.path.join(plugin_dir, "**", "*.py"), recursive=True):
            # store the python source file if we do not have a python file
            if file_name[:-2] not in files:
                files[file_name[:-2]] = file_name

        return list(files.values())

    def get_plugin_files(self) -> Iterator[Tuple[Path, ModuleName]]:
        """
        Returns a tuple (absolute_path, fq_mod_name) of all python files in this module.
        """
        plugin_dir: Optional[str] = self.get_plugin_dir()

        if plugin_dir is None:
            return iter(())

        if not os.path.exists(os.path.join(plugin_dir, "__init__.py")) and not os.path.exists(
            os.path.join(plugin_dir, "__init__.pyc")
        ):
            raise InvalidModuleException(f"Directory {plugin_dir} should be a valid python package with a __init__.py file")

        return (
            (
                Path(file_name),
                ModuleName(self._get_fq_mod_name_for_py_file(file_name, plugin_dir, self.name)),
            )
            for file_name in self._list_python_files(plugin_dir)
        )

    def load_plugins(self) -> None:
        """
        Load all plug-ins from a configuration module
        """
        for path_to_file, fq_mod_name in self.get_plugin_files():
            LOGGER.debug("Loading module %s", fq_mod_name)
            try:
                importlib.import_module(fq_mod_name)
            except Exception as e:
                tb: Optional[types.TracebackType] = sys.exc_info()[2]
                stack: traceback.StackSummary = traceback.extract_tb(tb)
                lineno: Optional[int] = more_itertools.first(
                    (frame.lineno for frame in reversed(stack) if frame.filename == path_to_file), None
                )
                raise PluginModuleLoadException(e, self.name, fq_mod_name, path_to_file, lineno).to_compiler_exception()

    # This method is not part of core's stable API but it is currently used by pytest-inmanta (inmanta/pytest-inmanta#76)
    def _get_fq_mod_name_for_py_file(self, py_file: str, plugin_dir: str, mod_name: str) -> str:
        """
        Returns the fully qualified Python module name for an inmanta module.
        :param py_file: The Python file for the module, relative to the plugin directory.
        :param plugin_dir: The plugin directory relative to the inmanta module's root directory.
        :param mod_name: The top-level name of this module.
        """
        rel_py_file = os.path.relpath(py_file, start=plugin_dir)
        return loader.convert_relative_path_to_module(os.path.join(mod_name, loader.PLUGIN_DIR, rel_py_file))

    def execute_command(self, cmd: str) -> None:
        print("executing %s on %s in %s" % (cmd, self.name, self._path))
        print("=" * 10)
        subprocess.call(cmd, shell=True, cwd=self._path)
        print("=" * 10)

    def unload(self) -> None:
        """
        Unloads this module instance from the project, the registered plugins and the loaded Python modules.
        """
        loader.unload_inmanta_plugins(self.name)
        plugins.PluginMeta.clear(self.name)
        if self._project is not None:
            self._project.invalidate_state(self.name)


@stable_api
class ModuleV1(Module[ModuleV1Metadata], ModuleLikeWithYmlMetadataFile):
    MODULE_FILE = "module.yml"
    GENERATION = ModuleGeneration.V1

    def __init__(self, project: Optional[Project], path: str):
        try:
            super(ModuleV1, self).__init__(project, path)
        except InvalidMetadata as e:
            raise InvalidModuleException(f"The module found at {path} is not a valid V1 module") from e
        except ModuleMetadataFileNotFound:
            if os.path.exists(os.path.join(path, ModuleV2.MODULE_FILE)):
                raise ModuleV2InV1PathException(
                    project=project,
                    module=ModuleV2(project, path),
                    msg=f"Module at {path} looks like a v2 module. Please have a look at the documentation on how to use v2"
                    " modules.",
                )
            raise

        # Only show the warning when we are not running tests. Especially on jenkins the directory of the module often does not
        # have the correct name.
        if self.name != os.path.basename(self._path) and not RUNNING_TESTS:
            LOGGER.warning(
                "The name in the module file (%s) does not match the directory name (%s)",
                self.name,
                os.path.basename(self._path),
            )

    @classmethod
    def from_path(cls: Type[TModule], path: str) -> Optional[TModule]:
        return cls(project=None, path=path) if os.path.exists(os.path.join(path, cls.MODULE_FILE)) else None

    def get_metadata_file_path(self) -> str:
        return os.path.join(self.path, self.MODULE_FILE)

    @classmethod
    def get_name_from_metadata(cls, metadata: ModuleV1Metadata) -> str:
        return metadata.name

    @property
    def compiler_version(self) -> Optional[str]:
        """
        Get the minimal compiler version required for this module version. Returns none is the compiler version is not
        constrained.
        """
        return str(self._metadata.compiler_version)

    def get_all_requires(self) -> List[InmantaModuleRequirement]:
        """
        :return: all modules required by an import from any sub-modules, with all constraints applied
        """
        # get all constraints
        spec: Dict[str, InmantaModuleRequirement] = {req.project_name: req for req in self.requires()}
        # find all imports
        imports = {imp.name.split("::")[0] for subm in sorted(self.get_all_submodules()) for imp in self.get_imports(subm)}
        return [spec[r] if spec.get(r) else InmantaModuleRequirement.parse(r) for r in imports]

    @classmethod
    def update(
        cls,
        project: Project,
        modulename: str,
        requirements: Iterable[InmantaModuleRequirement],
        path: Optional[str] = None,
        fetch: bool = True,
        install_mode: InstallMode = InstallMode.release,
    ) -> "ModuleV1":
        """
        Update a module, return module object
        """
        if path is None:
            mypath = project.module_source_v1.path_for(modulename)
            assert mypath is not None, f"trying to update module {modulename} not found on disk "
        else:
            mypath = path

        if fetch:
            LOGGER.info("Performing fetch on %s", mypath)
            gitprovider.fetch(mypath)

        if install_mode == InstallMode.master:
            LOGGER.info("Checking out master on %s", mypath)
            gitprovider.checkout_tag(mypath, "master")
            if fetch:
                LOGGER.info("Pulling master on %s", mypath)
                gitprovider.pull(mypath)
        else:
            release_only = install_mode == InstallMode.release
            version = cls.get_suitable_version_for(modulename, requirements, mypath, release_only=release_only)

            if version is None:
                print("no suitable version found for module %s" % modulename)
            else:
                LOGGER.info("Checking out %s on %s", str(version), mypath)
                gitprovider.checkout_tag(mypath, str(version))

        return cls(project, mypath)

    @classmethod
    def get_suitable_version_for(
        cls, modulename: str, requirements: Iterable[InmantaModuleRequirement], path: str, release_only: bool = True
    ) -> Optional[version.Version]:
        versions_str = gitprovider.get_all_tags(path)

        def try_parse(x: str) -> Optional[version.Version]:
            try:
                return parse_version(x)
            except Exception:
                return None

        versions: List[version.Version] = [x for x in [try_parse(v) for v in versions_str] if x is not None]
        versions = sorted(versions, reverse=True)

        for r in requirements:
            versions = [x for x in r.specifier.filter(versions, not release_only)]

        comp_version_raw = get_compiler_version()
        comp_version = parse_version(comp_version_raw)
        return cls.__best_for_compiler_version(modulename, versions, path, comp_version)

    @classmethod
    def __best_for_compiler_version(
        cls, modulename: str, versions: List[version.Version], path: str, comp_version: version.Version
    ) -> Optional[version.Version]:
        def get_cv_for(best: version.Version) -> Optional[version.Version]:
            cfg_text: str = gitprovider.get_file_for_version(path, str(best), cls.MODULE_FILE)
            metadata: ModuleV1Metadata = cls.get_metadata_file_schema_type().parse(cfg_text)
            if metadata.compiler_version is None:
                return None
            v = metadata.compiler_version
            if isinstance(v, (int, float)):
                v = str(v)
            return parse_version(v)

        if not versions:
            return None

        best = versions[0]
        atleast = get_cv_for(best)
        if atleast is None or comp_version >= atleast:
            return best

        # binary search
        hi = len(versions)
        lo = 1
        while lo < hi:
            mid = (lo + hi) // 2
            atleast = get_cv_for(versions[mid])
            if atleast is not None and atleast > comp_version:
                lo = mid + 1
            else:
                hi = mid
        if hi == len(versions):
            LOGGER.warning("Could not find version of module %s suitable for this compiler, try a newer compiler" % modulename)
            return None
        return versions[lo]

    @classmethod
    def get_metadata_file_schema_type(cls) -> Type[ModuleV1Metadata]:
        return ModuleV1Metadata

    def get_plugin_dir(self) -> Optional[str]:
        plugins_dir = os.path.join(self._path, loader.PLUGIN_DIR)
        if not os.path.exists(plugins_dir):
            return None
        return plugins_dir

    def get_all_python_requirements_as_list(self) -> List[str]:
        return self._get_requirements_txt_as_list()

    def get_module_requirements(self) -> List[str]:
        return [*self.metadata.requires, *(str(req) for req in self.get_module_v2_requirements())]

    def add_module_requirement_persistent(self, requirement: InmantaModuleRequirement, add_as_v1_module: bool) -> None:
        requirements_txt_file_path = os.path.join(self._path, "requirements.txt")
        if add_as_v1_module:
            # Add requirement to module.yml file
            self.add_module_requirement_to_requires_and_write(requirement)
            # Refresh in-memory metadata
            with open(self.get_metadata_file_path(), "r", encoding="utf-8") as fd:
                self._metadata = ModuleV1Metadata.parse(fd)
            # Remove requirement from requirements.txt file
            if os.path.exists(requirements_txt_file_path):
                requirements_txt_file = RequirementsTxtFile(requirements_txt_file_path)
                requirements_txt_file.remove_requirement_and_write(requirement.get_python_package_requirement().key)
        else:
            # Add requirement to requirements.txt
            requirements_txt_file = RequirementsTxtFile(requirements_txt_file_path, create_file_if_not_exists=True)
            requirements_txt_file.set_requirement_and_write(requirement.get_python_package_requirement())
            # Remove requirement from module.yml file
            self.remove_module_requirement_from_requires_and_write(requirement.key)

    def versions(self) -> List[version.Version]:
        """
        Provide a list of all versions available in the repository
        """
        versions_str: List[str] = gitprovider.get_all_tags(self._path)

        def try_parse(x: str) -> Optional[version.Version]:
            try:
                return parse_version(x)
            except Exception:
                return None

        versions = [x for x in [try_parse(v) for v in versions_str] if x is not None]
        versions = sorted(versions, reverse=True)

        return versions

    def status(self) -> None:
        """
        Run a git status on this module
        """
        try:
            output = gitprovider.status(self._path)

            files = [x.strip() for x in output.split("\n") if x != ""]

            if len(files) > 0:
                print(f"Module {self.name} ({self._path})")
                for f in files:
                    print("\t%s" % f)

                print()
            else:
                print(f"Module {self.name} ({self._path}) has no changes")
        except Exception:
            print("Failed to get status of module")
            LOGGER.exception("Failed to get status of module %s")

    def push(self) -> None:
        """
        Run a git push on this module
        """
        sys.stdout.write("%s (%s) " % (self.name, self._path))
        sys.stdout.flush()
        try:
            print(gitprovider.push(self._path))
        except CalledProcessError:
            print("Cloud not push module %s" % self.name)
        else:
            print("done")
        print()


@stable_api
class ModuleV2(Module[ModuleV2Metadata]):
    MODULE_FILE = "setup.cfg"
    GENERATION = ModuleGeneration.V2
    PKG_NAME_PREFIX = "inmanta-module-"

    def __init__(
        self,
        project: Optional[Project],
        path: str,
        is_editable_install: bool = False,
        installed_version: Optional[version.Version] = None,
    ) -> None:
        self._is_editable_install = is_editable_install
        self._version: Optional[version.Version] = installed_version
        super(ModuleV2, self).__init__(project, path)

        if not os.path.exists(os.path.join(self.model_dir, "_init.cf")):
            raise InvalidModuleException(
                f"The module at {path} contains no _init.cf file. This occurs when you install or build modules from source"
                " incorrectly. Always use the `inmanta module install` and `inmanta module build` commands to respectively"
                " install and build modules from source. Make sure to uninstall the broken package first."
            )

    @classmethod
    def from_path(cls: Type[TModule], path: str) -> Optional[TModule]:
        try:
            return cls(project=None, path=path) if os.path.exists(os.path.join(path, cls.MODULE_FILE)) else None
        except InvalidModuleException:
            # setup.cfg is a generic Python config file: if the metadata does not match an inmanta module's, return None
            return None

    def get_version(self) -> version.Version:
        return self._version if self._version is not None else self._metadata.get_full_version()

    version = property(get_version)

    def is_editable(self) -> bool:
        """
        Returns True iff this module has been installed in editable mode.
        """
        return self._is_editable_install

    def ensure_versioned(self) -> None:
        if self._is_editable_install:
            super(ModuleV2, self).ensure_versioned()
        else:
            # Only editable installs can be checked for versioning
            pass

    def get_metadata_file_path(self) -> str:
        return os.path.join(self.path, ModuleV2.MODULE_FILE)

    @classmethod
    def get_name_from_metadata(cls, metadata: ModuleV2Metadata) -> str:
        return metadata.name[len(cls.PKG_NAME_PREFIX) :].replace("-", "_")

    @classmethod
    def get_metadata_file_schema_type(cls) -> Type[ModuleV2Metadata]:
        return ModuleV2Metadata

    def get_plugin_dir(self) -> str:
        if self._is_editable_install:
            return os.path.join(self.path, const.PLUGINS_PACKAGE, self.name)
        else:
            return self.path

    def get_all_python_requirements_as_list(self) -> List[str]:
        return list(self.metadata.install_requires)

    def get_module_requirements(self) -> List[str]:
        return [str(req) for req in self.get_module_v2_requirements()]

    def add_module_requirement_persistent(self, requirement: InmantaModuleRequirement, add_as_v1_module: bool) -> None:
        if add_as_v1_module:
            raise Exception("Cannot add V1 requirement to a V2 module")
        # Parse config file
        config_parser = ConfigParser()
        config_parser.read(self.get_metadata_file_path())
        python_pkg_requirement: Requirement = requirement.get_python_package_requirement()
        if config_parser.has_option("options", "install_requires"):
            new_install_requires = [
                r
                for r in config_parser.get("options", "install_requires").split("\n")
                if r and Requirement.parse(r).key != python_pkg_requirement.key
            ]
            new_install_requires.append(str(python_pkg_requirement))
        else:
            new_install_requires = [str(python_pkg_requirement)]
        config_parser.set("options", "install_requires", "\n".join(new_install_requires))
        # Write config back to disk
        with open(self.get_metadata_file_path(), "w", encoding="utf-8") as fd:
            config_parser.write(fd)
        # Reload in-memory state
        with open(self.get_metadata_file_path(), "r", encoding="utf-8") as fd:
            self._metadata = ModuleV2Metadata.parse(fd)
