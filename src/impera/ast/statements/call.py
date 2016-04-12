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

from impera.stats import Stats
from impera.ast.statements import ReferenceStatement
from impera.execute.runtime import ResultVariable, Waiter
from impera.execute.proxy import UnsetException
import impera.plugins.base


class FunctionCall(ReferenceStatement):
    """
        This class models a call to a function

        @param name: The name of the function that needs to be called
        @param arguments: A list of arguments

        uses:          args
        provides:      return value
        contributes:
    """

    def __init__(self, name, arguments):
        ReferenceStatement.__init__(self, arguments)
        self.name = name
        self.arguments = arguments

    def normalize(self, resolver):
        ReferenceStatement.normalize(self, resolver)
        self.function = resolver.get_type(self.name)

    def requires_emit(self, resolver, queue):
        sub = ReferenceStatement.requires_emit(self, resolver, queue)
        # add lazy vars
        temp = ResultVariable()
        temp.set_provider(self)
        FunctionUnit(queue, resolver, temp, sub, self)
        return {self: temp}

    def execute(self, requires, resolver, queue):
        return requires[self]

    def resume(self, requires, resolver, queue, result):
        """
            Evaluate this statement.
        """
        # get the object to call the function on
        function = self.function
        arguments = [a.execute(requires, resolver, queue) for a in self.arguments]
        function.check_args(arguments)

        if function._context is not -1:
            arguments.insert(function._context,  impera.plugins.base.Context(resolver, queue, self, result))

        if function.opts["emits_statements"]:

            function(*arguments)
            Stats.get("function call").increment()
        else:
            value = function(*arguments)
            Stats.get("function call").increment()
            result.set_value(value)


class Dummy(object):

    def __getattr__(self, name):
        return self


class FunctionUnit(Waiter):

    def __init__(self, queue_scheduler, resolver, result: ResultVariable, requires, function: FunctionCall):
        Waiter.__init__(self, queue_scheduler)
        self.result = result
        result.set_provider(self)
        self.requires = requires
        self.function = function
        self.resolver = resolver
        self.queue_scheduler = queue_scheduler
        for (s, r) in requires.items():
            self.await(r)
        self.ready(self)

    def execute(self):
        requires = {k: v.get_value() for (k, v) in self.requires.items()}
        try:
            self.function.resume(requires, self.resolver, self.queue_scheduler, self.result)
        except UnsetException as e:
            #print("exc " + str(self.function.name) )
            self.await(e.get_result_variable())

    def __repr__(self):
        return repr(self.function)


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