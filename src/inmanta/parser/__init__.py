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
from inmanta.ast import CompilerException, Range
from inmanta.stable_api import stable_api
from inmanta.warnings import InmantaWarning


@stable_api
class ParserException(CompilerException):
    """Exception occurring during the parsing of the code"""

    def __init__(self, location: Range, value, msg: Optional[str] = None) -> None:
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

    def __init__(self, location: Range, value: object, msg: str) -> None:
        InmantaWarning.__init__(self)
        ParserException.__init__(self, location, value, msg)
        # Override parent message since it's not an error
        self.msg = msg


class SyntaxDeprecationWarning(ParserWarning):
    """Deprecation warning occurring during the parsing of the code"""

    def __init__(self, location: Range, value: object, msg: str) -> None:
        ParserWarning.__init__(self, location, value, msg)
