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

import glob
import imp
import inspect
from io import BytesIO
import logging
import os
from os.path import sys
import re
import shutil
from subprocess import CalledProcessError
import subprocess
from tarfile import TarFile
import tempfile
import time

from argparse import ArgumentParser
from pkg_resources import parse_version, parse_requirements
import texttable
import yaml

from inmanta import env
from inmanta import plugins
import inmanta
from inmanta.ast import Namespace, CompilerException, ModuleNotFoundException, Location, LocatableString
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.statements import DefinitionStatement, BiStatement
from inmanta.ast.statements.define import DefineImport
from inmanta.parser import plyInmantaParser
from inmanta.parser.plyInmantaParser import parse
from inmanta.util import memoize, get_compiler_version


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


class GitProvider(object):

    def clone(self, src, dest):
        pass

    def fetch(self, repo):
        pass

    def get_all_tags(self, repo):
        pass

    def get_file_for_version(self, repo, tag, file):
        pass

    def checkout_tag(self, repo, tag):
        pass

    def commit(self, repo, message, commit_all, add=[]):
        pass

    def tag(self, repo, tag):
        pass

    def push(self, repo):
        pass


class CLIGitProvider(GitProvider):

    def clone(self, src, dest):
        env = os.environ.copy()
        env["GIT_ASKPASS"] = "true"
        subprocess.check_call(["git", "clone", src, dest], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, env=env)

    def fetch(self, repo):
        env = os.environ.copy()
        env["GIT_ASKPASS"] = "true"
        subprocess.check_call(["git", "fetch", "--tags"], cwd=repo, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, env=env)

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

    def get_file_for_version(self, repo, tag, file):
        data = subprocess.check_output(["git", "archive", "--format=tar", tag, file],
                                       cwd=repo, stderr=subprocess.DEVNULL)
        tf = TarFile(fileobj=BytesIO(data))
        tfile = tf.next()
        b = tf.extractfile(tfile)
        return b.read().decode("utf-8")
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


class ModuleRepo(object):

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
            url = self.baseurl.format(name)
            if url == self.baseurl:
                url = self.baseurl + name

            gitprovider.clone(url, os.path.join(dest, name))
            return True
        except Exception:
            LOGGER.debug("could not clone repo", exc_info=True)
            return False

    def path_for(self, name: str):
        raise NotImplementedError("Should only be called on local repos")


def make_repo(path, root=None):
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


class ModuleLike(object):
    """
        Commons superclass for projects and modules, which are both versioned by git
    """

    def __init__(self, path):
        """
            @param path: root git directory
        """
        self._path = path
        self._meta = {}

    def get_name(self):
        raise NotImplemented()

    name = property(get_name)

    def _load_file(self, ns, file):
        ns.location = Location(file, 1)
        statements = []
        stmts = plyInmantaParser.parse(ns, file)
        block = BasicBlock(ns)
        for s in stmts:
            if isinstance(s, BiStatement):
                statements.append(s)
                block.add(s)
            elif isinstance(s, DefinitionStatement):
                statements.append(s)
            elif isinstance(s, str) or isinstance(s, LocatableString):
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


INSTALL_RELEASES = "release"
INSTALL_PRERELEASES = "prerelease"
INSTALL_MASTER = "master"
INSTALL_OPTS = [INSTALL_MASTER, INSTALL_PRERELEASES, INSTALL_RELEASES]


class Project(ModuleLike):
    """
        An inmanta project
    """
    PROJECT_FILE = "project.yml"
    _project = None

    def __init__(self, path, autostd=True, main_file="main.cf"):
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
        self.main_file = main_file

        if not os.path.exists(path):
            raise Exception("Unable to find project directory %s" % path)

        project_file = os.path.join(path, Project.PROJECT_FILE)

        if not os.path.exists(project_file):
            raise Exception("Project directory does not contain a project file")

        with open(project_file, "r") as fd:
            self._meta = yaml.load(fd)

        if "modulepath" not in self._meta:
            raise Exception("modulepath is required in the project(.yml) file")

        modulepath = self._meta["modulepath"]
        if not isinstance(modulepath, list):
            modulepath = [modulepath]
        self.modulepath = [os.path.abspath(os.path.join(path, x)) for x in modulepath]
        self.resolver = CompositeModuleRepo([make_repo(x) for x in self.modulepath])

        if "repo" not in self._meta:
            raise Exception("repo is required in the project(.yml) file")

        repo = self._meta["repo"]
        if not isinstance(repo, list):
            repo = [repo]
        self.repolist = [x for x in repo]
        self.externalResolver = CompositeModuleRepo([make_repo(x, root=path) for x in self.repolist])

        self.downloadpath = None
        if "downloadpath" in self._meta:
            self.downloadpath = os.path.abspath(os.path.join(
                path, self._meta["downloadpath"]))
            if self.downloadpath not in self.modulepath:
                LOGGER.warning("Downloadpath is not in module path! Module install will not work as expected")

            if not os.path.exists(self.downloadpath):
                os.mkdir(self.downloadpath)

        self.virtualenv = env.VirtualEnv(os.path.join(path, ".env"))

        self.loaded = False
        self.modules = {}

        self.root_ns = Namespace("__root__")

        self.autostd = autostd
        self._install_mode = INSTALL_RELEASES
        if "install_mode" in self._meta:
            mode = self._meta["install_mode"]
            if mode not in INSTALL_OPTS:
                LOGGER.warning("Invallid value for install_mode, should be one of [%s]" % ','.join(INSTALL_OPTS))
            else:
                self._install_mode = mode

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
            raise ProjectNotFoundExcpetion("Unable to find an inmanta project (project.yml expected)")

        return cls.get_project_dir(parent_dir)

    @classmethod
    def get(cls, main_file="main.cf"):
        """
            Get the instance of the project
        """
        if cls._project is None:
            cls._project = Project(cls.get_project_dir(os.curdir), main_file=main_file)

        return cls._project

    @classmethod
    def set(cls, project):
        """
            Get the instance of the project
        """
        cls._project = project
        os.chdir(project._path)
        plugins.PluginMeta.clear()

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
        return self._load_file(main_ns, os.path.join(self.project_path, self.main_file))

    def load_module(self, module_name):
        try:
            path = self.resolver.path_for(module_name)
            if path is not None:
                module = Module(self, path)
            else:
                reqs = self.collect_requirements()
                if module_name in reqs:
                    module = Module.install(self, module_name, reqs[module_name], install_mode=self._install_mode)
                else:
                    module = Module.install(self, module_name, parse_requirements(module_name), install_mode=self._install_mode)
            self.modules[module_name] = module
            return module
        except Exception:
            raise InvalidModuleException("Could not load module %s" % module_name)

    def load_plugins(self) -> None:
        """
            Load all plug-ins
        """
        if not self.loaded:
            LOGGER.warning("loading plugins on project that has not been loaded completely")
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
            LOGGER.warning("collecting reqs on project that has not been loaded completely")

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
    MODEL_DIR = "model"
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

    def rewrite_version(self, new_version):
        new_version = str(new_version)  # make sure it is a string!
        with open(self.get_config_file_name(), "r") as fd:
            module_def = fd.read()

        module_info = yaml.safe_load(module_def)
        if "version" not in module_info:
            raise Exception("Not a valid module definition")

        current_version = str(module_info["version"])
        if current_version == new_version:
            LOGGER.debug("Current version is the same as the new version: %s", current_version)

        new_module_def = re.sub("([\s]version\s*:\s*['\"\s]?)[^\"'}\s]+(['\"]?)",
                                "\g<1>" + new_version + "\g<2>", module_def)

        try:
            new_info = yaml.safe_load(new_module_def)
        except Exception:
            raise Exception("Unable to rewrite module definition %s" % self.get_config_file_name())

        if str(new_info["version"]) != new_version:
            raise Exception("Unable to write module definition, should be %s got %s instead." %
                            (new_version, new_info["version"]))

        with open(self.get_config_file_name(), "w+") as fd:
            fd.write(new_module_def)

        self._meta = new_info

    def get_name(self):
        """
            Returns the name of the module (if the meta data is set)
        """
        if "name" in self._meta:
            return self._meta["name"]

        return None

    name = property(get_name)

    def get_version(self) -> str:
        """
            Return the version of this module
        """
        if "version" in self._meta:
            return str(self._meta["version"])

        return None

    version = property(get_version)

    @property
    def compiler_version(self) -> str:
        """
            Get the minimal compiler version required for this module version. Returns none is the compiler version is not
            constrained.
        """
        if "compiler_version" in self._meta:
            return str(self._meta["compiler_version"])
        return None

    @classmethod
    def install(cls, project, modulename, requirements, install=True, install_mode=INSTALL_RELEASES):
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
                raise InvalidModuleException("could not locate module with name: %s" % modulename)

        return cls.update(project, modulename, requirements, path, False, install_mode=install_mode)

    @classmethod
    def update(cls, project, modulename, requirements, path=None, fetch=True, install_mode=INSTALL_RELEASES):
        """
           Update a module, return module object
        """

        if path is None:
            path = project.resolver.path_for(modulename)

        if fetch:
            gitprovider.fetch(path)

        if install_mode == INSTALL_MASTER:
            gitprovider.checkout_tag(path, "master")
        else:
            release_only = (install_mode == INSTALL_RELEASES)
            version = cls.get_suitable_version_for(modulename, requirements, path, release_only=release_only)

            if version is None:
                print("no suitable version found for module %s" % modulename)
            else:
                gitprovider.checkout_tag(path, str(version))

        return Module(project, path)

    @classmethod
    def get_suitable_version_for(cls, modulename, requirements, path, release_only=True):
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

        comp_version = get_compiler_version()
        if comp_version is not None:
            comp_version = parse_version(comp_version)
            # use base version, to make sure dev versions work as expected
            comp_version = parse_version(comp_version.base_version)
            return cls.__best_for_compiler_version(modulename, versions, path, comp_version)
        else:
            return versions[0]

    @classmethod
    def __best_for_compiler_version(cls, modulename, versions, path, comp_version):
        def get_cv_for(best):
            cfg = gitprovider.get_file_for_version(path, str(best), "module.yml")
            cfg = yaml.load(cfg)
            if "compiler_version" not in cfg:
                return None
            v = cfg["compiler_version"]
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
            file = os.path.join(self._path, Module.MODEL_DIR, "_init.cf")
        else:
            parts = name.split("::")
            parts = parts[1:]
            if os.path.isdir(os.path.join(self._path, Module.MODEL_DIR, *parts)):
                path_elements = [self._path, Module.MODEL_DIR] + parts + ["_init.cf"]
            else:
                path_elements = [self._path, Module.MODEL_DIR] + parts[:-1] + [parts[-1] + ".cf"]
            file = os.path.join(*path_elements)

        ns = self._project.get_root_namespace().get_ns_or_create(name)

        try:
            return self._load_file(ns, file)
        except FileNotFoundError:
            raise InvalidModuleException("could not locate module with name: %s", name)

    def _get_model_files(self, curdir):
        files = []
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

    def get_all_submodules(self):
        """
            Get all submodules of this module
        """
        modules = []
        cur_dir = os.path.join(self._path, Module.MODEL_DIR)
        files = self._get_model_files(cur_dir)

        for f in files:
            name = f[len(cur_dir) + 1:-3]
            parts = name.split("/")
            if parts[-1] == "_init":
                parts = parts[:-1]

            parts.insert(0, self.get_name())
            name = "::".join(parts)

            modules.append(name)

        return modules

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
            raise CompilerException("Unable to load all plug-ins for module %s" % self._meta["name"]) from e

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
        try:
            output = gitprovider.status(self._path)

            files = [x.strip() for x in output.split("\n") if x != ""]

            if len(files) > 0:
                print("Module %s (%s)" % (self._meta["name"], self._path))
                for f in files:
                    print("\t%s" % f)

                print()
            else:
                print("Module %s (%s) has no changes" % (self._meta["name"], self._path))
        except Exception:
            print("Failed to get status of module")
            LOGGER.exception("Failed to get status of module %s")

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

    def create(self, name):
        project = Project.get()
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
            try:
                Module.update(project, name, spec, install_mode=project._install_mode)
            except Exception:
                LOGGER.exception("Failed to update module")

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

    def verify(self):
        """
            Verify dependencies and frozen module versions
        """
        Project.get().verify()

    def _find_module(self):
        module = Module(None, os.path.realpath(os.curdir))
        LOGGER.info("Successfully loaded module %s with version %s" % (module.name, module.version))
        return module

    def determine_new_version(self, old_version, version, major, minor, patch, dev):
        was_dev = old_version.is_prerelease

        if was_dev:
            if major or minor or patch:
                print("WARNING: when releasing a dev version, options --major, --minor and --patch are ignored")

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
                    print("WARNING: when using the --version option, --major, --minor and --patch are ignored")
                outversion = version
            else:
                if len(opts) == 0:
                    print("One of the following options is required: --major, --minor or --patch")
                    return None
                elif len(opts) > 1:
                    print("You can use only one of the following options: --major, --minor or --patch")
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
            print("new versions (%s) is not larger then old version (%s), aborting" % (outversion, old_version))
            return None

        return outversion

    def commit(self, message, version=None, dev=False, major=False, minor=False, patch=False, commit_all=False):
        """
            Commit all current changes.
        """
        # find module
        module = self._find_module()
        # get version
        old_version = parse_version(str(module.version))

        outversion = self.determine_new_version(old_version, version, major, minor, patch, dev)

        if outversion is None:
            return

        module.rewrite_version(str(outversion))
        print("set version to: " + str(outversion))
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
