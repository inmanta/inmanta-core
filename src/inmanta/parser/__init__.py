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

from typing import Optional

import inmanta.ast.export as ast_export
from inmanta.ast import CompilerException, LocatableString, Location, Range
from inmanta.stable_api import stable_api
from inmanta.warnings import InmantaWarning


@stable_api
class ParserException(CompilerException):
    """Exception occurring during the parsing of the code"""

    def __init__(self, location: Location, value: object, msg: Optional[str] = None) -> None:
        if msg is None:
            msg = "Syntax error at token %s" % value
        else:
            msg = "Syntax error: %s" % msg
        CompilerException.__init__(self, msg)
        self.set_location(location)
        self.value = value

    def export(self) -> ast_export.Error:
        error: ast_export.Error = super().export()
        error.category = ast_export.ErrorCategory.parser
        return error


class ParserWarning(InmantaWarning, ParserException):
    """Warning occurring during the parsing of the code"""

    def __init__(self, location: Location, value: object, msg: str) -> None:
        InmantaWarning.__init__(self)
        ParserException.__init__(self, location, value, msg)
        # Override parent message since it's not an error
        self.msg = msg


class SyntaxDeprecationWarning(ParserWarning):
    """Deprecation warning occurring during the parsing of the code"""

    def __init__(self, location: Range, value: object, msg: str) -> None:
        ParserWarning.__init__(self, location, value, msg)


class InvalidNamespaceAccess(ParserException):
    """
    Exception raised when a namespace access is attempted with '.' rather than '::'.
    """

    def __init__(self, invalid: LocatableString) -> None:
        self.invalid: LocatableString = invalid
        super().__init__(
            location=invalid.location,
            value=str(invalid),
            msg=(
                f"invalid namespace access `{invalid}`. Namespaces should be accessed with '::' rather than '.'. "
                f"The '.' separator is reserved for attribute and relation access. Did you mean: `{self.suggest_replacement()}`"
            ),
        )

    def suggest_replacement(self) -> str:
        """
        Returns the suggested replacement to fix this error.
        """
        return str(self.invalid).replace(".", "::")
