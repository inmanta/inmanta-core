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

from . import CallStatement
from impera.ast.variables import Variable, LazyVariable
from impera.stats import Stats


class FunctionCall(CallStatement):
    """
        This class models a call to a function

        @param name: The name of the function that needs to be called
        @param arguments: A list of arguments

        uses:          args
        provides:      return value
        contributes:
    """
    def __init__(self, name, arguments):
        CallStatement.__init__(self)
        self.name = name
        self.arguments = arguments

    def references(self):
        """
            @see DynamicStatement#references
        """
        refs = []
        for i in range(len(self.arguments)):
            arg = self.arguments[i]
            refs.append(("arg %d" % i, arg))

        return refs

    def actions(self, state):
        """
            @see DynamicStatement#actions
        """
        result = state.get_result_reference()
        actions = [("set", result)]

        for i in range(len(self.arguments)):
            ref = state.get_ref("arg %d" % i)
            actions.append(("get", ref))

        return actions

    def types(self, recursive=False):
        """
            @see State#types
        """
        return [('function_%d' % id(self), self.name)]

    def __repr__(self):
        """
            The representation of this function call
        """
        return "Function(%s: %s)" % (self.name, ", ".join([repr(x) for x in self.arguments]))

    def get_argumentlist(self, state):
        """
            Return a list of arguments that can be passed to a function/method
            in python code
        """
        arguments = []
        for i in range(len(self.arguments)):
            variable = state.get_ref("arg %d" % i)
            value = variable.value

            if hasattr(value, "has_parameters") and not value.has_parameters():
                value = value()

            arguments.append(value)

        return arguments

    def evaluate(self, state, _local_scope):
        """
            Evaluate this statement.
        """
        # get the object to call the function on
        function = state.get_type("function_%d" % id(self))
        arguments = self.get_argumentlist(state)
        function.check_args(arguments)

        if function.opts["emits_statements"]:
            function(*arguments)
            Stats.get("function call").increment()
            new_statement = function.emit_statement()
            self.copy_location(new_statement)
            child_state = state.add_statement(new_statement)
            return child_state.get_result_reference()

        def lazy():
            result = function(*arguments)
            Stats.get("function call").increment()
            return result

        return_type = function.to_type(function._return)
        if return_type is None:
            lazy()
            return None

        return LazyVariable(lazy, return_type)


class Dummy(object):
    def __getattr__(self, name):
        return self


class ExpressionState(object):
    """
        Class emulates a state object to allow a statement to be used as a
        function with positional arguments
    """
    def __init__(self, state, expression, arguments, argument_map):
        self.state = state
        self.expression = expression
        self._map = argument_map
        self._arguments = []

        self._call_args = None

        self._register_variables(arguments)

    def _register_variables(self, arguments):
        """
            Register the argument variables
        """
        scope = self.state.get_local_scope()

        # first add the mapped values
        added = {}
        for name, value in self._map.items():
            index, ref = value

            var = Variable(Dummy())
            scope.add_variable(ref.name, var)
            added[index] = var

            self.state._refs[name] = var

        # check that we add all arguments
        for i in range(len(arguments)):
            if i in added:
                self._arguments.append(added[i])
            else:
                var = Variable(Dummy())
                scope.add_variable(arguments[i], var)
                self._arguments.append(var)

    def __getattr__(self, name):
        return getattr(self.state, name)

    def has_parameters(self):
        """
            Does this expression have any parameters?
        """
        return len(self._arguments) > 0

    def __call__(self, *args):
        self._call_args = args

        for index in range(len(args)):
            try:
                self._arguments[index].value = args[index]
            except Exception:
                # optional value?
                pass

        result = self.expression.evaluate(self, self.state.get_local_scope())
        self._call_args = None

        return result

    def __repr__(self):
        return "exp state: %s " % repr(self.expression)


class Expression(CallStatement):
    """
        Define a new expression

        @param expression: The expression
        @param arguments: A list of unbound arguments for this expression
    """
    def __init__(self, expression, arguments):
        CallStatement.__init__(self)
        self.expression = expression
        self.arguments = arguments

        if arguments is None:
            self.arguments = []

        self._argument_map = {}

    def __repr__(self):
        """
            The representation of this expression
        """
        return "Expression(%s)" % ", ".join([str(x) for x in self.arguments])

    def types(self, recursive=False):
        """
            @see State#types
        """
        if hasattr(self.expression, "types"):
            return self.expression.types()
        return []

    def _process_references(self, refs):
        """
            Process the given list of references
        """
        requires = []
        for name, ref in refs:
            if hasattr(ref, "name"):
                if ref.name in self.arguments and len(ref.namespace) == 0:
                    # keep the ref for us
                    self._argument_map[name] = (self.arguments.index(ref.name), ref)

                elif ref.name == "self":
                    # self is always an argument!
                    self._argument_map[name] = (len(self.arguments), ref)
                    self.arguments.append("self")

                else:
                    requires.append((name, ref))
            else:
                requires.append((name, ref))

        return requires

    def references(self):
        """
            @see DynamicStatement#references

            This expression needs references to all non-argument references
            of expression
        """
        refs = self.expression.references()
        req = self._process_references(refs)
        return req

    def new_statements(self, state):
        """
            Hack to register the expression variables -> we need the state  for this
        """
        exp_state = ExpressionState(state, self.expression, self.arguments, self._argument_map)
        state.set_attribute("exp", exp_state)

    def actions(self, state):
        """
            @see DynamicStatement#actions
        """
        return [("set", state.get_result_reference())]

    def evaluate(self, state, _local_scope):
        """
            Evaluate this statement.

            This actually defines a function
        """
        exp_state = state.get_attribute("exp")
        return exp_state
