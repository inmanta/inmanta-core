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
import inspect
import logging
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from argparse import ArgumentParser, RawTextHelpFormatter
from collections import abc
from configparser import ConfigParser
from functools import total_ordering
from types import TracebackType
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Pattern, Sequence, Set, Type

import click
import texttable
import yaml
from cookiecutter.main import cookiecutter
from pkg_resources import parse_version

import build
import build.env
import inmanta
import inmanta.warnings
import toml
from build.env import IsolatedEnvBuilder
from inmanta import const, env
from inmanta.ast import CompilerException
from inmanta.command import CLIException, ShowUsageException
from inmanta.const import CF_CACHE_DIR, MAX_UPDATE_ATTEMPT
from inmanta.module import (
    DummyProject,
    FreezeOperator,
    InmantaModuleRequirement,
    InstallMode,
    InvalidMetadata,
    InvalidModuleException,
    Module,
    ModuleGeneration,
    ModuleLike,
    ModuleMetadata,
    ModuleMetadataFileNotFound,
    ModuleNotFoundException,
    ModuleV1,
    ModuleV2,
    ModuleV2Source,
    Project,
    gitprovider,
)
from inmanta.stable_api import stable_api
from packaging.version import Version

if TYPE_CHECKING:
    from pkg_resources import Requirement  # noqa: F401

    from packaging.requirements import InvalidRequirement
else:
    from pkg_resources.extern.packaging.requirements import InvalidRequirement


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
        help="When this option is enabled, only version conflicts in the direct dependencies will result in an error. "
        "All other version conflicts will result in a warning. This option is mutually exclusive with the "
        "--strict-deps-check option.",
    )
    parser.add_argument(
        "--strict-deps-check",
        dest="strict_deps_check",
        action="store_true",
        default=False,
        help="When this option is enabled, a version conflict in any (transitive) dependency will results in an error. "
        "This option is mutually exclusive with the --no-strict-deps-check option.",
    )


def get_strict_deps_check(no_strict_deps_check: bool, strict_deps_check: bool) -> Optional[bool]:
    """
    Perform input validation on the --no-strict-deps-check and --strict-deps-check options and
    return True iff strict dependency checking should be used.
    """
    if no_strict_deps_check and strict_deps_check:
        raise Exception("Options --no-strict-deps-check and --strict-deps-check cannot be set together")
    if not no_strict_deps_check and not strict_deps_check:
        # If none of the *strict_deps_check options are provided, use the value set in the project.yml file
        return None
    if no_strict_deps_check:
        return False
    return strict_deps_check


class ModuleLikeTool(object):
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

    def get_project(self, load: bool = False, strict_deps_check: Optional[bool] = None) -> Project:
        project = Project.get(strict_deps_check=strict_deps_check)
        if load:
            project.load()
        return project

    def determine_new_version(self, old_version, version, major, minor, patch, dev):
        """
        Only used by the `inmanta module commit` command.
        """
        was_dev = old_version.is_prerelease

        if was_dev:
            if major or minor or patch:
                LOGGER.warning("when releasing a dev version, options --major, --minor and --patch are ignored")

            # determine new version
            if version is not None:
                baseversion = version
            else:
                baseversion = old_version.base_version

            if not dev:
                outversion = baseversion
            else:
                outversion = "%s.dev%d" % (baseversion, time.time())
        else:
            opts = [x for x in [major, minor, patch] if x]
            if version is not None:
                if len(opts) > 0:
                    LOGGER.warn("when using the --version option, --major, --minor and --patch are ignored")
                outversion = version
            else:
                if len(opts) == 0:
                    LOGGER.error("One of the following options is required: --major, --minor or --patch")
                    return None
                elif len(opts) > 1:
                    LOGGER.error("You can use only one of the following options: --major, --minor or --patch")
                    return None

                change_type: Optional[ChangeType] = ChangeType.parse_from_bools(patch, minor, major)
                if change_type:
                    outversion = str(VersionOperation.bump_version(change_type, old_version, version_tag=""))
                else:
                    outversion = str(VersionOperation.set_version_tag(old_version, version_tag=""))

            if dev:
                outversion = "%s.dev%d" % (outversion, time.time())

        outversion = parse_version(outversion)
        if outversion <= old_version:
            LOGGER.error("new versions (%s) is not larger then old version (%s), aborting" % (outversion, old_version))
            return None

        return outversion


@total_ordering
@enum.unique
class ChangeType(enum.Enum):
    MAJOR: str = "major"
    MINOR: str = "minor"
    PATCH: str = "patch"

    def less(self) -> Optional["ChangeType"]:
        """
        Returns the change type that is one less than this one.
        """
        if self == ChangeType.MAJOR:
            return ChangeType.MINOR
        if self == ChangeType.MINOR:
            return ChangeType.PATCH
        return None

    def __lt__(self, other: "ChangeType") -> bool:
        order: List[ChangeType] = [ChangeType.PATCH, ChangeType.MINOR, ChangeType.MAJOR]
        if other not in order:
            return NotImplemented
        return order.index(self) < order.index(other)

    @classmethod
    def diff(cls, *, low: Version, high: Version) -> Optional["ChangeType"]:
        """
        Returns the order of magnitude of the change type diff between two versions.
        Return None if the versions are less than a patch separated from each other.
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
        raise Exception("Couldn't determine version change type diff: this state should be unreachable")

    @classmethod
    def parse_from_bools(cls, patch: bool, minor: bool, major: bool) -> Optional["ChangeType"]:
        """
        Create a ChangeType for the type of which the boolean is set to True. If none
        of the boolean arguments is set to True, None is returned. If more
        than one boolean argument is set to True, a ValueError is raised.
        """
        if sum([patch, minor, major]) > 1:
            raise ValueError("Only one argument of patch, minor or major can be set to True at the same time.")
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
        parts = [int(x) for x in version.base_version.split(".")]
        while len(parts) < 3:
            parts.append(0)
        if change_type is ChangeType.PATCH:
            parts[2] += 1
        if change_type is ChangeType.MINOR:
            parts[1] += 1
            parts[2] = 0
        if change_type is ChangeType.MAJOR:
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        # Reset remaining digits to zero
        if len(parts) > 3:
            parts[3:] = [0 for _ in range(len(parts) - 3)]

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
    def parser_config(cls, parser: ArgumentParser) -> None:
        subparser = parser.add_subparsers(title="subcommand", dest="cmd")
        freeze = subparser.add_parser("freeze", help="Set all version numbers in project.yml")
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
        init = subparser.add_parser("init", help="Initialize directory structure for a project")
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
        )
        add_deps_check_arguments(update)

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

        with open(project.get_metadata_file_path(), "r", encoding="utf-8") as fd:
            newconfig = yaml.safe_load(fd)

        requires = sorted([k + " " + v for k, v in freeze.items()])
        newconfig["requires"] = requires

        close = False

        if outfile is None:
            outfile = open(project.get_metadata_file_path(), "w", encoding="UTF-8")
            close = True
        elif outfile == "-":
            outfile = sys.stdout
        else:
            outfile = open(outfile, "w", encoding="UTF-8")
            close = True

        try:
            outfile.write(yaml.dump(newconfig, default_flow_style=False, sort_keys=False))
        finally:
            if close:
                outfile.close()

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
        strict = get_strict_deps_check(no_strict_deps_check, strict_deps_check)
        project: Project = self.get_project(load=False, strict_deps_check=strict)
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
        strict = get_strict_deps_check(no_strict_deps_check, strict_deps_check)
        if project is None:
            # rename var to make mypy happy
            my_project = self.get_project(load=False, strict_deps_check=strict)
        else:
            my_project = project

        def do_update(specs: "Dict[str, List[InmantaModuleRequirement]]", modules: List[str]) -> None:
            v2_modules = {module for module in modules if my_project.module_source.path_for(module) is not None}

            v2_python_specs: List[Requirement] = [
                module_spec.get_python_package_requirement()
                for module, module_specs in specs.items()
                for module_spec in module_specs
                if module in v2_modules
            ]
            if v2_python_specs:
                # Get known requires and add them to prevent invalidating constraints through updates
                # These could be constraints (-c) as well, but that requires additional sanitation
                # Because for pip not every valid -r is a valid -c
                current_requires = my_project.get_strict_python_requirements_as_list()
                env.process_env.install_from_index(
                    v2_python_specs + [Requirement.parse(r) for r in current_requires],
                    my_project.module_source.urls,
                    upgrade=True,
                    allow_pre_releases=my_project.install_mode != InstallMode.release,
                )

            for v1_module in set(modules).difference(v2_modules):
                spec = specs.get(v1_module, [])
                try:
                    ModuleV1.update(my_project, v1_module, spec, install_mode=my_project.install_mode)
                except Exception:
                    LOGGER.exception("Failed to update module %s", v1_module)

            # Load the newly installed modules into the modules cache
            my_project.install_modules(bypass_module_cache=True, update_dependencies=True)

        attempt = 0
        done = False
        last_failure: Optional[CompilerException] = None

        while not done and attempt < MAX_UPDATE_ATTEMPT:
            LOGGER.info("Performing update attempt %d of %d", attempt + 1, MAX_UPDATE_ATTEMPT)
            try:
                loaded_mods_pre_update = {module_name: mod.version for module_name, mod in my_project.modules.items()}

                # get AST
                my_project.load_module_recursive(install=True)
                # get current full set of requirements
                specs: Dict[str, List[InmantaModuleRequirement]] = my_project.collect_imported_requirements()
                if module is None:
                    modules = list(specs.keys())
                else:
                    modules = [module]
                do_update(specs, modules)

                loaded_mods_post_update = {module_name: mod.version for module_name, mod in my_project.modules.items()}
                if loaded_mods_pre_update == loaded_mods_post_update:
                    # No changes => state has converged
                    done = True
                else:
                    # New modules were downloaded or existing modules were updated to a new version. Perform another pass to
                    # make sure that all dependencies, defined in these new modules, are taken into account.
                    last_failure = CompilerException("Module update did not converge")
            except CompilerException as e:
                last_failure = e
                # model is corrupt
                LOGGER.info("The model is not currently in an executable state, performing intermediate updates")
                # get all specs from all already loaded modules
                specs = my_project.collect_requirements()

                if module is None:
                    # get all loaded/partly loaded modules
                    modules = list(my_project.modules.keys())
                else:
                    modules = [module]
                do_update(specs, modules)
            attempt += 1

        if last_failure is not None and not done:
            raise last_failure


@stable_api
class ModuleTool(ModuleLikeTool):
    """
    A tool to manage configuration modules
    """

    def __init__(self) -> None:
        self._mod_handled_list = set()

    @classmethod
    def modules_parser_config(cls, parser: ArgumentParser) -> None:
        parser.add_argument("-m", "--module", help="Module to apply this command to", nargs="?", default=None)

        subparser = parser.add_subparsers(title="subcommand", dest="cmd")

        add_help_msg = "Add a module dependency to an Inmanta module or project."
        add = subparser.add_parser(
            "add",
            help=add_help_msg,
            description=f"{add_help_msg} When executed on a project, the module is installed as well. "
            f"Either --v1 or --v2 has to be set.",
        )
        add.add_argument(
            "module_req",
            help="The name of the module, optionally with a version constraint.",
        )
        add.add_argument("--v1", dest="v1", help="Add the given module as a v1 module", action="store_true")
        add.add_argument("--v2", dest="v2", help="Add the given module as a V2 module", action="store_true")
        add.add_argument(
            "--override",
            dest="override",
            help="Override the version constraint when the given module dependency already exists.",
            action="store_true",
        )

        subparser.add_parser("list", help="List all modules used in this project in a table")

        do = subparser.add_parser("do", help="Execute a command on all loaded modules")
        do.add_argument("command", metavar="command", help="the command to  execute")

        install: ArgumentParser = subparser.add_parser(
            "install",
            help="Install a module in the active Python environment.",
            description="""
Install a module in the active Python environment. Only works for v2 modules: v1 modules can only be installed in the context
of a project.

This command might reinstall Python packages in the development venv if the currently installed versions are not compatible
with the dependencies specified by the installed module.

Like `pip install`, this command does not reinstall a module for which the same version is already installed, except in editable
mode.
        """.strip(),
        )
        install.add_argument("-e", "--editable", action="store_true", help="Install in editable mode.")
        install.add_argument("path", nargs="?", help="The path to the module.")

        subparser.add_parser("status", help="Run a git status on all modules and report")

        subparser.add_parser("push", help="Run a git push on all modules and report")

        # not currently working
        subparser.add_parser("verify", help="Verify dependencies and frozen module versions")

        commit = subparser.add_parser("commit", help="Commit all changes in the current module.")
        commit.add_argument("-m", "--message", help="Commit message", required=True)
        commit.add_argument("-r", "--release", dest="dev", help="make a release", action="store_false")
        commit.add_argument("--major", dest="major", help="make a major release", action="store_true")
        commit.add_argument("--minor", dest="minor", help="make a major release", action="store_true")
        commit.add_argument("--patch", dest="patch", help="make a major release", action="store_true")
        commit.add_argument("-v", "--version", help="Version to use on tag")
        commit.add_argument("-a", "--all", dest="commit_all", help="Use commit -a", action="store_true")
        commit.add_argument(
            "-t",
            "--tag",
            dest="tag",
            help="Create a tag for the commit."
            "Tags are not created for dev releases by default, if you want to tag it, specify this flag explicitly",
            action="store_true",
        )
        commit.add_argument("-n", "--no-tag", dest="tag", help="Don't create a tag for the commit", action="store_false")
        commit.set_defaults(tag=False)

        create = subparser.add_parser("create", help="Create a new module")
        create.add_argument("name", help="The name of the module")
        create.add_argument(
            "--v1", dest="v1", help="Create a v1 module. By default a v2 module is created.", action="store_true"
        )

        freeze = subparser.add_parser("freeze", help="Set all version numbers in module.yml")
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

        build = subparser.add_parser("build", help="Build a Python package from a V2 module.")
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

        subparser.add_parser("v1tov2", help="Convert a V1 module to a V2 module in place")

        release = subparser.add_parser(
            "release",
            help="Release a new stable or dev release for this module.",
            description="""
When a stable release is done, this command:
* Does a commit that changes the current version to a stable version.
* Adds Git release tag.
* Does a commit that changes the current version to a development version that is one patch increment ahead of the released
  version.
When a development release is done using the --dev option, this command:
* Does a commit that updates the current version of the module to a development version that is a patch, minor or major version
  ahead of the previous stable release. The size of the increment is determined by the --patch, --minor or --major argument
  (--patch is the default). When a CHANGELOG.md file is present in the root of the module directory then the version number in
  the changelog is also updated accordingly. The changelog file is always populated with the associated stable version and
  not a development version.
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
        release.add_argument("-m", "--message", help="Commit message")
        release.add_argument(
            "-c",
            "--changelog-message",
            help="This changelog message will be written to the changelog file. If the -m option is not provided, "
            "this message will also be used as the commit message.",
        )

    def add(self, module_req: str, v1: bool = False, v2: bool = False, override: bool = False) -> None:
        """
        Add a module dependency to an Inmanta module or project.

        :param module_req: The module to add, optionally with a version constraint.
        :param v1: Whether the given module should be added as a V1 module or not.
        :param override: If set to True, override the version constraint when the module dependency already exists.
                         If set to False, this method raises an exception when the module dependency already exists.
        """
        if not v1 and not v2:
            raise CLIException("Either --v1 or --v2 has to be set", exitcode=1)
        if v1 and v2:
            raise CLIException("--v1 and --v2 cannot be set together", exitcode=1)
        module_like: Optional[ModuleLike] = ModuleLike.from_path(path=os.getcwd())
        if module_like is None:
            raise CLIException("Current working directory doesn't contain an Inmanta module or project", exitcode=1)
        try:
            module_requirement = InmantaModuleRequirement.parse(module_req)
        except InvalidRequirement:
            raise CLIException(f"'{module_req}' is not a valid requirement", exitcode=1)
        if not override and module_like.has_module_requirement(module_requirement.key):
            raise CLIException(
                "A dependency on the given module was already defined, use --override to override the version constraint",
                exitcode=1,
            )
        if isinstance(module_like, Project):
            try:
                module_like.install_module(module_requirement, install_as_v1_module=v1)
            except ModuleNotFoundException:
                raise CLIException(
                    f"Failed to install {module_requirement} as a {'v1' if v1 else 'v2'} module.",
                    exitcode=1,
                )
            else:
                # cached project might have inconsistent state after modifying the environment through another instance
                self.get_project(load=False).invalidate_state()
        module_like.add_module_requirement_persistent(requirement=module_requirement, add_as_v1_module=v1)

    def v1tov2(self, module: str) -> None:
        """
        Convert a V1 module to a V2 module in place
        """
        module = self.get_module(module)
        if not isinstance(module, ModuleV1):
            raise ModuleVersionException(f"Expected a v1 module, but found v{module.GENERATION.value} module")
        ModuleConverter(module).convert_in_place()

    def build(
        self, path: Optional[str] = None, output_dir: Optional[str] = None, dev_build: bool = False, byte_code: bool = False
    ) -> str:
        """
        Build a v2 module and return the path to the build artifact.
        """
        if path is not None:
            path = os.path.abspath(path)
        else:
            path = os.getcwd()

        module = self.construct_module(DummyProject(), path)

        if output_dir is None:
            output_dir = os.path.join(path, "dist")

        if isinstance(module, ModuleV1):
            with tempfile.TemporaryDirectory() as tmpdir:
                ModuleConverter(module).convert(tmpdir)
                return V2ModuleBuilder(tmpdir).build(output_dir, dev_build=dev_build, byte_code=byte_code)
        else:
            return V2ModuleBuilder(path).build(output_dir, dev_build=dev_build, byte_code=byte_code)

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

    def get_modules(self, module: Optional[str] = None) -> List[Module]:
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
            fd.write(
                """name: %(name)s
license: ASL 2.0
version: 0.0.1dev0"""
                % {"name": name}
            )

        os.mkdir(os.path.join(mod_path, "model"))
        with open(os.path.join(mod_path, "model", "_init.cf"), "w+", encoding="utf-8") as fd:
            fd.write("\n")

        with open(os.path.join(mod_path, ".gitignore"), "w+", encoding="utf-8") as fd:
            fd.write(
                """*.swp
*.pyc
*~
.cache
            """
            )

        subprocess.check_output(["git", "init"], cwd=mod_path)
        subprocess.check_output(["git", "add", ".gitignore", "module.yml", "model/_init.cf"], cwd=mod_path)

        LOGGER.info("Module successfully created.")

    def do(self, command: str, module: str) -> None:
        for mod in self.get_modules(module):
            if not isinstance(mod, ModuleV1):
                LOGGER.warning("Skipping module %s: v2 modules do not support this operation.", mod.name)
                continue
            try:
                mod.execute_command(command)
            except Exception as e:
                print(e)

    def list(self) -> None:
        """
        List all modules in a table
        """

        def show_bool(b: bool) -> str:
            return "yes" if b else "no"

        table = []

        project = Project.get()
        project.get_complete_ast()

        names: Sequence[str] = sorted(project.modules.keys())
        specs: Dict[str, List[InmantaModuleRequirement]] = project.collect_imported_requirements()
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
                reqv = ",".join(req.version_spec_str() for req in specs[name] if req.specs) or "*"
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
        Install a module in the active Python environment. Only works for v2 modules: v1 modules can only be installed in the
        context of a project.
        """

        def install(install_path: str) -> None:
            try:
                env.process_env.install_from_source([env.LocalPackagePath(path=install_path, editable=editable)])
            except env.ConflictingRequirements as e:
                raise InvalidModuleException("Module installation failed due to conflicting dependencies") from e

        module_path: str = os.path.abspath(path) if path is not None else os.getcwd()
        module: Module = self.construct_module(None, module_path)
        if editable:
            if module.GENERATION == ModuleGeneration.V1:
                raise ModuleVersionException(
                    "Can not install v1 modules in editable mode. You can upgrade your module with `inmanta module v1tov2`."
                )
            install(module_path)
        else:
            with tempfile.TemporaryDirectory() as build_dir:
                build_artifact: str = self.build(module_path, build_dir)
                install(build_artifact)

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

    def commit(
        self,
        message: str,
        module: Optional[str] = None,
        version: Optional[str] = None,
        dev: bool = False,
        major: bool = False,
        minor: bool = False,
        patch: bool = False,
        commit_all: bool = False,
        tag: bool = False,
    ) -> None:
        """
        Commit all current changes.
        """
        inmanta.warnings.warn(
            CommandDeprecationWarning(
                "The `inmanta module commit` command has been deprecated in favor of `inmanta module release`."
            )
        )
        # find module
        module = self.get_module(module)
        if not isinstance(module, ModuleV1):
            raise CLIException(f"{module.name} is a v2 module and does not support this operation.", exitcode=1)
        # get version
        old_version = parse_version(str(module.version))

        outversion = self.determine_new_version(old_version, version, major, minor, patch, dev)

        if outversion is None:
            return

        module.rewrite_version(str(outversion))
        # commit
        gitprovider.commit(module._path, message, commit_all, [module.get_metadata_file_path()])
        # tag
        if not dev or tag:
            gitprovider.tag(module._path, str(outversion))

    def freeze(self, outfile: Optional[str], recursive: Optional[bool], operator: str, module: Optional[str] = None) -> None:
        """
        !!! Big Side-effect !!! sets yaml parser to be order preserving
        """

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

        with open(module_obj.get_metadata_file_path(), "r", encoding="utf-8") as fd:
            newconfig = yaml.safe_load(fd)

        requires = sorted([k + " " + v for k, v in freeze.items()])
        newconfig["requires"] = requires

        close = False
        out_fd = None
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
                f"Stable release {versions_between_current_and_new_version[0]} exists between "
                f"current version {current_version} and new version {new_version}"
            )

        return new_version

    def release(
        self,
        dev: bool,
        message: Optional[str] = None,
        patch: bool = False,
        minor: bool = False,
        major: bool = False,
        changelog_message: Optional[str] = None,
    ) -> None:
        """
        Execute the release command.
        """

        # Validate patch, minor, major
        nb_version_bump_arguments_set = sum([patch, minor, major])
        if nb_version_bump_arguments_set > 1:
            raise click.UsageError("Only one of --patch, --minor and --major can be set at the same time.")

        # Make module
        module_dir = os.path.abspath(os.getcwd())
        module: Module[ModuleMetadata] = self.construct_module(project=DummyProject(), path=module_dir)
        if not gitprovider.is_git_repository(repo=module_dir):
            raise click.ClickException(f"Directory {module_dir} is not a git repository.")

        # Validate current state of the module
        current_version: Version = module.version
        if current_version.epoch != 0:
            raise click.ClickException("Version with an epoch value larger than zero are not supported by this tool.")
        gitprovider.fetch(module_dir)

        # Get history
        stable_releases: list[Version] = gitprovider.get_version_tags(module_dir, only_return_stable_versions=True)

        path_changelog_file = os.path.join(module_dir, const.MODULE_CHANGELOG_FILE)
        changelog: Optional[ModuleChangelog] = (
            ModuleChangelog(path_changelog_file) if os.path.exists(path_changelog_file) else None
        )

        requested_version_bump: Optional[ChangeType] = ChangeType.parse_from_bools(patch, minor, major)
        if not requested_version_bump and dev:
            # Dev always bumps
            requested_version_bump = ChangeType.PATCH

        if requested_version_bump:
            new_version: Version = self._get_dev_version_with_minimal_distance_to_previous_stable_release(
                current_version, stable_releases, requested_version_bump
            )
        else:
            # Never happens for dev release
            new_version = current_version

        if not changelog and changelog_message:
            changelog = ModuleChangelog.create_changelog_file(path_changelog_file, new_version, changelog_message)
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
                commit_all=True,
                add=[module.get_metadata_file_path()] + [changelog.get_path()] if changelog else [],
                raise_exc_when_nothing_to_commit=False,
            )
        else:
            release_tag: Version = VersionOperation.set_version_tag(new_version, version_tag="")
            if release_tag in stable_releases:
                raise click.ClickException(f"A Git version tag already exists for version {release_tag}")
            module.rewrite_version(new_version=str(release_tag), version_tag="")
            if changelog:
                changelog.set_release_date_for_version(release_tag)
            gitprovider.commit(
                repo=module_dir,
                message=message if message else f"Release version {module.metadata.get_full_version()}",
                commit_all=True,
                add=[module.get_metadata_file_path()] + [changelog.get_path()] if changelog else [],
                raise_exc_when_nothing_to_commit=False,
            )
            gitprovider.tag(repo=module_dir, tag=str(release_tag))
            # bump to the next dev version
            self.release(dev=True, message="Bump version to next development version", patch=True)


class ModuleChangelog:
    """
    This class represent the changelog file in an Inmanta module.

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
    def create_changelog_file(cls, path: str, version: Version, changelog_message: str) -> "ModuleChangelog":
        """
        Create a new changelog file at the given path. Add a section for the given version and write the given
        changelog message to it.
        """
        if os.path.exists(path):
            raise Exception(f"File {path} already exists.")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(
                f"""
{cls._get_top_level_header()}

{cls._get_header_for_version(version)}

- {changelog_message}
            """.strip()
            )
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
        with open(self.path_changelog_file, "r", encoding="utf-8") as fh:
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


class ModuleBuildFailedError(Exception):
    def __init__(self, msg: str, *args: Any) -> None:
        self.msg = msg
        super(ModuleBuildFailedError, self).__init__(msg, *args)

    def __str__(self) -> str:
        return self.msg


BUILD_FILE_IGNORE_PATTERN: Pattern[str] = re.compile("|".join(("__pycache__", "__cfcache__", r".*\.pyc", rf"{CF_CACHE_DIR}")))


class IsolatedEnvBuilderCached(IsolatedEnvBuilder):
    """
    An IsolatedEnvBuilder that maintains its build environment across invocations of the context manager.
    This class is only used by the test suite. It decreases the runtime of the test suite because the build
    environment is reused across test cases.

    This class is a singleton. The get_instance() method should be used to obtain an instance of this class.
    """

    _instance: Optional["IsolatedEnvBuilderCached"] = None

    def __init__(self) -> None:
        super().__init__()
        self._isolated_env: Optional[build.env.IsolatedEnv] = None

    @classmethod
    def get_instance(cls) -> "IsolatedEnvBuilderCached":
        """
        This method should be used to obtain an instance of this class, because this class is a singleton.
        """
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __enter__(self) -> build.env.IsolatedEnv:
        if not self._isolated_env:
            self._isolated_env = super(IsolatedEnvBuilderCached, self).__enter__()
            self._install_build_requirements(self._isolated_env)
            # All build dependencies are installed, so we can disable the install() method on self._isolated_env.
            # This prevents unnecessary pip processes from being spawned.
            setattr(self._isolated_env, "install", lambda *args, **kwargs: None)
        return self._isolated_env

    def _install_build_requirements(self, isolated_env: build.env.IsolatedEnv) -> None:
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
                fh.write(
                    """
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
                """
                )
            builder = build.ProjectBuilder(
                srcdir=tmp_python_project_dir,
                python_executable=self._isolated_env.executable,
                scripts_dir=self._isolated_env.scripts_dir,
            )
            isolated_env.install(builder.build_system_requires)
            isolated_env.install(builder.get_requires_for_build(distribution="wheel"))

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        # Ignore implementation from the super class to keep the environment
        pass

    def destroy(self) -> None:
        """
        Cleanup the cached build environment. It should be called at the end of the test suite.
        """
        if self._isolated_env:
            super(IsolatedEnvBuilderCached, self).__exit__(None, None, None)
            self._isolated_env = None


class V2ModuleBuilder:

    DISABLE_ISOLATED_ENV_BUILDER_CACHE: bool = False

    def __init__(self, module_path: str) -> None:
        """
        :raises InvalidModuleException: The given module_path doesn't reference a valid module.
        :raises ModuleBuildFailedError: Module build was unsuccessful.
        """
        self._module = ModuleV2(project=None, path=os.path.abspath(module_path))

    def build(self, output_directory: str, dev_build: bool = False, byte_code: bool = False) -> str:
        """
        Build the module and return the path to the build artifact.

        :param byte_code: When set to true, only bytecode will be included. This also results in a binary wheel
        """
        if os.path.exists(output_directory):
            if not os.path.isdir(output_directory):
                raise ModuleBuildFailedError(msg=f"Given output directory is not a directory: {output_directory}")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy module to temporary directory to perform the build
            build_path = os.path.join(tmpdir, "module")
            shutil.copytree(self._module.path, build_path)
            if dev_build:
                self._add_dev_build_tag_to_setup_cfg(build_path)
            self._ensure_plugins(build_path)
            self._move_data_files_into_namespace_package_dir(build_path)
            if byte_code:
                self._byte_compile_code(build_path)

            path_to_wheel = self._build_v2_module(build_path, output_directory)
            self._verify_wheel(build_path, path_to_wheel)
            return path_to_wheel

    def _add_dev_build_tag_to_setup_cfg(self, build_path: str) -> None:
        """
        Add a build_tag of the format `.dev<timestamp>` to the setup.cfg file. The timestamp has the form %Y%m%d%H%M%S.
        """
        path_setup_cfg = os.path.join(build_path, "setup.cfg")
        # Read setup.cfg file
        config_in = ConfigParser()
        config_in.read(path_setup_cfg)
        # Set build_tag
        if not config_in.has_section("egg_info"):
            config_in.add_section("egg_info")
        timestamp_uct = datetime.datetime.now(datetime.timezone.utc)
        timestamp_uct_str = timestamp_uct.strftime("%Y%m%d%H%M%S")
        config_in.set("egg_info", "tag_build", f".dev{timestamp_uct_str}")
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
            fd.write(
                f"""
from distutils.core import setup
from Cython.Build import cythonize
setup(name="{ModuleV2Source.get_package_name_for(self._module.name)}",
    version="{self._module.version}",
    ext_modules=cythonize("inmanta_plugins/{self._module.name}/_cdummy.c"),
)
            """
            )

        # make sure cython is in the pyproject.toml
        pyproject = ModuleConverter.get_pyproject(build_path, build_requires=["wheel", "setuptools", "cython"])
        with open(os.path.join(build_path, "pyproject.toml"), "w") as fh:
            fh.write(pyproject)

    def _verify_wheel(self, build_path: str, path_to_wheel: str) -> None:
        """
        Verify whether there were files in the python package on disk that were not packaged
        in the given wheel and log a warning if such a file exists.
        """
        rel_path_namespace_package = os.path.join("inmanta_plugins", self._module.name)
        abs_path_namespace_package = os.path.join(build_path, rel_path_namespace_package)
        files_in_python_package_dir = self._get_files_in_directory(abs_path_namespace_package, ignore=BUILD_FILE_IGNORE_PATTERN)
        with zipfile.ZipFile(path_to_wheel) as z:
            dir_prefix = f"{rel_path_namespace_package}/"
            files_in_wheel = set(
                info.filename[len(dir_prefix) :]
                for info in z.infolist()
                if not info.is_dir() and info.filename.startswith(dir_prefix)
            )
        unpackaged_files = files_in_python_package_dir - files_in_wheel
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

    def _get_files_in_directory(self, directory: str, ignore: Optional[Pattern[str]] = None) -> Set[str]:
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
        result: Set[str] = set()
        for (dirpath, dirnames, filenames) in os.walk(directory):
            if should_ignore(os.path.basename(dirpath)):
                # ignore whole subdirectory
                continue
            relative_paths_to_filenames = set(
                os.path.relpath(os.path.join(dirpath, f), directory) for f in filenames if not should_ignore(f)
            )
            result = result | relative_paths_to_filenames
        return result

    def _move_data_files_into_namespace_package_dir(self, build_path: str) -> None:
        """
        Copy all files that have to be packaged into the Python package of the module
        """
        python_pkg_dir = os.path.join(build_path, "inmanta_plugins", self._module.name)
        for dir_name in ["model", "files", "templates"]:
            fq_dir_name = os.path.join(build_path, dir_name)
            if os.path.exists(fq_dir_name):
                shutil.move(fq_dir_name, python_pkg_dir)
        metadata_file = os.path.join(build_path, "setup.cfg")
        shutil.copy(metadata_file, python_pkg_dir)

    def _get_isolated_env_builder(self) -> IsolatedEnvBuilder:
        """
        Returns the IsolatedEnvBuilder instance that should be used to build V2 modules. To speed to up the test
        suite, the build environment is cached when the tests are ran. This is possible because all modules, built
        by the test suite, have the same build requirements. For tests that need to test the code path used in
        production, the V2ModuleBuilder.DISABLE_ISOLATED_ENV_BUILDER_CACHE flag can be set to True.
        """
        if inmanta.RUNNING_TESTS and not V2ModuleBuilder.DISABLE_ISOLATED_ENV_BUILDER_CACHE:
            return IsolatedEnvBuilderCached.get_instance()
        else:
            return IsolatedEnvBuilder()

    def _build_v2_module(self, build_path: str, output_directory: str) -> str:
        """
        Build v2 module using PEP517 package builder.
        """
        try:
            with self._get_isolated_env_builder() as env:
                distribution = "wheel"
                builder = build.ProjectBuilder(srcdir=build_path, python_executable=env.executable, scripts_dir=env.scripts_dir)
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
            fh.write(
                f"""
include inmanta_plugins/{self._module.name}/setup.cfg
include inmanta_plugins/{self._module.name}/py.typed
recursive-include inmanta_plugins/{self._module.name}/model *.cf
graft inmanta_plugins/{self._module.name}/files
graft inmanta_plugins/{self._module.name}/templates
                """.strip()
                + "\n"
            )

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
            with open(os.path.join(in_folder, "pyproject.toml"), "r") as fh:
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
        module_requirements: List[InmantaModuleRequirement] = [
            req for req in self._module.get_all_requires() if req.project_name != self._module.name
        ]
        python_requirements: List[str] = self._module.get_strict_python_requirements_as_list()
        if module_requirements or python_requirements:
            requires: List[str] = sorted([str(r.get_python_package_requirement()) for r in module_requirements])
            requires += python_requirements
            config.set("options", "install_requires", "\n".join(requires))

        # Make setuptools work
        config["options"]["zip_safe"] = "False"
        config["options"]["include_package_data"] = "True"
        config["options"]["packages"] = "find_namespace:"
        config["options.packages.find"]["include"] = "inmanta_plugins*"

        return config
