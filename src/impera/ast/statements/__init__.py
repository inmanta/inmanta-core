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
from impera.execute.runtime import ResultVariable, ExecutionUnit

class Statement(object):
    """
        An abstract baseclass representing a statement in the configuration policy.
    """

    def __init__(self):
        self.location = None
        self.namespace = None

    def copy_location(self, statement):
        """
            Copy the location of this statement in the given statement
        """
        statement.location = self.location
        if hasattr(self, "filename"):
            statement.filename = self.filename
            statement.line = self.line

    def evaluate(self, state, scope):
        """
            Evaluate this statement.

            @param state: The object that contains all state of this statement
            @param scope: The scope that is connected to the namespace in which
                the evaluation is done.
        """

    def can_evaluate(self, state):
        """
            Can this statement be evaluated given 'state'. This method may not manipulate any state!
        """
        return True

    def types(self, recursive=False):
        """
            Return a list of tupples with the first element the name of how the
            type should be available and the second element the type.

            :param recursive: Recurse into embedded statement to retrieve all types
        """
        return []

    def get_containing_namespace(self,):
        return self.namespace


class DynamicStatement(Statement):
    """
        This class represents all statements that have dynamic properties.
        These are all statements that do not define typing.
    """

    def __init__(self):
        Statement.__init__(self)

    def normalize(self, resolver):
        raise Exception("Not Implemented" + str(type(self)))

    def requires(self):
        raise Exception("Not Implemented" + str(type(self)))

    def execute(self, requires, resolver, queue):
        raise Exception("Not Implemented" + str(type(self)))

    def references(self):
        """
            Return a list of tupples with as first element the name of make
            the reference result available and the second element the reference
            for which the value is required
        """
        return []

    def actions(self, state):
        """
            Returns which attributes it uses and which attributes it modifies.
            This method is called after resolved() == True

            (action, object, attribute)
        """
        return []


class ExpressionStatement(DynamicStatement):

    def __init__(self):
        DynamicStatement.__init__(self)

    def emit(self, resolver, queue):
        target = ResultVariable()
        target.set_provider(self)
        reqs = self.requires_emit(resolver, queue)
        ExecutionUnit(queue, resolver, target, reqs, self)

    def requires_emit(self, resolver, queue):
        """
            returns a dict of the result variables required, names are an opaque identifier
            may emit statements to break execution is smaller segements
        """
        raise "Not Implemented"


class AssignStatement(DynamicStatement):
    """
    This class models binary sts
    """

    def __init__(self, lhs, rhs):
        DynamicStatement.__init__(self)
        self.lhs = lhs
        self.rhs = rhs

    def normalize(self, resolver):
        self.rhs.normalize(resolver)


class BooleanExpression(DynamicStatement):
    """
    This class models expressions
    """

    def __init__(self):
        DynamicStatement.__init__(self)


class ReferenceStatement(ExpressionStatement):
    """
        This class models statements that refer to somethings
    """

    def __init__(self, children):
        ExpressionStatement.__init__(self)
        self.children = children

    def normalize(self, resolver):
        for c in self.children:
            c.normalize(resolver)

    def requires(self):
        return [req for v in self.children for req in v.requires()]

    def requires_emit(self, resolver, queue):
        return {rk: rv for i in self.children for (rk, rv) in i.requires_emit(resolver, queue).items()}


class DefinitionStatement(Statement):
    """
        This statement defines a new entity in the configuration.
    """

    def __init__(self):
        Statement.__init__(self)


class TypeDefinitionStatement(DefinitionStatement):

    def __init__(self, namespace, name):
        DefinitionStatement.__init__(self)
        self.name = name
        self.namespace = namespace
        self.fullName = namespace.get_full_name() + "::" + name

    def get_type(self):
        return (self.fullName, self.type)


class CallStatement(BooleanExpression):
    """
        Base class for statements that call python code
    """

    def __init__(self):
        BooleanExpression.__init__(self)


class GeneratorStatement(ExpressionStatement):
    """
        This statement models a statement that generates new statements
    """

    def __init__(self):
        ExpressionStatement.__init__(self)


class Literal(ExpressionStatement):

    def __init__(self, value):
        Statement.__init__(self)
        self.value = value

    def normalize(self, resolver):
        pass

    def __repr__(self):
        return repr(self.value)

    def requires(self):
        return []

    def requires_emit(self, resolver, queue):
        return {}

    def execute(self, requires, resolver, queue):
        return self.value
