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
from typing import TYPE_CHECKING, Any, Deque, Dict, Iterator, List, Sequence, Set, Tuple

from inmanta import plugins
from inmanta.ast import Anchor, CompilerException, CycleExcpetion, Location, MultiException, RuntimeException
from inmanta.ast.entity import Entity
from inmanta.ast.statements import DefinitionStatement, TypeDefinitionStatement
from inmanta.ast.statements.define import (
    DefineEntity,
    DefineImplement,
    DefineIndex,
    DefineRelation,
    DefineTypeConstraint,
    DefineTypeDefault,
)
from inmanta.ast.type import TYPES, Type
from inmanta.const import LOG_LEVEL_TRACE
from inmanta.execute.proxy import UnsetException
from inmanta.execute.runtime import (
    DelayedResultVariable,
    ExecutionContext,
    ExecutionUnit,
    Instance,
    QueueScheduler,
    Resolver,
    Waiter,
)
from inmanta.execute.tracking import ModuleTracker

if TYPE_CHECKING:
    from inmanta.ast import BasicBlock, NamedType, Statement  # noqa: F401
    from inmanta.compiler import Compiler  # noqa: F401


DEBUG = True
LOGGER = logging.getLogger(__name__)


MAX_ITERATIONS = 10000


class Scheduler(object):
    """
    This class schedules statements for execution
    """

    def __init__(self, track_dataflow: bool = False):
        self.track_dataflow: bool = track_dataflow
        self.types: Dict[str, Type] = {}

    def freeze_all(self, exns: List[CompilerException]) -> None:
        for t in [t for t in self.types.values() if isinstance(t, Entity)]:
            t.final(exns)

        instances: List[Instance] = self.types["std::Entity"].get_all_instances()

        for i in instances:
            i.final(exns)

    def dump(self, type: str = "std::Entity") -> None:
        instances: List[Instance] = self.types[type].get_all_instances()

        for i in instances:
            i.dump()

    def verify_done(self) -> List[Instance]:
        instances: List[Instance] = self.types["std::Entity"].get_all_instances()
        notdone = []
        for i in instances:
            if not i.verify_done():
                notdone.append(i)

        return notdone

    def get_types(self) -> Dict[str, Type]:
        return self.types

    def dump_not_done(self) -> None:
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

    def define_types(self, compiler: "Compiler", statements: Sequence["Statement"], blocks: Sequence["BasicBlock"]) -> None:
        """
        This is the first compiler stage that defines all types_and_impl
        """
        # get all relevant stmts
        definitions: List["DefinitionStatement"] = [d for d in statements if isinstance(d, DefinitionStatement)]
        others: List["Statement"] = [d for d in statements if not isinstance(d, DefinitionStatement)]

        if not len(others) == 0:
            raise Exception("others not empty %s" % repr(others))

        # collect all  types and impls
        types_and_impl = {}

        # set primitive types
        compiler.get_ns().set_primitives(TYPES)

        # all stmts contributing types and impls
        newtypes: List[Tuple[str, NamedType]] = [
            k for k in [t.register_types() for t in definitions if isinstance(t, TypeDefinitionStatement)] if k is not None
        ]

        for (name, type_symbol) in newtypes:
            types_and_impl[name] = type_symbol

        # now that we have objects for all types, populate them
        implements = [t for t in definitions if isinstance(t, DefineImplement)]
        other_definitions = [t for t in definitions if not isinstance(t, DefineImplement)]
        entities: Dict[str, DefineEntity] = {t.fullName: t for t in other_definitions if isinstance(t, DefineEntity)}
        type_constraints = [t for t in other_definitions if isinstance(t, DefineTypeConstraint)]
        typedefaults = [t for t in other_definitions if isinstance(t, DefineTypeDefault)]
        other_definitions = [
            t for t in other_definitions if not isinstance(t, (DefineEntity, DefineTypeDefault, DefineTypeConstraint))
        ]
        indices = [t for t in other_definitions if isinstance(t, DefineIndex)]
        other_definitions = [t for t in other_definitions if not isinstance(t, DefineIndex)]

        # first type constraints so attribute defaults can be type checked
        for tc in type_constraints:
            tc.evaluate()

        # then entities, so we have inheritance
        # parents first
        for entity in self.sort_entities(entities):
            entity.evaluate()

        for typedefault in typedefaults:
            typedefault.evaluate()

        for other in other_definitions:
            other.evaluate()

        # indices late, as they require all attributes
        for index in indices:
            index.evaluate()

        # lastly the implements, as they require implementations
        for implement in implements:
            implement.evaluate()

        compiler.plugins = {k: v for k, v in types_and_impl.items() if isinstance(v, plugins.Plugin)}
        types = {k: v for k, v in types_and_impl.items() if isinstance(v, Type)}

        # normalize plugins
        for p in compiler.plugins.values():
            p.normalize()

        # give type info to all types, to normalize blocks inside them
        for t in types.values():
            t.normalize()

        # normalize root blocks
        for block in blocks:
            block.normalize()

        self.types = {k: v for k, v in types_and_impl.items() if isinstance(v, Type)}

    def anchormap(
        self, compiler: "Compiler", statements: Sequence["Statement"], blocks: Sequence["BasicBlock"]
    ) -> Sequence[Tuple[Location, Location]]:
        prev = time.time()

        # first evaluate all definitions, this should be done in one iteration
        self.define_types(compiler, statements, blocks)

        # relations are also in blocks
        not_relation_statements: Iterator[Statement] = (s for s in statements if not isinstance(s, DefineRelation))

        anchors: Iterator[Anchor] = (
            anchor
            for container in itertools.chain(not_relation_statements, blocks)  # container: Union[Statement, BasicBlock]
            for anchor in container.get_anchors()
            if anchor is not None
        )

        rangetorange = [(anchor.get_location(), anchor.resolve()) for anchor in anchors]
        rangetorange = [(f, t) for f, t in rangetorange if t is not None]

        now = time.time()
        LOGGER.debug("Anchormap took %f seconds", now - prev)

        return rangetorange

    def find_wait_cycle(self, allwaiters: Set[Waiter]) -> bool:
        """
        Preconditions: no progress is made anymore

        This means that all DelayedResultVariable that have not been frozen either have
        no progress potential or have outstanding promises.
        In this case, all gradual execution has been executed to the maximal extent.

        Any DelayedResultVariable that still has progress potential has at least one waiter that doesn't support gradual
        execution (e.g. a plugin).
        If it takes input from another DelayedResultVariables, it will still have this promise outstanding.

        The compiler will not freeze the DelayedResultVariable with progress potential because it has an outstanding promise.
        The compiler will not freeze the other because it has no progress potential.

        This causes the compiler to be stuck.

        The root cause is that progress potential is only calculated locally.

        For performance reasons, we keep progress potential local and instead detect this situation here.
        """
        for waiter in allwaiters:
            for rv in waiter.requires.values():
                if isinstance(rv, DelayedResultVariable):
                    if rv.hasValue:
                        # get_progress_potential fails when there is a value already
                        continue
                    if rv.get_waiting_providers() > 0 and rv.get_progress_potential() > 0:
                        LOGGER.debug("Waiting blocked on %s", rv)
                        rv.freeze()
                        return True
        return False

    def run(self, compiler: "Compiler", statements: Sequence["Statement"], blocks: Sequence["BasicBlock"]) -> bool:
        """
        Evaluate the current graph
        """
        prev = time.time()
        start = prev

        # first evaluate all definitions, this should be done in one iteration
        self.define_types(compiler, statements, blocks)

        # give all loose blocks an empty XC
        # register the XC's as scopes
        # All named scopes are now present

        for block in blocks:
            res = Resolver(block.namespace, self.track_dataflow)
            xc = ExecutionContext(block, res)
            block.context = xc
            block.namespace.scope = xc
            block.warn_shadowed_variables()

        # setup queues
        # queue for runnable items
        basequeue: Deque[Waiter] = deque()
        # queue for RV's that are delayed
        waitqueue: Deque[DelayedResultVariable[Any]] = deque()
        # queue for RV's that are delayed and had no effective waiters when they were first in the waitqueue
        zerowaiters: Deque[DelayedResultVariable[Any]] = deque()
        # queue containing everything, to find hanging statements
        all_statements: Set[Waiter] = set()

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
                    next.requeue_with_additional_requires(object(), e.get_result_variable())

            # all safe stmts are done
            progress = False
            assert not basequeue

            # find a RV that has waiters, so freezing creates progress
            while len(waitqueue) > 0 and not progress:
                next_rv = waitqueue.popleft()
                if next_rv.hasValue:
                    # already froze itself
                    continue
                if next_rv.get_progress_potential() <= 0:
                    zerowaiters.append(next_rv)
                elif next_rv.get_waiting_providers() > 0:
                    # definitely not done
                    # drop from queue
                    # will requeue when value is added
                    next_rv.unqueue()
                else:
                    # freeze it and go to next iteration, new statements will be on the basequeue
                    LOGGER.log(LOG_LEVEL_TRACE, "Freezing %s", next_rv)
                    next_rv.freeze()
                    progress = True

            # no waiters in waitqueue,...
            # see if any zerowaiters have become gotten waiters
            if not progress:
                zerowaiters_tmp = [w for w in zerowaiters if not w.hasValue]
                waitqueue = deque(w for w in zerowaiters_tmp if w.get_progress_potential() > 0)
                queue.waitqueue = waitqueue
                zerowaiters = deque(w for w in zerowaiters_tmp if w.get_progress_potential() <= 0)
                while len(waitqueue) > 0 and not progress:
                    LOGGER.debug("Moved zerowaiters to waiters")
                    next_rv = waitqueue.popleft()
                    if next_rv.get_waiting_providers() > 0:
                        next_rv.unqueue()
                    else:
                        LOGGER.log(LOG_LEVEL_TRACE, "Freezing %s", next_rv)
                        next_rv.freeze()
                        progress = True

            if not progress:
                # nothing works anymore, attempt to unfreeze wait cycle
                progress = self.find_wait_cycle(queue.allwaiters)

            if not progress:
                # no one waiting anymore, all done, freeze and finish
                LOGGER.debug("Finishing statements with no waiters")

                while len(zerowaiters) > 0:
                    next_rv = zerowaiters.pop()
                    next_rv.freeze()

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

        excns: List[CompilerException] = []
        self.freeze_all(excns)

        now = time.time()
        LOGGER.info(
            "Total compilation time %f",
            now - start,
        )

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

            assert stmt is not None

            raise RuntimeException(stmt.expression, "not all statements executed %s" % all_statements)

        return True
