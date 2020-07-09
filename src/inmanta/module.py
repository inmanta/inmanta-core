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
import importlib
import logging
import os
import re
import subprocess
import sys
import traceback
from functools import lru_cache
from io import BytesIO
from subprocess import CalledProcessError
from tarfile import TarFile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple, Union

import yaml
from pkg_resources import parse_requirements, parse_version

from inmanta import const, env, loader, plugins
from inmanta.ast import CompilerException, LocatableString, Location, ModuleNotFoundException, Namespace, Range
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.statements import BiStatement, DefinitionStatement, DynamicStatement, Statement
from inmanta.ast.statements.define import DefineImport
from inmanta.parser import plyInmantaParser
from inmanta.types import JsonType
from inmanta.util import get_compiler_version

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    from pkg_resources.packaging.version import Version  # noqa: F401
    from pkg_resources import Requirement  # noqa: F401


LOGGER = logging.getLogger(__name__)


class InvalidModuleException(CompilerException):
    """
        This exception is raised if a module is invalid
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


class InvalidModuleFileException(CompilerException):
    """
        This exception is raised if a module file is invalid
    """


class ProjectNotFoundExcpetion(CompilerException):
    """
        This exception is raised when inmanta is unable to find a valid project
    """


class GitProvider(object):
    def clone(self, src: str, dest: str) -> None:
        pass

    def fetch(self, repo: str) -> None:
        pass

    def get_all_tags(self, repo: str) -> List[str]:
        pass

    def get_file_for_version(self, repo: str, tag: str, file: str) -> str:
        pass

    def checkout_tag(self, repo: str, tag: str) -> None:
        pass

    def commit(self, repo: str, message: str, commit_all: bool, add: List[str] = []) -> None:
        pass

    def tag(self, repo: str, tag: str) -> None:
        pass

    def push(self, repo: str) -> str:
        pass


class CLIGitProvider(GitProvider):
    def clone(self, src: str, dest: str) -> None:
        env = os.environ.copy()
        env["GIT_ASKPASS"] = "true"
        subprocess.check_call(["git", "clone", src, dest], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

    def fetch(self, repo: str) -> None:
        env = os.environ.copy()
        env["GIT_ASKPASS"] = "true"
        subprocess.check_call(
            ["git", "fetch", "--tags"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
        )

    def status(self, repo: str) -> str:
        return subprocess.check_output(["git", "status", "--porcelain"], cwd=repo).decode("utf-8")

    def get_all_tags(self, repo: str) -> List[str]:
        return subprocess.check_output(["git", "tag"], cwd=repo).decode("utf-8").splitlines()

    def checkout_tag(self, repo: str, tag: str) -> None:
        subprocess.check_call(["git", "checkout", tag], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def commit(self, repo: str, message: str, commit_all: bool, add: List[str] = []) -> None:
        for file in add:
            subprocess.check_call(["git", "add", file], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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


gitprovider = CLIGitProvider()


class ModuleRepo(object):
    def clone(self, name: str, dest: str) -> bool:
        raise NotImplementedError("Abstract method")

    def path_for(self, name: str) -> Optional[str]:
        # same class is used for search parh and remote repos, perhaps not optimal
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
        try:
            url = self.baseurl.format(name)
            if url == self.baseurl:
                url = self.baseurl + name

            gitprovider.clone(url, os.path.join(dest, name))
            return True
        except Exception:
            LOGGER.debug("could not clone repo", exc_info=True)
            return False

    def path_for(self, name: str) -> Optional[str]:
        raise NotImplementedError("Should only be called on local repos")


def make_repo(path: str, root: Optional[str] = None) -> Union[LocalFileRepo, RemoteRepo]:
    # check that the second char is not a colon (windows)
    if ":" in path and path[1] != ":":
        return RemoteRepo(path)
    else:
        return LocalFileRepo(path, parent_root=root)


def merge_specs(mainspec: "Dict[str, List[Requirement]]", new: "List[Requirement]") -> None:
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

    def __init__(self, path: str) -> None:
        """
            :param path: root git directory
        """
        self._path = path
        self._meta = {}  # type: JsonType

    def get_name(self) -> str:
        raise NotImplementedError()

    name = property(get_name)

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

    def requires(self) -> "List[Requirement]":
        """
            Get the requires for this module
        """
        # filter on import stmt

        if "requires" not in self._meta or self._meta["requires"] is None:
            return []

        reqs = []
        for spec in self._meta["requires"]:
            req = [x for x in parse_requirements(spec)]
            if len(req) > 1:
                print("Module file for %s has bad line in requirements specification %s" % (self._path, spec))
            reqe = req[0]
            reqs.append(reqe)
        return reqs

    def get_config(self, name: str, default: Any) -> Any:
        if name not in self._meta:
            return default
        else:
            return self._meta[name]


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

    def __init__(self, path: str, autostd: bool = True, main_file: str = "main.cf") -> None:
        """
            Initialize the project, this includes
             * Loading the project.yaml (into self._meta)
             * Setting paths from project.yaml
             * Loading all modules in the module path (into self.modules)
            It does not include
             * verify if project.yml corresponds to the modules in self.modules

            :param path: The directory where the project is located

        """
        super().__init__(path)
        self.project_path = path
        self.main_file = main_file

        if not os.path.exists(path):
            raise Exception("Unable to find project directory %s" % path)

        project_file = os.path.join(path, Project.PROJECT_FILE)

        if not os.path.exists(project_file):
            raise Exception("Project directory does not contain a project file")

        with open(project_file, "r", encoding="utf-8") as fd:
            self._meta = yaml.safe_load(fd)

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
            self.downloadpath = os.path.abspath(os.path.join(path, self._meta["downloadpath"]))
            if self.downloadpath not in self.modulepath:
                LOGGER.warning("Downloadpath is not in module path! Module install will not work as expected")

            if not os.path.exists(self.downloadpath):
                os.mkdir(self.downloadpath)

        self.virtualenv = env.VirtualEnv(os.path.join(path, ".env"))

        self.loaded = False
        self.modules = {}  # type: Dict[str, Module]

        self.root_ns = Namespace("__root__")

        self.autostd = autostd
        self._install_mode = INSTALL_RELEASES
        if "install_mode" in self._meta:
            mode = self._meta["install_mode"]
            if mode not in INSTALL_OPTS:
                LOGGER.warning("Invallid value for install_mode, should be one of [%s]" % ",".join(INSTALL_OPTS))
            else:
                self._install_mode = mode

    @classmethod
    def get_project_dir(cls, cur_dir: str) -> str:
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
    def get(cls, main_file: str = "main.cf") -> "Project":
        """
            Get the instance of the project
        """
        if cls._project is None:
            cls._project = Project(cls.get_project_dir(os.curdir), main_file=main_file)

        return cls._project

    @classmethod
    def set(cls, project: "Project") -> None:
        """
            Get the instance of the project
        """
        cls._project = project
        os.chdir(project._path)
        plugins.PluginMeta.clear()
        loader.unload_inmanta_plugins()

    def load(self) -> None:
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

    @lru_cache()
    def get_ast(self) -> Tuple[List[Statement], BasicBlock]:
        return self.__load_ast()

    @lru_cache()
    def get_imports(self) -> List[DefineImport]:
        (statements, _) = self.get_ast()
        imports = [x for x in statements if isinstance(x, DefineImport)]
        if self.autostd:
            std_locatable = LocatableString("std", Range("__internal__", 1, 1, 1, 1), -1, self.root_ns)
            imp = DefineImport(std_locatable, std_locatable)
            imp.location = std_locatable.location
            imports.insert(0, imp)
        return imports

    @lru_cache()
    def get_complete_ast(self) -> Tuple[List[Statement], List[BasicBlock]]:
        # load ast
        (statements, block) = self.get_ast()
        blocks = [block]
        statements = [x for x in statements]

        # get imports
        imports = [x for x in self.get_imports()]
        for _, nstmt, nb in self.load_module_recursive(imports):
            statements.extend(nstmt)
            blocks.append(nb)

        return (statements, blocks)

    def __load_ast(self) -> Tuple[List[Statement], BasicBlock]:
        main_ns = Namespace("__config__", self.root_ns)
        return self._load_file(main_ns, os.path.join(self.project_path, self.main_file))

    def get_modules(self) -> Dict[str, "Module"]:
        self.load()
        return self.modules

    def get_module(self, full_module_name: str) -> "Module":
        parts = full_module_name.split("::")
        module_name = parts[0]

        if module_name in self.modules:
            return self.modules[module_name]
        return self.load_module(module_name)

    def load_module_recursive(self, imports: List[DefineImport]) -> List[Tuple[str, List[Statement], BasicBlock]]:
        """
            Load a specific module and all submodules into this project

            For each module, return a triple of name, statements, basicblock
        """
        out = []

        # get imports
        imports = [x for x in self.get_imports()]

        done = set()  # type: Set[str]
        while len(imports) > 0:
            imp = imports.pop()
            ns = imp.name
            if ns in done:
                continue

            parts = ns.split("::")
            module_name = parts[0]

            try:
                # get module
                module = self.get_module(module_name)
                # get NS
                for i in range(1, len(parts) + 1):
                    subs = "::".join(parts[0:i])
                    if subs in done:
                        continue
                    (nstmt, nb) = module.get_ast(subs)

                    done.add(subs)
                    out.append((subs, nstmt, nb))

                    # get imports and add to list
                    imports.extend(module.get_imports(subs))
            except InvalidModuleException as e:
                raise ModuleNotFoundException(ns, imp, e)

        return out

    def load_module(self, module_name: str) -> "Module":
        try:
            path = self.resolver.path_for(module_name)
            if path is not None:
                module = Module(self, path)
            else:
                reqs = self.collect_requirements()
                if module_name in reqs:
                    module = Module.install(self, module_name, reqs[module_name], install_mode=self._install_mode)
                else:
                    module = Module.install(
                        self, module_name, list(parse_requirements(module_name)), install_mode=self._install_mode
                    )
            self.modules[module_name] = module
            return module
        except Exception as e:
            raise InvalidModuleException("Could not load module %s" % module_name) from e

    def load_plugins(self) -> None:
        """
            Load all plug-ins
        """
        if not self.loaded:
            LOGGER.warning("loading plugins on project that has not been loaded completely")

        loader.configure_module_finder(self.modulepath)

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
        names = list(self.modules.keys())
        names = sorted(names)

        mod_list = []
        for name in names:
            mod_list.append(self.modules[name])

        return mod_list

    def collect_requirements(self) -> "Mapping[str, Iterable[Requirement]]":
        """
            Collect the list of all requirements of all modules in the project.
        """
        specs = {}  # type: Dict[str, List[Requirement]]
        merge_specs(specs, self.requires())
        for module in self.modules.values():
            reqs = module.requires()
            merge_specs(specs, reqs)
        return specs

    def collect_imported_requirements(self) -> "Mapping[str, Iterable[Requirement]]":
        imports = set([x.name.split("::")[0] for x in self.get_complete_ast()[0] if isinstance(x, DefineImport)])
        imports.add("std")
        specs = self.collect_requirements()

        def get_spec(name: str) -> "Iterable[Requirement]":
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
                    LOGGER.warning("requirement %s on module %s not fullfilled, now at version %s" % (r, name, version))
                    good = False

        return good

    def collect_python_requirements(self) -> List[str]:
        """
            Collect the list of all python requirements off all modules in this project
        """
        req_files = [x.strip() for x in [mod.get_python_requirements() for mod in self.modules.values()] if x is not None]
        req_lines = [x for x in "\n".join(req_files).split("\n") if len(x.strip()) > 0]
        req_lines = self._remove_comments(req_lines)
        req_lines = self._remove_line_continuations(req_lines)
        return list(set(req_lines))

    def _remove_comments(self, lines: List[str]) -> List[str]:
        """
            Remove comments from lines in requirements.txt file.
        """
        result = []
        for line in lines:
            if line.strip().startswith("#"):
                continue
            if " #" in line:
                line_without_comment = line.split(" #", maxsplit=1)[0]
                result.append(line_without_comment)
            else:
                result.append(line)
        return result

    def _remove_line_continuations(self, lines: List[str]) -> List[str]:
        """
            Remove line continuation from lines in requirements.txt file.
        """
        result = []
        line_continuation_buffer = ""
        for line in lines:
            if line.endswith("\\"):
                line_continuation_buffer = f"{line_continuation_buffer}{line[0:-1]}"
            else:
                if line_continuation_buffer:
                    result.append(f"{line_continuation_buffer}{line}")
                    line_continuation_buffer = ""
                else:
                    result.append(line)
        return result

    def get_name(self) -> str:
        return "project.yml"

    name = property(get_name)

    def get_config_file_name(self) -> str:
        return os.path.join(self._path, "project.yml")

    def get_root_namespace(self) -> Namespace:
        return self.root_ns

    def get_freeze(self, mode: str = "==", recursive: bool = False) -> Dict[str, str]:
        # collect in scope modules
        if not recursive:
            modules = {m.name: m for m in (self.get_module(imp.name) for imp in self.get_imports())}
        else:
            modules = self.get_modules()

        out = {}
        for name, mod in modules.items():
            version = str(mod.version)
            out[name] = mode + " " + version

        return out


class Module(ModuleLike):
    """
        This class models an inmanta configuration module
    """

    MODEL_DIR = "model"
    requires_fields = ["name", "license", "version"]

    def __init__(self, project: Project, path: str, **kwmeta: dict) -> None:
        """
            Create a new configuration module

            :param project: A reference to the project this module belongs to.
            :param path: Where is the module stored
            :param kwmeta: Meta-data
        """
        super().__init__(path)
        self._project = project
        self._meta = kwmeta

        if not Module.is_valid_module(self._path):
            raise InvalidModuleException(
                (
                    "Module %s is not a valid inmanta configuration module. Make sure that a "
                    "model/_init.cf file exists and a module.yml definition file."
                )
                % self._path
            )

        self.load_module_file()
        self.is_versioned()

    def rewrite_version(self, new_version: str) -> None:
        new_version = str(new_version)  # make sure it is a string!
        with open(self.get_config_file_name(), "r", encoding="utf-8") as fd:
            module_def = fd.read()

        module_info = yaml.safe_load(module_def)
        if "version" not in module_info:
            raise Exception("Not a valid module definition")

        current_version = str(module_info["version"])
        if current_version == new_version:
            LOGGER.debug("Current version is the same as the new version: %s", current_version)

        new_module_def = re.sub(
            r"([\s]version\s*:\s*['\"\s]?)[^\"'}\s]+(['\"]?)", r"\g<1>" + new_version + r"\g<2>", module_def
        )

        try:
            new_info = yaml.safe_load(new_module_def)
        except Exception:
            raise Exception("Unable to rewrite module definition %s" % self.get_config_file_name())

        if str(new_info["version"]) != new_version:
            raise Exception(
                "Unable to write module definition, should be %s got %s instead." % (new_version, new_info["version"])
            )

        with open(self.get_config_file_name(), "w+", encoding="utf-8") as fd:
            fd.write(new_module_def)

        self._meta = new_info

    def get_name(self) -> str:
        """
            Returns the name of the module (if the meta data is set)
        """
        return self._meta["name"]

    name = property(get_name)

    def get_version(self) -> str:
        """
            Return the version of this module
        """
        return str(self._meta["version"])

    version = property(get_version)

    @property
    def compiler_version(self) -> Optional[str]:
        """
            Get the minimal compiler version required for this module version. Returns none is the compiler version is not
            constrained.
        """
        if "compiler_version" in self._meta:
            return str(self._meta["compiler_version"])
        return None

    @classmethod
    def install(
        cls,
        project: Project,
        modulename: str,
        requirements: "Iterable[Requirement]",
        install: bool = True,
        install_mode: str = INSTALL_RELEASES,
    ) -> "Module":
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
            if project.downloadpath is None:
                raise CompilerException(
                    f"Can not install module {modulename} because 'downloadpath' is not set in {project.PROJECT_FILE}"
                )
            path = os.path.join(project.downloadpath, modulename)
            result = project.externalResolver.clone(modulename, project.downloadpath)
            if not result:
                raise InvalidModuleException("could not locate module with name: %s" % modulename)

        return cls.update(project, modulename, requirements, path, False, install_mode=install_mode)

    @classmethod
    def update(
        cls,
        project: Project,
        modulename: str,
        requirements: "Iterable[Requirement]",
        path: str = None,
        fetch: bool = True,
        install_mode: str = INSTALL_RELEASES,
    ) -> "Module":
        """
           Update a module, return module object
        """
        if path is None:
            mypath = project.resolver.path_for(modulename)
            assert mypath is not None, f"trying to update module {modulename} not found on disk "
        else:
            mypath = path

        if fetch:
            LOGGER.info("Performing fetch on %s", mypath)
            gitprovider.fetch(mypath)

        if install_mode == INSTALL_MASTER:
            LOGGER.info("Checking out master on %s", mypath)
            gitprovider.checkout_tag(mypath, "master")
            if fetch:
                LOGGER.info("Pulling master on %s", mypath)
                gitprovider.pull(mypath)
        else:
            release_only = install_mode == INSTALL_RELEASES
            version = cls.get_suitable_version_for(modulename, requirements, mypath, release_only=release_only)

            if version is None:
                print("no suitable version found for module %s" % modulename)
            else:
                LOGGER.info("Checking out %s on %s", str(version), mypath)
                gitprovider.checkout_tag(mypath, str(version))

        return Module(project, mypath)

    @classmethod
    def get_suitable_version_for(
        cls, modulename: str, requirements: "Iterable[Requirement]", path: str, release_only: bool = True
    ) -> "Optional[Version]":
        versions = gitprovider.get_all_tags(path)

        def try_parse(x: str) -> "Version":
            try:
                return parse_version(x)
            except Exception:
                return None

        versions = [x for x in [try_parse(v) for v in versions] if x is not None]
        versions = sorted(versions, reverse=True)

        for r in requirements:
            versions = [x for x in r.specifier.filter(versions, not release_only)]

        comp_version_raw = get_compiler_version()
        if comp_version_raw is not None:
            comp_version = parse_version(comp_version_raw)
            # use base version, to make sure dev versions work as expected
            comp_version = parse_version(comp_version.base_version)
            return cls.__best_for_compiler_version(modulename, versions, path, comp_version)
        else:
            LOGGER.warning("The Inmanta compiler is not installed")
            return versions[0] if len(versions) > 0 else None

    @classmethod
    def __best_for_compiler_version(
        cls, modulename: str, versions: "List[Version]", path: str, comp_version: "Version"
    ) -> "Optional[Version]":
        def get_cv_for(best: "Version") -> "Optional[Version]":
            cfg_raw = gitprovider.get_file_for_version(path, str(best), "module.yml")
            cfg = yaml.safe_load(cfg_raw)
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

    def is_versioned(self) -> bool:
        """
            Check if this module is versioned, and if so the version number in the module file should
            have a tag. If the version has + the current revision can be a child otherwise the current
            version should match the tag
        """
        if not os.path.exists(os.path.join(self._path, ".git")):
            LOGGER.warning(
                "Module %s is not version controlled, we recommend you do this as soon as possible." % self._meta["name"]
            )
            return False
        return True

    @classmethod
    def is_valid_module(cls, module_path: str) -> bool:
        """
            Checks if this module is a valid configuration module. A module should contain a
            module.yml file.
        """
        if not os.path.isfile(os.path.join(module_path, "module.yml")):
            return False

        return True

    def load_module_file(self) -> None:
        """
            Load the module definition file
        """
        with open(self.get_config_file_name(), "r", encoding="utf-8") as fd:
            mod_def = yaml.safe_load(fd)

            if mod_def is None or len(mod_def) < len(Module.requires_fields):
                raise InvalidModuleFileException(
                    "The module file of %s does not have the required fields: %s"
                    % (self._path, ", ".join(Module.requires_fields))
                )

            for name, value in mod_def.items():
                self._meta[name] = value

        for req_field in Module.requires_fields:
            if req_field not in self._meta:
                raise InvalidModuleFileException("%s is required in module file of module %s" % (req_field, self._path))

        if self._meta["name"] != os.path.basename(self._path):
            LOGGER.warning(
                "The name in the module file (%s) does not match the directory name (%s)"
                % (self._meta["name"], os.path.basename(self._path))
            )

    def get_config_file_name(self) -> str:
        return os.path.join(self._path, "module.yml")

    def get_module_files(self) -> List[str]:
        """
            Returns the path of all model files in this module, relative to the module root
        """
        files = []
        for model_file in glob.glob(os.path.join(self._path, "model", "*.cf")):
            files.append(model_file)

        return files

    @lru_cache()
    def get_ast(self, name: str) -> Tuple[List[Statement], BasicBlock]:
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
        except FileNotFoundError as e:
            raise InvalidModuleException("could not locate module with name: %s" % name) from e

    def get_freeze(self, submodule: str, recursive: bool = False, mode: str = ">=") -> Dict[str, str]:
        imports = [statement.name for statement in self.get_imports(submodule)]

        out: Dict[str, str] = {}

        todo: List[str] = imports

        for impor in todo:
            if impor not in out:
                mainmod = self._project.get_module(impor)
                version = mainmod.version
                # track submodules for cycle avoidance
                out[impor] = mode + " " + version
                if recursive:
                    todo.extend([statement.name for statement in mainmod.get_imports(impor)])

        # drop submodules
        return {x: v for x, v in out.items() if "::" not in x}

    @lru_cache()
    def get_imports(self, name: str) -> List[DefineImport]:
        (statements, block) = self.get_ast(name)
        imports = [x for x in statements if isinstance(x, DefineImport)]
        if self._project.autostd:
            std_locatable = LocatableString("std", Range("internal", 0, 0, 0, 0), 0, block.namespace)
            imports.insert(0, DefineImport(std_locatable, std_locatable))
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
        cur_dir = os.path.join(self._path, Module.MODEL_DIR)
        files = self._get_model_files(cur_dir)

        for f in files:
            name = f[len(cur_dir) + 1 : -3]
            parts = name.split("/")
            if parts[-1] == "_init":
                parts = parts[:-1]

            parts.insert(0, self.get_name())
            name = "::".join(parts)

            modules.append(name)

        return modules

    def load_plugins(self) -> None:
        """
            Load all plug-ins from a configuration module
        """
        plugin_dir = os.path.join(self._path, "plugins")

        if not os.path.exists(plugin_dir):
            return

        if not os.path.exists(os.path.join(plugin_dir, "__init__.py")):
            raise CompilerException(
                "The plugin directory %s should be a valid python package with a __init__.py file" % plugin_dir
            )

        try:
            mod_name = self._meta["name"]
            for py_file in glob.glob(os.path.join(plugin_dir, "**", "*.py"), recursive=True):
                fq_mod_name = self._get_fq_mod_name_for_py_file(py_file, plugin_dir, mod_name)

                LOGGER.debug("Loading module %s", fq_mod_name)
                importlib.import_module(fq_mod_name)

        except ImportError as e:
            raise CompilerException("Unable to load all plug-ins for module %s" % self._meta["name"]) from e

    def _get_fq_mod_name_for_py_file(self, py_file: str, plugin_dir: str, mod_name: str) -> str:
        rel_py_file = os.path.relpath(py_file, start=plugin_dir)

        def add_prefix(prefix: str, item: str) -> str:
            if item == "":
                return prefix
            else:
                return f"{prefix}.{item}"

        (head, tail) = os.path.split(rel_py_file)
        if tail == "__init__.py":
            result = ""
        else:
            result = tail[0:-3]  # Remove .py

        while head != "":
            (head, tail) = os.path.split(head)
            result = add_prefix(tail, result)

        return add_prefix(f"{const.PLUGINS_PACKAGE}.{mod_name}", result)

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

    def status(self) -> None:
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

    def push(self) -> None:
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

    def get_python_requirements(self) -> Optional[str]:
        """
            Install python requirements with pip in a virtual environment
        """
        file = os.path.join(self._path, "requirements.txt")
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as fd:
                return fd.read()
        else:
            return None

    @lru_cache()
    def get_python_requirements_as_list(self) -> List[str]:
        raw = self.get_python_requirements()
        if raw is None:
            return []
        else:
            return [y for y in [x.strip() for x in raw.split("\n")] if len(y) != 0]

    def execute_command(self, cmd: str) -> None:
        print("executing %s on %s in %s" % (cmd, self.get_name(), self._path))
        print("=" * 10)
        subprocess.call(cmd, shell=True, cwd=self._path)
        print("=" * 10)
