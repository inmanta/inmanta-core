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

from . import DuplicateScopeException, DuplicateVariableException, NotFoundException


class Scope(object):
    """
        This class defines a scope that is used during evaluation to keep
        all defined entities and values

        @param graph: The execution graph
        @param name: The name of this scope
    """
    def __init__(self, exe_graph, name):
        self.filename = "<>"
        self.line = -1

        self.parent = None
        self.__name = name

        self.__variables = {}
        self.__subscopes = {}

        self._graph = exe_graph

        self._placeholder = set()

        self.restrict_to_parent = False

    def is_root(self):
        """
            Is this scope a root scope?
        """
        return self.parent is None

    def set_parent(self, parent):
        """
            Add a parent scope to the end of the parent list
        """
        self.parent = parent

    def get_name(self):
        """
            Get the name of the scope
        """
        return self.__name

    name = property(get_name)

    def add_placeholder(self, name):
        """
            Add a placeholder to signal the scope that this variable will
            be added somewhere in the future. If a placeholder is set for a
            variable, get_variable always returns a notfoundexception
        """
        self._placeholder.add(name)

    def add_variable(self, name, variable):
        """
            Add an entity that is identified with a value to this scope. It
            will be accessible by all entities in a subscopes.
        """
        if name in self.__variables:
            raise DuplicateVariableException(
                "The variable %s is already defined" % (variable))

        if name in self._placeholder:
            self._placeholder.remove(name)

        self.__variables[name] = variable

    def has_variable(self, name):
        """
            Does this scope contain a variable with the given name. It does
            not search up.
        """
        return name in self.__variables

    def _get_variable(self, name):
        """
            Similar to get_variable but returns None instead of throwing an
            exception.
        """
        if self.has_variable(name):
            return self.__variables[name]

        if name in self._placeholder:
            return None

        if self.restrict_to_parent and self.parent is not None:
            if self.parent.has_variable(name):
                return Scope._get_variable(self.parent, name)

        elif self.parent is not None:
            var = Scope._get_variable(self.parent, name)
            if var is not None:
                return var

        return None

    def resolve_reference(self, reference):
        """
            Resolve the reference
        """
        if reference.namespace is not None and len(reference.namespace) > 0:
            return self.get_variable(reference.name, reference.namespace)
        return self.get_variable(reference.name)

    def get_variable(self, name, namespace=None):
        """
            Get the variable with the given name from this scope. If the
            variable does not exist in this scope search it in a parent scope.
        """
        if namespace is None:
            scope = self
        else:
            scope = self.get_scope(namespace)
            if scope is None:
                raise NotFoundException("Variable '%s' not found" % name)

        result = Scope._get_variable(scope, name)

        if result is None:
            raise NotFoundException("Variable '%s' not found" % name)

        return result

    def get_subscope(self, scope_name):
        """
            Get a subscope of this scope with the given id
        """
        return self.__subscopes[scope_name]

    def has_subscope(self, scope_name):
        """
            Is the scope with the given name already defined as a child of this
            scope.
        """
        return scope_name in self.__subscopes

    def add_subscope(self, scope):
        """
            Add a subscope of this scope
        """
        scope_name = scope.name

        if scope_name in self.__subscopes:
            raise DuplicateScopeException()

        self.__subscopes[scope_name] = scope

    def __repr__(self):
        """
            The represention of this scope.
        """
        return 'Scope(%s)' % self.name

    def path(self):
        """
            Return the scope path
        """
        if self.is_root():
            return [self.name]
        parent_path = self.parent.path()
        parent_path.append(self.name)
        return parent_path

    def get_root(self):
        """
            Get the root scope of this node.
        """
        if self.is_root():
            return self

        return self.parent.get_root()

    def get_scope(self, path):
        """
            Get the scope that is identified by the given path
        """
        root = self.get_root()

        scope = root
        for item in path:
            if scope.has_subscope(item):
                scope = scope.get_subscope(item)
            else:
                return None

        return scope

    def get_child_scopes(self):
        """
            Get a list of all child scopes
        """
        scopes = []
        scopes.append(self)
        for sub in self.__subscopes.values():
            scopes.extend(sub.get_child_scopes())

        return scopes

    def get_scopes(self):
        """
            Get a list of scopes
        """
        return self.__subscopes.values()

    def get_variables(self):
        """
            Return the variables of this scope and all subscopes
        """
        variables = list(self.__variables.values())

        for child in self.__subscopes.values():
            variables.extend(child.get_variables())

        return variables

    def available_variables(self):
        """
            Returns a list of all available variables
        """
        variables = list(self.__variables.values())

#         if self.parent is not None:
#             variables.extend(self.parent.available_variables())

        return variables

    def variables(self):
        """
            Get a list of variable values
        """
        return self.__variables.values()

    @classmethod
    def object_to_name(cls, obj):
        """
            This method transforms an object to a usable name to identify a
            scope.
        """
        return hex(id(obj))

    @classmethod
    def create_scope(cls, exe_graph, name, parent):
        """
            Create a scope that belongs to the given object and that
            has the given parents. Resolution is done based on the order of the
            parents in the parents list.
        """
        scope = Scope(exe_graph, name)
        scope.set_parent(parent)
        parent.add_subscope(scope)

        return scope

    @classmethod
    def get_or_create_scope(cls, exe_graph, path, restrict_to_parent=False):
        """
            Get a scope with the given path or create it if it does not exist.
        """
        scope = exe_graph.root_scope
        target = scope.get_scope(path)

        if target is None:
            parent = cls.get_or_create_scope(exe_graph, path[0:-1])
            target = cls.create_scope(exe_graph, path[-1], parent)

            target.restrict_to_parent = restrict_to_parent

        return target
