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

from impera.ast.statements import DefinitionStatement, TypeDefinitionStatement
from impera.execute.util import Unset
from impera.execute.proxy import UnsetException
from impera.ast.variables import AttributeVariable, Variable
import impera.plugins.base
from impera.stats import Stats
from impera.ast.type import TYPES, BasicResolver, Type, NameSpacedResolver

from impera.ast.statements.define import DefineEntity, DefineImplement
from impera.compiler.main import Compiler
from impera.execute.runtime import Resolver, ExecutionContext, QueueScheduler, dumpHangs
from impera.ast.entity import Entity
from impera.plugins import PluginStatement
import time

DEBUG = True
LOGGER = logging.getLogger(__name__)

MAX_ITERATIONS = 500


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

    def freeze_all(self):
        instances = self.types["std::Entity"].get_all_instances()

        for i in instances:
            i.final()

    def dump(self, type="std::Entity"):
        instances = self.types[type].get_all_instances()

        for i in instances:
            i.dump()

    def verify_done(self):
        instances = self.types["std::Entity"].get_all_instances()
        notdone = []
        for i in instances:
            if not i.verify_done():
                notdone.append(i)

        return notdone

    def get_types(self):
        return self.types

    def get_scopes(self):
        return self.scopes

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

        types = {k: v for k, v in types_and_impl.items() if isinstance(v, Type) or isinstance(v, impera.plugins.base.Plugin)}
        compiler.plugins = {k: v for k, v in types.items() if isinstance(v, impera.plugins.base.Plugin)}

        resolver = NameSpacedResolver(types, None)

        for (n, t) in types.items():
            t.normalize(resolver)

        for block in blocks:
            block.normalize(resolver)

        self.types = types

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

    def run(self, compiler, statements, blocks):
        """
            Evaluate the current graph
        """
        prev = time.time()

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
        count = 0
        while i < MAX_ITERATIONS:
            now = time.time()

            # check if we can stop the execution
            if len(basequeue) == 0 and len(waitqueue) == 0 and len(zerowaiters) == 0:
                break
            else:
                i += 1

            LOGGER.debug("Iteration %d (e: %d, w: %d, p: %d, done: %d, time: %f)", i,
                         len(basequeue), len(waitqueue), len(zerowaiters), count, now - prev)
            prev = now
            # determine which of those can be evaluated, prefer generator and
            # reference statements over call statements
            while len(basequeue) > 0:
                next = basequeue.pop()
                try:
                    next.execute()
                    count = count + 1
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
                    LOGGER.debug("Moved zerowaiters to waiters")
                    waitqueue.pop(0).freeze()
                    progress = True

            if not progress:
                LOGGER.debug("Finishing statements with no waiters")
                while len(zerowaiters) > 0:
                    next = zerowaiters.pop()
                    next.freeze()

        if i == MAX_ITERATIONS:
            print("could not complete model")
            return False
        #now = time.time()
        #print(now - prev)
        # end evaluation loop
        # self.dump_not_done()
        #print(basequeue, waitqueue)
        # dumpHangs()
        # self.dump()
        # rint(len(self.types["std::Entity"].get_all_instances()))

        self.freeze_all()

        return True
