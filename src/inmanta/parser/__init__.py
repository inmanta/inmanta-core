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

from inmanta.ast import CompilerException, Range


class ParserException(CompilerException):
    """Exception occurring during the parsing of the code"""

    def __init__(self, location: Range, value, msg=None):
        if msg is None:
            msg = "Syntax error at token %s" % value
        else:
            msg = "Syntax error %s" % msg
        CompilerException.__init__(self, msg)
        self.set_location(location)
        self.value = value
