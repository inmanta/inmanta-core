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

import logging
import sys
import traceback
import inspect

from impera.ast.statements import DefinitionStatement, CallStatement, DynamicStatement
from .state import State, DynamicState
from impera.execute.scope import Scope
from impera.execute.util import EntityType, Unset
from impera.execute.proxy import UnsetException
from impera.ast.variables import AttributeVariable, Variable
from impera.plugins.base import Context
from impera.stats import Stats

DEBUG = True
LOGGER = logging.getLogger(__name__)

MAX_ITERATIONS = 50


class CallbackHandler(object):
    """
        This class registers and handles callbacks
    """
    _callbacks = {}

    @classmethod
    def schedule_callback(cls, when, callback):
        """
            Schedule a callback
        """
        if when not in cls._callbacks:
            cls._callbacks[when] = []

        cls._callbacks[when].append(callback)

    @classmethod
    def _call(cls, func, context):
        """
            Call the given function
        """
        arg_spec = inspect.getfullargspec(func)

        arg_len = len(arg_spec.args)
        if arg_len > 1:
            raise Exception("Callback function can only have a context parameter")

        if arg_len == 0 or arg_spec.args[0] == "self":
            func()
        else:
            func(context)

    @classmethod
    def run_callbacks(cls, when, context):
        """
            Run callbacks for when
        """
        if when in cls._callbacks:
            for callback in cls._callbacks[when]:
                cls._call(callback, context)


class Scheduler(object):
    """
        This class schedules statements for execution
    """
    def __init__(self, graph):
        self._statement_count = 0
        self._graph = graph
        self._graph.root_scope = Scope(self._graph, "__root__")

        self._statements = {}

        self._evaluation_queue = set()
        self._wait_queue = set()

        # a set of statements that we know that are problematic and that
        # need to stay in the queue as long as possible
        self._problem_list = {}

    def _evaluate_statement_list(self):
        """
            Evaluate the given list of statements. This method will return
            if a new statement is generated during evaluation or when there
            is no progress during the evaluation.

            Returns false when not all statements have been evaluated
        """
        previous = -1
        current = 0

        while previous < current:
            previous = current

            for state in list(self._evaluation_queue):
                if state.can_evaluate() and self.evaluate_statement(state):
                    self._evaluation_queue.remove(state)
                    current += 1

            self._sort_statements()

        if len(self._evaluation_queue) > 0:
            return False

        return True

    def evaluate_statement(self, statement):
        """
            Evaluate the given statement
        """
        try:
            statement.evaluate()

            return True
        except UnsetException as exception:
            # This statement tried to access an attribute that was not set. Add
            # a "get" action for this variable.
            attr_var = AttributeVariable.create(Variable(exception.instance),
                                                exception.attribute)
            self._graph.add_actions(statement, [("get", attr_var)])
            Stats.get("backtrack").increment()
        except Exception as exception:
            self.show_exception(statement, exception)

        return False

    def show_exception(self, statement, message):
        """
            Print out the given exception
        """
        if DEBUG and not isinstance(message, str):
            print("Exception while evaluation %s" % statement)
            exec_name, _exec_args, exec_tb = self.format_exception_info()
            print(exec_name)
            print("".join(exec_tb))

        sys.stderr.write("%s\n" % message)
        sys.stderr.write("  at %s:%d\n" % (statement.statement.filename, statement.statement.line))

        sys.exit(1)

    def define_types(self, compiler, statements):
        """
            This is the first compiler stage that defines all types
        """
        definition_count = 0
        for stmt in statements:
            if isinstance(stmt, DefinitionStatement):
                state = State(compiler, stmt.namespace, stmt)
                state.add_to_graph(self._graph)
                definition_count += 1

                self._evaluation_queue.add(state)

        LOGGER.debug("Added %d definition statements." % definition_count)

        # TODO(err reporting) add error reporting here
        if not self._evaluate_statement_list():
            for state in self._evaluation_queue:
                if not state.evaluated:
                    print(state)

            raise Exception("Unable to define all types")

        # now query the graph again for statements that cannot resolve
        for state in self._graph.get_statements():
            if isinstance(stmt, DefinitionStatement) and not state.evaluated:
                local_scope = state.get_local_scope()

                for _name, type_ref in state._required_types.items():
                    if not type_ref.is_available(local_scope):
                        self.show_exception(state, "Unable to resolve %s" % type_ref)

        # call scheduled callbacks for 'after_types'
        ctx = Context(self._graph, self._graph.root_scope, None, None)
        CallbackHandler.run_callbacks("after_types", ctx)

    def print_unresolved(self, stmt):
        """
            If the given stmt is not resolved it will return a list of
            unresolved references.
        """
        if stmt.resolved():
            return []

        scope = stmt.get_local_scope()
        for ref in stmt._refs.values():
            if not ref.is_available(scope):
                sys.stderr.write("\t%s not available in scope %s (%s:%d) [%s]\n" %
                                 (ref, scope, scope.filename, scope.line, " > ".join(scope.path())))

    def check_unset_attributes(self, obj):
        """
            Check if any attributes of obj are unset
        """
        cls_def = obj.__class__.__definition__
        attributes = cls_def.get_all_attribute_names()

        for attr in attributes:
            value = getattr(obj, attr)

            if isinstance(value, Unset):
                self.show_exception(obj.__statement__, "Attribute '%s' of object %s is not set." % (attr, obj))

    def check_unset(self):
        """
            Check if attributes are left un-set
        """
        for sub_scope in self._graph.root_scope.get_child_scopes():
            for var in sub_scope.variables():
                if var.is_available(sub_scope):
                    value = var.value

                    if isinstance(value, EntityType):
                        self.check_unset_attributes(value)

    def format_exception_info(self, max_tb_level=100):
        """
            Get information about the last exception
        """
        cla, exc, trbk = sys.exc_info()
        exec_name = cla.__name__

        try:
            exec_args = exc.__dict__["args"]
        except KeyError:
            exec_args = "<no args>"

        exec_tb = traceback.format_tb(trbk, max_tb_level)

        return (exec_name, exec_args, exec_tb)

    def _sort_statements(self):
        """
            This method sorts all statements in the graph into an evaluation
            queue and a wait queue
        """
        self._evaluation_queue = set()

        for state in self._graph.get_statements():
            try:
                if state.evaluated or state in self._evaluation_queue or state in self._wait_queue:
                    pass

                elif state.resolved():
                    # lists are hard to schedule correctly, so make them a
                    # special waiting case
                    if self._graph.uses_list(state):
                        self._problem_list[state] = -1
                        self._wait_queue.add(state)

                    elif isinstance(state.statement, CallStatement):
                        self._wait_queue.add(state)

                    else:
                        self._evaluation_queue.add(state)

            except Exception as exception:
                self.show_exception(state, exception)

    def run(self, compiler, statements):
        """
            Evaluate the current graph
        """
        # first evaluate all definitions, this should be done in one iteration
        self.define_types(compiler, statements)

        # add all other statements to the graph (create the initial model)
        for stmt in statements:
            if isinstance(stmt, DynamicStatement):
                state = DynamicState(compiler, stmt.namespace, stmt)
                state.add_to_graph(self._graph)

        # start an evaluation loop
        i = 0
        while i < MAX_ITERATIONS:
            self._sort_statements()

            # check if we can stop the execution
            if len(self._evaluation_queue) == 0 and len(self._wait_queue) == 0:
                break
            else:
                i += 1

            LOGGER.debug("Iteration %d (e: %d, w: %d, p: %d)", i,
                         len(self._evaluation_queue), len(self._wait_queue), len(self._problem_list))

            # determine which of those can be evaluated, prefer generator and
            # reference statements over call statements
            result = False
            if len(self._evaluation_queue) > 0:
                LOGGER.debug("  Evaluating normal queue")
                result = self._evaluate_statement_list()

            # not everything was evaluated -> try all statements now
            if not result:
                LOGGER.debug("  Evaluating waiting queue")

                # move statements from the waiting queue. Only move statements
                # that use a list when all of them use a list.
                current_len = len(self._evaluation_queue)

                for statement in self._wait_queue.copy():
                    if statement not in self._problem_list:
                        self._evaluation_queue.add(statement)
                        self._wait_queue.remove(statement)

                    else:
                        if self._problem_list[statement] < 0:
                            self._problem_list[statement] = i

                if len(self._evaluation_queue) == current_len and len(self._problem_list) > 0:
                    # add the oldest statements from the waiting queue to
                    # the evaluation queue. All statements in this queue are
                    # now statements that we want to postpone as long as
                    # possible.
                    values = sorted(list(self._problem_list.values()))
                    evaluate_value = values[0]

                    LOGGER.debug("  Using problem statements of generation %d", evaluate_value)

                    for stmt in list(self._problem_list.keys()):
                        if self._problem_list[stmt] == evaluate_value:
                            self._evaluation_queue.add(stmt)
                            self._wait_queue.remove(stmt)
                            del self._problem_list[stmt]

                self._evaluate_statement_list()

            self._graph.process_un_compared()
        # end evaluation loop

        # call post hook
        ctx = Context(self._graph, self._graph.root_scope, None, None)
        CallbackHandler.run_callbacks("post", ctx)

        result = True
        for state in self._graph.get_statements():
            if not state.evaluated:
                sys.stderr.write("Unable to evaluate %s at %s:%d\n" %
                                 (state, state.statement.filename, state.statement.line))
                self.print_unresolved(state)
                result = False

        # check if all values are set
        if result:
            self.check_unset()
            ctx = Context(self._graph, self._graph.root_scope, None, None)
            CallbackHandler.run_callbacks("verify", ctx)

        return result
