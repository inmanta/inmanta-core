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


class Statement(object):
    """
        An abstract baseclass representing a statement in the configuration policy.
    """
    def __init__(self):
        self.filename = "<>"
        self.line = -1
        self.namespace = None

    def copy_location(self, statement):
        """
            Copy the location of this statement in the given statement
        """
        statement.filename = self.filename
        statement.line = self.line

    def new_statements(self, _state):
        """
            Scheduled call to add new statements to the graph. This can be used
            to included statements that can only be determined after some
            requires have been resolved.
        """
        return 0

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


class DynamicStatement(Statement):
    """
        This class represents all statements that have dynamic properties.
        These are all statements that do not define typing.
    """
    def __init__(self):
        Statement.__init__(self)

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


class ReferenceStatement(DynamicStatement):
    """
        This class models statements that refere to somethings
    """
    def __init__(self):
        DynamicStatement.__init__(self)


class DefinitionStatement(Statement):
    """
        This statement defines a new entity in the configuration.
    """
    def __init__(self):
        Statement.__init__(self)


class CallStatement(DynamicStatement):
    """
        Base class for statements that call python code
    """
    def __init__(self):
        DynamicStatement.__init__(self)


class GeneratorStatement(DynamicStatement):
    """
        This statement models a statement that generates new statements
    """
    def __init__(self):
        DynamicStatement.__init__(self)
