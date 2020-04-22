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
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

from inmanta.ast import CompilerException, Location, Range, ExplicitPluginException
from inmanta.parser import ParserException


class CompileData:
    def __init__(self) -> None:
        self.errors: List[CompilerException] = []

    def add_error(self, error: CompilerException) -> None:
        self.errors.append(error)

    def to_json(self) -> str:
        return ExportCompileData.from_compile_data(self).json()


class ExportCompileData(BaseModel):
    """
        Top level structure of compiler data to be exported.
    """

    errors: List["ExportError"]

    @classmethod
    def from_compile_data(cls, compile_data: CompileData) -> "ExportCompileData":
        return ExportCompileData(errors=[ExportError.from_exception(e) for e in compile_data.errors])


class ErrorType(str, Enum):
    plugin = "plugin_exception"
    parser = "parse_error"
    runtime = "runtime_error"


class ExportError(BaseModel):
    type: "ErrorType" = ErrorType.runtime
    message: str
    location: Optional["ExportLocation"] = None

    @classmethod
    def exception_type(cls, exception: CompilerException) -> "ErrorType":
        if isinstance(exception, ExplicitPluginException):
            return ErrorType.plugin
        if isinstance(exception, ParserException):
            return ErrorType.parser
        return ErrorType.runtime

    @classmethod
    def from_exception(cls, exception: CompilerException) -> "ExportError":
        location: Optional[Location] = exception.get_location()
        return ExportError(
            type=cls.exception_type(exception),
            message=exception.get_message(),
            location=ExportLocation.from_location(location) if location is not None else None,
        )


class ExportLocation(BaseModel):
    """
        Location in a file. Based on the LSP spec 3.15
    """

    uri: str
    range: "ExportRange"

    @classmethod
    def from_location(cls, location: Location) -> "ExportLocation":
        range_start: ExportPosition
        range_end: ExportPosition
        if isinstance(location, Range):
            # internal range is 1-based, LSP spec range is 0-based
            range_start = ExportPosition(line=location.lnr - 1, character=location.start_char - 1)
            range_end = ExportPosition(line=location.end_lnr - 1, character=location.end_char - 1)
        else:
            # whole line: range from line:0 to line+1:0
            range_start = ExportPosition(line=location.lnr - 1, character=0)
            range_end = ExportPosition(line=location.lnr, character=0)
        return ExportLocation(uri=location.file, range=ExportRange(start=range_start, end=range_end))


class ExportRange(BaseModel):
    """
        Range in a file. Based on the LSP spec 3.15
    """

    start: "ExportPosition"
    end: "ExportPosition"


class ExportPosition(BaseModel):
    """
        Position in a file. Based on the LSP spec 3.15
    """

    line: int
    character: int
