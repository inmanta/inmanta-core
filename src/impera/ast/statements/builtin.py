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

from impera.compiler.unit import CompileUnit
from impera.ast.statements import DefinitionStatement
from impera.ast.type import TYPES
from impera.ast.variables import Variable


class DummyStatement(DefinitionStatement):
    """
        A dummy statement that adds the built-in types
    """
    def evaluate(self, scope, local_scope):
        """
            The scope to evaluate this statement in
        """
        for name, type_class in TYPES.items():
            local_scope.add_variable(name, Variable(type_class))

    def __repr__(self):
        """
            Representation
        """
        return "BuiltinTypes"


class BuiltinCompileUnit(CompileUnit):
    """
        A compile unit that contains all embeded types
    """
    def __init__(self, compiler, namespace):
        CompileUnit.__init__(self, compiler, namespace)

    def compile(self):
        """
            Compile the configuration file for this compile unit
        """
        statements = []

        # add built in types
        dummy = DummyStatement()
        dummy.namespace = self._namespace
        statements.append(dummy)

        return statements
