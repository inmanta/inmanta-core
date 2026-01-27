"""
Copyright 2018 Inmanta

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

import argparse
import configparser
import datetime
import enum
import gzip
import inspect
import itertools
import logging
import os
import pathlib
import py_compile
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from argparse import ArgumentParser, RawTextHelpFormatter
from collections import abc
from collections.abc import Sequence
from configparser import ConfigParser
from functools import total_ordering
from re import Pattern
from typing import IO, Any, Literal, Optional

import click
import more_itertools
import texttable
import yaml
from cookiecutter.main import cookiecutter

import build
import inmanta
import inmanta.warnings
import packaging.requirements
import toml
from build.env import DefaultIsolatedEnv
from inmanta import const, env, util
from inmanta.command import CLIException, ShowUsageException
from inmanta.const import CF_CACHE_DIR
from inmanta.data import model
from inmanta.module import (
    DummyProject,
    FreezeOperator,
    InmantaModuleRequirement,
    InstallMode,
    InvalidMetadata,
    InvalidModuleException,
    Module,
    ModuleLike,
    ModuleMetadata,
    ModuleMetadataFileNotFound,
    ModuleNotFoundException,
    ModuleV1,
    ModuleV2,
    ModuleV2Metadata,
    ModuleV2Source,
    Project,
    gitprovider,
)
from inmanta.stable_api import stable_api
from packaging.version import Version

LOGGER = logging.getLogger(__name__)


class ModuleVersionException(CLIException):
    def __init__(self, msg: str) -> None:
        super().__init__(msg, exitcode=5)


class CommandDeprecationWarning(inmanta.warnings.InmantaWarning, FutureWarning):
    pass


def add_deps_check_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add the --no-strict-deps-check and --strict-deps-check options to the given parser.
    """
    parser.add_argument(
        "--no-strict-deps-check",
        dest="no_strict_deps_check",
        action="store_true",
        default=False,
        help="[Deprecated] This flag is ignored. It will be removed in a future version.",
    )
    parser.add_argument(
        "--strict-deps-check",
        dest="strict_deps_check",
        action="store_true",
        default=False,
        help="[Deprecated] This flag is ignored. It will be removed in a future version.",
    )


class ModuleLikeTool:
    """Shared code for modules and projects"""

    def execute(self, cmd: Optional[str], args: argparse.Namespace) -> None:
        """
        Execute the given subcommand
        """
        if cmd is not None and cmd != "" and hasattr(self, cmd):
            method = getattr(self, cmd)
            margs = inspect.getfullargspec(method).args
            margs.remove("self")
            outargs = {k: getattr(args, k) for k in margs if hasattr(args, k)}
            method(**outargs)
        else:
            if cmd is None or cmd == "":
                msg = "A subcommand is required."
            else:
                msg = f"{cmd} does not exist."
            raise ShowUsageException(msg)

    def get_project(self, load: bool = False) -> Project:
        project = Project.get()
        if load:
            project.load()
        return project


@total_ordering
@enum.unique
class ChangeType(enum.Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    REVISION = "revision"

    def __lt__(self, other: "ChangeType") -> bool:
        order: list[ChangeType] = [ChangeType.REVISION, ChangeType.PATCH, ChangeType.MINOR, ChangeType.MAJOR]
        if other not in order:
            return NotImplemented
        return order.index(self) < order.index(other)

    @classmethod
    def diff(cls, *, low: Version, high: Version) -> Optional["ChangeType"]:
        """
        Returns the order of magnitude of the change type diff between two versions.
        Return None if the versions are less than a patch / a revision (if 4 digit version number) separated from each other.
        For example, a dev release and a post release for the same version number are less
        than a patch separated from each other.
        """
        if low > high:
            raise ValueError(f"Expected low <= high, got {low} > {high}")
        if Version(low.base_version) == Version(high.base_version):
            return None
        if high.major > low.major:
            return cls.MAJOR
        if high.minor > low.minor:
            return cls.MINOR
        if high.micro > low.micro:
            return cls.PATCH
        if len(high.base_version.split(".")) >= 4:
            high_revision = int(high.base_version.split(".")[3])
            # We are switching from 3 digits to 4
            if len(low.base_version.split(".")) < 4 or high_revision > int(low.base_version.split(".")[3]):
                return cls.REVISION
        raise Exception("Couldn't determine version change type diff: this state should be unreachable")

    @classmethod
    def parse_from_bools(cls, revision: bool, patch: bool, minor: bool, major: bool) -> Optional["ChangeType"]:
        """
        Create a ChangeType for the type of which the boolean is set to True. If none
        of the boolean arguments is set to True, None is returned. If more
        than one boolean argument is set to True, a ValueError is raised.
        """
        if sum([revision, patch, minor, major]) > 1:
            raise ValueError("Only one argument of revision, patch, minor or major can be set to True at the same time.")
        if revision:
            return ChangeType.REVISION
        if patch:
            return ChangeType.PATCH
        if minor:
            return ChangeType.MINOR
        if major:
            return ChangeType.MAJOR
        return None


class VersionOperation:
    @classmethod
    def bump_version(cls, change_type: ChangeType, version: Version, version_tag: str) -> Version:
        """
        Bump the release part of the given version with this ChangeType and apply the given version_tag to it.
        If the given version has a different version tag set, it will be ignored.
        """
        bump_index: int
        if change_type is ChangeType.REVISION:
            bump_index = 3
        elif change_type is ChangeType.PATCH:
            bump_index = 2
        elif change_type is ChangeType.MINOR:
            bump_index = 1
        elif change_type is ChangeType.MAJOR:
            bump_index = 0
        else:
            raise RuntimeError(f"Unsupported change type: {change_type}!")

        base_parts = [int(x) for x in version.base_version.split(".")]
        # use 4th digit only if it already existed or if it is being bumped
        nb_digits: int = max(bump_index + 1, 3, len(base_parts))
        parts = list(
            more_itertools.take(
                nb_digits,
                itertools.chain(
                    base_parts[: bump_index + 1],
                    itertools.repeat(0),
                ),
            )
        )
        parts[bump_index] += 1

        while len(parts) > 3 and parts[-1] == 0:
            parts.pop()

        return cls._to_version(parts, version_tag)

    @classmethod
    def set_version_tag(cls, version: Version, version_tag: str) -> Version:
        """
        Return a new version that is a copy of the given version where the version_tag
        is replaced with the given version_tag.
        """
        return cls._to_version(version.release, version_tag)

    @classmethod
    def _to_version(cls, release_part_version_number: abc.Iterable[int], version_tag: str) -> Version:
        """
        Compose a version from the release part of the version number and the version_tag.
        """
        release_part_str = ".".join(str(number) for number in release_part_version_number)
        version_tag_str = f".{version_tag.lstrip('.')}" if version_tag else ""
        return Version(f"{release_part_str}{version_tag_str}")


class ProjectTool(ModuleLikeTool):
    @classmethod
    def parser_config(cls, parser: ArgumentParser, parent_parsers: abc.Sequence[ArgumentParser]) -> None:
        subparser = parser.add_subparsers(title="subcommand", dest="cmd")

        freeze = subparser.add_parser("freeze", help="Set all version numbers in project.yml", parents=parent_parsers)
        freeze.add_argument(
            "-o",
            "--outfile",
            help="File in which to put the new project.yml, default is the existing project.yml. Use - to write to stdout.",
            default=None,
        )
        freeze.add_argument(
            "-r",
            "--recursive",
            help="Freeze dependencies recursively. If not set, freeze_recursive option in project.yml is used,"
            "which defaults to False",
            action="store_true",
            default=None,
        )
        freeze.add_argument(
            "--operator",
            help="Comparison operator used to freeze versions, If not set, the freeze_operator option in"
            " project.yml is used which defaults to ~=",
            choices=[o.value for o in FreezeOperator],
            default=None,
        )
        init = subparser.add_parser("init", help="Initialize directory structure for a project", parents=parent_parsers)
        init.add_argument("--name", "-n", help="The name of the new project", required=True)
        init.add_argument("--output-dir", "-o", help="Output directory path", default="./")
        init.add_argument(
            "--default", help="Use default parameters for the project generation", action="store_true", default=False
        )
        install = subparser.add_parser(
            "install",
            help="Install all modules required for this project.",
            description="""
Install all modules required for this project.

This command installs missing modules in the development venv, but doesn't update already installed modules if that's not
required to satisfy the module version constraints. Use `inmanta project update` instead if the already installed modules need
to be updated to the latest compatible version.

This command might reinstall Python packages in the development venv if the currently installed versions are not compatible
with the dependencies specified by the different Inmanta modules.
        """.strip(),
            parents=parent_parsers,
        )
        add_deps_check_arguments(install)

        update = subparser.add_parser(
            "update",
            help=(
                "Update all modules to the latest version compatible with the module version constraints and install missing "
                "modules"
            ),
            description="""
Update all modules to the latest version compatible with the module version constraints and install missing modules.

This command might reinstall Python packages in the development venv if the currently installed versions are not the latest
compatible with the dependencies specified by the updated modules.
            """.strip(),
            parents=parent_parsers,
        )
        add_deps_check_arguments(update)

        download = subparser.add_parser(
            "download",
            help="Download all dependencies of the Inmanta project from the pip index, extract them and convert them into"
            " their source format. The extracted modules will be stored in the directory indicated by the downloadpath"
            " option in the project.yml file or into <project-dir>/libs if the downloadpath option was not defined.",
            parents=parent_parsers,
        )
        download.add_argument(
            "--install",
            dest="install",
            help="Install the downloaded module in editable mode into the active Python environment.",
            action="store_true",
        )

    def download(self, install: bool) -> None:
        project = self.get_project()
        downloadpath = project.downloadpath if project.downloadpath else os.path.join(project.path, "libs")
        os.makedirs(downloadpath, exist_ok=True)

        dependencies, constraints = project.get_all_dependencies_and_constraints()
        if not dependencies:
            return
        converter = PythonPackageToSourceConverter()
        paths_python_packages: list[str] = converter.download_in_source_format(
            output_dir=downloadpath,
            dependencies=dependencies,
            constraints=constraints,
            ignore_transitive_dependencies=False,
            pip_config=project.metadata.pip,
            override_if_already_exists=True,
        )
        if paths_python_packages and install:
            env.process_env.install_for_config(
                requirements=[],
                constraints=[*dependencies, *constraints],
                config=project.metadata.pip,
                paths=[env.LocalPackagePath(path=path, editable=True) for path in paths_python_packages],
            )

    def freeze(self, outfile: Optional[str], recursive: Optional[bool], operator: Optional[str]) -> None:
        """
        !!! Big Side-effect !!! sets yaml parser to be order preserving
        """
        project = self.get_project(load=True)

        if recursive is None:
            recursive = project.freeze_recursive

        if operator is None:
            operator = project.freeze_operator

        freeze = project.get_freeze(mode=operator, recursive=recursive)

        with open(project.get_metadata_file_path(), encoding="utf-8") as fd:
            newconfig = yaml.safe_load(fd)

        requires = sorted([k + " " + v for k, v in freeze.items()])
        newconfig["requires"] = requires

        close = False

        outfile_fd: IO[str]
        if outfile is None:
            outfile_fd = open(project.get_metadata_file_path(), "w", encoding="UTF-8")
            close = True
        elif outfile == "-":
            outfile_fd = sys.stdout
        else:
            outfile_fd = open(outfile, "w", encoding="UTF-8")
            close = True

        try:
            outfile_fd.write(yaml.dump(newconfig, default_flow_style=False, sort_keys=False))
        finally:
            if close:
                outfile_fd.close()

    def init(self, output_dir: str, name: str, default: bool) -> None:
        os.makedirs(output_dir, exist_ok=True)
        project_path = os.path.join(output_dir, name)
        if os.path.exists(project_path):
            raise Exception(f"Project directory {project_path} already exists")
        cookiecutter(
            "https://github.com/inmanta/inmanta-project-template.git",
            output_dir=output_dir,
            extra_context={"project_name": name},
            no_input=default,
        )

    def install(self, no_strict_deps_check: bool = False, strict_deps_check: bool = False) -> None:
        """
        Install all modules the project requires.
        """
        project: Project = self.get_project(load=False)
        project.install_modules()

    def update(
        self,
        module: Optional[str] = None,
        project: Optional[Project] = None,
        no_strict_deps_check: bool = False,
        strict_deps_check: bool = False,
    ) -> None:
        """
        Update all modules to the latest version compatible with the given module version constraints.
        """
        if project is None:
            # rename var to make mypy happy
            my_project = self.get_project(load=False)
        else:
            my_project = project

        my_project.install_modules(update=True)


@stable_api
class ModuleTool(ModuleLikeTool):
    """
    A tool to manage configuration modules
    """

    @classmethod
    def modules_parser_config(cls, parser: ArgumentParser, parent_parsers: abc.Sequence[ArgumentParser]) -> None:
        parser.add_argument("-m", "--module", help="Module to apply this command to", nargs="?", default=None)
        subparser = parser.add_subparsers(title="subcommand", dest="cmd")

        add_help_msg = "Add a module dependency to an Inmanta module or project."
        add = subparser.add_parser(
            "add",
            help=add_help_msg,
            description=f"{add_help_msg} When executed on a project, the module is installed as well.",
            parents=parent_parsers,
        )
        add.add_argument(
            "module_req",
            help="The name of the module, optionally with a version constraint.",
        )
        add.add_argument(
            "--v2",
            dest="v2",
            help=(
                "Add the given module as a V2 module. This is currently the only supported module version."
                " This flag is kept for backwards compatibility."
            ),
            action="store_true",
        )
        add.add_argument(
            "--override",
            dest="override",
            help="Override the version constraint when the given module dependency already exists.",
            action="store_true",
        )

        subparser.add_parser(
            "list",
            help="List all modules used in this project in a table",
            parents=parent_parsers,
        )

        install: ArgumentParser = subparser.add_parser(
            "install",
            parents=parent_parsers,
            help="This command is no longer supported.",
            description="""
        The 'inmanta module install' command is no longer supported. Instead, use one of the following approaches:

        1. To install a module in editable mode, use 'pip install -e .'.
        2. For a non-editable installation, first run 'inmanta module build' followed by 'pip install ./dist/<dist-package>'.
            """.strip(),
        )
        install.add_argument("-e", "--editable", action="store_true", help="Install in editable mode.")
        install.add_argument("path", nargs="?", help="The path to the module.")

        subparser.add_parser(
            "status",
            help="Run a git status on all modules and report",
            parents=parent_parsers,
        )

        subparser.add_parser(
            "push",
            help="Run a git push on all modules and report",
            parents=parent_parsers,
        )

        # not currently working
        subparser.add_parser(
            "verify",
            help="Verify dependencies and frozen module versions",
            parents=parent_parsers,
        )

        create = subparser.add_parser(
            "create",
            help="Create a new module",
            parents=parent_parsers,
        )
        create.add_argument("name", help="The name of the module")
        create.add_argument(
            "--v1", dest="v1", help="Create a v1 module. By default a v2 module is created.", action="store_true"
        )

        freeze = subparser.add_parser(
            "freeze",
            help="Freeze all version numbers in module.yml. This command is only supported on v1 modules. On v2 modules use"
            " the pip freeze command instead.",
            parents=parent_parsers,
        )
        freeze.add_argument(
            "-o",
            "--outfile",
            help="File in which to put the new module.yml, default is the existing module.yml. Use - to write to stdout.",
            default=None,
        )
        freeze.add_argument(
            "-r",
            "--recursive",
            help="Freeze dependencies recursively. If not set, freeze_recursive option in module.yml is used,"
            " which defaults to False",
            action="store_true",
            default=None,
        )
        freeze.add_argument(
            "--operator",
            help="Comparison operator used to freeze versions, If not set, the freeze_operator option in"
            " module.yml is used which defaults to ~=",
            choices=[o.value for o in FreezeOperator],
            default=None,
        )

        build = subparser.add_parser(
            "build",
            help="Build a Python package from a V2 module. By default, a wheel and a sdist package is built.",
            parents=parent_parsers,
        )
        build.add_argument(
            "path",
            help="The path to the module that should be built. By default, the current working directory is used.",
            nargs="?",
        )
        build.add_argument(
            "-o",
            "--output-dir",
            help="The directory where the Python package will be stored. Default: <module_root>/dist",
            default=None,
            dest="output_dir",
        )
        build.add_argument(
            "--dev",
            dest="dev_build",
            help="Perform a development build of the module. This adds the build tag `.dev<timestamp>` to the "
            "package name. The timestamp has the form %%Y%%m%%d%%H%%M%%S.",
            default=False,
            action="store_true",
        )
        build.add_argument(
            "-b",
            "--byte-code",
            help="Produce a module wheel that contains only python bytecode for the plugins.",
            action="store_true",
            default=False,
            dest="byte_code",
        )
        build.add_argument(
            "-w",
            "--wheel",
            help="Build a wheel.",
            action="store_true",
            default=False,
            dest="wheel",
        )
        build.add_argument(
            "-s",
            "--sdist",
            help="Build a sdist.",
            action="store_true",
            default=False,
            dest="sdist",
        )

        subparser.add_parser(
            "v1tov2",
            help="Convert a V1 module to a V2 module in place",
            parents=parent_parsers,
        )

        release = subparser.add_parser(
            "release",
            parents=parent_parsers,
            help="Release a new stable or dev release for this module.",
            description=r"""
When a stable release is done, this command:

* Does a commit that changes the current version to a stable version.
* Adds Git release tag.
* Does a commit that changes the current version to a development version that is one patch increment ahead of the released
  version.

When a development release is done using the \--dev option, this command:

* Does a commit that updates the current version of the module to a development version that is a patch, minor or major version
  ahead of the previous stable release. The size of the increment is determined by the \--revision, \--patch, \--minor or
  \--major argument (\--patch is the default). When a CHANGELOG.md file is present in the root of the module
  directory then the version number in the changelog is also updated accordingly. The changelog file is always populated with
  the associated stable version and not a development version.
            """.strip(),
            formatter_class=RawTextHelpFormatter,
        )
        release.add_argument(
            "--dev",
            dest="dev",
            help="Create a development version. The new version number will have the .dev0 build tag.",
            action="store_true",
            default=False,
        )
        release.add_argument(
            "--major",
            dest="major",
            help="Do a major version bump compared to the previous stable release.",
            action="store_true",
        )
        release.add_argument(
            "--minor",
            dest="minor",
            help="Do a minor version bump compared to the previous stable release.",
            action="store_true",
        )
        release.add_argument(
            "--patch",
            dest="patch",
            help="Do a patch version bump compared to the previous stable release.",
            action="store_true",
        )
        release.add_argument(
            "--revision",
            dest="revision",
            help="Do a revision version bump compared to the previous stable release (only with 4 digits version).",
            action="store_true",
        )
        release.add_argument("-m", "--message", help="Commit message")
        release.add_argument(
            "-c",
            "--changelog-message",
            help="This changelog message will be written to the changelog file. If the -m option is not provided, "
            "this message will also be used as the commit message.",
        )
        release.add_argument("-a", "--all", dest="commit_all", help="Use commit -a", action="store_true")
        download = subparser.add_parser(
            "download",
            help="Download the source distribution of an Inmanta module from a Python package repository,"
            " extract it and convert it to its source format.",
            parents=parent_parsers,
        )
        download.add_argument(
            "module_req",
            help="The name of the module, optionally with a version constraint.",
        )
        download.add_argument(
            "--install",
            dest="install",
            help="Install the downloaded module in editable mode into the active Python environment.",
            action="store_true",
        )
        download.add_argument(
            "-d",
            "--directory",
            dest="directory",
            help="Download the module in this directory instead of the current working directory.",
        )

    def download(self, module_req: str, install: bool, directory: str | None) -> None:
        if directory is None:
            directory = os.getcwd()
        module_requirement = InmantaModuleRequirement.parse(module_req)
        converter = PythonPackageToSourceConverter()
        paths_module_sources = converter.download_in_source_format(
            output_dir=directory,
            dependencies=[module_requirement.get_python_package_requirement()],
            ignore_transitive_dependencies=True,
        )
        assert len(paths_module_sources) == 1
        # Install in editable mode if requested
        if install:
            env.process_env.install_from_source(paths=[env.LocalPackagePath(path=paths_module_sources[0], editable=True)])

    def add(self, module_req: str, v2: bool = True, override: bool = False) -> None:
        """
        Add a module dependency to an Inmanta module or project.

        :param module_req: The module to add, optionally with a version constraint.
        :param override: If set to True, override the version constraint when the module dependency already exists.
                         If set to False, this method raises an exception when the module dependency already exists.
        """
        module_like: Optional[ModuleLike] = ModuleLike.from_path(path=os.getcwd())
        if module_like is None:
            raise CLIException("Current working directory doesn't contain an Inmanta module or project", exitcode=1)
        try:
            module_requirement = InmantaModuleRequirement.parse(module_req)
        except packaging.requirements.InvalidRequirement:
            raise CLIException(f"'{module_req}' is not a valid requirement", exitcode=1)
        if not override and module_like.has_module_requirement(module_requirement.key):
            raise CLIException(
                "A dependency on the given module was already defined, use --override to override the version constraint",
                exitcode=1,
            )
        module_like.add_module_requirement_persistent(requirement=module_requirement)
        if isinstance(module_like, Project):
            try:
                module_like.install_modules()
            except ModuleNotFoundException:
                raise CLIException(
                    f"Failed to install {module_requirement}.",
                    exitcode=1,
                )
            else:
                # cached project might have inconsistent state after modifying the environment through another instance
                self.get_project(load=False).invalidate_state()

    def v1tov2(self, module: str) -> None:
        """
        Convert a V1 module to a V2 module in place
        """
        mod = self.get_module(module)
        if not isinstance(mod, ModuleV1):
            raise ModuleVersionException(f"Expected a v1 module, but found v{mod.GENERATION.value} module")
        ModuleConverter(mod).convert_in_place()

    def build(
        self,
        path: Optional[str] = None,
        output_dir: Optional[str] = None,
        dev_build: bool = False,
        byte_code: bool = False,
        wheel: bool = False,
        sdist: bool = False,
    ) -> list[str]:
        """
        Build a v2 module and return the path to the build artifact(s).

        :param wheel: True iff build a wheel package.
        :param sdist: True iff build a sdist package.
        :returns: A list of paths to the distribution packages that were built.
        """
        if path is not None:
            path = os.path.abspath(path)
        else:
            path = os.getcwd()

        module = self.construct_module(DummyProject(), path)

        if output_dir is None:
            output_dir = os.path.join(path, "dist")

        timestamp = datetime.datetime.now(datetime.timezone.utc)

        distributions_to_build: Sequence[Literal["wheel", "sdist"]]
        if wheel is sdist:
            # Build sdist and wheel by default or if both wheel and sdist are set.
            distributions_to_build = ["wheel", "sdist"]
        elif wheel:
            distributions_to_build = ["wheel"]
        elif sdist:
            distributions_to_build = ["sdist"]

        def _build_distribution_packages(module_dir: str) -> list[str]:
            return [
                V2ModuleBuilder(module_dir).build(
                    output_dir, dev_build=dev_build, byte_code=byte_code, distribution=current_distribution, timestamp=timestamp
                )
                for current_distribution in distributions_to_build
            ]

        if isinstance(module, ModuleV1):
            with tempfile.TemporaryDirectory() as tmpdir:
                ModuleConverter(module).convert(tmpdir)
                artifacts = _build_distribution_packages(tmpdir)
        else:
            artifacts = _build_distribution_packages(path)

        return artifacts

    def get_project_for_module(self, module: str) -> Project:
        try:
            return self.get_project()
        except Exception:
            # see #721
            return DummyProject()

    def construct_module(self, project: Optional[Project], path: str) -> Module:
        """Construct a V1 or V2 module from a folder"""
        try:
            return ModuleV2(project, path)
        except (ModuleMetadataFileNotFound, InvalidMetadata, InvalidModuleException):
            try:
                return ModuleV1(project, path)
            except (ModuleMetadataFileNotFound, InvalidModuleException):
                raise InvalidModuleException(f"No module can be found at {path}")
            except InvalidMetadata as e:
                raise InvalidModuleException(e.msg)

    def get_module(self, module: Optional[str] = None, project: Optional[Project] = None) -> Module:
        """Finds and loads a module, either based on the CWD or based on the name passed in as an argument and the project"""
        if module is None:
            project = self.get_project_for_module(module)
            path: str = os.path.realpath(os.curdir)
            return self.construct_module(project, path)
        else:
            project = self.get_project(load=True)
            return project.get_module(module, allow_v1=True)

    def get_modules(self, module: Optional[str] = None) -> list[Module]:
        if module is not None:
            return [self.get_module(module)]
        else:
            return self.get_project(load=True).sorted_modules()

    def create(self, name: str, v1: bool, no_input: bool = False) -> None:
        """
        Create a new module with the given name. Defaults to a v2 module.

        :param name: The name for the new module.
        :param v1: Create a v1 module instead.
        :param no_input: Create a module with the default settings, without interaction. Only relevant for v2 modules.
        """
        if v1:
            self._create_v1(name)
        else:
            module_dir: str = name
            if os.path.exists(module_dir):
                raise Exception(f"Directory {module_dir} already exists")
            cookiecutter(
                "https://github.com/inmanta/inmanta-module-template.git",
                no_input=no_input,
                extra_context={"module_name": name},
            )

    def _create_v1(self, name: str) -> None:
        project = self.get_project()
        mod_root = project.modulepath[-1]
        LOGGER.info("Creating new module %s in %s", name, mod_root)

        mod_path = os.path.join(mod_root, name)

        if os.path.exists(mod_path):
            LOGGER.error("%s already exists.", mod_path)
            return

        os.mkdir(mod_path)
        with open(os.path.join(mod_path, "module.yml"), "w+", encoding="utf-8") as fd:
            fd.write("""name: %(name)s
license: ASL 2.0
version: 0.0.1dev0""" % {"name": name})

        os.mkdir(os.path.join(mod_path, "model"))
        with open(os.path.join(mod_path, "model", "_init.cf"), "w+", encoding="utf-8") as fd:
            fd.write("\n")

        with open(os.path.join(mod_path, ".gitignore"), "w+", encoding="utf-8") as fd:
            fd.write("""*.swp
*.pyc
*~
.cache
            """)

        subprocess.check_output(["git", "init"], cwd=mod_path)
        subprocess.check_output(["git", "add", ".gitignore", "module.yml", "model/_init.cf"], cwd=mod_path)

        LOGGER.info("Module successfully created.")

    def list(self) -> None:
        """
        List all modules in a table
        """

        def show_bool(b: bool) -> str:
            return "yes" if b else "no"

        table = []

        project = Project.get()
        project.get_complete_ast()

        names: abc.Sequence[str] = sorted(project.modules.keys())
        specs: dict[str, list[InmantaModuleRequirement]] = project.collect_imported_requirements()
        for name in names:
            mod: Module = Project.get().modules[name]
            version = str(mod.version)
            if name not in specs:
                specs[name] = []

            generation: str = str(mod.GENERATION.name).lower()

            reqv: str
            matches: bool
            editable: bool
            if isinstance(mod, ModuleV1):
                try:
                    if project.install_mode == InstallMode.master:
                        reqv = "master"
                    else:
                        release_only = project.install_mode == InstallMode.release
                        versions = ModuleV1.get_suitable_version_for(name, specs[name], mod._path, release_only=release_only)
                        if versions is None:
                            reqv = "None"
                        else:
                            reqv = str(versions)
                except Exception:
                    LOGGER.exception("Problem getting version for module %s" % name)
                    reqv = "ERROR"
                matches = version == reqv
                editable = True
            else:
                reqv = ",".join(str(req.specifier) for req in specs[name] if len(req.specifier) > 0) or "*"
                matches = all(version in req for req in specs[name])
                editable = mod.is_editable()

            table.append((name, generation, editable, version, reqv, matches))

        t = texttable.Texttable()
        t.set_deco(texttable.Texttable.HEADER | texttable.Texttable.BORDER | texttable.Texttable.VLINES)
        t.header(("Name", "Type", "Editable", "Installed version", "Expected in project", "Matches"))
        t.set_cols_dtype(("t", "t", show_bool, "t", "t", show_bool))
        for row in table:
            t.add_row(row)
        print(t.draw())

    def install(self, editable: bool = False, path: Optional[str] = None) -> None:
        """
        This command is no longer supported.
        Use 'pip install -e .' to install a module in editable mode.
        Use 'inmanta module build' followed by 'pip install ./dist/<dist-package>' for non-editable install.
        """
        raise CLIException(
            "The 'inmanta module install' command is no longer supported. "
            "For editable mode installation, use 'pip install -e .'. "
            "For a regular installation, first run 'inmanta module build' and then 'pip install ./dist/<dist-package>'.",
            exitcode=1,
        )

    def status(self, module: Optional[str] = None) -> None:
        """
        a git status on all modules and report
        """
        for mod in self.get_modules(module):
            if not isinstance(mod, ModuleV1):
                LOGGER.warning("Skipping module %s: v2 modules do not support this operation.", mod.name)
                continue
            mod.status()

    def push(self, module: Optional[str] = None) -> None:
        """
        Push all modules
        """
        for mod in self.get_modules(module):
            if not isinstance(mod, ModuleV1):
                LOGGER.warning("Skipping module %s: v2 modules do not support this operation.", mod.name)
                continue
            mod.push()

    def verify(self) -> None:
        """
        Verify dependencies and frozen module versions
        """
        self.get_project(load=True)

    def freeze(self, outfile: Optional[str], recursive: Optional[bool], operator: str, module: Optional[str] = None) -> None:
        """
        !!! Big Side-effect !!! sets yaml parser to be order preserving
        """
        if (module and ModuleV2.from_path(module)) or ModuleV2.from_path(os.curdir):
            raise CLIException(
                "The `inmanta module freeze` command is not supported on V2 modules. Use the `pip freeze` command instead.",
                exitcode=1,
            )

        # find module
        module_obj = self.get_module(module)

        if recursive is None:
            recursive = module_obj.freeze_recursive

        if operator is None:
            operator = module_obj.freeze_operator

        if operator not in ["==", "~=", ">="]:
            LOGGER.warning("Operator %s is unknown, expecting one of ['==', '~=', '>=']", operator)

        freeze = {}

        for submodule in module_obj.get_all_submodules():
            freeze.update(module_obj.get_freeze(submodule=submodule, mode=operator, recursive=recursive))

        with open(module_obj.get_metadata_file_path(), encoding="utf-8") as fd:
            newconfig = yaml.safe_load(fd)

        requires = sorted([k + " " + v for k, v in freeze.items()])
        newconfig["requires"] = requires

        close = False
        out_fd: IO[str]
        if outfile is None:
            out_fd = open(module_obj.get_metadata_file_path(), "w", encoding="UTF-8")
            close = True
        elif outfile == "-":
            out_fd = sys.stdout
        else:
            out_fd = open(outfile, "w", encoding="UTF-8")
            close = True

        try:
            out_fd.write(yaml.dump(newconfig, default_flow_style=False, sort_keys=False))
        finally:
            if close:
                out_fd.close()

    def _get_dev_version_with_minimal_distance_to_previous_stable_release(
        self,
        current_version: Version,
        all_existing_stable_version: abc.Collection[Version],
        minimal_version_bump_to_prev_release: ChangeType,
    ) -> Version:
        """
        Turn the given current_version into a dev version with version_tag dev0 and ensure
        the version number is at least `minimal_version_bump_to_prev_release` separated
        from its predecessor in all_existing_stable_version.

        Invariants:
        1. return a dev version
        2. this version is at least `minimal_version_bump_to_prev_release`
            separated from its predecessor in all_existing_stable_version
        3. it is >= the current version
        """
        version_previous_release: Version
        try:
            version_previous_release = sorted([v for v in all_existing_stable_version if v <= current_version])[-1]
        except IndexError:
            # No previous release happened
            version_previous_release = Version("0.0.0")

        LOGGER.debug("Previous release was %s", version_previous_release)

        assert version_previous_release <= current_version
        current_diff: Optional[ChangeType] = ChangeType.diff(low=version_previous_release, high=current_version)

        LOGGER.debug("Different from current to previous release is %s", current_diff)

        # Determine if we are already sufficiently far ahead
        if current_diff is None or minimal_version_bump_to_prev_release > current_diff:
            LOGGER.debug(
                "Incrementing version number because the current difference is smaller than requested difference: %s<%s",
                current_diff,
                minimal_version_bump_to_prev_release,
            )
            # We are not sufficiently far ahead of the previous release
            # Increment from current_version
            new_version = VersionOperation.bump_version(
                minimal_version_bump_to_prev_release, current_version, version_tag="dev0"
            )
            # invariant 2 holds because
            # current_version >= version_previous_release
            # current_version + minimal_version_bump_to_prev_release >=
            #   version_previous_release + minimal_version_bump_to_prev_release
            # new_version-version_previous_release >= minimal_version_bump_to_prev_release
        else:
            # We are sufficiently far ahead (invariant 2 holds)
            if current_version.is_devrelease:
                LOGGER.debug(
                    "Keeping current dev version because we are sufficiently far ahead of the previous release: %s>=%s",
                    current_diff,
                    minimal_version_bump_to_prev_release,
                )
                # It is good as it is
                new_version = current_version
            else:
                LOGGER.debug(
                    "Incrementing to next dev version because we are sufficiently far ahead of the previous release: %s>=%s",
                    current_diff,
                    minimal_version_bump_to_prev_release,
                )
                # We are a normal or pre release version
                # Adding 0.0.0.dev would make the new_version < current_version
                # so we add 0.0.1.dev
                new_version = VersionOperation.bump_version(ChangeType.PATCH, current_version, version_tag="dev0")
        LOGGER.debug("New version is %s", new_version)

        # Sanity checks
        versions_between_current_and_new_version = [
            v for v in all_existing_stable_version if current_version < v <= new_version
        ]
        if versions_between_current_and_new_version:
            raise click.ClickException(
                f"Error: Stable release {versions_between_current_and_new_version[0]} exists between "
                f"current version {current_version} and new version {new_version}. Make sure your branch is up-to-update "
                f"with the remote repository."
            )

        return new_version

    def release(
        self,
        dev: bool,
        message: Optional[str] = None,
        revision: bool = False,
        patch: bool = False,
        minor: bool = False,
        major: bool = False,
        commit_all: bool = False,
        changelog_message: Optional[str] = None,
    ) -> None:
        """
        Execute the release command. Expects an Inmanta module to live in the current working directory.

        :param dev: Set to True to perform a dev release that will bump the version to the next appropriate dev version
            (Using the revision/patch/minor/major semver flag if set).
            Set to False to perform a stable release that will tag the version and perform a dev release right after
            to ensure the module is ready for further development.
        :param message: Optional commit message
        :param revision: Set this flag to indicate a revision release
        :param patch: Set this flag to indicate a patch release
        :param minor: Set this flag to indicate a minor release
        :param major: Set this flag to indicate a major release
        :param commit_all: Commit changes to ALL tracked files before releasing.
        :param changelog_message: Message to add to the changelog file. A changelog file will be created
            at the root of the module if it doesn't exist.
        """

        # Validate patch, minor, major
        nb_version_bump_arguments_set = sum([revision, patch, minor, major])
        if nb_version_bump_arguments_set > 1:
            raise click.UsageError("Error: Only one of --revision, --patch, --minor and --major can be set at the same time.")

        # Make module
        module_dir = os.path.abspath(os.getcwd())
        module: Module[ModuleMetadata] = self.construct_module(project=DummyProject(), path=module_dir)
        if not gitprovider.is_git_repository(repo=module_dir):
            raise click.ClickException(f"Error: Directory {module_dir} is not a git repository.")

        # Validate current state of the module
        current_version: Version = module.version
        if current_version.epoch != 0:
            raise click.ClickException("Error: Version with an epoch value larger than zero are not supported by this tool.")
        gitprovider.fetch(module_dir)

        # Get history
        stable_releases: list[Version] = gitprovider.get_version_tags(module_dir, only_return_stable_versions=True)

        path_changelog_file = os.path.join(module_dir, const.MODULE_CHANGELOG_FILE)
        changelog: Optional[Changelog] = Changelog(path_changelog_file) if os.path.exists(path_changelog_file) else None

        requested_version_bump: Optional[ChangeType] = ChangeType.parse_from_bools(revision, patch, minor, major)
        if not requested_version_bump and dev:
            # Dev always bumps
            if isinstance(module.metadata, ModuleV2Metadata) and module.metadata.four_digit_version:
                requested_version_bump = ChangeType.REVISION
            else:
                requested_version_bump = ChangeType.PATCH

        if requested_version_bump:
            new_version: Version = self._get_dev_version_with_minimal_distance_to_previous_stable_release(
                current_version, stable_releases, requested_version_bump
            )
        else:
            # Never happens for dev release
            new_version = current_version

        if not changelog and changelog_message:
            changelog = Changelog.create_changelog_file(path_changelog_file, new_version, changelog_message)
        elif changelog:
            if current_version.is_devrelease:
                # Update the existing dev version to the new dev version
                changelog.rewrite_version_in_changelog_header(old_version=current_version, new_version=new_version)
            else:
                changelog.add_section_for_version(current_version, new_version)

            if changelog_message:
                changelog.add_changelog_entry(current_version, new_version, changelog_message)

        if dev:
            assert new_version.dev is not None and new_version.dev == 0
            new_base_version_str, version_tag = str(new_version).rsplit(".", maxsplit=1)
            module.rewrite_version(new_version=new_base_version_str, version_tag=version_tag)
            # If no changes, commit will not happen
            gitprovider.commit(
                repo=module_dir,
                message=changelog_message if changelog_message else message if message else f"Bump version to {new_version}",
                commit_all=commit_all,
                add=[module.get_metadata_file_path()] + ([changelog.get_path()] if changelog else []),
                raise_exc_when_nothing_to_commit=False,
            )
        else:
            release_tag: Version = VersionOperation.set_version_tag(new_version, version_tag="")
            if release_tag in stable_releases:
                raise click.ClickException(f"Error: A Git version tag already exists for version {release_tag}")
            module.rewrite_version(new_version=str(release_tag), version_tag="")
            if changelog:
                changelog.set_release_date_for_version(release_tag)
            gitprovider.commit(
                repo=module_dir,
                message=message if message else f"Release version {module.metadata.get_full_version()}",
                commit_all=commit_all,
                add=[module.get_metadata_file_path()] + ([changelog.get_path()] if changelog else []),
                raise_exc_when_nothing_to_commit=False,
            )
            gitprovider.tag(repo=module_dir, tag=str(release_tag))
            print(f"Tag created successfully: {release_tag}")
            # bump to the next dev version
            if isinstance(module.metadata, ModuleV2Metadata) and module.metadata.four_digit_version:
                self.release(dev=True, message="Bump version to next development version", revision=True)
            else:
                self.release(dev=True, message="Bump version to next development version", patch=True)


class Changelog:
    """
    This class represent a changelog file e.g. in an Inmanta module or an Inmanta python package.

    The expected format of the changelog is the following:

    ```
    # Changelog

    ## v1.2.1 - ?

    - Change3

    ## v1.2.0 - 2022-12-19

    - Change1
    - change2
    ```
    """

    def __init__(self, path_changelog_file: str) -> None:
        if not os.path.isfile(path_changelog_file):
            raise Exception(f"{path_changelog_file} is not a file.")
        self.path_changelog_file = os.path.abspath(path_changelog_file)

    @classmethod
    def create_changelog_file(cls, path: str, version: Version, changelog_message: str) -> "Changelog":
        """
        Create a new changelog file at the given path. Add a section for the given version and write the given
        changelog message to it.
        """
        if os.path.exists(path):
            raise Exception(f"File {path} already exists.")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"""
{cls._get_top_level_header()}

{cls._get_header_for_version(version)}

- {changelog_message}
            """.strip())
        return cls(path)

    def get_path(self) -> str:
        return self.path_changelog_file

    @classmethod
    def _get_header_for_version(cls, version: Version) -> str:
        """
        Return the header the given version would have in the changelog.
        """
        return f"## v{version.base_version} - ?"

    @classmethod
    def _get_top_level_header(cls) -> str:
        """
        Return the top-level header of the changelog file.
        """
        return "# Changelog"

    def regex_for_changelog_line(self, version: Version) -> re.Pattern[str]:
        return re.compile(rf"(^#{{1,2}} [vV]?{re.escape(version.base_version)}[^\n]*$)", re.MULTILINE)

    def _add_changelog_section(self, content_changelog: str, old_version: Version, new_version: Version) -> str:
        """
        Add a new section for the given new_version to the changelog, given the current content of the changelog file.
        """
        header_for_new_version: str = self._get_header_for_version(new_version)
        # Try to insert the section before the section of the previous version if such a section exists
        regex_header_previous_version: re.Pattern[str] = self.regex_for_changelog_line(old_version)
        new_content_changelog = regex_header_previous_version.sub(
            repl=f"{header_for_new_version}\n\n\n\\g<1>",
            string=content_changelog,
            count=1,
        )
        if new_content_changelog != content_changelog:
            return new_content_changelog
        # No changelog section exists for the previous version. Search for the top-level header of the changelog and insert the
        # section below it.
        regex_top_level_header: re.Pattern[str] = re.compile(r"(^\# [^\n]*$)", re.MULTILINE)
        new_content_changelog = regex_top_level_header.sub(
            repl=f"\\g<1>\n\n{header_for_new_version}\n\n\n",
            string=content_changelog,
            count=1,
        )
        if new_content_changelog != content_changelog:
            return new_content_changelog
        # No top-level header exists in changelog file. It's a new changelog, insert at the beginning of the file.
        return f"{self._get_top_level_header()}\n\n{header_for_new_version}\n\n\n{content_changelog}"

    def add_section_for_version(self, old_version: Version, new_version: Version) -> None:
        """
        Add a new section for the given new_version to the changelog file. This new section is added right
        above the section of the previous version. If no such section exists, it's added at the top of the file.
        """
        with open(self.path_changelog_file, "r+", encoding="utf-8") as fh:
            content_changelog: str = fh.read()
            new_content_changelog: str = self._add_changelog_section(content_changelog, old_version, new_version)
            fh.seek(0, 0)
            fh.write(new_content_changelog)
            fh.truncate()

    def _has_section_for_version(self, version: Version) -> bool:
        """
        Return True iff this changelog contains a section of the given version.
        """
        with open(self.path_changelog_file, encoding="utf-8") as fh:
            regex_version_header: re.Pattern[str] = self.regex_for_changelog_line(version)
            content = fh.read()
            return regex_version_header.search(content) is not None

    def rewrite_version_in_changelog_header(self, old_version: Version, new_version: Version) -> None:
        """
        Replaces the first occurrence of the given old_version in this changelog file with new_version.
        This operation is performed in-place.
        """
        with open(self.path_changelog_file, "r+", encoding="utf-8") as fh:
            content_changelog = fh.read()
            # The changelog only contains the base_version. Replace only the first occurrence
            # to not accidentally perform invalid replacements in the remainder of the file.
            new_content_changelog = content_changelog.replace(old_version.base_version, new_version.base_version, 1)
            if content_changelog != new_content_changelog:
                fh.seek(0, 0)
                fh.write(new_content_changelog)
                fh.truncate()

    def set_release_date_for_version(self, version: Version) -> None:
        """
        Replace the question mark placeholder in the changelog file with the current data.
        """
        with open(self.path_changelog_file, "r+", encoding="utf-8") as fh:
            content_changelog = fh.read()
            regex_version_header: re.Pattern[str] = re.compile(rf"^({re.escape(f'## v{version} - ')})\?([ ]*)$", re.MULTILINE)
            new_content_changelog = regex_version_header.sub(
                repl=f"\\g<1>{datetime.date.today().isoformat()}\\g<2>",
                string=content_changelog,
                count=1,
            )
            if new_content_changelog != content_changelog:
                fh.seek(0, 0)
                fh.write(new_content_changelog)
                fh.truncate()
            else:
                LOGGER.warning(
                    "Failed to set the release date in the changelog for version %s.",
                    str(version.base_version),
                )

    def add_changelog_entry(self, old_version: Version, version: Version, message: str) -> None:
        """
        Add an entry to the changelog section of the given version.
        """
        if not self._has_section_for_version(version):
            self.add_section_for_version(old_version, version)
        with open(self.path_changelog_file, "r+", encoding="utf-8") as fh:
            content_changelog = fh.read()
            regex_version_header: re.Pattern[str] = re.compile(rf"({re.escape(f'## v{version.base_version} - ?')}[ ]*\n\n)")
            new_content_changelog = regex_version_header.sub(repl=f"\\g<1>- {message}\n", string=content_changelog, count=1)
            if new_content_changelog != content_changelog:
                fh.seek(0, 0)
                fh.write(new_content_changelog)
                fh.truncate()
            else:
                LOGGER.warning(
                    "Failed to add changelog entry to section for version %s.",
                    str(version.base_version),
                )


ModuleChangelog = Changelog  # For backwards compatibility after class rename


class ModuleBuildFailedError(Exception):
    def __init__(self, msg: str, *args: Any) -> None:
        self.msg = msg
        super().__init__(msg, *args)

    def __str__(self) -> str:
        return self.msg


BUILD_FILE_IGNORE_PATTERN: Pattern[str] = re.compile("|".join(("__pycache__", "__cfcache__", r".*\.pyc", rf"{CF_CACHE_DIR}")))


class DefaultIsolatedEnvCached(DefaultIsolatedEnv):
    """
    An IsolatedEnvBuilder that maintains its build environment across invocations of the context manager.
    This class is only used by the test suite. It decreases the runtime of the test suite because the build
    environment is reused across test cases.

    This class is a singleton. The get_instance() method should be used to obtain an instance of this class.
    """

    _instance: Optional["DefaultIsolatedEnvCached"] = None

    def __init__(self) -> None:
        super().__init__()
        self._isolated_env: Optional[DefaultIsolatedEnv] = None

    @classmethod
    def get_instance(cls) -> "DefaultIsolatedEnvCached":
        """
        This method should be used to obtain an instance of this class, because this class is a singleton.
        """
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __enter__(self) -> DefaultIsolatedEnv:
        if not self._isolated_env:
            self._isolated_env = super().__enter__()
            self._install_build_requirements(self._isolated_env)
            # All build dependencies are installed, so we can disable the install() method on self._isolated_env.
            # This prevents unnecessary pip processes from being spawned.
            setattr(self._isolated_env, "install", lambda *args, **kwargs: None)
        return self._isolated_env

    def _install_build_requirements(self, isolated_env: DefaultIsolatedEnv) -> None:
        """
        Install the build requirements required to build the modules present in the tests/data/modules_v2 directory.
        """
        # Make mypy happy
        assert self._isolated_env is not None
        with tempfile.TemporaryDirectory() as tmp_python_project_dir:
            # All modules in the tests/data/modules_v2 directory have the same pyproject.toml file.
            # So we can safely use the pyproject.toml file below.
            pyproject_toml_path = os.path.join(tmp_python_project_dir, "pyproject.toml")
            with open(pyproject_toml_path, "w", encoding="utf-8") as fh:
                fh.write("""
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
                """)
            builder = build.ProjectBuilder(
                source_dir=tmp_python_project_dir,
                python_executable=self._isolated_env.python_executable,
            )
            isolated_env.install(builder.build_system_requires)
            isolated_env.install(builder.get_requires_for_build(distribution="wheel"))

    def __exit__(self, *args: object) -> None:
        # Ignore implementation from the super class to keep the environment
        pass

    def destroy(self) -> None:
        """
        Cleanup the cached build environment. It should be called at the end of the test suite.
        """
        if self._isolated_env:
            super().__exit__()
            self._isolated_env = None


class V2ModuleBuilder:
    DISABLE_DEFAULT_ISOLATED_ENV_CACHED: bool = False

    def __init__(self, module_path: str) -> None:
        """
        :raises InvalidModuleException: The given module_path doesn't reference a valid module.
        :raises ModuleBuildFailedError: Module build was unsuccessful.
        """
        self._module = ModuleV2(project=None, path=os.path.abspath(module_path))

    def build(
        self,
        output_directory: str,
        dev_build: bool = False,
        byte_code: bool = False,
        distribution: Literal["wheel", "sdist"] = "wheel",
        timestamp: datetime.datetime | None = None,
    ) -> str:
        """
        Build the module using the pip system config and return the path to the build artifact.

        :param byte_code: When set to true, only bytecode will be included. This also results in a binary wheel.
        :param timestamp: If a dev build is requested, this timestamp will be used in the version number of the dev build.
                          If None, the current time will be used as a timestamp.
        """
        if os.path.exists(output_directory):
            if not os.path.isdir(output_directory):
                raise ModuleBuildFailedError(msg=f"Given output directory is not a directory: {output_directory}")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy module to temporary directory to perform the build
            build_path = os.path.join(tmpdir, "module")
            shutil.copytree(self._module.path, build_path)
            if dev_build:
                self._add_dev_build_tag_to_setup_cfg(build_path, timestamp)
            self._ensure_plugins(build_path)
            self._move_data_files_into_namespace_package_dir(build_path)
            if byte_code:
                self._byte_compile_code(build_path)

            distribution_pkg = self._build_v2_module(build_path, output_directory, distribution)
            self._verify(build_path, distribution_pkg, distribution)
            return distribution_pkg

    def _add_dev_build_tag_to_setup_cfg(self, build_path: str, timestamp: datetime.datetime | None = None) -> None:
        """
        Add a build_tag of the format `.dev<timestamp>` to the setup.cfg file. The timestamp has the form %Y%m%d%H%M%S.

        :param timestamp: The timestamp to use in the version number of the dev build. If None, use the current time
                          as the timestamp.
        """
        path_setup_cfg = os.path.join(build_path, "setup.cfg")
        # Read setup.cfg file
        config_in = ConfigParser()
        config_in.read(path_setup_cfg)
        # Set build_tag
        if not config_in.has_section("egg_info"):
            config_in.add_section("egg_info")
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        timestamp_str = timestamp.strftime("%Y%m%d%H%M%S")
        config_in.set("egg_info", "tag_build", f".dev{timestamp_str}")
        # Write file back
        with open(path_setup_cfg, "w") as fh:
            config_in.write(fh)

    def _byte_compile_code(self, build_path: str) -> None:
        # Backup src dir and replace .py files with .pyc files
        for root, dirs, files in os.walk(os.path.join(build_path, "inmanta_plugins"), followlinks=True):
            for current_file in [f for f in files if f.endswith(".py")]:
                py_file = os.path.join(root, current_file)
                pyc_file = f"{py_file}c"
                py_compile.compile(file=py_file, cfile=pyc_file, doraise=True)
                os.remove(py_file)

        # Make sure there is a pyc line in the manifest.in
        with open(os.path.join(build_path, "MANIFEST.in"), "r+", encoding="utf-8") as fh:
            content = fh.read()
            # Make sure that there is at least one .pyc include
            if ".pyc" not in content:
                # Add it to the manifest. The read has moved the pointer to the end of the file
                LOGGER.info("Adding .pyc include line to the MANIFEST")
                fh.write("\nrecursive-include inmanta_plugins *.pyc\n")
                fh.write("global-exclude */__pycache__/*\n")

        # For wheel to build a non universal python wheel we need to trick it into thinking it contains
        # compiled extensions against a specific python ABI. If not we might install this wheel on a python with incompatible
        # python code
        dummy_file = os.path.join(build_path, "inmanta_plugins", self._module.name, "_cdummy.c")
        with open(dummy_file, "w") as fd:
            fd.write("// Dummy python file")

        setup_file = os.path.join(build_path, "setup.py")
        if os.path.exists(setup_file):
            LOGGER.warning("This command will overwrite setup.py to make sure a correct wheel is generated.")

        with open(os.path.join(build_path, "setup.py"), "w") as fd:
            fd.write(f"""
from distutils.core import setup
from Cython.Build import cythonize
setup(name="{ModuleV2Source.get_package_name_for(self._module.name)}",
    version="{self._module.version}",
    ext_modules=cythonize("inmanta_plugins/{self._module.name}/_cdummy.c"),
)
            """)

        # make sure cython is in the pyproject.toml
        pyproject = ModuleConverter.get_pyproject(build_path, build_requires=["wheel", "setuptools", "cython"])
        with open(os.path.join(build_path, "pyproject.toml"), "w") as fh:
            fh.write(pyproject)

    def _verify(self, build_path: str, path_distribution_pkg: str, distribution: Literal["wheel", "sdist"]) -> None:
        """
        Verify whether there were files in the python package on disk that were not packaged
        in the given distribution package and log a warning if such a file exists.
        """
        rel_path_namespace_package = os.path.join("inmanta_plugins", self._module.name)
        abs_path_namespace_package = os.path.join(build_path, rel_path_namespace_package)
        files_in_python_package_dir = self._get_files_in_directory(abs_path_namespace_package, ignore=BUILD_FILE_IGNORE_PATTERN)
        dir_prefix = f"{rel_path_namespace_package}/"
        files_in_plugins_dir: set[str]
        if distribution == "wheel":
            # It's a wheel
            with zipfile.ZipFile(path_distribution_pkg) as z:
                files_in_plugins_dir = {
                    info.filename[len(dir_prefix) :]
                    for info in z.infolist()
                    if not info.is_dir() and info.filename.startswith(dir_prefix)
                }
        else:
            # It's an sdist
            files_in_plugins_dir = set()
            with tarfile.open(name=path_distribution_pkg) as tar:
                for member in tar.getmembers():
                    if member.isdir():
                        continue
                    path = pathlib.Path(member.name)
                    path_without_root_dir = path.relative_to(path.parts[0])
                    if path_without_root_dir.parts[0:2] == ("inmanta_plugins", self._module.name):
                        path_from_mod_plugins_dir = path_without_root_dir.relative_to(dir_prefix)
                        files_in_plugins_dir.add(str(path_from_mod_plugins_dir))
        unpackaged_files = files_in_python_package_dir - files_in_plugins_dir
        if unpackaged_files:
            LOGGER.warning(
                f"The following files are present in the {rel_path_namespace_package} directory on disk, but were not "
                f"packaged: {list(unpackaged_files)}. Update you MANIFEST.in file if they need to be packaged."
            )

    def _ensure_plugins(self, build_path: str) -> None:
        plugins_folder = os.path.join(build_path, "inmanta_plugins", self._module.name)
        if not os.path.exists(plugins_folder):
            os.makedirs(plugins_folder)
        init_file = os.path.join(plugins_folder, "__init__.py")
        if not os.path.exists(init_file):
            open(init_file, "w").close()

    def _get_files_in_directory(self, directory: str, ignore: Optional[Pattern[str]] = None) -> set[str]:
        """
        Return the relative paths to all the files in all subdirectories of the given directory.

        :param directory: The directory to list the files of.
        :param ignore: Pattern for files and subdirectories to ignore, regardless of their relative depth. The pattern should
            match the full file or directory names.
        """

        def should_ignore(name: str) -> bool:
            return ignore is not None and ignore.fullmatch(name) is not None

        if not os.path.isdir(directory):
            raise Exception(f"{directory} is not a directory")
        result: set[str] = set()
        for dirpath, dirnames, filenames in os.walk(directory):
            if should_ignore(os.path.basename(dirpath)):
                # ignore whole subdirectory
                continue
            relative_paths_to_filenames = {
                os.path.relpath(os.path.join(dirpath, f), directory) for f in filenames if not should_ignore(f)
            }
            result = result | relative_paths_to_filenames
        return result

    def _move_data_files_into_namespace_package_dir(self, build_path: str) -> None:
        """
        Copy all files that have to be packaged into the Python package of the module
        """
        python_pkg_dir: str = os.path.join(build_path, "inmanta_plugins", self._module.name)
        dir_path_bundling_description_mapping = {
            ("model", "the inmanta model files"),
            ("files", "inmanta files for managed machines"),
            ("templates", "inmanta templates that will be used to generate configuration files"),
        }
        for problematic_dir, bundling_description in dir_path_bundling_description_mapping:
            if os.path.exists(os.path.join(python_pkg_dir, problematic_dir)):
                raise ModuleBuildFailedError(
                    msg="There is already a `%s` directory in %s. "
                    "The `inmanta_plugins.%s.%s` package is reserved for bundling %s. "
                    "Please use a different name for this Python package."
                    % (
                        problematic_dir,
                        os.path.join(self._module.path, "inmanta_plugins", self._module.name),
                        self._module.name,
                        problematic_dir,
                        bundling_description,
                    )
                )

        for dir_name in ["model", "files", "templates"]:
            fq_dir_name = os.path.join(build_path, dir_name)
            if os.path.exists(fq_dir_name):
                shutil.move(fq_dir_name, python_pkg_dir)
        metadata_file = os.path.join(build_path, "setup.cfg")
        shutil.copy(metadata_file, python_pkg_dir)

    def _get_isolated_env_builder(self) -> DefaultIsolatedEnv:
        """
        Returns the DefaultIsolatedEnv instance that should be used to build V2 modules. To speed to up the test
        suite, the build environment is cached when the tests are ran. This is possible because all modules, built
        by the test suite, have the same build requirements. For tests that need to test the code path used in
        production, the V2ModuleBuilder.DISABLE_DEFAULT_ISOLATED_ENV_CACHED flag can be set to True.
        """
        if inmanta.RUNNING_TESTS and not V2ModuleBuilder.DISABLE_DEFAULT_ISOLATED_ENV_CACHED:
            return DefaultIsolatedEnvCached.get_instance()
        else:
            return DefaultIsolatedEnv()

    def _build_v2_module(self, build_path: str, output_directory: str, distribution: Literal["wheel", "sdist"]) -> str:
        """
        Build v2 module using the pip system config and using PEP517 package builder.
        """
        try:
            with self._get_isolated_env_builder() as env:
                builder = build.ProjectBuilder(source_dir=build_path, python_executable=env.python_executable)
                env.install(builder.build_system_requires)
                env.install(builder.get_requires_for_build(distribution=distribution))
                return builder.build(distribution=distribution, output_directory=output_directory)
        except Exception:
            raise ModuleBuildFailedError(msg="Module build failed")


@stable_api
class ModuleConverter:
    def __init__(self, module: ModuleV1) -> None:
        self._module = module

    def convert(self, output_directory: str) -> None:
        # validate input
        if os.path.exists(output_directory):
            if not os.path.isdir(output_directory):
                raise ModuleBuildFailedError(msg=f"Given output directory is not a directory: {output_directory}")
            if os.listdir(output_directory):
                raise ModuleBuildFailedError(msg=f"Non-empty output directory {output_directory}")
            os.rmdir(output_directory)

        output_directory = os.path.abspath(output_directory)

        # convert meta-data (also performs validation, so we do it first to fail fast)
        setup_cfg = self.get_setup_cfg(self._module.path, warn_on_merge=False)

        # copy all files
        shutil.copytree(self._module.path, output_directory)

        self._do_update(output_directory, setup_cfg, warn_on_merge=False)

    def convert_in_place(self) -> None:
        output_directory = os.path.abspath(self._module.path)

        if os.path.exists(os.path.join(output_directory, "MANIFEST.in")):
            raise CLIException("MANIFEST.in already exists, aborting. Please remove/rename this file", exitcode=1)

        if os.path.exists(os.path.join(output_directory, "inmanta_plugins")):
            raise CLIException("inmanta_plugins folder already exists, aborting. Please remove/rename this file", exitcode=1)

        if os.path.exists(os.path.join(output_directory, "setup.py")):
            raise CLIException(
                f"Cannot convert v1 module at {output_directory} to v2 because a setup.py file is present."
                " Please remove/rename this file",
                exitcode=1,
            )

        setup_cfg = self.get_setup_cfg(output_directory, warn_on_merge=True)
        self._do_update(output_directory, setup_cfg, warn_on_merge=True)

    def _do_update(self, output_directory: str, setup_cfg: ConfigParser, warn_on_merge: bool = False) -> None:
        # remove module.yaml
        os.remove(os.path.join(output_directory, self._module.MODULE_FILE))
        # move plugins or create
        old_plugins = os.path.join(output_directory, "plugins")
        new_plugins = os.path.join(output_directory, "inmanta_plugins", self._module.name)
        if os.path.exists(new_plugins) and os.listdir(new_plugins):
            raise ModuleBuildFailedError(
                msg=f"Could not build module: inmanta_plugins/{self._module.name} directory already exists and is not empty"
            )
        if os.path.exists(new_plugins):
            os.rmdir(new_plugins)
        if os.path.exists(old_plugins):
            shutil.move(old_plugins, new_plugins)
        else:
            os.makedirs(new_plugins)
            with open(os.path.join(new_plugins, "__init__.py"), "w"):
                pass

        # write out pyproject.toml
        # read before erasing
        pyproject = self.get_pyproject(output_directory, warn_on_merge=warn_on_merge)
        with open(os.path.join(output_directory, "pyproject.toml"), "w") as fh:
            fh.write(pyproject)
        # write out setup.cfg
        with open(os.path.join(output_directory, "setup.cfg"), "w") as fh:
            setup_cfg.write(fh)
        # write out MANIFEST.in
        with open(os.path.join(output_directory, "MANIFEST.in"), "w", encoding="utf-8") as fh:
            fh.write(f"""
include inmanta_plugins/{self._module.name}/setup.cfg
include inmanta_plugins/{self._module.name}/py.typed
recursive-include inmanta_plugins/{self._module.name}/model *.cf
graft inmanta_plugins/{self._module.name}/files
graft inmanta_plugins/{self._module.name}/templates
                """.strip() + "\n")

    @classmethod
    def get_pyproject(cls, in_folder: str, warn_on_merge: bool = False, build_requires: Optional[list[str]] = None) -> str:
        """
        Adds this to the existing config

        [build-system]
        requires = ["setuptools", "wheel"]
        build-backend = "setuptools.build_meta"
        """
        if build_requires is None:
            build_requires = ["setuptools", "wheel"]

        config_in = {}
        if os.path.exists(os.path.join(in_folder, "pyproject.toml")):
            with open(os.path.join(in_folder, "pyproject.toml")) as fh:
                loglevel = logging.WARNING if warn_on_merge else logging.INFO
                LOGGER.log(
                    level=loglevel,
                    msg="pyproject.toml file already exists, merging. This will remove all comments from the file",
                )
                config_in = toml.load(fh)

        # Simple schema validation on relevant part
        build_system = config_in.setdefault("build-system", {})
        if not isinstance(build_system, dict):
            raise CLIException(
                f"Invalid pyproject.toml: 'build-system' should be of type dict but is of type '{type(build_system)}'",
                exitcode=1,
            )

        requires = build_system.setdefault("requires", [])
        if not isinstance(requires, list):
            if isinstance(requires, str):
                # is it a single string, convert to list
                build_system["requires"] = [requires]
                requires = build_system["requires"]
            else:
                raise CLIException(
                    f"Invalid pyproject.toml: 'build-system.requires' should be of type list but is of type '{type(requires)}'",
                    exitcode=1,
                )

        for req in build_requires:
            if req not in requires:
                requires.append(req)
        build_system["build-backend"] = "setuptools.build_meta"

        return toml.dumps(config_in)

    def get_setup_cfg(self, in_folder: str, warn_on_merge: bool = False) -> configparser.ConfigParser:
        config_in = ConfigParser()
        if os.path.exists(os.path.join(in_folder, "setup.cfg")):
            loglevel = logging.WARNING if warn_on_merge else logging.INFO
            LOGGER.log(
                level=loglevel, msg="setup.cfg file already exists, merging. This will remove all comments from the file"
            )
            config_in.read(os.path.join(in_folder, "setup.cfg"))

        # convert main config
        config = self._module.metadata.to_v2().to_config(config_in)

        config.add_section("options")
        config.add_section("options.packages.find")

        # add requirements
        module_requirements: list[InmantaModuleRequirement] = [
            req for req in self._module.get_all_requires() if req.name != self._module.name
        ]
        python_requirements: list[str] = self._module.get_strict_python_requirements_as_list()
        if module_requirements or python_requirements:
            requires: list[str] = sorted([str(r.get_python_package_requirement()) for r in module_requirements])
            requires += python_requirements
            config.set("options", "install_requires", "\n".join(requires))

        # Make setuptools work
        config["options"]["zip_safe"] = "False"
        config["options"]["include_package_data"] = "True"
        config["options"]["packages"] = "find_namespace:"
        config["options.packages.find"]["include"] = "inmanta_plugins*"

        return config


class PythonPackageToSourceConverter:
    """
    A class that offers support to download Inmanta modules in source format
    from a Python package repository.
    """

    def download_in_source_format(
        self,
        output_dir: str,
        dependencies: Sequence[util.CanonicalRequirement],
        ignore_transitive_dependencies: bool,
        constraints: Sequence[util.CanonicalRequirement] | None = None,
        pip_config: model.PipConfig | None = None,
        override_if_already_exists: bool = False,
    ) -> list[str]:
        """
        This method:
            * Downloads the source distribution packages for the given
              dependencies from a Python package repository.
            * Extracts them.
            * Converts them into their source format.

        :param ignore_transitive_dependencies: False iff also download and extract the Inmanta modules
                                               that are transitive dependencies of the given dependencies.
        :param override_if_already_exists: True iff any directory in the output directory that already exists
                                           will be overriden. Otherwise an exception is raised.
        """
        if not dependencies:
            return []
        result = []
        with tempfile.TemporaryDirectory() as path_tmp_dir:
            # Download the python package
            download_dir = os.path.join(path_tmp_dir, "download")
            os.mkdir(download_dir)
            paths_source_packages: list[str] = self._download_source_packages(
                dependencies=dependencies,
                constraints=constraints,
                ignore_transitive_dependencies=ignore_transitive_dependencies,
                download_dir=download_dir,
                pip_config=pip_config,
            )
            # Extract the packages and convert to source format
            extract_dir = os.path.join(path_tmp_dir, "extract")
            os.mkdir(extract_dir)
            for path_current_package in paths_source_packages:
                inmanta_module_name: str = util.get_module_name(path_distribution_pkg=path_current_package)
                path_extracted_pkg = self._extract_source_package(path_current_package, extract_dir)
                self._convert_to_source_format(path_extracted_pkg, inmanta_module_name)
                # Move to desired output directory
                path_pkg_in_output_dir = os.path.join(output_dir, inmanta_module_name)
                if os.path.exists(path_pkg_in_output_dir):
                    if override_if_already_exists:
                        shutil.rmtree(path_pkg_in_output_dir)
                    else:
                        raise Exception(f"Directory {path_pkg_in_output_dir} already exists")
                shutil.move(src=path_extracted_pkg, dst=path_pkg_in_output_dir)
                result.append(path_pkg_in_output_dir)
        return result

    def _download_source_packages(
        self,
        dependencies: Sequence[util.CanonicalRequirement],
        constraints: Sequence[util.CanonicalRequirement] | None,
        ignore_transitive_dependencies: bool,
        download_dir: str,
        pip_config: model.PipConfig | None,
    ) -> list[str]:
        """
        Download the source distribution packages for the given requirements into the download_dir.

        :return: A list of paths to the source distribution packages that were downloaded.
        """
        assert not os.listdir(download_dir)

        with tempfile.TemporaryDirectory() as path_tmp_dir:
            # Stage 1: Determine which versions to download
            requirements: list[util.CanonicalRequirement]
            if len(dependencies) == 1 and not constraints:
                # We only have one dependency, so we cannot have any version conflicts between dependencies.
                requirements = list(dependencies)
            else:
                # Perform download with all dependencies, so that we know the exact version we need.
                env.process_env.download_distributions(
                    output_directory=path_tmp_dir,
                    pip_config=pip_config,
                    dependencies=dependencies,
                    constraints=constraints,
                    no_deps=False,
                )
                # Fetch the packages and their exact versions
                requirements = []
                dependencies_pkg_names: set[str] = {d.name for d in dependencies}
                for filename in os.listdir(path_tmp_dir):
                    if not filename.startswith("inmanta_module_"):
                        # Not an Inmanta module
                        continue
                    pkg_name, version = util.get_pkg_name_and_version(filename)
                    if ignore_transitive_dependencies and pkg_name not in dependencies_pkg_names:
                        # It's a transitive dependency we can ignore
                        continue
                    requirements.append(util.parse_requirement(f"{pkg_name}=={version}"))

            # Stage 2: Download the correct versions of the requested packages as source distribution.
            for req in requirements:
                try:
                    env.process_env.download_distributions(
                        output_directory=download_dir,
                        pip_config=pip_config,
                        dependencies=[req],
                        constraints=constraints,
                        no_deps=True,
                        # Setting no_binary to :all: would imply that `pip download` downloads dependencies
                        # (e.g. setuptools) of these modules in source format as well. This would make the
                        # command fail if these dependencies are not available in a source distribution package.
                        no_binary=req.name,
                    )
                except env.PackageNotFound:
                    LOGGER.warning("Package %s is not available as a source distribution package. Skipping it.", str(req))

        return [os.path.join(download_dir, filename) for filename in os.listdir(download_dir)]

    def _extract_source_package(self, path_source_package: str, extract_dir: str) -> str:
        """
        Extract the given source distribution package into the given extract_dir directory.
        """
        assert not os.listdir(extract_dir)
        with gzip.open(filename=path_source_package, mode="rb") as tar_file_obj:
            with tarfile.TarFile(mode="r", fileobj=tar_file_obj) as tar:
                tar.extractall(path=extract_dir, filter="data")

        files_extract_dir = os.listdir(extract_dir)
        assert len(files_extract_dir) == 1
        return os.path.join(extract_dir, files_extract_dir[0])

    def _convert_to_source_format(self, path_extracted_pkg: str, module_name: str) -> None:
        """
        Move the files from the extracted Python package into their location on the source code repository.
        """
        try:
            # Remove this file as it will be replaced by the one present in the inmanta_plugins/<mod-name> directory.
            os.remove(os.path.join(path_extracted_pkg, "setup.cfg"))
        except FileNotFoundError:
            pass
        files_and_dirs_to_move = ["model", "templates", "files", "setup.cfg"]
        for file_or_dir in files_and_dirs_to_move:
            fq_path = os.path.join(path_extracted_pkg, "inmanta_plugins", module_name, file_or_dir)
            if os.path.exists(fq_path):
                shutil.move(src=fq_path, dst=path_extracted_pkg)
