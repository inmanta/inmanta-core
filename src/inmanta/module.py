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
import traceback
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import lru_cache
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
    Set,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import more_itertools
import yaml
from pkg_resources import Requirement, parse_requirements, parse_version
from pydantic import BaseModel, Field, NameEmail, ValidationError, validator

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

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    from pkg_resources.packaging.version import Version  # noqa: F401


LOGGER = logging.getLogger(__name__)

Path = NewType("Path", str)
ModuleName = NewType("ModuleName", str)


TModule = TypeVar("TModule", bound="Module")


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


class ModuleMetadataFileNotFound(InvalidModuleException):
    pass


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


class ModuleSource(Generic[TModule]):
    def get_module(
        self, project: "Project", module_spec: List[Requirement], install: bool = False
    ) -> Optional[TModule]:
        """
        Returns the appropriate module instance for a given module spec.

        :param project: The project associated with the module.
        :param module_spec: The module specification including any constraints on its version. Ignored if module
            is already installed. In this case, the project is responsible for verifying constraint compatibility.
        :param install: Whether to attempt to install the module if it hasn't been installed yet.
        """
        module_name: str = self._get_module_name(module_spec)
        path: Optional[str] = self.path_for(module_name)
        if path is not None:
            return self.from_path(project, path)
        elif install:
            return self.install(project, module_spec)
        else:
            return None

    @abstractmethod
    def install(self, project: "Project", module_spec: List[Requirement]) -> Optional[TModule]:
        """
        Attempt to install a module given a module spec.

        :param project: The project associated with the module.
        :param module_spec: The module specification including any constraints on its version.
        """
        raise NotImplementedError("Abstract method")

    def path_for(self, name: str) -> Optional[str]:
        raise NotImplementedError("Abstract method")

    @classmethod
    @abstractmethod
    def from_path(cls, project: Optional["Project"], path: str) -> TModule:
        raise NotImplementedError("Abstract method")

    def _get_module_name(self, module_spec: List[Requirement]) -> str:
        module_names: Set[str] = {req.key for req in module_spec}
        module_name: str = more_itertools.one(
            module_names,
            too_short=ValueError("module_spec should contain at least one requirement"),
            too_long=ValueError("module_spec should contain requirements for exactly one module"),
        )
        return module_name


class ModuleV2Source(ModuleSource["ModuleV2"]):
    def __init__(self, urls: List[str]) -> None:
        self.urls: List[str] = urls

    def install(self, project: Optional["Project"], module_spec: List[Requirement]) -> Optional["ModuleV2"]:
        module_name: str = self._get_module_name(module_spec)
        requirements: List[Requirement] = [Requirement.parse(f"{ModuleV2.PKG_NAME_PREFIX}{str(req)}") for req in module_spec]
        try:
            env.ProcessEnv.install_from_index(requirements, self.urls)
        except env.PackageNotFound:
            return None
        path: Optional[str] = self.path_for(module_name)
        if path is None:
            raise Exception(f"Inconsistent state: installed module {module_name} but it does not exist in the Python environment.")
        return self.from_path(project, path)

    def path_for(self, name: str) -> Optional[str]:
        if name.startswith(ModuleV2.PKG_NAME_PREFIX):
            raise Exception("PythonRepo instances work with inmanta module names, not Python package names.")
        package: str = f"inmanta_plugins.{name}"
        init: Optional[str] = env.ProcessEnv.get_module_file(package)
        if init is None:
            return None
        try:
            return ModuleLike.get_first_directory_containing_file(os.path.dirname(init), ModuleV2.MODULE_FILE)
        except FileNotFoundError:
            return None

    @classmethod
    def from_path(cls, project: Optional["Project"], path: str) -> "ModuleV2":
        return ModuleV2(project, path)

    def _get_module_name(self, module_spec: List[Requirement]) -> str:
        module_name: str = super()._get_module_name(module_spec)
        if module_name.startswith(ModuleV2.PKG_NAME_PREFIX.lower()):
            raise Exception("PythonRepo instances work with inmanta module names, not Python package names.")
        return module_name


class ModuleRepo(ModuleSource["ModuleV1"]):
    def clone(self, name: str, dest: str) -> bool:
        raise NotImplementedError("Abstract method")

    def install(self, project: "Project", module_spec: List[Requirement]) -> Optional["ModuleV1"]:
        module_name: str = self._get_module_name(module_spec)
        path: Optional[str] = self.path_for(module_name)
        if path is not None:
            return self.from_path(project, path)
        else:
            return ModuleV1.install(project, module_name, module_spec, install_mode=project.install_mode)

    @classmethod
    def from_path(cls, project: Optional["Project"], path: str) -> "ModuleV1":
        return ModuleV1(project, path)


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
    """
    Returns the appropriate `ModuleRepo` instance (v1) for the given path.
    """
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
    ``requires`` lists for the project or any other modules (see :class:`ProjectMetadata` and :class:`ModuleV2Metadata`).

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
            return config["metadata"]
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


T = TypeVar("T", bound="Metadata")


@stable_api
class Metadata(BaseModel):
    name: str
    description: Optional[str] = None
    freeze_recursive: bool = False
    freeze_operator: str = Field(default="~=", regex=FreezeOperator.get_regex_for_validation())

    _raw_parser: Type[RawParser]

    @classmethod
    def parse(cls: Type[T], source: Union[str, TextIO]) -> T:
        raw: Mapping[str, object] = cls._raw_parser.parse(source)
        try:
            return cls(**raw)
        except ValidationError as e:
            if isinstance(source, TextIOBase):
                raise InvalidMetadata(msg=f"Metadata defined in {source.name} is invalid", validation_error=e) from e
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


TModuleMetadata = TypeVar("TModuleMetadata", bound="ModuleMetadata")


@stable_api
class ModuleMetadata(ABC, Metadata):
    version: str
    license: str

    @validator("version")
    @classmethod
    def is_pep440_version(cls, v: str) -> str:
        try:
            version.Version(v)
        except version.InvalidVersion as e:
            raise ValueError(f"Version {v} is not PEP440 compliant") from e
        return v

    @classmethod
    def rewrite_version(cls: Type[TModuleMetadata], source: str, new_version: str) -> Tuple[str, TModuleMetadata]:
        """
        Returns the source text with the version replaced by the new version.
        """
        metadata: TModuleMetadata = cls.parse(source)
        current_version = metadata.version
        if current_version == new_version:
            LOGGER.debug("Current version is the same as the new version: %s", current_version)

        result: str = cls._substitute_version(source, new_version)

        try:
            new_metadata = cls.parse(result)
        except Exception:
            raise Exception("Unable to rewrite module definition.")

        if new_metadata.version != new_version:
            raise Exception(f"Unable to write module definition, should be {new_version} got {new_metadata.version} instead.")

        return result, new_metadata

    @classmethod
    @abstractmethod
    def _substitute_version(cls: Type[TModuleMetadata], source: str, new_version: str) -> str:
        raise NotImplementedError()


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
    def _substitute_version(cls: Type[TModuleMetadata], source: str, new_version: str) -> str:
        return re.sub(r"([\s]version\s*:\s*['\"\s]?)[^\"'}\s]+(['\"]?)", r"\g<1>" + new_version + r"\g<2>", source)

    def to_v2(self) -> "ModuleV2Metadata":
        values = self.dict()
        del values["compiler_version"]
        del values["requires"]
        values["name"] = ModuleV2.PKG_NAME_PREFIX + values["name"]
        return ModuleV2Metadata(**values)


@stable_api
class ModuleV2Metadata(ModuleMetadata):
    """
    :param name: The name of the python package that is generated when packaging this module.
                 This name should follow the format "inmanta-module-<module-name>"
    :param description: (Optional) The description of the module
    :param version: The version of the inmanta module.
    :param license: The license for this module
    :param freeze_recursive: (Optional) This key determined if the freeze command will behave recursively or not. If
      freeze_recursive is set to false or not set, the current version of all modules imported directly in any submodule of
      this module will be set in setup.cfg. If it is set to true, all modules imported in any of those modules will also be
      set.
    :param freeze_operator: (Optional) This key determines the comparison operator used by the freeze command.
      Valid values are [==, ~=, >=]. *Default is '~='*
    """

    _raw_parser: Type[CfgParser] = CfgParser

    @validator("name")
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        """
        The name field of a V2 module should follow the format "inmanta-module-<module-name>"
        """
        if not v.startswith(ModuleV2.PKG_NAME_PREFIX) or not len(v) > len(ModuleV2.PKG_NAME_PREFIX):
            raise ValueError(f'The name field should follow the format "{ModuleV2.PKG_NAME_PREFIX}<module-name>"')
        return v

    @classmethod
    def _substitute_version(cls: Type[TModuleMetadata], source: str, new_version: str) -> str:
        return re.sub(r"(\[metadata\][^\[]*\s*version\s*=\s*)[^\"'}\s\[]+", r"\g<1>" + new_version, source)

    def to_config(self, inp: Optional[configparser.ConfigParser] = None) -> configparser.ConfigParser:
        if inp:
            out = inp
        else:
            out = configparser.ConfigParser()

        if not out.has_section("metadata"):
            out.add_section("metadata")

        for k, v in self.dict().items():
            out.set("metadata", k, str(v))

        return out


@stable_api
class ModuleRepoType(enum.Enum):
    git = "git"
    package = "package"


@stable_api
class ModuleRepoInfo(BaseModel):

    url: str
    type: ModuleRepoType = ModuleRepoType.git


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
    requires: List[str] = []

    _raw_parser: Type[YamlParser] = YamlParser

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
        self.name = self.get_name_from_metadata(self._metadata)

    @classmethod
    def get_first_directory_containing_file(cls, cur_dir: str, filename: str) -> str:
        """
        Travel up in the directory structure until a file with the given name if found.
        """
        fq_path_to_filename = os.path.join(cur_dir, filename)

        if os.path.exists(fq_path_to_filename):
            return cur_dir

        parent_dir = os.path.abspath(os.path.join(cur_dir, os.pardir))
        if parent_dir == cur_dir:
            raise FileNotFoundError(f"No file with name {filename} exists in any of the parent directories")

        return cls.get_first_directory_containing_file(parent_dir, filename)

    def _get_metadata_from_disk(self) -> T:
        metadata_file_path = self.get_metadata_file_path()

        if not os.path.exists(metadata_file_path):
            raise ModuleMetadataFileNotFound(f"Metadata file {metadata_file_path} does not exist")

        with open(metadata_file_path, "r", encoding="utf-8") as fd:
            return self.get_metadata_from_source(source=fd)

    def get_metadata_from_source(self, source: Union[str, TextIO]) -> T:
        """
        :param source: Either the yaml content as a string or an input stream from the yaml file
        """
        metadata_type: Type[T] = self.get_metadata_file_schema_type()
        return metadata_type.parse(source)

    @property
    def path(self) -> str:
        return self._path

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

    @classmethod
    @abstractmethod
    def get_metadata_file_schema_type(cls) -> Type[T]:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def get_name_from_metadata(cls, metadata: T) -> str:
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

        self._metadata.modulepath = [os.path.abspath(os.path.join(path, x)) for x in self._metadata.modulepath]
        self.module_source: ModuleV2Source = ModuleV2Source(
            [repo.url for repo in self._metadata.repo if repo.type == ModuleRepoType.package]
        )
        self.resolver_v1 = CompositeModuleRepo([make_repo(x) for x in self.modulepath])
        self.external_resolver_v1 = CompositeModuleRepo(
            [make_repo(repo.url, root=path) for repo in self._metadata.repo if repo.type == ModuleRepoType.git]
        )

        if self._metadata.downloadpath is not None:
            self._metadata.downloadpath = os.path.abspath(os.path.join(path, self._metadata.downloadpath))
            if self._metadata.downloadpath not in self._metadata.modulepath:
                LOGGER.warning("Downloadpath is not in module path! Module install will not work as expected")

            if not os.path.exists(self._metadata.downloadpath):
                os.mkdir(self._metadata.downloadpath)

        if venv_path is None:
            venv_path = os.path.join(path, ".env")
        else:
            venv_path = os.path.abspath(venv_path)
        self.virtualenv = env.VirtualEnv(venv_path)
        self.loaded = False
        self.modules: Dict[str, Module] = {}
        self.root_ns = Namespace("__root__")
        self.autostd = autostd

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

    def install_modules(self) -> None:
        """
        Installs all modules, both v1 and v2.
        """
        self.load_module_recursive(install=True)
        self.load()

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

    def get_module(self, full_module_name: str, install: bool = False, allow_v1: bool = False) -> "Module":
        """
        Get a module instance for a given module name. Caches modules by top level name for later access.

        :param full_module_name: The full name of the module. If this is a submodule, the corresponding top level module is
            used.
        :param install: Run in install mode, installing any modules that have not yet been installed, instead of only
            installing v1 modules.
        :param allow_v1: Allow this module to be loaded as v1.
        """
        parts = full_module_name.split("::")
        module_name = parts[0]

        if module_name in self.modules:
            return self.modules[module_name]
        return self.load_module(module_name, install=install, allow_v1=allow_v1)

    def load_module_recursive(self, install: bool = False) -> List[Tuple[str, List[Statement], BasicBlock]]:
        """
        Load a specific module and all submodules into this project.

        For each module, return a triple of name, statements, basicblock

        :param install: Run in install mode, installing modules that have not yet been installed, instead of only
            installing v1 modules.
        """
        ast_by_top_level_mod: Dict[str, List[Tuple[str, List[Statement], BasicBlock]]] = defaultdict(list)

        # get imports
        imports: Set[DefineImport] = {x for x in self.get_imports()}

        v2_modules: Set[str] = set()
        done: Dict[str, Dict[str, DefineImport]] = defaultdict(dict)

        def require_v2(module_name: str) -> None:
            """
            Promote a module to v2, requiring it to be loaded as v2.
            """
            if module_name in v2_modules:
                # already v2
                return
            v2_modules.add(module_name)
            if module_name in done and len(done[module_name]) > 0:
                # some submodules already loaded as v1 => reload
                imports.update(done[module_name].values())
                del done[module_name]
                del ast_by_top_level_mod[module_name]

        while len(imports) > 0:
            imp: DefineImport = imports.pop()
            ns: str = imp.name

            parts = ns.split("::")
            module_name: str = parts[0]
            v1_mode: bool = module_name not in v2_modules

            if ns in done[module_name]:
                continue

            try:
                # get module
                module: Module = self.get_module(module_name, install=install, allow_v1=v1_mode)
                # get NS
                for i in range(1, len(parts) + 1):
                    subs = "::".join(parts[0:i])
                    if subs in done[module_name]:
                        continue
                    (nstmt, nb) = module.get_ast(subs)

                    done[module_name][subs] = imp
                    ast_by_top_level_mod[module_name].append((subs, nstmt, nb))

                    # get imports and add to list
                    subs_imports: List[DefineImport] = module.get_imports(subs)
                    imports.update(subs_imports)
                    if not v1_mode:
                        # TODO: test this behavior!
                        for dep_module_name in (subs_imp.name.split("::")[0] for subs_imp in subs_imports):
                            require_v2(dep_module_name)
            except InvalidModuleException as e:
                raise ModuleNotFoundException(ns, imp, e)

        return list(chain.from_iterable(ast_by_top_level_mod.values()))

    def load_module(self, module_name: str, install: bool = False, allow_v1: bool = False) -> "Module":
        """
        Get a module instance for a given module name.

        :param module_name: The name of the module.
        :param install: Run in install mode, installing any modules that have not yet been installed, instead of only
            installing v1 modules.
        :param allow_v1: Allow this module to be loaded as v1.
        """
        reqs: Mapping[str, List[Requirement]] = self.collect_requirements()
        module_reqs: List[Requirement] = list(reqs[module_name]) if module_name in reqs else [Requirement.parse(module_name)]

        module: Optional[Module]
        try:
            module = self.module_source.get_module(self, module_reqs, install=install)
            if module is None and allow_v1:
                module = self.resolver_v1.get_module(self, module_reqs, install=True)
        except Exception as e:
            raise InvalidModuleException(f"Could not load module {module_name}") from e

        if module is None:
            raise CompilerException(
                f"Could not find module {module_name}. Please make sure to install it by running `inmanta project install`."
            )

        self.modules[module_name] = module
        return module

    def load_plugins(self) -> None:
        """
        Load all plug-ins
        """
        if not self.loaded:
            LOGGER.warning("loading plugins on project that has not been loaded completely")

        loader.configure_module_finder(self.modulepath)

        for module in self.modules.values():
            if isinstance(module, ModuleV1):
                module.load_plugins()

    def verify(self) -> None:
        # verify module dependencies
        result = True
        result &= self.verify_requires()
        if not result:
            raise CompilerException("Not all module dependencies have been met. Run `inmanta modules update` to resolve this.")

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

    def collect_requirements(self) -> "Dict[str, List[Requirement]]":
        """
        Collect the list of all requirements of all V1 modules in the project.
        """
        specs = {}  # type: Dict[str, List[Requirement]]
        merge_specs(specs, self.requires())
        for module in self.modules.values():
            if isinstance(module, ModuleV1):
                reqs = module.requires()
                merge_specs(specs, reqs)
        return specs

    def collect_imported_requirements(self) -> "Dict[str, List[Requirement]]":
        imports = set([x.name.split("::")[0] for x in self.get_complete_ast()[0] if isinstance(x, DefineImport)])
        imports.add("std")
        specs: Dict[str, List[Requirement]] = self.collect_requirements()

        def get_spec(name: str) -> "List[Requirement]":
            if name in specs:
                return specs[name]
            return [Requirement.parse(name)]

        return {name: get_spec(name) for name in imports}

    def verify_requires(self) -> bool:
        """
        Check if all the required modules for this module have been loaded
        """
        LOGGER.info("verifying project")
        imports = set([x.name for x in self.get_complete_ast()[0] if isinstance(x, DefineImport)])
        modules = self.modules

        good = True

        requirements: Dict[str, List[Requirement]] = self.collect_requirements()
        v2_requirements: Dict[str, List[Requirement]] = {
            name: spec for name, spec in requirements.items() if self.module_source.path_for(name) is not None
        }
        v1_requirements: Dict[str, List[Requirement]] = {
            name: spec for name, spec in requirements.items() if name not in v2_requirements
        }

        # TODO: for each ModuleV1 instance in self.modules, check that self.module_source.path_for(m) returns None.
        #   If it doesn't, this means the module was installed as v2 as an unintended side effect. The v1 code was loaded
        #   instead, but the plugin loader would load the v2 code, which presents an inconsistency. If this is the case, fail.

        for name, spec in v1_requirements.items():
            if name not in imports:
                continue
            module = modules[name]
            version = parse_version(str(module.version))
            for r in spec:
                if version not in r:
                    LOGGER.warning("requirement %s on module %s not fullfilled, now at version %s" % (r, name, version))
                    good = False

        good &= env.ProcessEnv.check(
            in_scope=re.compile(f"{ModuleV2.PKG_NAME_PREFIX}.*"),
            constraints=[Requirement.parse(f"{ModuleV2.PKG_NAME_PREFIX}{req}") for req in chain.from_iterable(v2_requirements.values())],
        )

        return good

    def collect_python_requirements(self) -> List[str]:
        """
        Collect the list of all python requirements off all V1 modules in this project
        """
        req_files = [
            x.strip()
            for x in [mod.get_python_requirements() for mod in self.modules.values() if isinstance(mod, ModuleV1)]
            if x is not None
        ]
        req_lines = [x for x in "\n".join(req_files).split("\n") if len(x.strip()) > 0]
        req_lines = self._remove_comments(req_lines)
        req_lines = self._remove_line_continuations(req_lines)
        return list(set(req_lines))

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


class DummyProject(Project):
    """ Placeholder project that does nothing """

    def __init__(self) -> None:
        super().__init__(tempfile.gettempdir())

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

        if self._metadata.name != os.path.basename(self._path):
            LOGGER.warning(
                "The name in the module file (%s) does not match the directory name (%s)",
                self._metadata.name,
                os.path.basename(self._path),
            )

        self._project: Optional[Project] = project
        self.is_versioned()

    @classmethod
    def get_module_dir(cls, module_subdirectory: str) -> str:
        """
        Find the top level module from the given subdirectory of a module.
        """
        try:
            return cls.get_first_directory_containing_file(module_subdirectory, cls.MODULE_FILE)
        except FileNotFoundError:
            raise InvalidModuleException(f"Directory {module_subdirectory} is not part of a valid {cls.GENERATION.name} module")

    def rewrite_version(self, new_version: str) -> None:
        new_version = str(new_version)  # make sure it is a string!
        with open(self.get_metadata_file_path(), "r", encoding="utf-8") as fd:
            module_def = fd.read()
        new_module_def, new_metadata = self.get_metadata_file_schema_type().rewrite_version(module_def, new_version)
        with open(self.get_metadata_file_path(), "w+", encoding="utf-8") as fd:
            fd.write(new_module_def)
        self._metadata = new_metadata

    def get_version(self) -> str:
        """
        Return the version of this module
        """
        return str(self._metadata.version)

    version = property(get_version)

    def is_versioned(self) -> bool:
        """
        Check if this module is versioned, and if so the version number in the module file should
        have a tag. If the version has + the current revision can be a child otherwise the current
        version should match the tag
        """
        if not os.path.exists(os.path.join(self._path, ".git")):
            LOGGER.warning(
                "Module %s is not version controlled, we recommend you do this as soon as possible.", self._metadata.name
            )
            return False
        return True

    def get_metadata_file_path(self) -> str:
        return os.path.join(self._path, self.MODULE_FILE)

    @lru_cache()
    def get_ast(self, name: str) -> Tuple[List[Statement], BasicBlock]:
        if self._project is None:
            raise ValueError("Can only get module's AST in the context of a project.")

        if name == self.name:
            file = os.path.join(self._path, self.MODEL_DIR, "_init.cf")
        else:
            parts = name.split("::")
            parts = parts[1:]
            if os.path.isdir(os.path.join(self._path, self.MODEL_DIR, *parts)):
                path_elements = [self._path, self.MODEL_DIR] + parts + ["_init.cf"]
            else:
                path_elements = [self._path, self.MODEL_DIR] + parts[:-1] + [parts[-1] + ".cf"]
            file = os.path.join(*path_elements)

        ns = self._project.get_root_namespace().get_ns_or_create(name)

        try:
            return self._load_file(ns, file)
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
                mainmod = self._project.get_module(impor, install=v1_mode, allow_v1=v1_mode)
                version = mainmod.version
                # track submodules for cycle avoidance
                out[impor] = mode + " " + version
                if recursive:
                    todo.extend([statement.name for statement in mainmod.get_imports(impor)])

        # drop submodules
        return {x: v for x, v in out.items() if "::" not in x}

    @lru_cache()
    def get_imports(self, name: str) -> List[DefineImport]:
        if self._project is None:
            raise ValueError("Can only get module's imports in the context of a project.")

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
        cur_dir = os.path.join(self._path, self.MODEL_DIR)
        files = self._get_model_files(cur_dir)

        for f in files:
            name = f[len(cur_dir) + 1 : -3]
            parts = name.split("/")
            if parts[-1] == "_init":
                parts = parts[:-1]

            parts.insert(0, self.name)
            name = "::".join(parts)

            modules.append(name)

        return modules

    def get_plugin_files(self) -> Iterator[Tuple[Path, ModuleName]]:
        """
        Returns a tuple (absolute_path, fq_mod_name) of all python files in this module.
        """
        plugin_dir: str = os.path.join(self._path, loader.PLUGIN_DIR)

        if not os.path.exists(plugin_dir):
            return iter(())

        if not os.path.exists(os.path.join(plugin_dir, "__init__.py")):
            raise CompilerException(
                "The plugin directory %s should be a valid python package with a __init__.py file" % plugin_dir
            )
        return (
            (
                Path(file_name),
                ModuleName(self._get_fq_mod_name_for_py_file(file_name, plugin_dir, self._metadata.name)),
            )
            for file_name in glob.iglob(os.path.join(plugin_dir, "**", "*.py"), recursive=True)
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
                    f"Unable to load all plug-ins for module {self._metadata.name}:"
                    f"\n\t{e.get_cause_type_name()} while loading plugin module {e.module}: {e.cause}"
                )
                exception.set_location(Location(e.path, e.lineno if e.lineno is not None else 0))
                raise exception

    # This method is not part of core's stable API but it is currently used by pytest-inmanta (inmanta/pytest-inmanta#76)
    def _get_fq_mod_name_for_py_file(self, py_file: str, plugin_dir: str, mod_name: str) -> str:
        """
        Returns the fully qualified Python module name for an inmanta module.

        :param py_file: The Python file for the module, relative to the plugin directory.
        :param plugin_dir: The plugin directory relative to the inmanta module's root directory.
        :param mod_name: The top-level name of this module.
        """
        rel_py_file = os.path.relpath(py_file, start=plugin_dir)
        return loader.PluginModuleLoader.convert_relative_path_to_module(os.path.join(mod_name, loader.PLUGIN_DIR, rel_py_file))

    def versions(self) -> List["Version"]:
        """
        Provide a list of all versions available in the repository
        """
        versions = gitprovider.get_all_tags(self._path)

        def try_parse(x: str) -> "Optional[Version]":
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
                print(f"Module {self._metadata.name} ({self._path})")
                for f in files:
                    print("\t%s" % f)

                print()
            else:
                print(f"Module {self._metadata.name} ({self._path}) has no changes")
        except Exception:
            print("Failed to get status of module")
            LOGGER.exception("Failed to get status of module %s")

    def push(self) -> None:
        """
        Run a git status on this module
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

    def execute_command(self, cmd: str) -> None:
        print("executing %s on %s in %s" % (cmd, self.name, self._path))
        print("=" * 10)
        subprocess.call(cmd, shell=True, cwd=self._path)
        print("=" * 10)


@stable_api
class ModuleV1(Module[ModuleV1Metadata]):
    MODULE_FILE = "module.yml"
    GENERATION = ModuleGeneration.V1

    def __init__(self, project: Optional[Project], path: str):
        try:
            super(ModuleV1, self).__init__(project, path)
        except InvalidMetadata as e:
            raise InvalidModuleException(f"The module found at {path} is not a valid V1 module") from e

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

    def get_all_requires(self) -> List[Requirement]:
        """
        :return: all modules required by an import from any sub-modules, with all constraints applied
        """
        # get all constraints
        spec: Dict[str, Requirement] = {req.project_name: req for req in self.requires()}
        # find all imports
        imports = {imp.name.split("::")[0] for subm in sorted(self.get_all_submodules()) for imp in self.get_imports(subm)}
        return [spec[r] if spec.get(r) else Requirement.parse(r) for r in imports]

    @classmethod
    def install(
        cls,
        project: Project,
        modulename: str,
        requirements: Iterable[Requirement],
        install: bool = True,
        install_mode: InstallMode = InstallMode.release,
    ) -> "ModuleV1":
        """
        Install a module, return module object
        """
        # verify presence in module path
        path = project.resolver_v1.path_for(modulename)
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
            result = project.external_resolver_v1.clone(modulename, project.downloadpath)
            if not result:
                raise InvalidModuleException("could not locate module with name: %s" % modulename)

        return cls.update(project, modulename, requirements, path, False, install_mode=install_mode)

    @classmethod
    def update(
        cls,
        project: Project,
        modulename: str,
        requirements: Iterable[Requirement],
        path: str = None,
        fetch: bool = True,
        install_mode: InstallMode = InstallMode.release,
    ) -> "ModuleV1":
        """
        Update a module, return module object
        """
        if path is None:
            mypath = project.resolver_v1.path_for(modulename)
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
        cls, modulename: str, requirements: Iterable[Requirement], path: str, release_only: bool = True
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
        comp_version = parse_version(comp_version_raw)
        return cls.__best_for_compiler_version(modulename, versions, path, comp_version)

    @classmethod
    def __best_for_compiler_version(
        cls, modulename: str, versions: "List[Version]", path: str, comp_version: "Version"
    ) -> "Optional[Version]":
        def get_cv_for(best: "Version") -> "Optional[Version]":
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
            requirements_lines = [y for y in [x.strip() for x in raw.split("\n")] if len(y) != 0]
            requirements_lines = self._remove_comments(requirements_lines)
            requirements_lines = self._remove_line_continuations(requirements_lines)
            return requirements_lines


@stable_api
class ModuleV2(Module[ModuleV2Metadata]):
    MODULE_FILE = "setup.cfg"
    GENERATION = ModuleGeneration.V2
    PKG_NAME_PREFIX = "inmanta-module-"

    def __init__(self, project: Optional[Project], path: str):
        try:
            super(ModuleV2, self).__init__(project, path)
        except InvalidMetadata as e:
            raise InvalidModuleException(f"The module found at {path} is not a valid V2 module") from e

    @classmethod
    def get_name_from_metadata(cls, metadata: ModuleV2Metadata) -> str:
        return metadata.name[len(cls.PKG_NAME_PREFIX) :]

    @classmethod
    def get_metadata_file_schema_type(cls) -> Type[ModuleV2Metadata]:
        return ModuleV2Metadata
