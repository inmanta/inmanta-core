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

from impera.ast.statements import DefinitionStatement, CallStatement, TypeDefinitionStatement
from .state import State
from impera.execute.scope import Scope
from impera.execute.util import EntityType, Unset
from impera.execute.proxy import UnsetException
from impera.ast.variables import AttributeVariable, Variable
from impera.plugins.base import Context, Plugin
from impera.stats import Stats
from impera.ast.type import TYPES, BasicResolver, Type, NameSpacedResolver

from impera.ast.statements.define import DefineEntity, DefineImplement
from impera.compiler.main import Compiler
from impera.execute.runtime import Resolver, ExecutionContext, QueueScheduler, dumpHangs
from impera.ast.entity import Entity
from impera.plugins import PluginStatement

DEBUG = True
LOGGER = logging.getLogger(__name__)

MAX_ITERATIONS = 500


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

    def __init__(self):
        self._statement_count = 0

        self._statements = {}

        self._evaluation_queue = set()
        self._wait_queue = set()

        # a set of statements that we know that are problematic and that
        # need to stay in the queue as long as possible
        self._problem_list = {}

    def dump(self):
        instances = self.types["std::Entity"].get_all_instances()

        for i in instances:
            i.dump()

    def verify_done(self):
        instances = self.types["std::Entity"].get_all_instances()
        notdone = []
        for i in instances:
            if not i.verify_done():
                notdone.append(i)

        return notdone

    def dump_not_done(self):

        for i in self.verify_done():
            i.dump()

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

        raise Exception()

    def define_types(self, compiler: Compiler, statements, blocks):
        """
            This is the first compiler stage that defines all types_and_impl
        """
        # get all relevant stmts
        definitions = [d for d in statements if isinstance(d, DefinitionStatement)]
        others = [d for d in statements if not isinstance(d, DefinitionStatement)]

        if not len(others) == 0:
            raise Exception("others not empty %s" % repr(others))

        # collect all  types and impls
        types_and_impl = {}

        # primitive types
        for name, type_symbol in TYPES.items():
            types_and_impl[name] = type_symbol

        # all stmts contributing types and impls
        newtypes = [t.get_type() for t in definitions if isinstance(t, TypeDefinitionStatement)]

        for (name, type_symbol) in newtypes:
            types_and_impl[name] = type_symbol

        resolver = BasicResolver(types_and_impl)

        # now that we have objects for all types, popuate them
        implements = [t for t in definitions if isinstance(t, DefineImplement)]
        others = [t for t in definitions if not isinstance(t, DefineImplement)]
        entities = [t for t in others if isinstance(t, DefineEntity)]
        others = [t for t in others if not isinstance(t, DefineEntity)]

        # first entities, so we have inheritance
        for d in entities:
            d.evaluate(resolver)

        for d in others:
            d.evaluate(resolver)

        # lastly the implements, as they require implementations
        for d in implements:
            d.evaluate(resolver)

        types = {k: v for k, v in types_and_impl.items() if isinstance(v, Type) or isinstance(v, Plugin)}
        compiler.plugins = {k: v for k, v in types.items() if isinstance(v, Plugin)}

        resolver = NameSpacedResolver(types, None)

        for (n, t) in types.items():
            t.normalize(resolver)

        for block in blocks:
            block.normalize(resolver)

        self.types = types

    def show_error(self, msg: str, scope: Scope):
        """
            Print out an error and the filename and line where it occurs
        """
        sys.stderr.write(msg + " (%s:%d) [%s]\n" %
                         (scope.filename, scope.line, " > ".join(scope.path())))

    def print_unresolved(self, stmt: State):
        """
            If the given stmt is not resolved it will return a list of
            unresolved references.
        """
        if stmt.resolved():
            return []

        scope = stmt.get_local_scope()
        for ref in stmt._refs.values():
            if not ref.is_available(scope):
                if isinstance(ref, AttributeVariable):
                    if self._check_required(ref, scope):
                        continue

                self.show_error("\t%s not available in scope %s" % (ref, scope), scope)

    def _check_required(self, attr_var: AttributeVariable, scope: Scope):
        """
            Check if the given attribute of the instance in attr_var is required and not set, and therefore causing
            this error.
        """
        try:  # catch exceptions, because we are navigating parts of the model that might not have been resolved yet!
            instance = attr_var.instance.value
            entity = instance.__class__.__entity__
            attributes = entity.attributes
            attribute = attr_var.attribute

            if attribute not in attributes:
                self.show_error("\tEntity %s should have attributes %s" % (entity.get_full_name(), attribute), scope)
                return

            attr_obj = attributes[attribute]
            if attr_obj.low > 0:
                self.show_error("\tAttribute %s of entity %s should have a value." % (attribute, entity.get_full_name()), scope)
                return
        except Exception:
            pass

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

    def run(self, compiler, statements, blocks):
        """
            Evaluate the current graph
        """
        # first evaluate all definitions, this should be done in one iteration
        self.define_types(compiler, statements, blocks)

        self.scopes = {}
        rootresolver = Resolver(self.scopes)

        # add all other statements to the graph (create the initial model)
        for block in blocks:
            xc = ExecutionContext(block, rootresolver)
            self.scopes[block.namespace.get_full_name()] = xc
            block.context = xc

        # setup queues
        basequeue = []
        waitqueue = []
        zerowaiters = []
        queue = QueueScheduler(compiler, basequeue, waitqueue)

        for block in blocks:
            block.context.emit(queue)

        # start an evaluation loop
        i = 0
        while i < MAX_ITERATIONS:
            # check if we can stop the execution
            if len(basequeue) == 0 and len(waitqueue) == 0 and len(zerowaiters) == 0:
                break
            else:
                i += 1

            LOGGER.debug("Iteration %d (e: %d, w: %d, p: %d)", i,
                         len(self._evaluation_queue), len(self._wait_queue), len(self._problem_list))

            # determine which of those can be evaluated, prefer generator and
            # reference statements over call statements
            while len(basequeue) > 0:
                next = basequeue.pop()
                try:
                    next.execute()
                except UnsetException as e:
                    next.await(e.get_result_variable())

            progress = False

            while len(waitqueue) > 0 and not progress:
                next = waitqueue.pop(0)
                if len(next.waiters) == 0:
                    zerowaiters.append(next)
                else:
                    next.freeze()
                    progress = True

            if not progress:
                waitqueue = [w for w in zerowaiters if len(w.waiters) is not 0]
                zerowaiters = [w for w in zerowaiters if len(w.waiters) is 0]
                if(len(waitqueue) > 0):
                    waitqueue.pop(0).freeze()
                    progress = True

            if not progress:
                print("last resort:")
                while len(zerowaiters) > 0:
                    next = zerowaiters.pop()
                    next.freeze()

        # end evaluation loop
        self.dump_not_done()
        #print(basequeue, waitqueue)
        #dumpHangs()
        print(len(self.types["std::Entity"].get_all_instances()))
        return True
        
