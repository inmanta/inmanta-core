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

    def __init__(self, location: Range, value, msg=None):
        CompilerException.__init__(self)
        self.set_location(location)
        self.value = value
        self.position = None
        self.msg = msg

    def findCollumn(self, content):  # noqa: N802
        pass

    def __str__(self, *args, **kwargs):
        if self.msg is None:
            return "Syntax error at token %s (%s)" % (self.value, self.location)
        else:
            return "Syntax error %s (%s)" % (self.msg, self.location)
