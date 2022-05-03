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
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Sequence, Tuple

import inmanta.execute.dataflow as dataflow
from inmanta.ast import Anchor, DirectExecuteException, Location, Named, Namespace, Namespaced, RuntimeException
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import (
    ExecutionUnit,
    Instance,
    ProgressionPromise,
    QueueScheduler,
    RawUnit,
    Resolver,
    ResultCollector,
    ResultVariable,
    Typeorvalue,
    Waiter,
)

if TYPE_CHECKING:
    from inmanta.ast.assign import SetAttribute  # noqa: F401
    from inmanta.ast.blocks import BasicBlock  # noqa: F401
    from inmanta.ast.type import NamedType  # noqa: F401
    from inmanta.ast.variables import Reference  # noqa: F401


class Statement(Namespaced):
    """
    An abstract baseclass representing a statement in the configuration policy.
    """

    def __init__(self) -> None:
        Namespaced.__init__(self)
        self.namespace = None  # type: Namespace
        self.anchors = []  # type: List[Anchor]

    def get_namespace(self) -> "Namespace":
        return self.namespace

    def pretty_print(self) -> str:
        return str(self)

    def get_location(self) -> Location:
        return self.location

    def get_anchors(self) -> List[Anchor]:
        return self.anchors

    def nested_blocks(self) -> Iterator["BasicBlock"]:
        """
        Returns an iterator over blocks contained within this statement.
        """
        return iter(())


class DynamicStatement(Statement):
    """
    This class represents all statements that have dynamic properties.
    These are all statements that do not define typing.
    """

    def __init__(self) -> None:
        Statement.__init__(self)
        self._own_eager_promises: Sequence["StaticEagerPromise"] = []

    def get_own_eager_promises(self) -> Sequence["StaticEagerPromise"]:
        """
        Returns all eager promises this statement itself is responsible for.
        """
        return self._own_eager_promises

    def get_all_eager_promises(self) -> Iterator["StaticEagerPromise"]:
        """
        Returns all eager promises for this statement, including eager promises on sub-expressions in case of composition.
        These are the promises that should be acquired by parent blocks.
        """
        return iter(self._own_eager_promises)

    def normalize(self) -> None:
        raise NotImplementedError()

    def requires(self) -> List[str]:
        """List of all variable names used by this statement"""
        raise NotImplementedError()

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        """Emit new instructions to the queue, executing this instruction in the context of the resolver"""
        raise NotImplementedError()

    def execute_direct(self, requires: Dict[object, object]) -> object:
        raise DirectExecuteException(self, f"The statement {str(self)} can not be executed in this context")

    def declared_variables(self) -> Iterator[str]:
        """
        Returns an iterator over this statement's own declared variables.
        """
        return iter(())


class RequiresEmitStatement(DynamicStatement):
    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        """
        Emits this statement by scheduling its promises and scheduling a unit to wait on its requirements. Injects the
        schedulred promise objects in the waiter's requires in order to pass it on to the execute method.
        """
        target = ResultVariable()
        reqs = self.requires_emit(resolver, queue)
        ExecutionUnit(queue, resolver, target, reqs, self)

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        """
        Returns a dict of the result variables required for execution. Names are an opaque identifier. May emit statements to
        break execution is smaller segments.
        Additionally schedules this statement's eager promises and includes them (wrapped in a result variable) in the requires
        dict in order to pass it on to the execution phase.
        When this method is called, the caller must make sure to eventually call `execute` as well.
        """
        return self._requires_emit_promises(resolver, queue)

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector
    ) -> Dict[object, ResultVariable]:
        """
        Returns a dict of the result variables required for execution. Behaves like requires_emit, but additionally may attach
        resultcollector as a listener to result variables.
        When this method is called, the caller must make sure to eventually call `execute` as well.
        """
        return self.requires_emit(resolver, queue)

    def _requires_emit_promises(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        """
        Acquires eager promises this statement is responsible for and returns them, wrapped in a result variable, in a requires
        dict.
        """
        promises: ResultVariable = ResultVariable()
        promises.set_value(self.schedule_eager_promises(resolver, queue), self.location)
        return {(self, EagerPromise): promises}

    def schedule_eager_promises(self, resolver: Resolver, queue: QueueScheduler) -> Sequence["EagerPromise"]:
        """
        Schedules this statement's eager promises to be acquired in the given dynamic context.
        """
        return [promise.schedule(self, resolver, queue) for promise in self.get_own_eager_promises()]

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        """
        execute the statement, give the values provided in the requires dict.
        These values correspond to the values requested via requires_emit
        """
        self._fulfill_promises(requires)
        return None

    def _fulfill_promises(self, requires: Dict[object, object]) -> None:
        """
        Given a requires dict, fulfills this statements dynamic promises
        """
        promises: Sequence["EagerPromise"] = requires[(self, EagerPromise)]
        for promise in promises:
            promise.fulfill()


class ExpressionStatement(RequiresEmitStatement):
    def as_constant(self) -> object:
        """
        Returns this expression as a constant value, if possible. Otherwise, raise a RuntimeException.
        """
        raise RuntimeException(None, "%s is not a constant" % self)

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        """
        Return the node in the data flow graph this ExpressionStatement will evaluate to.
        """
        raise NotImplementedError()


class Resumer(ExpressionStatement):
    """
    Resume on a set of requirement variables' values when they become ready (i.e. they are complete).
    """

    def resume(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler, target: ResultVariable) -> None:
        pass


class RawResumer(ExpressionStatement):
    """
    Resume on a set of requirement variables when they become ready (i.e. they are complete).
    """

    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> None:
        pass


class VariableReferenceHook(RawResumer):
    """
    Generic helper class for adding a hook to a variable (ResultVariable) object. Supports both plain variables and instance
    attributes. Calls variable resumer with the variable object as soon as it's available.
    This class is not a full AST node, rather it is a Resumer only. It is meant to delegate common resumer behavior that would
    otherwise need to be implemented as custom resumer logic in each class that needs it.
    """

    def __init__(
        self,
        instance: Optional["Reference"],
        name: str,
        variable_resumer: "VariableResumer",
    ) -> None:
        super().__init__()
        self.instance: Optional["Reference"] = instance
        self.name: str = name
        self.variable_resumer: "VariableResumer" = variable_resumer

    def schedule(self, resolver: Resolver, queue: QueueScheduler) -> None:
        """
        Schedules this instance for execution. Waits for the variable's requirements before resuming.
        """
        RawUnit(
            queue,
            resolver,
            # no need for gradual execution here because this class represents an attribute reference on self.instance,
            # which is not allowed on multi variables (the only kind of variables that would benefit from gradual execution)
            self.instance.requires_emit(resolver, queue) if self.instance is not None else {},
            self,
        )

    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> None:
        """
        Fetches the variable when it's available and calls variable resumer.
        """
        variable: ResultVariable[object]
        if self.instance is not None:
            # get the Instance
            instance: object = self.instance.execute({k: v.get_value() for k, v in requires.items()}, resolver, queue)

            if isinstance(instance, list):
                raise RuntimeException(self, "can not get attribute %s, %s is not an entity but a list" % (self.name, instance))
            if not isinstance(instance, Instance):
                raise RuntimeException(
                    self,
                    "can not get attribute %s, %s is not an entity but a %s with value '%s'"
                    % (self.name, self.instance, type(instance).__name__, instance),
                )

            # get the attribute result variable
            variable = instance.get_attribute(self.name)
        else:
            obj: Typeorvalue = resolver.lookup(self.name)
            if not isinstance(obj, ResultVariable):
                raise RuntimeException(self, "can not get variable %s, it is a type" % self.name)
            variable = obj

        self.variable_resumer.variable_resume(variable, resolver, queue)

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        raise RuntimeException(self, "%s is not an actual AST node, it should never be executed" % self.__class__.__name__)

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        raise RuntimeException(self, "%s is not an actual AST node, it should never be executed" % self.__class__.__name__)

    def __str__(self):
        return "%s.%s" % (self.instance, self.name)

    def __repr__(self):
        return "%s(%r, %s, %r)" % (self.__class__.__name__, self.instance, self.name, self.variable_resumer)


class VariableResumer:
    """
    Resume execution on a variable object when it becomes available (i.e. it exists).
    """

    def variable_resume(
        self,
        variable: ResultVariable,
        resolver: Resolver,
        queue: QueueScheduler,
    ) -> None:
        """
        Resume execution with the given result variable.
        """
        raise NotImplementedError()


@dataclass(frozen=True)
class StaticEagerPromise:
    """
    Static representation of an eager promise for an attribute assignment.

    :ivar instance: The reference to the instance on which to acquire a promise. Might differ from the assign statement's
        reference due to scoping differences between the context where the statement is executed and the one where the promise
        is acquired.
    :ivar attribute: The attribute name for which to acquire a promise.
    :ivar statement: The assignment statement that led to this promise.
    """

    instance: "Reference"
    attribute: str
    statement: "SetAttribute"

    def get_root_variable(self) -> str:
        """
        Returns the name of the variable at the start of the attribute traversal chain. e.g. for a.b.c.d, returns "a". Includes
        namespace information if specified in the original reference.
        """
        return self.instance.get_root_variable().name

    def schedule(self, responsible: DynamicStatement, resolver: Resolver, queue: QueueScheduler) -> "EagerPromise":
        """
        Schedule the acquisition of this promise in a given dynamic context: set up a waiter to wait for the referenced
        ResultVariable to exist, then acquire the promise.

        :param responsible: The statement responsible for this eager promise, i.e. the statement that will fulfill it once it
            will make no further progression.
        """
        dynamic: "EagerPromise" = EagerPromise(self, responsible)
        hook: VariableReferenceHook = VariableReferenceHook(
            self.instance,
            self.attribute,
            variable_resumer=dynamic,
        )
        self.statement.copy_location(hook)
        hook.schedule(resolver, queue)
        return dynamic


class EagerPromise(VariableResumer):
    """
    Dynamic node for eager promising (stateful). Eagerly acquires a progression promise on a variable when it becomes available.
    Fulfilling this promise aborts the waiter if it has not finished yet, otherwise it fulfills the acquired progression
    promise.
    """

    def __init__(self, static: StaticEagerPromise, responsible: DynamicStatement) -> None:
        super().__init__()
        self.static: StaticEagerPromise = static
        self.responsible: DynamicStatement = responsible
        self._promise: Optional[ProgressionPromise] = None
        self._fulfilled: bool = False

    def _acquire(self, variable: ResultVariable) -> None:
        """
        Entry point for the ResultVariable waiter: actually acquire the promise
        """
        if not self._fulfilled:
            assert self._promise is None
            self._promise = variable.get_progression_promise(self.responsible)

    def fulfill(self) -> None:
        """
        If a promise was already acquired, fulfills it, otherwise makes sure that no new promise is acquired when the variable
        becomes available.
        """
        if self._promise is not None:
            self._promise.fulfill()
        self._fulfilled = True

    def variable_resume(
        self,
        variable: ResultVariable,
        resolver: Resolver,
        queue: QueueScheduler,
    ) -> None:
        self._acquire(variable)


class ReferenceStatement(ExpressionStatement):
    """
    This class models statements that refer to other statements
    """

    def __init__(self, children: List[ExpressionStatement]) -> None:
        ExpressionStatement.__init__(self)
        self.children: Sequence[ExpressionStatement] = children
        self.anchors.extend((anchor for e in self.children for anchor in e.get_anchors()))

    def normalize(self) -> None:
        for c in self.children:
            c.normalize()

    def get_all_eager_promises(self) -> Iterator["StaticEagerPromise"]:
        return chain(super().get_all_eager_promises(), *(subexpr.get_all_eager_promises() for subexpr in self.children))

    def requires(self) -> List[str]:
        return [req for v in self.children for req in v.requires()]

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        parent_req: Mapping[object, ResultVariable] = super().requires_emit(resolver, queue)
        own_req: Mapping[object, ResultVariable] = {
            rk: rv for i in self.children for (rk, rv) in i.requires_emit(resolver, queue).items()
        }
        return {**parent_req, **own_req}


class AssignStatement(DynamicStatement):
    """
    This class models binary sts
    """

    def __init__(self, lhs: Optional["Reference"], rhs: ExpressionStatement) -> None:
        DynamicStatement.__init__(self)
        self.lhs: Optional["Reference"] = lhs
        self.rhs: ExpressionStatement = rhs
        if lhs is not None:
            self.anchors.extend(lhs.get_anchors())
        self.anchors.extend(rhs.get_anchors())

    def normalize(self) -> None:
        self.rhs.normalize()

    def get_all_eager_promises(self) -> Iterator["StaticEagerPromise"]:
        return chain(
            super().get_all_eager_promises(),
            (self.lhs.get_all_eager_promises() if self.lhs is not None else []),
            self.rhs.get_all_eager_promises(),
        )

    def requires(self) -> List[str]:
        out = self.lhs.requires() if self.lhs is not None else []  # type : List[str]
        out.extend(self.rhs.requires())  # type : List[str]
        return out

    def _add_to_dataflow_graph(self, graph: Optional[DataflowGraph]) -> None:
        """
        Adds this assignment to the resolver's data flow graph.
        """
        raise NotImplementedError()


class Literal(ExpressionStatement):
    def __init__(self, value: object) -> None:
        ExpressionStatement.__init__(self)
        self.value = value
        self.lexpos: Optional[int] = None

    def normalize(self) -> None:
        pass

    def __repr__(self) -> str:
        if isinstance(self.value, bool):
            return repr(self.value).lower()
        return repr(self.value)

    def requires(self) -> List[str]:
        return []

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        super().execute(requires, resolver, queue)
        return self.value

    def execute_direct(self, requires: Dict[object, object]) -> object:
        return self.value

    def as_constant(self) -> object:
        return self.value

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.ValueNodeReference:
        return dataflow.ValueNode(self.value).reference()


class DefinitionStatement(Statement):
    """
    This statement defines a new entity in the configuration.
    """

    def __init__(self) -> None:
        Statement.__init__(self)


class TypeDefinitionStatement(DefinitionStatement, Named):
    comment: Optional[str]

    def __init__(self, namespace: Namespace, name: str) -> None:
        DefinitionStatement.__init__(self)
        self.name = name
        self.namespace = namespace
        self.fullName = namespace.get_full_name() + "::" + str(name)
        self.type = None  # type: NamedType
        self.comment = None

    def register_types(self) -> Tuple[str, "NamedType"]:
        self.namespace.define_type(self.name, self.type)
        return (self.fullName, self.type)

    def evaluate(self) -> None:
        pass

    def get_full_name(self) -> str:
        return self.fullName


class BiStatement(DefinitionStatement, DynamicStatement):
    def __init__(self):
        Statement.__init__(self)
