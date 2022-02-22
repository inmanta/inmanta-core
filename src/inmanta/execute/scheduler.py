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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Deque, Dict, Iterator, List, Optional, Sequence, Set, Tuple

from inmanta import plugins
from inmanta.ast import Anchor, CompilerException, CycleException, Location, MultiException, RuntimeException
from inmanta.ast.attribute import RelationAttribute
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
    TempListVariable,
    Waiter,
)
from inmanta.execute.tracking import ModuleTracker

if TYPE_CHECKING:
    from inmanta.ast import BasicBlock, NamedType, Statement  # noqa: F401
    from inmanta.compiler import Compiler  # noqa: F401
    from inmanta.module import TypeHint


DEBUG = True
LOGGER = logging.getLogger(__name__)


MAX_ITERATIONS = 10000


class Scheduler(object):
    """
    This class schedules statements for execution
    """

    def __init__(self, track_dataflow: bool = False, type_hints: Optional[List["TypeHint"]] = None):
        self.track_dataflow: bool = track_dataflow
        self.types: Dict[str, Type] = {}
        self.type_hints: List["TypeHint"] = type_hints if type_hints else []

    def _get_valid_type_hints(self) -> List["TypeHint"]:
        """
        This method validates the type hints in self.type_hints, logs warning for invalid hints and
        return a list containing only the valid type hints.
        """
        if not self.types:
            raise Exception("The self.define_types() method should be called first")
        if self.type_hints:
            LOGGER.warning(
                "[EXPERIMENTAL FEATURE] Using type hints defined in the project.yml file to determine list freeze order."
            )
        valid_type_hints = []
        for hint in self.type_hints:
            LOGGER.info("Loaded type hint: %s", hint)
            for (entity_type_name, relationship_name) in hint.iterate_types():
                if entity_type_name not in self.types:
                    LOGGER.warning("A type hint was defined for %s, but no such type was defined", entity_type_name)
                    continue
                current_type: Type = self.types[entity_type_name]
                if not isinstance(current_type, Entity):
                    LOGGER.warning("A type hint was defined for non-entity type %s", current_type)
                    continue
                assert isinstance(current_type, Entity)  # Make mypy happy
                attributes_of_entity = current_type.attributes
                if relationship_name not in attributes_of_entity:
                    LOGGER.warning(
                        "A type hint was defined for %s, but entity %s doesn't have an attribute %s.",
                        f"{entity_type_name}.{relationship_name}",
                        entity_type_name,
                        relationship_name,
                    )
                    continue
                if not isinstance(attributes_of_entity[relationship_name], RelationAttribute):
                    LOGGER.warning(
                        "A type hint was defined for %s, but attribute %s is not a relationship attribute.",
                        f"{entity_type_name}.{relationship_name}",
                        relationship_name,
                    )
                else:
                    valid_type_hints.append(hint)
        return valid_type_hints

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
                    raise CycleException(nexte, p)
                if p in entity_map:
                    self.do_sort_entities(entity_map, p, acc, loopstack)
            loopstack.remove(name)
            acc.append(nexte)
        except CycleException as ce:
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
        waitqueue = PrioritisedDelayedResultVariableQueue(self._get_valid_type_hints())
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
                waitqueue.replace(w for w in zerowaiters_tmp if w.get_progress_potential() > 0)
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


@dataclass(frozen=True)
class EntityRelationship:
    """
    Represent a relationship attribute of an entity.
    """

    fq_entity_name: str
    relationship_name: str

    @classmethod
    def from_type_hint(cls, type_hint: "TypeHint") -> Tuple["EntityRelationship", "EntityRelationship"]:
        first = cls(type_hint.first_type, type_hint.first_relation_name)
        then = cls(type_hint.then_type, type_hint.then_relation_name)
        return first, then

    @classmethod
    def from_delayed_result_variable(cls, drv: DelayedResultVariable[Any]) -> "EntityRelationship":
        return cls(
            fq_entity_name=drv.myself.get_type().get_full_name(),
            relationship_name=drv.attribute.name,
        )


class PrioritisedDelayedResultVariableQueue:
    """
    A queue for DelayedResultVariables that is prioritized based on the
    type hints passed to the Compiler. This queue will return elements
    in the following order:

    * First return the DelayedResultVariables, which are not an instance of
      TempListVariable and that do not have an order constraint.
    * Then return DelayedResultVariables with order constraint.
      They are returned in an order that is valid with respect to the
      constraints.
    * Finally, all TempListVariables are returned.

    TempListVariables is subclass of DelayedResultVariables that is not
    associated with an entity. That way it's not possible to set
    type hints on them.
    """

    def __init__(self, type_hints: List["TypeHint"]) -> None:
        self._all_constraint_entity_relationships: Set[EntityRelationship] = set(
            itertools.chain.from_iterable(EntityRelationship.from_type_hint(hint) for hint in type_hints)
        )

        self._unconstraint_variables: Deque[DelayedResultVariable[object]] = deque()
        self._constraint_variables: Dict[EntityRelationship, Deque[DelayedResultVariable[object]]] = {
            entity_relationship: deque() for entity_relationship in self._all_constraint_entity_relationships
        }
        self._tmp_list_variables: Deque[TempListVariable] = deque()

        # A queue that indicates a valid order in which the self._constraint_variables have to be returned
        # This queue is never modified.
        self._freeze_order: Deque[EntityRelationship] = deque(TypePrecedenceGraph(type_hints).get_freeze_order())
        # Copy of self._freeze_order. At all times the first element of this queue
        # points to the next type that should be returned from self._constraint_variables
        self._freeze_order_working_list: Deque[EntityRelationship] = self._freeze_order.copy()

    def __len__(self) -> int:
        """
        Return the number of elements present in this queue.
        """
        return (
            len(self._unconstraint_variables)
            + sum(len(v) for v in self._constraint_variables.values())
            + len(self._tmp_list_variables)
        )

    def append(self, drv: DelayedResultVariable[object], dont_reset_working_list: bool = False) -> None:
        """
        Append on the right side of the queue.
        """
        if isinstance(drv, TempListVariable):
            self._tmp_list_variables.append(drv)
            return
        entity_relationship = EntityRelationship.from_delayed_result_variable(drv)
        if entity_relationship in self._constraint_variables:
            self._constraint_variables[entity_relationship].append(drv)
            if not dont_reset_working_list and entity_relationship not in self._freeze_order_working_list:
                # working list is dirty
                self._freeze_order_working_list = self._freeze_order.copy()
        else:
            self._unconstraint_variables.append(drv)

    def popleft(self) -> DelayedResultVariable[Any]:
        """
        Remove element from the left side of the queue and return it.
        """
        try:
            return self._unconstraint_variables.popleft()
        except IndexError:
            # Empty
            pass
        try:
            return self._get_next_constraint_variable()
        except IndexError:
            # Empty
            pass
        return self._tmp_list_variables.popleft()

    def _get_next_constraint_variable(self) -> DelayedResultVariable[Any]:
        if not self._constraint_variables:
            raise IndexError()
        while len(self._freeze_order_working_list) > 0:
            entity_relationship = self._freeze_order_working_list[0]
            if (
                entity_relationship not in self._constraint_variables
                or len(self._constraint_variables[entity_relationship]) == 0
            ):
                self._freeze_order_working_list.popleft()
            else:
                return self._constraint_variables[entity_relationship].popleft()
        raise IndexError()

    def replace(self, drvs: Iterator[DelayedResultVariable[Any]]) -> None:
        """
        Remove all elements from this queue and add the elements provided in drvs.
        """
        self._unconstraint_variables = deque()
        self._constraint_variables = {
            entity_relationship: deque() for entity_relationship in self._all_constraint_entity_relationships
        }
        self._tmp_list_variables = deque()
        for drv in drvs:
            self.append(drv, dont_reset_working_list=True)
        self._freeze_order_working_list = self._freeze_order.copy()


class CycleInTypeHintsError(CompilerException):
    """
    Raised when a cycle exists in the type hints provided to the compiler.
    """

    pass


class TypePrecedenceGraph:
    """
    A graph representation of the type hints provided to the compiler.
    """

    def __init__(self, type_hints: List["TypeHint"] = []) -> None:
        # The root nodes of the graph, where all other nodes attach to.
        self.root_nodes: Set[TypePrecedenceGraphNode] = set()
        # Dict of all nodes in the graph
        self.type_to_node: Dict[EntityRelationship, TypePrecedenceGraphNode] = {}
        # Creates nodes in graph
        for hint in type_hints:
            first_type, then_type = EntityRelationship.from_type_hint(hint)
            self.add_precedence_rule(first_type, then_type)

    def add_precedence_rule(self, first_type: EntityRelationship, then_type: EntityRelationship) -> None:
        """
        Add a rule that `first_type` should be frozen before `then_type`.
        """
        first_node = self._get_or_create_node(first_type, attach_to_root=True)
        then_node = self._get_or_create_node(then_type, attach_to_root=False)
        first_node.add_dependent(then_node)

    def _get_or_create_node(self, entity_relationship: EntityRelationship, attach_to_root: bool) -> "TypePrecedenceGraphNode":
        """
        Get the TypePrecedenceGraphNode for the given entity_relationship in this graph
        or create a new node if no such node exists.

        :param attach_to_root: Whether a newly created node should be added to the
                               root_nodes.
        """
        if entity_relationship not in self.type_to_node:
            node = TypePrecedenceGraphNode(entity_relationship)
            self.type_to_node[entity_relationship] = node
            if attach_to_root:
                self.root_nodes.add(node)
            return node
        else:
            return self.type_to_node[entity_relationship]

    def get_freeze_order(self) -> List[EntityRelationship]:
        """
        Return all the EntityRelationship in this graph in the order in which
        they should be frozen.
        """
        if not self.root_nodes:
            return []
        work: Set[TypePrecedenceGraphNode] = set(self.root_nodes)
        result: List[EntityRelationship] = []

        def get_next_ready_item_in_work() -> TypePrecedenceGraphNode:
            assert work
            for current_node in work:
                if all(dep.entity_relationship in result for dep in current_node.dependencies):
                    return current_node
            raise CycleInTypeHintsError("Cycle in type hints")

        while work:
            node = get_next_ready_item_in_work()
            work.remove(node)
            result.append(node.entity_relationship)
            work.update(node.dependents)
        return result


class TypePrecedenceGraphNode:
    """
    A node in the TypePrecedenceGraph that represents an Inmanta entity type
    """

    def __init__(self, entity_relationship: EntityRelationship) -> None:
        self.entity_relationship: EntityRelationship = entity_relationship
        self.dependents: Set[TypePrecedenceGraphNode] = set()
        self.dependencies: Set[TypePrecedenceGraphNode] = set()

    def add_dependent(self, dependent: "TypePrecedenceGraphNode") -> None:
        self.dependents.add(dependent)
        dependent.dependencies.add(self)
