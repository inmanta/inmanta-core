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
import inspect
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from argparse import ArgumentParser
from collections import OrderedDict
from typing import TYPE_CHECKING, Iterable, List, Mapping, Optional, Set

import texttable
import yaml
from cookiecutter.main import cookiecutter
from pkg_resources import parse_version

import build
import build.env
from inmanta.ast import CompilerException
from inmanta.command import CLIException, ShowUsageException
from inmanta.const import MAX_UPDATE_ATTEMPT
from inmanta.module import (
    FreezeOperator,
    InstallMode,
    Module,
    ModuleMetadataFileNotFound,
    ModuleV1,
    ModuleV2,
    Project,
    gitprovider,
)

if TYPE_CHECKING:
    from pkg_resources import Requirement  # noqa: F401

LOGGER = logging.getLogger(__name__)


def set_yaml_order_preserving():
    """
    Set yaml modules to be order preserving.

    !!! Big Side-effect !!!

    Library is not OO, unavoidable

    Will no longer be needed in python3.7
    """
    _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

    def dict_representer(dumper, data):
        return dumper.represent_dict(data.items())

    def dict_constructor(loader, node):
        return OrderedDict(loader.construct_pairs(node))

    yaml.add_representer(OrderedDict, dict_representer)
    yaml.add_constructor(_mapping_tag, dict_constructor)


class ModuleLikeTool(object):
    """Shared code for modules and projects """

    def execute(self, cmd, args):
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

    def get_project(self, load=False) -> Project:
        project = Project.get()
        if load:
            project.load()
        return project

    def determine_new_version(self, old_version, version, major, minor, patch, dev):
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
                parts = old_version.base_version.split(".")
                while len(parts) < 3:
                    parts.append("0")
                parts = [int(x) for x in parts]
                if patch:
                    parts[2] += 1
                if minor:
                    parts[1] += 1
                    parts[2] = 0
                if major:
                    parts[0] += 1
                    parts[1] = 0
                    parts[2] = 0
                outversion = ".".join([str(x) for x in parts])

            if dev:
                outversion = "%s.dev%d" % (outversion, time.time())

        outversion = parse_version(outversion)
        if outversion <= old_version:
            LOGGER.error("new versions (%s) is not larger then old version (%s), aborting" % (outversion, old_version))
            return None

        return outversion


class ProjectTool(ModuleLikeTool):
    @classmethod
    def parser_config(cls, parser: ArgumentParser):
        subparser = parser.add_subparsers(title="subcommand", dest="cmd")
        freeze = subparser.add_parser("freeze", help="Set all version numbers in project.yml")
        freeze.add_argument(
            "-o",
            "--outfile",
            help="File in which to put the new project.yml, default is the existing project.yml",
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

    def freeze(self, outfile, recursive, operator):
        """
        !!! Big Side-effect !!! sets yaml parser to be order preserving
        """
        try:
            project = self.get_project(load=True)
        except Exception:
            raise CLIException(1, "Could not load project")

        if recursive is None:
            recursive = project.freeze_recursive

        if operator is None:
            operator = project.freeze_operator

        freeze = project.get_freeze(mode=operator, recursive=recursive)

        set_yaml_order_preserving()

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

    def init(self, output_dir, name, default):
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


class ModuleTool(ModuleLikeTool):
    """
    A tool to manage configuration modules
    """

    def __init__(self):
        self._mod_handled_list = set()

    @classmethod
    def modules_parser_config(cls, parser: ArgumentParser):
        parser.add_argument("-m", "--module", help="Module to apply this command to", nargs="?", default=None)

        subparser = parser.add_subparsers(title="subcommand", dest="cmd")

        lst = subparser.add_parser("list", help="List all modules used in this project in a table")
        lst.add_argument(
            "-r", help="Output a list of requires that can be included in project.yml", dest="requires", action="store_true"
        )

        do = subparser.add_parser("do", help="Execute a command on all loaded modules")
        do.add_argument("command", metavar="command", help="the command to  execute")

        subparser.add_parser("update", help="Update all modules used in this project")

        subparser.add_parser("install", help="Install all modules required for this this project")

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

        freeze = subparser.add_parser("freeze", help="Set all version numbers in project.yml")
        freeze.add_argument(
            "-o",
            "--outfile",
            help="File in which to put the new project.yml, default is the existing project.yml",
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

        build = subparser.add_parser("build", help="Build an Python package from an V2 module.")
        build.add_argument(
            "path",
            help="The path to the module that should be updated",
            nargs="?",
        )

    def build(self, path: Optional[str] = None) -> None:
        if path is not None:
            path = os.path.abspath(path)
        else:
            path = os.getcwd()
        module_path_root = ModuleV2.get_module_dir(path)
        V2ModuleBuilder(module_path_root).build()

    def get_project_for_module(self, module):
        try:
            return self.get_project()
        except Exception:
            # see #721
            return None

    def get_module(self, module: str = None, project=None) -> Module:
        """Finds and loads a module, either based on the CWD or based on the name passed in as an argument and the project"""
        if module is None:
            project = self.get_project_for_module(module)
            path: str = os.path.realpath(os.curdir)
            try:
                return ModuleV2(project, path)
            except ModuleMetadataFileNotFound as e:
                try:
                    return ModuleV1(project, path)
                except ModuleMetadataFileNotFound:
                    # ignore this exception in favor of the v2 one
                    pass
                raise e
        else:
            project = self.get_project(load=True)
            return project.get_module(module)

    def get_modules(self, module: str = None):
        if module is not None:
            return [self.get_module(module)]
        else:
            return self.get_project(load=True).sorted_modules()

    def create(self, name):
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

    def do(self, command, module):
        for mod in self.get_modules(module):
            try:
                mod.execute_command(command)
            except Exception as e:
                print(e)

    def list(self, requires=False):
        """
        List all modules in a table
        """
        table = []
        name_length = 10
        version_length = 10

        project = Project.get()
        project.get_complete_ast()

        names = sorted(project.modules.keys())
        specs = project.collect_imported_requirements()
        for name in names:

            name_length = max(len(name), name_length)
            mod = Project.get().modules[name]
            version = str(mod.version)
            if name not in specs:
                specs[name] = []

            try:
                if project._install_mode == InstallMode.master:
                    reqv = "master"
                else:
                    release_only = project._install_mode == InstallMode.release
                    versions = ModuleV1.get_suitable_version_for(name, specs[name], mod._path, release_only=release_only)
                    if versions is None:
                        reqv = "None"
                    else:
                        reqv = str(versions)
            except Exception:
                LOGGER.exception("Problem getting version for module %s" % name)
                reqv = "ERROR"

            version_length = max(len(version), len(reqv), version_length)

            table.append((name, version, reqv, version == reqv))

        if requires:
            print("requires:")
            for name, version, reqv, _ in table:
                print("    - %s==%s" % (name, version))
        else:
            t = texttable.Texttable()
            t.set_deco(texttable.Texttable.HEADER | texttable.Texttable.BORDER | texttable.Texttable.VLINES)
            t.header(("Name", "Installed version", "Expected in project", "Matches"))
            for row in table:
                t.add_row(row)
            print(t.draw())

    def update(self, module: str = None, project: Project = None):
        """
        Update all modules from their source
        """

        if project is None:
            # rename var to make mypy happy
            my_project = self.get_project(False)
        else:
            my_project = project

        def do_update(specs: "Mapping[str, Iterable[Requirement]]", modules: List[str]) -> None:
            for module in modules:
                spec = specs.get(module, [])
                try:
                    ModuleV1.update(my_project, module, spec, install_mode=my_project._install_mode)
                except Exception:
                    LOGGER.exception("Failed to update module %s", module)

        attempt = 0
        done = False
        last_failure = None

        while not done and attempt < MAX_UPDATE_ATTEMPT:
            LOGGER.info("Performing update attempt %d of %d", attempt + 1, MAX_UPDATE_ATTEMPT)
            try:
                # get AST
                my_project.get_complete_ast()
                # get current full set of requirements
                specs = my_project.collect_imported_requirements()
                if module is None:
                    modules = list(specs.keys())
                else:
                    modules = [module]
                do_update(specs, modules)
                done = True
            except CompilerException as e:
                last_failure = e
                # model is corrupt
                LOGGER.info(
                    "The model is not currently in an executable state, performing intermediate updates", stack_info=True
                )
                # get all specs from all already loaded modules
                specs = my_project.collect_requirements()

                if module is None:
                    # get all loaded/partly loaded modules
                    modules = list(my_project.modules.keys())
                else:
                    modules = [module]
                do_update(specs, modules)
                # this should resolve the exception, get_complete_ast should find additional modules/constraints
                attempt += 1

        if last_failure is not None and not done:
            raise last_failure

    def install(self, module=None, project=None):
        """
        Install all modules the project requires or a single module without its dependencies
        """
        if project is None:
            project = self.get_project(False)

        if module is None:
            project.load()
        else:
            project.load_module(module)

    def status(self, module=None):
        """
        Run a git status on all modules and report
        """
        for mod in self.get_modules(module):
            mod.status()

    def push(self, module=None):
        """
        Push all modules
        """
        for mod in self.get_modules(module):
            mod.push()

    def verify(self):
        """
        Verify dependencies and frozen module versions
        """
        Project.get().verify()

    def commit(
        self,
        message,
        module=None,
        version=None,
        dev=False,
        major=False,
        minor=False,
        patch=False,
        commit_all=False,
        tag=False,
    ):
        """
        Commit all current changes.
        """
        # find module
        module = self.get_module(module)
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

    def freeze(self, outfile, recursive, operator, module=None):
        """
        !!! Big Side-effect !!! sets yaml parser to be order preserving
        """

        # find module
        module = self.get_module(module)

        if recursive is None:
            recursive = module.freeze_recursive

        if operator is None:
            operator = module.freeze_operator

        if operator not in ["==", "~=", ">="]:
            LOGGER.warning("Operator %s is unknown, expecting one of ['==', '~=', '>=']", operator)

        freeze = {}

        for submodule in module.get_all_submodules():
            freeze.update(module.get_freeze(submodule=submodule, mode=operator, recursive=recursive))

        set_yaml_order_preserving()

        with open(module.get_metadata_file_path(), "r", encoding="utf-8") as fd:
            newconfig = yaml.safe_load(fd)

        requires = sorted([k + " " + v for k, v in freeze.items()])
        newconfig["requires"] = requires

        close = False
        if outfile is None:
            outfile = open(module.get_metadata_file_path(), "w", encoding="UTF-8")
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


class ModuleBuildFailedError(Exception):
    def __init__(self, msg: str, *args, **kwargs) -> None:
        self.msg = msg
        super(ModuleBuildFailedError, self).__init__(*args, **kwargs)

    def __str__(self) -> str:
        return self.msg


class V2ModuleBuilder:
    def __init__(self, module_path: str) -> None:
        """
        :raises InvalidModuleException: The given module_path doesn't reference a valid module.
        :raises ModuleBuildFailedError: Module build was unsuccessful.
        """
        self._module = ModuleV2(project=None, path=os.path.abspath(module_path))

    def build(self) -> None:
        output_directory = os.path.join(self._module.path, "dist")
        if os.path.exists(output_directory):
            raise ModuleBuildFailedError(msg=f"Output directory {output_directory} already exists")
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy module to temporary directory to perform the build
            build_path = os.path.join(tmpdir, "module")
            shutil.copytree(self._module.path, build_path)
            self._move_data_files_into_namespace_package_dir(build_path)
            path_to_wheel = self._build_v2_module(build_path, output_directory)
            self._verify_wheel(build_path, path_to_wheel)

    def _verify_wheel(self, build_path: str, path_to_wheel: str) -> None:
        """
        Verify whether there were files in the python package on disk that were not packaged
        in the given wheel and log a warning if such a file exists.
        """
        rel_path_namespace_package = os.path.join("inmanta_plugins", self._module.get_name_namespace_package())
        abs_path_namespace_package = os.path.join(build_path, rel_path_namespace_package)
        files_in_python_package_dir = self._get_files_in_directory(abs_path_namespace_package)
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
                f"packaged: {list(unpackaged_files)}. Update you setup.cfg file if they need to be packaged."
            )

    def _get_files_in_directory(self, directory: str) -> Set[str]:
        """
        Return the relative paths to all the files in all subdirectories of the given directory.
        """
        if not os.path.isdir(directory):
            raise Exception(f"{directory} is not a directory")
        result = set()
        for (dirpath, dirnames, filenames) in os.walk(directory):
            relative_paths_to_filenames = set(os.path.relpath(os.path.join(dirpath, f), directory) for f in filenames)
            result = result | relative_paths_to_filenames
        return result

    def _move_data_files_into_namespace_package_dir(self, build_path: str) -> None:
        """
        Copy all files that have to be packaged into the Python package of the module
        """
        python_pkg_dir = os.path.join(build_path, "inmanta_plugins", self._module.get_name_namespace_package())
        for dir_name in ["model", "files", "templates"]:
            fq_dir_name = os.path.join(build_path, dir_name)
            if os.path.exists(fq_dir_name):
                shutil.move(fq_dir_name, python_pkg_dir)
        metadata_file = os.path.join(build_path, "setup.cfg")
        shutil.copy(metadata_file, python_pkg_dir)

    def _build_v2_module(self, build_path: str, output_directory: str) -> str:
        """
        Build v2 module using PEP517 package builder.
        """
        try:
            with build.env.IsolatedEnvBuilder() as env:
                distribution = "wheel"
                builder = build.ProjectBuilder(srcdir=build_path, python_executable=env.executable, scripts_dir=env.scripts_dir)
                env.install(builder.build_system_requires)
                env.install(builder.get_requires_for_build(distribution=distribution))
                return builder.build(distribution=distribution, output_directory=output_directory)
        except Exception:
            raise ModuleBuildFailedError(msg="Module build failed")
