"""
Copyright 2019 Inmanta

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

import hashlib
from typing import ClassVar

from pydantic import ConfigDict

from inmanta.dto.agent import AgentName
from inmanta.types import BaseModel as BaseModel


class Source(BaseModel):
    """Model for source code"""

    hash: str
    is_byte_code: bool
    module_name: str
    requirements: list[str]


class ModuleSourceMetadata(BaseModel):
    """
    This class holds metadata for a given python module. i.e. it doesn't contain
    the source itself.

    :param name: the fully qualified name of the python module. e.g. inmanta_plugins.model.x
    :param hash_value: hash of the underlying content
    :param is_byte_code: is this content python byte code or python source

    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    name: str
    hash_value: str
    is_byte_code: bool

    def sort_key(self) -> tuple[str, str, bool]:
        """Stable ordering key covering the full identity of this metadata."""
        return (self.name, self.hash_value, self.is_byte_code)

    def get_inmanta_module_name(self) -> str:
        return self.name.split(".")[1]


class ModuleSource(BaseModel):
    """
    This class represents a python module (file metadata + the source itself).

    :param metadata: metadata describing the python module (name, content hash, byte-code flag).
    :param source: the content of the file.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    metadata: ModuleSourceMetadata
    source: bytes

    @classmethod
    def from_path(cls, absolute_path: str, name: str) -> "ModuleSource":
        """Get the content of the file"""
        with open(absolute_path, "rb") as fd:
            _content = fd.read()

        sha1sum = hashlib.new("sha1")
        sha1sum.update(_content)
        _hash = sha1sum.hexdigest()

        return ModuleSource(
            metadata=ModuleSourceMetadata(
                name=name,
                is_byte_code=absolute_path.endswith(".pyc"),
                hash_value=_hash,
            ),
            source=_content,
        )

    def get_inmanta_module_name(self) -> str:
        return self.metadata.get_inmanta_module_name()

    def get_fq_module_name(self) -> str:
        return self.metadata.name


class ExecutorModuleSource(ModuleSource):
    """
    A ModuleSource destined for a specific executor, extended with the load semantics that describe
    what the executor should do with the source during agent code install.


    :param load_module: whether the source of this python module should be loaded during agent
        code install. This is true iff the encapsulating inmanta module was registered for that agent.


    load_module is part of this model's (pydantic structural) identity: the same file content
    can be loaded differently depending on the agent it is destined for, and an executor that ships these
    sources is identified by what it installs and loads, not only by the file contents.
    """

    load_module: bool

    def sort_key(self) -> tuple[tuple[str, str, bool], bool]:
        """Stable ordering key covering the full identity of this source."""
        return (self.metadata.sort_key(), self.load_module)


type InmantaModuleName = str


type InmantaModuleVersion = str


type LoadOnAgents = set[AgentName]


class InmantaModule(BaseModel):
    """
    This class represents an Inmanta module during code upload.

    :param name: Name of this inmanta module. e.g. std
    :param version: Version of this inmanta module. For editable install modules, this is a hash that is
        computed using the hashes of the python files in this module as well as the python requirements of this module.
        For packaged install modules, this is the plain pep 440 version to install e.g. "1.0.5".
    :param files_in_module: The list of python files composing this inmanta module if it is installed in editable mode
        in the compiler venv, or None if this module is installed as a package. The files of a package install module
        are not transported: the agent installs the module with pip and discovers its files in its venv.
    :param requirements: The list of python requirements this inmanta module requires. This list is only set for
        editable installed modules. It is None for package install modules, where we rely on pip to fetch the correct
        requirements for the given pep 440 version.
    :param load_module_on_agents: List of agents on which we will attempt to load this inmanta module. The agents on which
        the module is installed are derived from this list by the server: an editable install module is installed on every
        agent of the model version, because it can only reach an agent through its transported source, while a package
        install module is only installed on the agents that load it.
    :param editable_install: Whether this inmanta module was installed in editable mode in the compiler venv.
    """

    name: InmantaModuleName
    version: InmantaModuleVersion
    files_in_module: list[ModuleSourceMetadata] | None
    requirements: list[str] | None
    load_module_on_agents: list[AgentName]
    editable_install: bool
