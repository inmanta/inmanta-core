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

import functools
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


@functools.total_ordering
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

    def __lt__(self, other: object) -> bool | None:
        if not isinstance(other, ModuleSourceMetadata):
            return NotImplemented
        return (self.name, self.hash_value, self.is_byte_code) < (other.name, other.hash_value, other.is_byte_code)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleSourceMetadata):
            return False
        return (self.name, self.hash_value, self.is_byte_code) == (other.name, other.hash_value, other.is_byte_code)

    def get_inmanta_module_name(self) -> str:
        return self.name.split(".")[1]


@functools.total_ordering
class ModuleSource(BaseModel):
    """
    This class represents a python module (file metadata + the source itself)
    :param source: the content of the file
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

    def __lt__(self, other: object) -> bool | None:
        if not isinstance(other, ModuleSource):
            return NotImplemented
        return self.metadata < other.metadata

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleSource):
            return False
        return self.metadata == other.metadata

    def get_inmanta_module_name(self) -> str:
        return self.metadata.get_inmanta_module_name()


type InmantaModuleName = str


type InmantaModuleVersion = str


class InmantaModule(BaseModel):
    """
    This class represents an Inmanta module during code upload.

    :param name: Name of this inmanta module. e.g. std
    :param version: Version of this inmanta module. This hash is computed using the hashes of
        the python files in this module as well as the python requirements of this module.
    :param files_in_module: The list of python files composing this inmanta module.
    :param requirements: The list of python requirements this inmanta module requires.
    :param for_agents: The list of agent names that require to install this inmanta module to
        deploy resources.
    """

    name: InmantaModuleName
    version: InmantaModuleVersion
    files_in_module: list[ModuleSourceMetadata]
    requirements: list[str]
    for_agents: list[AgentName]
