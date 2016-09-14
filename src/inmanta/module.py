"""
    Copyright 2016 Inmanta

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

import glob
import imp
import logging
import os
from os.path import sys
import subprocess
import tempfile
import shutil
from argparse import ArgumentParser
import inspect
from pkg_resources import parse_version, parse_requirements
import time
from subprocess import CalledProcessError

import yaml
import inmanta
from inmanta import env
from inmanta.ast import Namespace, CompilerException, ModuleNotFoundException
from inmanta import plugins
from inmanta.parser.plyInmantaParser import parse
import ruamel.yaml
from inmanta.parser import plyInmantaParser
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.statements import DefinitionStatement
from inmanta.util import memoize
from inmanta.ast.statements.define import DefineImport


LOGGER = logging.getLogger(__name__)


class InvalidModuleException(Exception):
    """
        This exception is raised if a module is invalid
    """


class InvalidModuleFileException(Exception):
    """
        This exception is raised if a module file is invalid
    """


class ProjectNotFoundExcpetion(Exception):
    """
        This exception is raised when inmanta is unable to find a valid project
    """


class GitProvider:

    def clone(self, src, dest):
        pass

    def fetch(self, repo):
        pass

    def get_all_tags(self, repo):
        pass


class CLIGitProvider(GitProvider):

    def clone(self, src, dest):
        subprocess.check_call(["git", "clone", src, dest], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, env={"GIT_ASKPASS": "true"})

    def fetch(self, repo):
        subprocess.check_call(["git", "fetch", "--tags"], cwd=repo, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, env={"GIT_ASKPASS": "true"})

    def status(self, repo):
        return subprocess.check_output(["git", "status", "--porcelain"], cwd=repo).decode("utf-8")

    def get_all_tags(self, repo):
        return subprocess.check_output(["git", "tag"], cwd=repo).decode("utf-8").splitlines()

    def checkout_tag(self, repo, tag):
        subprocess.check_call(["git", "checkout", tag], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def commit(self, repo, message, commit_all, add=[]):
        for file in add:
            subprocess.check_call(["git", "add", file], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not commit_all:
            subprocess.check_call(["git", "commit", "-m", message], cwd=repo,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.check_call(["git", "commit", "-a", "-m", message], cwd=repo,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def tag(self, repo, tag):
        subprocess.check_call(["git", "tag", "-a", "-m", "auto tag by module tool", tag], cwd=repo,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def push(self, repo):
        return subprocess.check_output(["git", "push", "--follow-tags", "--porcelain"],
                                       cwd=repo, stderr=subprocess.DEVNULL).decode("utf-8")

# try:
#     import pygit2
#     import re
#
#     class LibGitProvider(GitProvider):
#
#         def clone(self, src, dest):
#             pygit2.clone_repository(src, dest)
#
#         def fetch(self, repo):
#             repoh = pygit2.Repository(repo)
#             repoh.remotes["origin"].fetch()
#
#         def status(self, repo):
#             # todo
#             return subprocess.check_output(["git", "status", "--porcelain"], cwd=repo).decode("utf-8")
#
#         def get_all_tags(self, repo):
#             repoh = pygit2.Repository(repo)
#             regex = re.compile('^refs/tags/(.*)')
#             return [m.group(1) for m in [regex.match(t) for t in repoh.listall_references()] if m]
#
#         def checkout_tag(self, repo, tag):
#             repoh = pygit2.Repository(repo)
#             repoh.checkout("refs/tags/" + tag)
#
#         def commit(self, repo, message, commit_all, add=[]):
#             repoh = pygit2.Repository(repo)
#             index = repoh.index
#             index.read()
#
#             for file in add:
#                 index.add(os.path.relpath(file, repo))
#
#             if commit_all:
#                 index.add_all()
#
#             index.write()
#             tree = index.write_tree()
#
#             config = pygit2.Config.get_global_config()
#             try:
#                 email = config["user.email"]
#             except KeyError:
#                 email = "inmanta@example.com"
#                 LOGGER.warn("user.email not set in git config")
#
#             try:
#                 username = config["user.name"]
#             except KeyError:
#                 username = "Inmanta Moduletool"
#                 LOGGER.warn("user.name not set in git config")
#
#             author = pygit2.Signature(username, email)
#
#             return repoh.create_commit("HEAD", author, author, message, tree, [repoh.head.get_object().hex])
#
#         def tag(self, repo, tag):
#             repoh = pygit2.Repository(repo)
#
#             config = pygit2.Config.get_global_config()
#             try:
#                 email = config["user.email"]
#             except KeyError:
#                 email = "inmanta@example.com"
#                 LOGGER.warn("user.email not set in git config")
#
#             try:
#                 username = config["user.name"]
#             except KeyError:
#                 username = "Inmanta Moduletool"
#                 LOGGER.warn("user.name not set in git config")
#
#             author = pygit2.Signature(username, email)
#
#             repoh.create_tag(tag, repoh.head.target, pygit2.GIT_OBJ_COMMIT, author, "auto tag by module tool")
#
#     gitprovider = LibGitProvider()
# except ImportError as e:
gitprovider = CLIGitProvider()


class ModuleRepo:

    def clone(self, name: str, dest: str) -> bool:
        raise NotImplementedError("Abstract method")

    def path_for(self, name: str):
        # same class is used for search parh and remote repos, perhaps not optimal
        raise NotImplementedError("Abstract method")


class CompositeModuleRepo(ModuleRepo):

    def __init__(self, children):
        self.children = children

    def clone(self, name: str, dest: str) -> bool:
        for child in self.children:
            if child.clone(name, dest):
                return True
        return False

    def path_for(self, name: str):
        for child in self.children:
            result = child.path_for(name)
            if result is not None:
                return result
        return None


class LocalFileRepo(ModuleRepo):

    def __init__(self, root, parent_root=None):
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

    def path_for(self, name: str):
        path = os.path.join(self.root, name)
        if os.path.exists(path):
            return path
        return None


class RemoteRepo(ModuleRepo):

    def __init__(self, baseurl):
        self.baseurl = baseurl

    def clone(self, name: str, dest: str) -> bool:
        try:
            gitprovider.clone(self.baseurl + name, os.path.join(dest, name))
            return True
        except Exception:
            LOGGER.debug("could not clone repo", exc_info=True)
            return False

    def path_for(self, name: str):
        raise NotImplementedError("Should only be called on local repos")


def makeRepo(path, root=None):
    if ":" in path:
        return RemoteRepo(path)
    else:
        return LocalFileRepo(path, parent_root=root)


def merge_specs(mainspec, new):
    """Merge two maps str->[T] by concatting their lists."""
    for req in new:
        key = req.project_name
        if key not in mainspec:
            mainspec[key] = [req]
        else:
            mainspec[key] = mainspec[key] + [req]


class ModuleLike:
    """
        Commons superclass for projects and modules, which are both versioned by git
    """

    def __init__(self, path):
        """
            @param path: root git directory
        """
        self._path = path

    def get_name(self):
        raise NotImplemented()

    name = property(get_name)

    def get_config_for_rewrite(self):
        with open(self.get_config_file_name(), "r") as fd:
            return ruamel.yaml.load(fd.read(), ruamel.yaml.RoundTripLoader)

    def rewrite_config(self, data):
        with open(self.get_config_file_name(), "w") as fd:
            fd.write(ruamel.yaml.dump(data, Dumper=ruamel.yaml.RoundTripDumper))

    def _load_file(self, ns, file):
        statements = []
        stmts = plyInmantaParser.parse(ns, file)
        block = BasicBlock(ns)
        for s in stmts:
            if isinstance(s, DefinitionStatement):
                statements.append(s)
            elif isinstance(s, str):
                pass
            else:
                block.add(s)
        return (statements, block)

    def requires(self) -> dict:
        """
            Get the requires for this module
        """
        # filter on import stmt

        if "requires" not in self._meta or self._meta["requires"] is None:
            return {}

        reqs = []
        for spec in self._meta["requires"]:
            req = [x for x in parse_requirements(spec)]
            if len(req) > 1:
                print("Module file for %s has bad line in requirements specification %s" % (self._path, spec))
            req = req[0]
            reqs.append(req)
        return reqs


class Project(ModuleLike):
    """
        An inmanta project
    """
    PROJECT_FILE = "project.yml"
    _project = None

    def __init__(self, path, autostd=True):
        """
            Initialize the project, this includes
             * Loading the project.yaml (into self._meta)
             * Setting paths from project.yaml
             * Loading all modules in the module path (into self.modules)
            It does not include
             * verify if project.yml corresponds to the modules in self.modules

            @param path: The directory where the project is located

        """
        super().__init__(path)
        self.project_path = path

        if not os.path.exists(path):
            raise Exception("Unable to find project directory %s" % path)

        project_file = os.path.join(path, Project.PROJECT_FILE)

        if not os.path.exists(project_file):
            raise Exception(
                "Project directory does not contain a project file")

        with open(project_file, "r") as fd:
            self._meta = yaml.load(fd)

        if "modulepath" not in self._meta:
            raise Exception("modulepath is required in the project(.yml) file")

        modulepath = self._meta["modulepath"]
        if not isinstance(modulepath, list):
            modulepath = [modulepath]
        self.modulepath = [os.path.abspath(os.path.join(path, x)) for x in modulepath]
        self.resolver = CompositeModuleRepo([makeRepo(x) for x in self.modulepath])

        if "repo" not in self._meta:
            raise Exception("repo is required in the project(.yml) file")

        repo = self._meta["repo"]
        if not isinstance(repo, list):
            repo = [repo]
        self.repolist = [x for x in repo]
        self.externalResolver = CompositeModuleRepo([makeRepo(x, root=path) for x in self.repolist])

        self.downloadpath = None
        if "downloadpath" in self._meta:
            self.downloadpath = os.path.abspath(os.path.join(
                path, self._meta["downloadpath"]))
            if self.downloadpath not in self.modulepath:
                LOGGER.warning("Downloadpath is not in module path! Module install will not work as expected")

            if not os.path.exists(self.downloadpath):
                os.mkdir(self.downloadpath)

        self.freeze_file = os.path.join(path, "module.version")
        self._freeze_versions = self._load_freeze(self.freeze_file)

        self.virtualenv = env.VirtualEnv(os.path.join(path, ".env"))

        self.loaded = False
        self.modules = {}

        self.root_ns = Namespace("__root__")

        self.autostd = autostd
        self._release_only = True
        if "use_prerelease" in self._meta:
            if self._meta["use_prerelease"]:
                self._release_only = False

    @classmethod
    def get_project_dir(cls, cur_dir):
        """
            Find the project directory where we are working in. Traverse up until we find Project.PROJECT_FILE or reach /
        """
        project_file = os.path.join(cur_dir, Project.PROJECT_FILE)

        if os.path.exists(project_file):
            return cur_dir

        parent_dir = os.path.abspath(os.path.join(cur_dir, os.pardir))
        if parent_dir == cur_dir:
            raise ProjectNotFoundExcpetion("Unable to find an inmanta project")

        return cls.get_project_dir(parent_dir)

    @classmethod
    def get(cls):
        """
            Get the instance of the project
        """
        if cls._project is None:
            cls._project = Project(cls.get_project_dir(os.curdir))

        return cls._project

    @classmethod
    def set(cls, project):
        """
            Get the instance of the project
        """
        cls._project = project
        os.chdir(project._path)
        plugins.PluginMeta.clear()

    def _load_freeze(self, freeze_file: str) -> {}:
        """
            Load the versions defined in the freeze file
        """
        if not os.path.exists(freeze_file):
            return {}

        with open(freeze_file, "r") as fd:
            return yaml.load(fd)

    def load(self):
        if not self.loaded:
            self.get_complete_ast()
            self.use_virtual_env()
            self.loaded = True
            self.verify()
            try:
                self.load_plugins()
            except CompilerException:
                # do python install
                pyreq = self.collect_python_requirements()
                if len(pyreq) > 0:
                    try:
                        # install reqs, with cache
                        self.virtualenv.install_from_list(pyreq)
                        self.load_plugins()
                    except CompilerException:
                        # cache could be damaged, ignore it
                        self.virtualenv.install_from_list(pyreq, cache=False)
                        self.load_plugins()
                else:
                    self.load_plugins()

    @memoize
    def get_complete_ast(self):
        # load ast
        (statements, block) = self.__load_ast()
        blocks = [block]
        statements = [x for x in statements]
        # get imports
        imports = [x for x in statements if isinstance(x, DefineImport)]
        if self.autostd:
            imports.insert(0, DefineImport("std", "std"))
        done = set()
        while len(imports) > 0:
            imp = imports.pop()
            ns = imp.name
            if ns in done:
                continue

            parts = ns.split("::")
            module_name = parts[0]

            try:
                # get module
                if module_name in self.modules:
                    module = self.modules[module_name]
                else:
                    module = self.load_module(module_name)
                # get NS
                for i in range(1, len(parts) + 1):
                    subs = '::'.join(parts[0:i])
                    if subs in done:
                        continue
                    (nstmt, nb) = module.get_ast(subs)
                    done.add(subs)
                    statements.extend(nstmt)
                    blocks.append(nb)

                # get imports and add to list
                    nimp = [x for x in nstmt if isinstance(x, DefineImport)]
                    imports.extend(nimp)
            except InvalidModuleException:
                raise ModuleNotFoundException(ns, imp)

        return (statements, blocks)

    def __load_ast(self):
        main_ns = Namespace("__config__", self.root_ns)
        return self._load_file(main_ns, os.path.join(self.project_path, "main.cf"))

    def load_module(self, module_name):
        path = self.resolver.path_for(module_name)
        if path is not None:
            module = Module(self, path)
        else:
            reqs = self.collect_requirements()
            if module_name in reqs:
                module = Module.install(self, module_name, reqs[module_name], self._release_only)
            else:
                module = Module.install(self, module_name, parse_requirements(module_name), self._release_only)
        self.modules[module_name] = module
        return module

    def load_plugins(self) -> None:
        """
            Load all plug-ins
        """
        if not self.loaded:
            LOGGER.warn("loading plugins on project that has not been loaded completely")
        for module in self.modules.values():
            module.load_plugins()

    def verify(self) -> None:
        # verify module dependencies
        result = True
        result &= self.verify_requires()
        if not result:
            raise CompilerException("Not all module dependencies have been met.")

    def use_virtual_env(self) -> None:
        """
            Use the virtual environment
        """
        self.virtualenv.use_virtual_env()

    def sorted_modules(self) -> list:
        """
            Return a list of all modules, sorted on their name
        """
        names = self.modules.keys()
        names = sorted(names)

        mod_list = []
        for name in names:
            mod_list.append(self.modules[name])

        return mod_list

    def collect_requirements(self):
        """
            Collect the list of all requirements of all modules in the project.
        """
        if not self.loaded:
            LOGGER.warn("collecting reqs on project that has not been loaded completely")

        specs = {}
        merge_specs(specs, self.requires())
        for module in self.modules.values():
            reqs = module.requires()
            merge_specs(specs, reqs)
        return specs

    def collect_imported_requirements(self):
        imports = set([x.name.split("::")[0] for x in self.get_complete_ast()[0] if isinstance(x, DefineImport)])
        imports.add("std")
        specs = self.collect_requirements()

        def get_spec(name):
            if name in specs:
                return specs[name]
            return parse_requirements(name)

        return {name: get_spec(name) for name in imports}

    def verify_requires(self) -> bool:
        """
            Check if all the required modules for this module have been loaded
        """
        LOGGER.info("verifying project")
        imports = set([x.name for x in self.get_complete_ast()[0] if isinstance(x, DefineImport)])
        modules = self.modules

        good = True

        for name, spec in self.collect_requirements().items():
            if name not in imports:
                continue
            module = modules[name]
            version = parse_version(str(module.version))
            for r in spec:
                if version not in r:
                    LOGGER.warning("requirement %s on module %s not fullfilled, not at version %s" % (r, name, version))
                    good = False

        return good

    def collect_python_requirements(self):
        """
            Collect the list of all python requirements off all modules in this project
        """
        pyreq = [x.strip() for x in [mod.get_python_requirements() for mod in self.modules.values()] if x is not None]
        pyreq = '\n'.join(pyreq).split("\n")
        pyreq = [x for x in pyreq if len(x.strip()) > 0]
        return list(set(pyreq))

    def get_name(self):
        return "project.yml"

    name = property(get_name)

    def get_config_file_name(self):
        return os.path.join(self._path, "project.yml")

    def get_root_namespace(self):
        return self.root_ns


class Module(ModuleLike):
    """
        This class models an inmanta configuration module
    """
    requires_fields = ["name", "license", "version"]

    def __init__(self, project: Project, path: str, **kwmeta: dict):
        """
            Create a new configuration module

            :param project: A reference to the project this module belongs to.
            :param path: Where is the module stored
            :param kwmeta: Meta-data
        """
        super().__init__(path)
        self._project = project
        self._meta = kwmeta
        self._plugin_namespaces = []

        if not Module.is_valid_module(self._path):
            raise InvalidModuleException(("Module %s is not a valid inmanta configuration module. Make sure that a " +
                                          "model/_init.cf file exists and a module.yml definition file.") % self._path)

        self.load_module_file()
        self.is_versioned()

    def get_name(self):
        """
            Returns the name of the module (if the meta data is set)
        """
        if "name" in self._meta:
            return self._meta["name"]

        return None

    name = property(get_name)

    def get_version(self):
        """
            Return the version of this module
        """
        if "version" in self._meta:
            return self._meta["version"]

        return None

    version = property(get_version)

    @classmethod
    def install(cls, project, modulename, requirements, install=True, release_only=True):
        """
           Install a module, return module object
        """
        # verify pressence in module path
        path = project.resolver.path_for(modulename)
        if path is not None:
            # if exists, report
            LOGGER.info("module %s already found at %s", modulename, path)
            gitprovider.fetch(path)
        else:
            # otherwise install
            path = os.path.join(project.downloadpath, modulename)
            result = project.externalResolver.clone(modulename, project.downloadpath)
            if not result:
                raise InvalidModuleException("could not locate module with name: %s", modulename)

        return cls.update(project, modulename, requirements, path, False, release_only=release_only)

    @classmethod
    def update(cls, project, modulename, requirements, path=None, fetch=True, release_only=True):
        """
           Update a module, return module object
        """

        if path is None:
            path = project.resolver.path_for(modulename)

        if fetch:
            gitprovider.fetch(path)

        versions = cls.get_suitable_versions_for(modulename, requirements, path, release_only=release_only)

        if len(versions) == 0:
            print("no suitable version found for module %s" % modulename)
        else:
            gitprovider.checkout_tag(path, str(versions[0]))

        return Module(project, path)

    @classmethod
    def get_suitable_versions_for(cls, modulename, requirements, path, release_only=True):
        versions = gitprovider.get_all_tags(path)

        def try_parse(x):
            try:
                return parse_version(x)
            except Exception:
                return None

        versions = [x for x in [try_parse(v) for v in versions] if x is not None]
        versions = sorted(versions, reverse=True)

        for r in requirements:
            versions = [x for x in r.specifier.filter(versions, not release_only)]

        return versions

    def is_versioned(self):
        """
            Check if this module is versioned, and if so the version number in the module file should
            have a tag. If the version has + the current revision can be a child otherwise the current
            version should match the tag
        """
        if not os.path.exists(os.path.join(self._path, ".git")):
            LOGGER.warning("Module %s is not version controlled, we recommend you do this as soon as possible."
                           % self._meta["name"])
            return False
        return True

    @classmethod
    def is_valid_module(cls, module_path):
        """
            Checks if this module is a valid configuration module. A module should contain a
            module.yml file.
        """
        if not os.path.isfile(os.path.join(module_path, "module.yml")):
            return False

        return True

    def load_module_file(self):
        """
            Load the module definition file
        """
        with open(self.get_config_file_name(), "r") as fd:
            mod_def = yaml.load(fd)

            if mod_def is None or len(mod_def) < len(Module.requires_fields):
                raise InvalidModuleFileException("The module file of %s does not have the required fields: %s" %
                                                 (self._path, ", ".join(Module.requires_fields)))

            for name, value in mod_def.items():
                self._meta[name] = value

        for req_field in Module.requires_fields:
            if req_field not in self._meta:
                raise InvalidModuleFileException(
                    "%s is required in module file of module %s" % (req_field, self._path))

        if self._meta["name"] != os.path.basename(self._path):
            LOGGER.warning("The name in the module file (%s) does not match the directory name (%s)"
                           % (self._meta["name"], os.path.basename(self._path)))

    def get_config_file_name(self):
        return os.path.join(self._path, "module.yml")

    def get_module_files(self):
        """
            Returns the path of all model files in this module, relative to the module root
        """
        files = []
        for model_file in glob.glob(os.path.join(self._path, "model", "*.cf")):
            files.append(model_file)

        return files

    def get_ast(self, name):
        if name == self.name:
            file = os.path.join(self._path, "model/_init.cf")
        else:
            parts = name.split("::")
            parts = parts[1:]
            if os.path.isdir(os.path.join(self._path, "model/" + "/".join(parts))):
                file = os.path.join(self._path, "model/" + "/".join(parts) + "/_init.cf")
            else:
                file = os.path.join(self._path, "model/" + "/".join(parts) + ".cf")

        ns = self._project.get_root_namespace().get_ns_or_create(name)

        try:
            return self._load_file(ns, file)
        except FileNotFoundError:
            raise InvalidModuleException("could not locate module with name: %s", name)

    def load_plugins(self):
        """
            Load all plug-ins from a configuration module
        """
        plugin_dir = os.path.join(self._path, "plugins")

        if not os.path.exists(plugin_dir):
            return

        if not os.path.exists(os.path.join(plugin_dir, "__init__.py")):
            raise CompilerException(
                "The plugin directory %s should be a valid python package with a __init__.py file" % plugin_dir)

        try:
            mod_name = self._meta["name"]
            imp.load_package("inmanta_plugins." + mod_name, plugin_dir)

            self._plugin_namespaces.append(mod_name)

            for py_file in glob.glob(os.path.join(plugin_dir, "*.py")):
                if not py_file.endswith("__init__.py"):
                    # name of the python module
                    sub_mod = "inmanta_plugins." + mod_name + "." + os.path.basename(py_file).split(".")[0]
                    self._plugin_namespaces.append(sub_mod)

                    # load the python file
                    imp.load_source(sub_mod, py_file)

        except ImportError as e:
            raise CompilerException(
                "Unable to load all plug-ins for module %s" % self._meta["name"]) from e

    def versions(self):
        """
            Provide a list of all versions available in the repository
        """
        versions = gitprovider.get_all_tags(self._path)

        def try_parse(x):
            try:
                return parse_version(x)
            except Exception:
                return None

        versions = [x for x in [try_parse(v) for v in versions] if x is not None]
        versions = sorted(versions, reverse=True)

        return versions

    def status(self):
        """
            Run a git status on this module
        """
        output = gitprovider.status(self._path)

        files = [x.strip() for x in output.split("\n") if x != ""]

        if len(files) > 0:
            print("Module %s (%s)" % (self._meta["name"], self._path))
            for f in files:
                print("\t%s" % f)

            print()
        else:
            print("Module %s (%s) has no changes" % (self._meta["name"], self._path))

    def push(self):
        """
            Run a git status on this module
        """
        sys.stdout.write("%s (%s) " % (self.get_name(), self._path))
        sys.stdout.flush()
        try:
            print(gitprovider.push(self._path))
        except CalledProcessError:
            print("Cloud not push module %s" % self.get_name())
        else:
            print("done")
        print()

    def get_python_requirements(self):
        """
            Install python requirements with pip in a virtual environment
        """
        file = os.path.join(self._path, "requirements.txt")
        if os.path.exists(file):
            with open(file, 'r') as fd:
                return fd.read()
        else:
            return None

    @memoize
    def get_python_requirements_as_list(self):
        raw = self.get_python_requirements()
        if raw is None:
            return []
        else:
            return [y for y in [x.strip() for x in raw.split("\n")] if len(y) != 0]

    def execute_command(self, cmd):
        print("executing %s on %s in %s" % (cmd, self.get_name(), self._path))
        print("=" * 10)
        subprocess.call(cmd, shell=True, cwd=self._path)
        print("=" * 10)


class ModuleTool(object):
    """
        A tool to manage configuration modules
    """

    def __init__(self):
        self._mod_handled_list = set()

    @classmethod
    def modules_parser_config(cls, parser: ArgumentParser):
        subparser = parser.add_subparsers(title="subcommand", dest="cmd")
        subparser.add_parser("list", help="List all modules used in this project in a table")
        do = subparser.add_parser("do", help="Execute a command on all loaded modules")
        do.add_argument("command", metavar='command', help='the command to  execute')
        subparser.add_parser("update", help="Update all modules used in this project")
        subparser.add_parser("install", help="Install all modules required for this this project")
        subparser.add_parser("status", help="Run a git status on all modules and report")
        subparser.add_parser("push", help="Run a git push on all modules and report")
        # not currently working
        # subparser.add_parser("freeze", help="Freeze the version of all modules")
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
        commit.add_argument("-v", "--version", help="Version to use on tag")
        commit.add_argument("-a", "--all", dest="commit_all", help="Use commit -a", action="store_true")

    def execute(self, cmd, args):
        """
            Execute the given command
        """
        if cmd is not None and cmd != '' and hasattr(self, cmd):
            method = getattr(self, cmd)
            margs = inspect.getfullargspec(method).args
            margs.remove("self")
            outargs = {k: getattr(args, k) for k in margs if hasattr(args, k)}
            method(**outargs)
        else:
            raise Exception("%s not implemented" % cmd)

    def help(self):
        """
            Show a list of commands
        """
        print("Available commands: list")

    def do(self, command):
        project = Project.get()

        project.load()
        for mod in Project.get().sorted_modules():
            try:
                mod.execute_command(command)
            except Exception as e:
                print(e)

    def list(self):
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
            versions = Module.get_suitable_versions_for(name, specs[name], mod._path, release_only=project._release_only)
            if len(versions) == 0:
                reqv = "None"
            else:
                reqv = str(versions[0])

            version_length = max(len(version), len(reqv), version_length)

            table.append((name, version, reqv))
        print("+" + "-" * (name_length + version_length * 2 + 8) + "+")
        print("| Name%s | Version%s | Expected%s |" % (
            " " * (name_length - len("Name")),
            " " * (version_length - len("Version")),
            " " * (version_length - len("Expected"))))
        print("+" + "-" * (name_length + version_length * 2 + 8) + "+")
        for name, version, reqv in table:
            print("| %s | %s | %s |" % (name + " " * (name_length - len(name)),
                                        version + " " * (version_length - len(version)),
                                        reqv + " " * (version_length - len(reqv))))

        print("+" + "-" * (name_length + version_length * 2 + 8) + "+")

    def update(self, project=None):
        """
            Update all modules from their source
        """

        if project is None:
            project = Project.get()

        project.get_complete_ast()
        specs = project.collect_imported_requirements()

        for name, spec in specs.items():
            print("updating module: %s" % name)
            Module.update(project, name, spec, release_only=project._release_only)

    def install(self, project=None):
        """
            Install all modules the project requires
        """
        if project is None:
            project = Project.get()

        project.load()

    def status(self):
        """
            Run a git status on all modules and report
        """
        project = Project.get()

        project.load()
        for mod in project.sorted_modules():
            mod.status()

    def push(self):
        """
            Push all modules
        """
        project = Project.get()

        project.load()
        for mod in Project.get().sorted_modules():
            mod.push()

    def freeze(self, create_file=True):
        """
            Freeze the version of all modules
        """
        project = Project.get()
        if os.path.exists(project.freeze_file) and create_file:
            print(
                "A module.version file already exists, overwrite this file? y/n")
            while True:
                value = sys.stdin.readline().strip()
                if value != "y" and value != "n":
                    print("Please answer with y or n")
                else:
                    if value == "n":
                        return

                    break

        file_content = {}

        for mod in Project.get().sorted_modules():
            version = str(mod.get_version())
            modc = {'version': version}

            repo = mod.get_scm_url()
            tag = mod.get_scm_version()

            if repo is not None:
                modc["repo"] = repo
                modc["hash"] = tag

            branch = mod.get_scm_branch()

            if branch is not None:
                modc["branch"] = branch

            file_content[mod._meta["name"]] = modc

        if create_file:
            with open(project.freeze_file, "w+") as fd:
                fd.write(yaml.dump(file_content))

        return file_content

    def verify(self):
        """
            Verify dependencies and frozen module versions
        """
        Project.get().verify()

    def _find_module(self):
        module = Module(None, os.path.realpath(os.curdir))
        LOGGER.info("Successfully loaded module %s with version %s" % (module.name, module.version))
        return module

    def commit(self, message, version=None, dev=True, commit_all=False):
        """
            Commit all current changes.
        """
        # find module
        module = self._find_module()
        # get version
        old_version = parse_version(str(module.version))
        # determine new version
        if version is not None:
            baseversion = version
        else:
            if old_version.is_prerelease:
                baseversion = old_version.base_version
            else:
                baseversion = old_version.base_version
                parts = baseversion.split('.')
                parts[-1] = str(int(parts[-1]) + 1)
                baseversion = '.'.join(parts)

        if dev:
            baseversion = "%s.dev%d" % (baseversion, time.time())

        baseversion = parse_version(baseversion)
        if baseversion <= old_version:
            print("new versions (%s) is not larger then old version (%s), aborting" % (baseversion, old_version))
            return

        cfg = module.get_config_for_rewrite()
        cfg["version"] = str(baseversion)
        module.rewrite_config(cfg)
        print("set version to: " + str(baseversion))
        # commit
        gitprovider.commit(module._path, message, commit_all, [module.get_config_file_name()])
        # tag
        gitprovider.tag(module._path, str(baseversion))

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

            LOGGER.info("Setting up project")
            with open(os.path.join(project_dir, "project.yml"), "w+") as fd:
                fd.write("""name: test
description: Project to validate module %(name)s
repo: [%(repo)s]
modulepath: libs
downloadpath: libs
requires:
    %(name)s: %(name)s == %(version)s
""" % {"name": module.name, "version": str(module.versions()[0]), "repo": allrepos})

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
