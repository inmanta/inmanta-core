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

from inmanta.ast import CompilerException, Location


class ParserException(CompilerException):

    def __init__(self, file, lnr, position, value, msg=None):
        CompilerException.__init__(self)
        self.set_location(Location(file, lnr))
        self.value = value
        self.position = position
        self.msg = msg

    def findCollumn(self, content):  # noqa: N802
        last_cr = content.rfind('\n', 0, self.position)
        if last_cr < 0:
            last_cr = 0
        self.column = (self.position - last_cr) + 1

    def __str__(self, *args, **kwargs):
        if self.msg is None:
            return "Syntax error at token %s (%s:%d)" % (self.value, self.location, self.column)
        else:
            return "Syntax error %s (%s:%d)" % (self.msg, self.location, self.column)
