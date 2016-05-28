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

import logging
import time

from impera.ast.statements import DefinitionStatement, TypeDefinitionStatement
from impera.execute.proxy import UnsetException
from impera import plugins
from impera.ast.type import TYPES, Type

from impera.ast.statements.define import DefineEntity, DefineImplement
from impera.execute.runtime import Resolver, ExecutionContext, QueueScheduler

DEBUG = True
LOGGER = logging.getLogger(__name__)

MAX_ITERATIONS = 500


class Scheduler(object):
    """
        This class schedules statements for execution
    """

    def __init__(self):
        pass

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

    def define_types(self, compiler, statements, blocks):
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

        # set primitive types
        compiler.get_ns().set_primitives(TYPES)

        # all stmts contributing types and impls
        newtypes = [k for k in [t.register_types()
                                for t in definitions if isinstance(t, TypeDefinitionStatement)] if k is not None]

        for (name, type_symbol) in newtypes:
            types_and_impl[name] = type_symbol

        # now that we have objects for all types, popuate them
        implements = [t for t in definitions if isinstance(t, DefineImplement)]
        others = [t for t in definitions if not isinstance(t, DefineImplement)]
        entities = [t for t in others if isinstance(t, DefineEntity)]
        others = [t for t in others if not isinstance(t, DefineEntity)]

        # first entities, so we have inheritance
        for d in entities:
            d.evaluate()

        for d in others:
            d.evaluate()

        # lastly the implements, as they require implementations
        for d in implements:
            d.evaluate()

        types = {k: v for k, v in types_and_impl.items() if isinstance(v, Type) or isinstance(v, plugins.Plugin)}
        compiler.plugins = {k: v for k, v in types.items() if isinstance(v, plugins.Plugin)}

        # give type info to all types, to normalize blocks inside them
        for t in types.values():
            t.normalize()

        # normalize other blocks
        for block in blocks:
            block.normalize()

        self.types = types

    def run(self, compiler, statements, blocks):
        """
            Evaluate the current graph
        """
        prev = time.time()

        # first evaluate all definitions, this should be done in one iteration
        self.define_types(compiler, statements, blocks)

        # give all loose blocks an empty XC
        # register the XC's as scopes
        # All named scopes are now present
        for block in blocks:
            res = Resolver(block.namespace)
            xc = ExecutionContext(block, res)
            block.context = xc
            block.namespace.scope = xc

        # setup queues
        # queue for runnable items
        basequeue = []
        # queue for RV's that are delayed
        waitqueue = []
        # queue for RV's that are delayed and had no waiters when they were first in the waitqueue
        zerowaiters = []
        # Wrap in object to pass around
        queue = QueueScheduler(compiler, basequeue, waitqueue, self.types)

        # emit all top level statements
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

            # evaluate all that is ready
            while len(basequeue) > 0:
                next = basequeue.pop()
                try:
                    next.execute()
                    count = count + 1
                except UnsetException as e:
                    next.await(e.get_result_variable())

            # all safe stmts are done
            progress = False

            # find a RV that is has waiters
            while len(waitqueue) > 0 and not progress:
                next = waitqueue.pop(0)
                if len(next.waiters) == 0:
                    zerowaiters.append(next)
                else:
                    # freeze it and go to next iteration, new statements will be on the basequeue
                    next.freeze()
                    progress = True

            # no waiters in waitqueue,...
            # see if any zerowaiters have become gotten waiters
            if not progress:
                waitqueue = [w for w in zerowaiters if len(w.waiters) is not 0]
                zerowaiters = [w for w in zerowaiters if len(w.waiters) is 0]
                if(len(waitqueue) > 0):
                    LOGGER.debug("Moved zerowaiters to waiters")
                    waitqueue.pop(0).freeze()
                    progress = True

            # no one waiting anymore, all done, freeze and finish
            if not progress:
                LOGGER.debug("Finishing statements with no waiters")
                while len(zerowaiters) > 0:
                    next = zerowaiters.pop()
                    next.freeze()

        now = time.time()
        LOGGER.debug("Iteration %d (e: %d, w: %d, p: %d, done: %d, time: %f)", i,
                     len(basequeue), len(waitqueue), len(zerowaiters), count, now - prev)

        if i == MAX_ITERATIONS:
            print("could not complete model")
            return False
        # now = time.time()
        # print(now - prev)
        # end evaluation loop
        # self.dump_not_done()
        # print(basequeue, waitqueue)
        # dumpHangs()
        # self.dump()
        # rint(len(self.types["std::Entity"].get_all_instances()))

        self.freeze_all()

        return True
