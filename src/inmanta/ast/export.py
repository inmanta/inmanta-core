"""
    Copyright 2020 Inmanta

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

from enum import Enum
from typing import Optional

import pydantic
from pydantic import BaseModel

from inmanta.stable_api import stable_api


# can't inherit from ABC because it breaks __slots__ of child classes in Python 3.6
class Exportable:
    # explicitly set empty slots so child classes are allowed to use __slots__
    __slots__ = ()

    def export(self) -> BaseModel:
        raise NotImplementedError()


@stable_api
class Position(BaseModel):
    """
    Position in a file. Based on the
    `LSP spec 3.15 <https://microsoft.github.io/language-server-protocol/specifications/specification-3-15/#position>`__
    """

    line: int
    character: int


@stable_api
class Range(BaseModel):
    """
    Range in a file. Based on the
    `LSP spec 3.15 <https://microsoft.github.io/language-server-protocol/specifications/specification-3-15/#range>`__
    """

    start: Position
    end: Position


@stable_api
class Location(BaseModel):
    """
    Location in a file. Based on the
    `LSP spec 3.15 <https://microsoft.github.io/language-server-protocol/specifications/specification-3-15/#location>`__
    """

    uri: str
    range: Range


@stable_api
class ErrorCategory(str, Enum):
    """
    Category of an error.
    """

    plugin = "plugin_exception"
    """
        A plugin explicitly raised an :py:class:`inmanta.plugins.PluginException`.
    """

    parser = "parse_error"
    """
        Error occurred while parsing.
    """

    runtime = "runtime_error"
    """
        Error occurred after parsing.
    """


@stable_api
class Error(BaseModel):
    """
    Error occurred while trying to compile.
    """

    category: ErrorCategory = ErrorCategory.runtime
    """
        Category of this error.
    """

    type: str
    """
        Fully qualified name of the actual exception.
    """

    message: str
    """
        Error message.
    """

    location: Optional[Location] = None
    """
        Location where this error occurred.
    """

    class Config:
        # allow additional fields to be set for exception types that require it
        extra = pydantic.Extra.allow
        validate_assignment = True
