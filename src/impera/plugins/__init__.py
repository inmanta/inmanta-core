"""
    Copyright 2016 Inmanta

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

from impera.compiler.unit import CompileUnit
from impera.ast.statements import TypeDefinitionStatement
from . import base


class PluginStatement(TypeDefinitionStatement):
    """
        This statement defines a plugin function
    """
    def __init__(self, namespace, name, function_class):
        TypeDefinitionStatement.__init__(self, namespace, name)
        self._name = name
        self._function_class = function_class
        self.type = self._function_class(namespace)

    def __repr__(self):
        """
            The representation of this function
        """
        return "Function(%s)" % self._name

    def evaluate(self, resolver):
        """
            Evaluate this plugin
        """


class PluginCompileUnit(CompileUnit):
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
        for name, cls in base.PluginMeta.get_functions().items():
            ns_root = self._namespace.get_root()

            mod_ns = cls.__module__.split(".")
            if mod_ns[0] != "impera_plugins":
                raise Exception("All plugin modules should be loaded in the impera_plugins package")

            mod_ns = mod_ns[1:]

            ns = ns_root
            for part in mod_ns:
                if ns is None:
                    break
                ns = ns.get_child(part)

            if ns is None:
                raise Exception("Unable to find namespace for plugin module %s" % (cls.__module__))

            cls.namespace = ns

            name = name.split("::")[-1]
            statement = PluginStatement(ns, name, cls)
            statements.append(statement)

        return statements
