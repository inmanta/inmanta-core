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
from impera.execute.proxy import UnsetException, UnknownException
import impera.plugins.base
from impera.execute.util import Unknown
from impera.ast import RuntimeException


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
        no_unknows = function.check_args(arguments)

        if not no_unknows:
            result.set_value(Unknown(self))
            return

        if function._context is not -1:
            arguments.insert(function._context, impera.plugins.base.Context(resolver, queue, self, result))

        if function.opts["emits_statements"]:
            function(*arguments)
            Stats.get("function call").increment()
        else:
            try:
                value = function(*arguments)
                Stats.get("function call").increment()
                result.set_value(value)
            except UnknownException as e:
                result.set_value(e.unknown)


class FunctionUnit(Waiter):

    def __init__(self, queue_scheduler, resolver, result: ResultVariable, requires, function: FunctionCall):
        Waiter.__init__(self, queue_scheduler)
        self.result = result
        result.set_provider(self)
        self.requires = requires
        self.function = function
        self.resolver = resolver
        self.queue_scheduler = queue_scheduler
        for r in requires.values():
            self.await(r)
        self.ready(self)

    def execute(self):
        requires = {k: v.get_value() for (k, v) in self.requires.items()}
        try:
            self.function.resume(requires, self.resolver, self.queue_scheduler, self.result)
        except UnsetException as e:
            self.await(e.get_result_variable())
        except RuntimeException as e:
            e.set_statement(self.function)
            raise e

    def __repr__(self):
        return repr(self.function)
