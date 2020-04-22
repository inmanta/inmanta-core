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


# can't inherit from ABC because it breaks __slots__ of child classes in Python 3.6
class Exportable:
    # explicitly set empty slots so child classes are allowed to use __slots__
    __slots__ = ()

    def export(self) -> BaseModel:
        raise NotImplementedError()


class Position(BaseModel):
    """
        Position in a file. Based on the LSP spec 3.15
    """

    line: int
    character: int


class Range(BaseModel):
    """
        Range in a file. Based on the LSP spec 3.15
    """

    start: Position
    end: Position


class Location(BaseModel):
    """
        Location in a file. Based on the LSP spec 3.15
    """

    uri: str
    range: Range


class ErrorCategory(str, Enum):
    plugin = "plugin_exception"
    parser = "parse_error"
    runtime = "runtime_error"


class Error(BaseModel):
    category: ErrorCategory = ErrorCategory.runtime
    type: str  # str(type(exception))
    message: str
    location: Optional[Location] = None

    class Config:
        # allow additional fields to be set for exception types that require it
        extra = pydantic.Extra.allow
        validate_assignment = True
