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
from inmanta.module import INSTALL_MASTER, Project, Module,\
    INSTALL_RELEASES, gitprovider
import inspect
import logging
import os
import sys
import shutil
import subprocess
import tempfile
import time

from argparse import ArgumentParser
from pkg_resources import parse_version
import texttable

import inmanta
from inmanta.ast import Namespace
from inmanta.parser.plyInmantaParser import parse
from inmanta.command import CLIException
import yaml
from collections import OrderedDict

LOGGER = logging.getLogger(__name__)


def set_yaml_order_perserving():
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
        if cmd is not None and cmd != '' and hasattr(self, cmd):
            method = getattr(self, cmd)
            margs = inspect.getfullargspec(method).args
            margs.remove("self")
            outargs = {k: getattr(args, k) for k in margs if hasattr(args, k)}
            method(**outargs)
        else:
            raise Exception("%s not implemented" % cmd)

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
                outversion = '.'.join([str(x) for x in parts])

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
        freeze.add_argument("-o", "--outfile",
                            help="File in which to put the new project.yml, default is the existing project.yml",
                            default=None)
        freeze.add_argument("-r", "--recursive",
                            help="Freeze dependencies recursively. If not set, freeze_recursive option in project.yml is used,"
                            "which defaults to False",
                            action="store_true",
                            default=None)
        freeze.add_argument("--operator",
                            help="Comparison operator used to freeze versions, If not set, the freeze_operator option in"
                            " project.yml is used which defaults to ~=",
                            default=None)

    def freeze(self, outfile, recursive, operator):
        """
        !!! Big Side-effect !!! sets yaml parser to be order preserving
         """
        try:
            project = self.get_project(load=True)
        except Exception:
            raise CLIException(1, "Could not load project")

        if recursive is None:
            recursive = bool(project.get_config("freeze_recursive", False))

        if operator is None:
            operator = project.get_config("freeze_operator", "~=")

        if operator not in ["==", "~=", ">="]:
            LOGGER.warning("Operator %s is unknown, expecting one of ['==', '~=', '>=']", operator)

        freeze = project.get_freeze(mode=operator, recursive=recursive)

        set_yaml_order_perserving()

        with open(project.get_config_file_name(), "r") as fd:
            newconfig = yaml.safe_load(fd)

        requires = sorted([k + " " + v for k, v in freeze.items()])
        newconfig["requires"] = requires

        if outfile is None:
            outfile = open(project.get_config_file_name(), "w", encoding='UTF-8')
        elif outfile == "-":
            outfile = sys.stdout
        else:
            outfile = open(outfile, "w", encoding='UTF-8')

        outfile.write(yaml.dump(newconfig, default_flow_style=False, sort_keys=False))


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
        lst.add_argument("-r", help="Output a list of requires that can be included in project.yml", dest="requires",
                         action="store_true")

        do = subparser.add_parser("do", help="Execute a command on all loaded modules")
        do.add_argument("command", metavar='command', help='the command to  execute')

        subparser.add_parser("update", help="Update all modules used in this project")

        subparser.add_parser("install", help="Install all modules required for this this project")

        subparser.add_parser("status", help="Run a git status on all modules and report")

        subparser.add_parser("push", help="Run a git push on all modules and report")

        # not currently working
        subparser.add_parser("verify", help="Verify dependencies and frozen module versions")

        validate = subparser.add_parser(
            "validate", help="Validate the module we are currently in. i.e. try to compile it against an empty main model")
        validate.add_argument("-r", "--repo", help="Additional repo to load modules from", action="append")
        validate.add_argument("-n", "--no-clean", help="Do not remove the validation project when finished",
                              action="store_true")
        validate.add_argument("-s", "--parse-only", help="Only parse the module", action="store_true")
        validate.add_argument("-i", "--isolate", help="Move the module to another directory before cloning."
                              " I.e. remove all other modules in the current directory from the search path",
                              action="store_true")
        validate.add_argument("-w", "--workingcopy", help="Use the actual state of the module instead of the latest tag",
                              action="store_true")

        commit = subparser.add_parser("commit", help="Commit all changes in the current module.")
        commit.add_argument("-m", "--message", help="Commit message", required=True)
        commit.add_argument("-r", "--release", dest="dev", help="make a release", action="store_false")
        commit.add_argument("--major", dest="major", help="make a major release", action="store_true")
        commit.add_argument("--minor", dest="minor", help="make a major release", action="store_true")
        commit.add_argument("--patch", dest="patch", help="make a major release", action="store_true")
        commit.add_argument("-v", "--version", help="Version to use on tag")
        commit.add_argument("-a", "--all", dest="commit_all", help="Use commit -a", action="store_true")

        create = subparser.add_parser("create", help="Create a new module")
        create.add_argument("name", help="The name of the module")

        freeze = subparser.add_parser("freeze", help="Set all version numbers in project.yml")
        freeze.add_argument("-o", "--outfile",
                            help="File in which to put the new project.yml, default is the existing project.yml",
                            default=None)
        freeze.add_argument("-r", "--recursive",
                            help="Freeze dependencies recursively. If not set, freeze_recursive option in project.yml is used,"
                            "which defaults to False",
                            action="store_true",
                            default=None)
        freeze.add_argument("--operator",
                            help="Comparison operator used to freeze versions, If not set, the freeze_operator option in"
                                 " project.yml is used which defaults to ~=",
                            default=None)

    def get_project_for_module(self, module):
        try:
            return self.get_project()
        except Exception:
            # see #721
            return None

    def get_module(self, module: str=None, project=None) -> Module:
        """Finds and loads a module, either based on the CWD or based on the name passed in as an argument and the project"""
        if module is None:
            module = Module(self.get_project_for_module(module), os.path.realpath(os.curdir))
            return module
        else:
            project = self.get_project(load=True)
            return project.get_module(module)

    def get_modules(self, module: str=None):
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
        with open(os.path.join(mod_path, "module.yml"), "w+") as fd:
            fd.write("""name: %(name)s
license: ASL 2.0
version: 0.0.1dev0""" % {"name": name})

        os.mkdir(os.path.join(mod_path, "model"))
        with open(os.path.join(mod_path, "model", "_init.cf"), "w+") as fd:
            fd.write("\n")

        with open(os.path.join(mod_path, ".gitignore"), "w+") as fd:
            fd.write("""*.swp
*.pyc
*~
.cache
            """)

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
                if project._install_mode == INSTALL_MASTER:
                    reqv = "master"
                else:
                    release_only = project._install_mode == INSTALL_RELEASES
                    versions = Module.get_suitable_version_for(
                        name, specs[name], mod._path, release_only=release_only)
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

    def update(self, module=None, project=None):
        """
            Update all modules from their source
        """

        if project is None:
            project = self.get_project(False)

        project.get_complete_ast()
        specs = project.collect_imported_requirements()

        if module is None:
            for name, spec in specs.items():
                print("updating module: %s" % name)
                try:
                    Module.update(project, name, spec, install_mode=project._install_mode)
                except Exception:
                    LOGGER.exception("Failed to update module")
        else:
            if module not in specs:
                print("Could not find module: %s" % module)
            else:
                spec = specs[module]
                try:
                    Module.update(project, module, spec, install_mode=project._install_mode)
                except Exception:
                    LOGGER.exception("Failed to update module")

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

    def _find_module(self):
        module = Module(None, os.path.realpath(os.curdir))
        LOGGER.info("Successfully loaded module %s with version %s" % (module.name, module.version))
        return module

    def commit(self, message, module=None, version=None, dev=False, major=False, minor=False, patch=False, commit_all=False):
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
        gitprovider.commit(module._path, message, commit_all, [module.get_config_file_name()])
        # tag
        gitprovider.tag(module._path, str(outversion))

    def validate(self, repo=[], no_clean=False, parse_only=False, isolate=False, workingcopy=False):
        """
            Validate the module we are currently in
        """
        if repo is None:
            repo = []
        valid = True
        module = self._find_module()
        if not module.is_versioned():
            LOGGER.error("Module is not versioned correctly, validation will fail")
            valid = False

        # compile the source files in the module
        ns_root = Namespace("__root__")
        ns_mod = Namespace(module.name, ns_root)
        for model_file in module.get_module_files():
            try:
                ns = ns_mod
                if not model_file.endswith("_init.cf"):
                    part_name = model_file.split("/")[-1][:-3]
                    ns = Namespace(part_name, ns_mod)

                parse(ns, model_file)
                LOGGER.info("Successfully parsed %s" % model_file)
            except Exception:
                valid = False
                LOGGER.exception("Unable to parse %s, validation will fail" % model_file)

        if parse_only:
            if not valid:
                sys.exit(1)
            sys.exit(0)
        # create a test project
        LOGGER.info("Creating a new project to test the module")
        project_dir = tempfile.mkdtemp()

        if isolate:
            search_root = tempfile.mkdtemp()
            os.symlink(module._path, os.path.join(search_root, module.name))
        else:
            search_root = os.path.split(module._path)[0]

        try:
            lib_dir = os.path.join(project_dir, "libs")
            os.mkdir(lib_dir)

            repo.insert(0, search_root)
            allrepos = ["'%s'" % x for x in repo]
            allrepos = ','.join(allrepos)

            if len(module.versions()) > 0:
                version_constraint = "%(name)s: %(name)s == %(version)s" % \
                                     {"name": module.name, "version": str(module.versions()[0])}
            else:
                version_constraint = module.name

            LOGGER.info("Setting up project")
            with open(os.path.join(project_dir, "project.yml"), "w+") as fd:
                fd.write("""name: test
description: Project to validate module %(name)s
repo: [%(repo)s]
modulepath: libs
downloadpath: libs
requires:
    %(version)s
""" % {"name": module.name, "version": version_constraint, "repo": allrepos})

            LOGGER.info("Installing dependencies")
            test_project = Project(project_dir)
            test_project.use_virtual_env()
            Project.set(test_project)

            LOGGER.info("Compiling empty initial model")
            main_cf = os.path.join(project_dir, "main.cf")
            with open(main_cf, "w+") as fd:
                fd.write("import %s" % (module.name))

            if workingcopy:
                # overwrite with actual
                modpath = os.path.join(project_dir, "libs", module.name)
                if os.path.exists(modpath):
                    shutil.rmtree(modpath)
                shutil.copytree(module._path, modpath)

            project = Project(project_dir)
            project.use_virtual_env()
            Project.set(project)
            LOGGER.info("Verifying modules")
            project.verify()
            LOGGER.info("Loading all plugins")
            project.load()

            values = inmanta.compiler.do_compile()

            if values is not None:
                LOGGER.info("Successfully compiled module and its dependencies.")
            else:
                LOGGER.error("Unable to compile module and its dependencies, validation will fail")
                valid = False

        except Exception:
            LOGGER.exception("An exception occurred during validation")
            valid = False

        finally:
            if no_clean:
                LOGGER.info("Project not cleaned, root at %s", project_dir)

            else:
                shutil.rmtree(project_dir)

        if not valid:
            sys.exit(1)

        sys.exit(0)

    def freeze(self, outfile, recursive, operator, module=None):
        """
        !!! Big Side-effect !!! sets yaml parser to be order preserving
         """

        # find module
        module = self.get_module(module)

        if recursive is None:
            recursive = bool(module.get_config("freeze_recursive", False))

        if operator is None:
            operator = module.get_config("freeze_operator", "~=")

        if operator not in ["==", "~=", ">="]:
            LOGGER.warning("Operator %s is unknown, expecting one of ['==', '~=', '>=']", operator)

        freeze = {}

        for submodule in module.get_all_submodules():
            freeze.update(module.get_freeze(submodule=submodule, mode=operator, recursive=recursive))

        set_yaml_order_perserving()

        with open(module.get_config_file_name(), "r") as fd:
            newconfig = yaml.safe_load(fd)

        requires = sorted([k + " " + v for k, v in freeze.items()])
        newconfig["requires"] = requires

        if outfile is None:
            outfile = open(module.get_config_file_name(), "w", encoding='UTF-8')
        elif outfile == "-":
            outfile = sys.stdout
        else:
            outfile = open(outfile, "w", encoding='UTF-8')

        outfile.write(yaml.dump(newconfig, default_flow_style=False, sort_keys=False))
