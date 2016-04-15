"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""
from impera.ast import CompilerException, Location


class ParserException(CompilerException):

    def __init__(self, file, lnr, position, value):
        CompilerException.__init__(self)
        self.set_location(Location(file, lnr))
        self.value = value
        self.position = position

    def findCollumn(self, content):
        last_cr = content.rfind('\n', 0, self.position)
        if last_cr < 0:
            last_cr = 0
        self.column = (self.position - last_cr) + 1

    def __str__(self, *args, **kwargs):
        return "Syntax error: %s:%d, at token %s" % (self.location, self.column, self.value)
