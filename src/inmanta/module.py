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

import enum
import glob
import importlib
import logging
import os
import re
import subprocess
import sys
import traceback
from abc import ABC, abstractmethod
from functools import lru_cache
from io import BytesIO, TextIOBase
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
    Set,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import yaml
from pkg_resources import parse_requirements, parse_version
from pydantic import BaseModel, Field, NameEmail, ValidationError, validator
from configparser import ConfigParser

import inmanta.warnings
from inmanta import env, loader, plugins
from inmanta.ast import CompilerException, LocatableString, Location, ModuleNotFoundException, Namespace, Range
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.statements import BiStatement, DefinitionStatement, DynamicStatement, Statement
from inmanta.ast.statements.define import DefineImport
from inmanta.parser import plyInmantaParser
from inmanta.parser.plyInmantaParser import cache_manager
from inmanta.stable_api import stable_api
from inmanta.util import get_compiler_version
from packaging import version
from configparser import ConfigParser

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    from pkg_resources import Requirement  # noqa: F401
    from pkg_resources.packaging.version import Version  # noqa: F401


LOGGER = logging.getLogger(__name__)

Path = NewType("Path", str)
ModuleName = NewType("ModuleName", str)


@stable_api
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
        for error in validation_error.errors():
            mgs: str = error["msg"]
            error_type = error["type"]
            msg += f"\n{error['loc']}\n\t{mgs} ({error_type})"
        return msg


class MetadataDeprecationWarning(inmanta.warnings.InmantaWarning):
    pass


class ProjectNotFoundException(CompilerException):
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


@stable_api
class InstallMode(str, enum.Enum):
    """
    The module install mode determines what version of a module should be selected when a module is downloaded.
    """

    release = "release"
    """
    Only use a released version that is compatible with the current compiler and any version constraints defined in the
    ``requires`` lists for the project or any other modules (see :class:`ProjectMetadata` and :class:`ModuleMetadata`).

    A version is released when there is a tag on a commit. This tag should be a valid version identifier (PEP440) and should
    not be a prerelease version. Inmanta selects the latest available version (version sort based on PEP440) that is compatible
    with all constraints.
    """

    prerelease = "prerelease"
    """
    Similar to :attr:`InstallMode.release` but prerelease versions are allowed as well.
    """

    master = "master"
    """
    Use the module's master branch.
    """


INSTALL_OPTS: List[str] = [mode.value for mode in InstallMode]  # Part of the stable API
"""
List of possible module install modes, kept for backwards compatibility. New code should use :class:`InstallMode` instead.
"""


class FreezeOperator(str, enum.Enum):
    eq = "=="
    compatible = "~="
    ge = ">="

    @classmethod
    def get_regex_for_validation(cls) -> str:
        all_values = [re.escape(o.value) for o in cls]
        return f"^({'|'.join(all_values)})$"


class Metadata(BaseModel):
    name: str
    description: Optional[str] = None
    requires: List[str] = []
    freeze_recursive: bool = False
    freeze_operator: str = Field(default="~=", regex=FreezeOperator.get_regex_for_validation())

    @classmethod
    def to_list(cls, v: object) -> object:
        if v is None:
            return []
        if not isinstance(v, list):
            return [v]
        return v

    @validator("requires", pre=True)
    @classmethod
    def requires_to_list(cls, v: object) -> object:
        if isinstance(v, dict):
            # transform legacy format for backwards compatibility
            inmanta.warnings.warn(
                MetadataDeprecationWarning(
                    "The yaml dictionary syntax for specifying module requirements has been deprecated. Please use the"
                    " documented list syntax instead."
                )
            )
            result: List[str] = []
            for key, value in v.items():
                if not (isinstance(key, str) and isinstance(value, str) and value.startswith(key)):
                    raise ValueError("Invalid legacy requires format, expected `mod: mod [constraint]`.")
                result.append(value)
            return result
        return cls.to_list(v)


class ModuleMetadata(Metadata):
    """
    :param name: The name of the module.
    :param description: (Optional) The description of the module
    :param version: The version of the inmanta module.
    :param license: The license for this module
    :param compiler_version: (Optional) The minimal compiler version required to compile this module.
    :param requires: (Optional) Model files import other modules. These imports do not determine a version, this
      is based on the install_model setting of the project. Modules and projects can constrain a version in the
      requires setting. Similar to the module, version constraints are defined using
      `PEP440 syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.
    :param freeze_recursive: (Optional) This key determined if the freeze command will behave recursively or not. If
      freeze_recursive is set to false or not set, the current version of all modules imported directly in any submodule of
      this module will be set in module.yml. If it is set to true, all modules imported in any of those modules will also be
      set.
    :param freeze_operator: (Optional) This key determines the comparison operator used by the freeze command.
      Valid values are [==, ~=, >=]. *Default is '~='*
    """

    version: str
    license: str
    compiler_version: Optional[str] = None

    @validator("version", "compiler_version")
    @classmethod
    def is_pep440_version(cls, v: str) -> str:
        try:
            version.Version(v)
        except version.InvalidVersion as e:
            raise ValueError(f"Version {v} is not PEP440 compliant") from e
        return v


class ModuleRepoType(enum.Enum):
    git = "git"
    package = "package"


class ModuleRepoInfo(BaseModel):

    url: str
    type: ModuleRepoType = ModuleRepoType.git

    @validator("type")
    @classmethod
    def validate_type(cls, v: object) -> object:
        if v == ModuleRepoType.package:
            raise ValidationError("Repository type `package` is not yet supported.")
        return v


class ModuleRepoType(enum.Enum):
    git = "git"
    package = "package"


class ModuleRepoInfo(BaseModel):

    url: str
    type: ModuleRepoType = ModuleRepoType.git


class ProjectMetadata(Metadata):
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
      * package: When the type is set to package, the URL field should contains the URL of the Python package repository.
        The repository should be `PEP 503 <https://www.python.org/dev/peps/pep-0503/>`_ (the simple repository API) compliant.

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
    """

    author: Optional[str] = None
    author_email: Optional[NameEmail] = None
    license: Optional[str] = None
    copyright: Optional[str] = None
    modulepath: List[str] = []
    repo: List[ModuleRepoInfo] = []
    downloadpath: Optional[str] = None
    install_mode: InstallMode = InstallMode.release

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
                raise ValidationError(f"Value should be either a string of a dict, got {elem}")
        return result

    @validator("requires")
    @classmethod
    def convert_require_to_python_packages(cls, v: List[str]) -> List[str]:
        return [f"inmanta-module-{elem}" for elem in v]


T = TypeVar("T", bound=Metadata)


@stable_api
class ModuleLike(ABC, Generic[T]):
    """
    Commons superclass for projects and modules, which are both versioned by git
    """

    def __init__(self, path: str) -> None:
        """
        :param path: root git directory
        """
        self._path = path
        self._metadata = self._get_metadata_from_disk()

    def _get_metadata_from_disk(self) -> T:
        metadata_file_path = self.get_metadata_file_path()

        if not os.path.exists(metadata_file_path):
            raise InvalidModuleException(f"Metadata file {metadata_file_path} does not exist")

        with open(metadata_file_path, "r", encoding="utf-8") as fd:
            return self.get_metadata_from_source(file_content=fd.read())

    def get_metadata_from_source(self, file_content: str) -> T:
        """
        :param file_content: The content of the metadata file.
        """
        schema_type = self.get_metadata_file_schema_type()
        try:
            metadata_obj = self.get_metadata_as_dct(file_content)
            return schema_type(**dict(metadata_obj))
        except ValidationError as e:
            raise InvalidMetadata(msg=str(e), validation_error=e) from e
        except yaml.YAMLError as e:
            raise InvalidMetadata(msg=str(e)) from e

    @abstractmethod
    def get_metadata_as_dct(self, file_content: str) -> Dict[str, Any]:
        raise NotImplementedError()

    def get_name(self) -> str:
        return self._metadata.name

    name = property(get_name)

    @property
    def metadata(self) -> T:
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

    @abstractmethod
    def get_metadata_file_schema_type(self) -> Type[T]:
        raise NotImplementedError()

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
        reqs = []
        for spec in self._metadata.requires:
            req = [x for x in parse_requirements(spec)]
            if len(req) > 1:
                print("Module file for %s has bad line in requirements specification %s" % (self._path, spec))
            reqe = req[0]
            reqs.append(reqe)
        return reqs

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


@stable_api
class Project(ModuleLike[ProjectMetadata]):
    """
    An inmanta project
    """

    PROJECT_FILE = "project.yml"
    _project = None

    def __init__(self, path: str, autostd: bool = True, main_file: str = "main.cf", venv_path: Optional[str] = None) -> None:
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
        """
        if not os.path.exists(path):
            raise ProjectNotFoundException(f"Directory {path} doesn't exist")
        super().__init__(path)
        self.project_path = path
        self.main_file = main_file

        if venv_path is None:
            venv_path = os.path.join(path, ".env")
        else:
            venv_path = os.path.abspath(venv_path)
        self.virtualenv = env.VirtualEnv(venv_path)
        self.loaded = False
        self.modules: Dict[str, Module] = {}
        self.root_ns = Namespace("__root__")
        self.autostd = autostd

    def get_metadata_as_dct(self, file_content: str) -> Dict[str, Any]:
        return yaml.safe_load(file_content)

    @property
    def _install_mode(self) -> InstallMode:
        return self._metadata.install_mode

    @property
    def modulepath(self) -> List[str]:
        return self._metadata.modulepath

    @property
    def downloadpath(self) -> Optional[str]:
        return self._metadata.downloadpath

    def get_metadata_file_path(self) -> str:
        return os.path.join(self._path, Project.PROJECT_FILE)

    def get_metadata_file_schema_type(self) -> Type[ProjectMetadata]:
        return ProjectMetadata

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
            raise ProjectNotFoundException("Unable to find an inmanta project (project.yml expected)")

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
        Set the instance of the project
        """
        cls._project = project
        os.chdir(project._path)
        plugins.PluginMeta.clear()
        loader.unload_inmanta_plugins()

    def load(self) -> None:
        if not self.loaded:
            self.use_virtual_env()
            self.load_module_recursive()
            self.loaded = True
            self.verify()
            self.load_plugins()

    @lru_cache()
    def get_ast(self) -> Tuple[List[Statement], BasicBlock]:
        return self.__load_ast()

    @lru_cache()
    def get_imports(self) -> List[DefineImport]:
        (statements, _) = self.get_ast()
        imports = [x for x in statements if isinstance(x, DefineImport)]
        # if self.autostd:
        #     std_locatable = LocatableString("std", Range("__internal__", 1, 1, 1, 1), -1, self.root_ns)
        #     imp = DefineImport(std_locatable, std_locatable)
        #     imp.location = std_locatable.location
        #     imports.insert(0, imp)
        return imports

    @lru_cache()
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

    def get_module(self, full_module_name: str) -> "Module":
        parts = full_module_name.split("::")
        module_name = parts[0]

        if module_name in self.modules:
            return self.modules[module_name]
        return self.load_module(module_name)

    def load_module_recursive(self) -> None:
        """
        Load all submodules into this project
        """
        index_urls = [repo.url for repo in self.metadata.repo]
        self.virtualenv.install_from_list(
            self.metadata.requires, pip_pre=self._install_mode == InstallMode.prerelease, pip_index_urls=index_urls
        )
        installed_modules = [
            pkg_name[len("inmanta-module-"):]
            for pkg_name in self.virtualenv._get_installed_packages(self.virtualenv.virtual_python).keys()
            if pkg_name.startswith("inmanta-module-")
        ]

        for mod_name in installed_modules:
            self.modules[mod_name] = Module(self, self.virtualenv.get_installation_dir(mod_name))

    def load_module(self, module_name: str) -> "Module":
        try:
            reqs = self.collect_requirements()
            use_pip_pre = self._install_mode == InstallMode.prerelease
            index_urls = [repo.url for repo in self.metadata.repo]
            if module_name in reqs:
                module_reqs = [str(r) for r in reqs[module_name]]
                self.virtualenv.install_from_list([module_name] + module_reqs, pip_pre=use_pip_pre, pip_index_urls=index_urls)
            else:
                self.virtualenv.install_from_list([module_name], pip_pre=use_pip_pre, pip_index_urls=index_urls)
            module = Module(self, self.virtualenv.get_installation_dir(f"inmanta-module-{module_name}"))
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

    def use_virtual_env(self) -> None:
        """
        Use the virtual environment
        """
        self.virtualenv.use_virtual_env()

    def verify(self) -> None:
        if not self.virtualenv.check():
            raise CompilerException("Not all module dependencies have been met.")

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
        # imports.add("std")
        specs = self.collect_requirements()

        def get_spec(name: str) -> "Iterable[Requirement]":
            if name in specs:
                return specs[name]
            return parse_requirements(name)

        return {name: get_spec(name) for name in imports}

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


@stable_api
class Module(ModuleLike[ModuleMetadata]):
    """
    This class models an inmanta configuration module
    """

    MODEL_DIR = "model"
    MODULE_METADATA_FILE = "setup.cfg"

    def __init__(self, project: Project, path: str) -> None:
        """
        Create a new configuration module

        :param project: A reference to the project this module belongs to.
        :param path: Point to the installation of the namespace package of the module
        """
        if not os.path.exists(path):
            raise InvalidModuleException(f"Directory {path} doesn't exist")
        super().__init__(path)

        self._project = project
        self._model_dir = self._get_model_directory()

    def _get_root_data_dirs(self) -> str:
        metadata_file = os.path.join(self._path, self.MODULE_METADATA_FILE)
        if os.path.exists(metadata_file):
            return self._path
        else:
            two_dirs_up = os.path.normpath(os.path.join(self._path, os.pardir, os.pardir))
            metadata_file = os.path.join(two_dirs_up, self.MODULE_METADATA_FILE)
            if os.path.exists(metadata_file):
                return two_dirs_up
            else:
                raise Exception("Directory layout of module is invalid")

    def get_name(self) -> str:
        # Override get_name from parent
        return self._metadata.name[len("inmanta-module-"):]

    def _get_model_directory(self) -> str:
        return os.path.join(self._get_root_data_dirs(), self.MODEL_DIR)

    def get_metadata_as_dct(self, file_content: str) -> Dict[str, Any]:
        config_parser = ConfigParser()
        config_parser.read_string(file_content)
        metadata = {}
        for option_name in ["name", "description", "version", "license", "compiler_version", "freeze_recursive",
                            "freeze_operator"]:
            if config_parser.has_option("metadata", option_name):
                metadata[option_name] = config_parser.get("metadata", option_name)
        if config_parser.has_option("options", "install_requires"):
            metadata["requires"] = config_parser.get("options", "install_requires")
        return metadata

    def rewrite_version(self, new_version: str) -> None:
        new_version = str(new_version)  # make sure it is a string!
        with open(self.get_metadata_file_path(), "r", encoding="utf-8") as fd:
            module_def = fd.read()

        module_metadata = self.get_metadata_from_source(module_def)

        current_version = module_metadata.version
        if current_version == new_version:
            LOGGER.debug("Current version is the same as the new version: %s", current_version)

        new_module_def = re.sub(
            r"([\s]version\s*:\s*['\"\s]?)[^\"'}\s]+(['\"]?)", r"\g<1>" + new_version + r"\g<2>", module_def
        )

        try:
            module_metadata = self.get_metadata_from_source(new_module_def)
        except Exception:
            raise Exception(f"Unable to rewrite module definition {self.get_metadata_file_path()}")

        if module_metadata.version != new_version:
            raise Exception(
                f"Unable to write module definition, should be {new_version} got {module_metadata.version} instead."
            )

        with open(self.get_metadata_file_path(), "w+", encoding="utf-8") as fd:
            fd.write(new_module_def)

        self._metadata = module_metadata

    def get_version(self) -> str:
        """
        Return the version of this module
        """
        return str(self._metadata.version)

    version = property(get_version)

    @property
    def compiler_version(self) -> Optional[str]:
        """
        Get the minimal compiler version required for this module version. Returns none is the compiler version is not
        constrained.
        """
        return str(self._metadata.compiler_version)

    # @classmethod
    # def install(
    #     cls,
    #     project: Project,
    #     modulename: str,
    #     requirements: "Iterable[Requirement]",
    #     install: bool = True,
    #     install_mode: InstallMode = InstallMode.release,
    # ) -> "Module":
    #     """
    #     Install a module, return module object
    #     """
    #     return cls.update(project, modulename, requirements, install_mode=install_mode)
    #
    # @classmethod
    # def update(
    #     cls,
    #     project: Project,
    #     modulename: str,
    #     requirements: "Iterable[Requirement]",
    #     install_mode: InstallMode = InstallMode.release,
    # ) -> "Module":
    #     """
    #     Update a module, return module object
    #     """
    #     release_only = install_mode == InstallMode.release
    #     version = cls.get_suitable_version_for(modulename, requirements, mypath, release_only=release_only)
    #
    #     if version is None:
    #         print("no suitable version found for module %s" % modulename)
    #         raise Exception(f"Cannot install module {modulename}")
    #     else:
    #         LOGGER.info("Installing module version %s", str(version))
    #
    #         project.virtualenv.install_from_list([f"inmanta-module-{modulename}=={version}"])`
    #         return Module(project, project.virtualenv.get_installation_dir(modulename))

    def get_metadata_file_schema_type(self) -> Type[ModuleMetadata]:
        return ModuleMetadata

    def get_metadata_file_path(self) -> str:
        return os.path.join(self._get_root_data_dirs(), self.MODULE_METADATA_FILE)

    def get_module_files(self) -> List[str]:
        """
        Returns the path of all model files in this module, relative to the module root
        """
        files = []
        for model_file in glob.glob(os.path.join(self._model_dir, "*.cf")):
            files.append(model_file)

        return files

    @lru_cache()
    def get_ast(self, name: str) -> Tuple[List[Statement], BasicBlock]:
        if name == self.name:
            file = os.path.join(self._model_dir, "_init.cf")
        else:
            parts = name.split("::")
            parts = parts[1:]
            if os.path.isdir(os.path.join(self._model_dir, *parts)):
                path_elements = [self._model_dir] + parts + ["_init.cf"]
            else:
                path_elements = [self._model_dir] + parts[:-1] + [parts[-1] + ".cf"]
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
        # if self._project.autostd:
        #     std_locatable = LocatableString("std", Range("internal", 0, 0, 0, 0), 0, block.namespace)
        #     imports.insert(0, DefineImport(std_locatable, std_locatable))
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
        cur_dir = self._model_dir
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

    def get_plugin_files(self) -> Iterator[Tuple[Path, ModuleName]]:
        """
        Returns a tuple (absolute_path, fq_mod_name) of all python files in this module.
        """
        if not os.path.exists(os.path.join(self._path, "__init__.py")):
            raise CompilerException(
                "The directory %s should be a valid python package with a __init__.py file" % self._path
            )
        return (
            (
                Path(file_name), ModuleName(self._get_fq_mod_name_for_py_file(file_name, self._path))
            )
            for file_name in glob.iglob(os.path.join(self._path, "**", "*.py"), recursive=True)
        )

    def load_plugins(self) -> None:
        """
        Load all plug-ins from a configuration module
        """
        for _, fq_mod_name in self.get_plugin_files():
            try:
                LOGGER.debug("Loading module %s", fq_mod_name)
                importlib.import_module(fq_mod_name)
            except loader.PluginModuleLoadException as e:
                exception = CompilerException(
                    f"Unable to load all plug-ins for module {self.name}:"
                    f"\n\t{e.get_cause_type_name()} while loading plugin module {e.module}: {e.cause}"
                )
                exception.set_location(Location(e.path, e.lineno if e.lineno is not None else 0))
                raise exception

    # This method is not part of core's stable API but it is currently used by pytest-inmanta (inmanta/pytest-inmanta#76)
    def _get_fq_mod_name_for_py_file(self, py_file: str, inmanta_plugins_pkg_dir: str) -> str:
        """
        Returns the fully qualified Python module name for an inmanta module.

        :param py_file: The Python file for the module, relative to the plugin directory.
        :param inmanta_plugins_pkg_dir: The directory that contains the inmanta_plugins namespace package.
        """
        rel_py_file = os.path.relpath(py_file, start=inmanta_plugins_pkg_dir)
        return loader.PluginModuleLoader.convert_relative_path_to_module(rel_py_file)

    def versions(self):
        """
        Provide a list of all versions available in the repository
        """
        # TODO: Not used in inmanta-core
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
        # TODO: Used by status functionality in moduletool
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
        Run a git status on this module
        """
        # TODO: Used by push functionality in moduletool
        sys.stdout.write("%s (%s) " % (self.get_name(), self._path))
        sys.stdout.flush()
        try:
            print(gitprovider.push(self._path))
        except CalledProcessError:
            print("Cloud not push module %s" % self.get_name())
        else:
            print("done")
        print()

    @lru_cache()
    def get_python_requirements_as_list(self) -> List[str]:
        config_parser = ConfigParser()
        with open(self.get_metadata_file_path(), "r", encoding="utf-8") as fd:
            config_parser.read_file(fd)
        if not config_parser.has_section("options") or not config_parser.has_option("options", "install_requires"):
            return []
        return  [req for req in config_parser.get("options", "install_requires").split("\n") if req.strip()]

    def execute_command(self, cmd: str) -> None:
        # TODO: Used by do functionality of moduletool
        print("executing %s on %s in %s" % (cmd, self.get_name(), self._path))
        print("=" * 10)
        subprocess.call(cmd, shell=True, cwd=self._path)
        print("=" * 10)
