"""
    Copyright 2017 Inmanta

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

import itertools
import logging
import os
import time
from collections import deque
from typing import Dict, List, Set, Tuple

from inmanta import plugins
from inmanta.ast import CompilerException, CycleExcpetion, Location, MultiException, RuntimeException
from inmanta.ast.entity import Entity
from inmanta.ast.statements import DefinitionStatement, TypeDefinitionStatement
from inmanta.ast.statements.define import DefineEntity, DefineImplement, DefineIndex, DefineRelation, DefineTypeDefault
from inmanta.ast.type import TYPES, Type
from inmanta.const import LOG_LEVEL_TRACE
from inmanta.execute.proxy import UnsetException
from inmanta.execute.runtime import ExecutionContext, ExecutionUnit, QueueScheduler, Resolver
from inmanta.execute.tracking import ModuleTracker

DEBUG = True
LOGGER = logging.getLogger(__name__)


MAX_ITERATIONS = 10000


class Scheduler(object):
    """
        This class schedules statements for execution
    """

    def __init__(self):
        pass

    def freeze_all(self, exns):
        for t in [t for t in self.types.values() if isinstance(t, Entity)]:
            t.final(exns)

        instances = self.types["std::Entity"].get_all_instances()

        for i in instances:
            i.final(exns)

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

    def sort_entities(self, entity_map: Dict[str, DefineEntity]) -> List[DefineEntity]:
        out: List[DefineEntity] = []
        loopstack: Set[str] = set()
        while len(entity_map) > 0:
            workon = next(iter(entity_map.keys()))
            self.do_sort_entities(entity_map, workon, out, loopstack)
        return out

    def do_sort_entities(
        self, entity_map: Dict[str, DefineEntity], name: str, acc: List[DefineEntity], loopstack: Set[str]
    ) -> None:
        nexte = entity_map[name]
        try:
            del entity_map[name]
            loopstack.add(name)
            for p in nexte.get_full_parent_names():
                if p in loopstack:
                    raise CycleExcpetion(nexte, p)
                if p in entity_map:
                    self.do_sort_entities(entity_map, p, acc, loopstack)
            loopstack.remove(name)
            acc.append(nexte)
        except CycleExcpetion as ce:
            ce.add(nexte)
            raise

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
        newtypes = [
            k for k in [t.register_types() for t in definitions if isinstance(t, TypeDefinitionStatement)] if k is not None
        ]

        for (name, type_symbol) in newtypes:
            types_and_impl[name] = type_symbol

        # now that we have objects for all types, populate them
        implements = [t for t in definitions if isinstance(t, DefineImplement)]
        others = [t for t in definitions if not isinstance(t, DefineImplement)]
        entities = {t.fullName: t for t in others if isinstance(t, DefineEntity)}
        typedefaults = [t for t in others if isinstance(t, DefineTypeDefault)]
        others = [t for t in others if not (isinstance(t, DefineEntity) or isinstance(t, DefineTypeDefault))]
        indices = [t for t in others if isinstance(t, DefineIndex)]
        others = [t for t in others if not isinstance(t, DefineIndex)]

        # first entities, so we have inheritance
        # parents first
        for d in self.sort_entities(entities):
            d.evaluate()

        for d in typedefaults:
            d.evaluate()

        for d in others:
            d.evaluate()

        # indices late, as they require all attributes
        for d in indices:
            d.evaluate()

        # lastly the implements, as they require implementations
        for d in implements:
            d.evaluate()

        types = {k: v for k, v in types_and_impl.items() if isinstance(v, Type) or isinstance(v, plugins.Plugin)}
        compiler.plugins = {k: v for k, v in types_and_impl.items() if isinstance(v, plugins.Plugin)}

        # give type info to all types, to normalize blocks inside them
        for t in types.values():
            t.normalize()

        # normalize root blocks
        for block in blocks:
            block.normalize()

        self.types = {k: v for k, v in types_and_impl.items() if isinstance(v, Type)}

    def anchormap(self, compiler, statements, blocks) -> List[Tuple[Location, Location]]:
        prev = time.time()

        # first evaluate all definitions, this should be done in one iteration
        self.define_types(compiler, statements, blocks)

        # relations are also in blocks
        statements = (s for s in statements if not isinstance(s, DefineRelation))
        anchors = (
            anchor
            for container in itertools.chain(statements, blocks)
            for anchor in container.get_anchors()
            if anchor is not None
        )

        rangetorange = [(anchor.get_location(), anchor.resolve()) for anchor in anchors]
        rangetorange = [(f, t) for f, t in rangetorange if t is not None]

        now = time.time()
        LOGGER.debug("Anchormap took %f seconds", now - prev)

        return rangetorange

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
        basequeue = deque()
        # queue for RV's that are delayed
        waitqueue = deque()
        # queue for RV's that are delayed and had no effective waiters when they were first in the waitqueue
        zerowaiters = deque()
        # queue containing everything, to find hanging statements
        all_statements = set()

        # Wrap in object to pass around
        queue = QueueScheduler(compiler, basequeue, waitqueue, self.types, all_statements)

        # emit all top level statements
        for block in blocks:
            block.context.emit(queue.for_tracker(ModuleTracker(block)))

        # start an evaluation loop
        i = 0
        count = 0
        max_iterations = int(os.getenv("INMANTA_MAX_ITERATIONS", MAX_ITERATIONS))
        while i < max_iterations:
            now = time.time()

            # check if we can stop the execution
            if len(basequeue) == 0 and len(waitqueue) == 0 and len(zerowaiters) == 0:
                break
            else:
                i += 1

            LOGGER.debug(
                "Iteration %d (e: %d, w: %d, p: %d, done: %d, time: %f)",
                i,
                len(basequeue),
                len(waitqueue),
                len(zerowaiters),
                count,
                now - prev,
            )
            prev = now

            # evaluate all that is ready
            while len(basequeue) > 0:
                next = basequeue.popleft()
                try:
                    next.execute()
                    all_statements.discard(next)
                    count = count + 1
                except UnsetException as e:
                    # some statements don't know all their dependencies up front,...
                    next.waitfor(e.get_result_variable())

            # all safe stmts are done
            progress = False

            # find a RV that has waiters, so freezing creates progress
            while len(waitqueue) > 0 and not progress:
                next = waitqueue.popleft()
                if next.hasValue:
                    # already froze itself
                    continue
                if next.get_progress_potential() == 0:
                    zerowaiters.append(next)
                elif next.get_waiting_providers() > 0:
                    # definitely not done
                    # drop from queue
                    # will requeue when value is added
                    next.unqueue()
                else:
                    # freeze it and go to next iteration, new statements will be on the basequeue
                    LOGGER.log(LOG_LEVEL_TRACE, "Freezing %s", next)
                    next.freeze()
                    progress = True

            # no waiters in waitqueue,...
            # see if any zerowaiters have become gotten waiters
            if not progress:
                waitqueue = deque(w for w in zerowaiters if w.get_progress_potential() != 0)
                queue.waitqueue = waitqueue
                zerowaiters = deque(w for w in zerowaiters if w.get_progress_potential() == 0)
                while len(waitqueue) > 0 and not progress:
                    LOGGER.debug("Moved zerowaiters to waiters")
                    next = waitqueue.popleft()
                    if next.get_waiting_providers() > 0:
                        next.unqueue()
                    else:
                        LOGGER.log(LOG_LEVEL_TRACE, "Freezing %s", next)
                        next.freeze()
                        progress = True

            # no one waiting anymore, all done, freeze and finish
            if not progress:
                LOGGER.debug("Finishing statements with no waiters")
                while len(zerowaiters) > 0:
                    next = zerowaiters.pop()
                    next.freeze()

        now = time.time()
        LOGGER.info(
            "Iteration %d (e: %d, w: %d, p: %d, done: %d, time: %f)",
            i,
            len(basequeue),
            len(waitqueue),
            len(zerowaiters),
            count,
            now - prev,
        )

        if i == max_iterations:
            raise CompilerException(f"Could not complete model, max_iterations {max_iterations} reached.")

        # now = time.time()
        # print(now - prev)
        # end evaluation loop
        # self.dump_not_done()
        # print(basequeue, waitqueue)
        # dumpHangs()
        # self.dump()
        # rint(len(self.types["std::Entity"].get_all_instances()))

        excns = []
        self.freeze_all(excns)

        if len(excns) == 0:
            pass
        elif len(excns) == 1:
            raise excns[0]
        else:
            raise MultiException(excns)

        if all_statements:
            stmt = None
            for st in all_statements:
                if isinstance(st, ExecutionUnit):
                    stmt = st
                    break

            raise RuntimeException(stmt.expression, "not all statements executed %s" % all_statements)
        # self.dump("std::File")

        return True
