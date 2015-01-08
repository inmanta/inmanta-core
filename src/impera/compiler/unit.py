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

    Contect: bart@impera.io
"""

import logging
from antlr3.exceptions import NoViableAltException, MismatchedTokenException

LOGGER = logging.getLogger()

# pylint: disable-msg=R0201,R0902


class CompileUnit(object):
    """
        This class represents a module containing configuration statements
    """
    def __init__(self, compiler, namespace):
        self._compiler = compiler
        self._namespace = namespace

    def compile(self):
        """
            Compile the configuration file for this compile unit
        """
        raise NotImplementedError()


class FileCompileUnit(CompileUnit):
    """
        A compile unit based on a parsed file.
    """
    def __init__(self, compiler, path, namespace):
        CompileUnit.__init__(self, compiler, namespace)
        self.__statements = {}
        self.__requires = {}
        self.__provides = {}
        self.__path = path
        self.__ast = None

    def compile(self):
        """
            Compile the configuration file for this compile unit
        """
        # compile the data
        parser = self._compiler.get_parser()

        try:
            self.__ast = parser.parse(self._namespace, self.__path)
        except NoViableAltException as exp:
            msg = str(exp) + " in file %s at line %d position %d" % (self.__path, exp.line, exp.charPositionInLine)
            raise Exception(msg)
        except MismatchedTokenException as exp:
            msg = str(exp) + " in file %s at line %d position %d" % (self.__path, exp.line, exp.charPositionInLine)
            raise Exception(msg)

        return self.__ast

    def is_compiled(self):
        """
            Is this already compiled?
        """
        return self.__ast is not None
