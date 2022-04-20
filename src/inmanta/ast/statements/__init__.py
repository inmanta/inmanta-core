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
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterator, List, Optional, Sequence, Tuple, TYPE_CHECKING

import inmanta.execute.dataflow as dataflow
from inmanta.ast import Anchor, DirectExecuteException, Locatable, Location, Named, Namespace, Namespaced, RuntimeException
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import (
    ExecutionUnit,
    Instance,
    ProgressionPromiseABC,
    QueueScheduler,
    RawUnit,
    Resolver,
    ResultCollector,
    ResultVariable,
    Typeorvalue,
    ProgressionPromise,
)


if TYPE_CHECKING:
    from inmanta.ast.blocks import BasicBlock  # noqa: F401
    from inmanta.ast.type import NamedType, Type  # noqa: F401
    from inmanta.ast.variables import AttributeReferencePromise, Reference  # noqa: F401
    from inmanta.ast.assign import SetAttribute  # noqa: F401


class Statement(Namespaced):
    """
    An abstract baseclass representing a statement in the configuration policy.
    """

    def __init__(self) -> None:
        Namespaced.__init__(self)
        self.namespace = None  # type: Namespace
        self.anchors = []  # type: List[Anchor]
        # TODO: perhaps this could move to DynamicStatement?
        self.eager_promises: Sequence["StaticEagerPromise"] = []

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


# TODO: remove
class ConditionalPromiseABC(ProgressionPromiseABC):
    """
    Promise for progression that might or might not be made depending on a condition. Can be either picked or dropped when the
    condition becomes known.
    """

    def pick(self) -> None:
        """
        Fulfills this promise with the additional context that further progression will be made by newly emitted statements
        and/or promises.
        """
        # for simple conditional promises the context is irrelevant, just fulfill the promise
        self.fulfill()

    def drop(self) -> None:
        """
        Fulfills this promise with the additional context that the potential progression for this promise will never occur.
        """
        # for simple conditional promises the context is irrelevant, just fulfill the promise
        self.fulfill()


# TODO: could be a lot cleaner if this is mutable so classes don't need to store a list of blocks that differ only in reference
#       scope, but how to merge? Might need a different data structure alltogether. First make it work with this one, then clean
#       up
@dataclass(frozen=True)
class ConditionalPromiseBlock(ConditionalPromiseABC):
    """
    Conditional promise for a whole block. Contains promises for statements in the block. Dropping a block means dropping
    everything below it while picking a block means fulfilling the immediate promises of this block and leaving nested
    conditional block promises hanging (their condition isn't known yet).
    """

    sub_promises: Sequence[ConditionalPromiseABC]

    def fulfill(self) -> None:
        """
        Fulfills this promise without fulfilling any of its sub promises.
        """
        pass

    def pick(self) -> None:
        """
        Fulfills all promises in the block without recursing on nested blocks.
        """
        for promise in self.sub_promises:
            promise.fulfill()
        self.fulfill()

    def drop(self) -> None:
        """
        Drops all promises in the block, recursing on nested blocks.
        """
        for promise in self.sub_promises:
            promise.drop()
        self.fulfill()


class DynamicStatement(Statement):
    """
    This class represents all statements that have dynamic properties.
    These are all statements that do not define typing.
    """

    def __init__(self) -> None:
        Statement.__init__(self)

    def normalize(self) -> None:
        raise NotImplementedError()

    def requires(self) -> List[str]:
        """List of all variable names used by this statement"""
        raise NotImplementedError()

    # TODO: remove
    # TODO: implement in For, Implement/SubConstructor
    # TODO: name: emit_eager_promises? emit_conditional_promises?
    def emit_progression_promises(
        self, resolver: Resolver, queue: QueueScheduler, *, in_scope: FrozenSet[str], root: bool = False
    ) -> Sequence[ConditionalPromiseABC]:
        """
        Emits progression promises for this statement if emitting it would make progression towards any of the in scope
        variables' completeness and returns these promises. The caller is responsible for fulfilling each of these promises,
        either by picking them or by dropping them.

        Expected to be called after normalization and before emit. May be called multiple times with different scopes.

        :param resolver: Resolver for the parent context promises should be acquired on.
        :param in_scope: Set of variables that are considered in scope. Promises will only be acquired for these variables or
            their attributes. This allows to emit promises only relative to a certain parent context, excluding sibling and/or
            intermediate parent (shadowed) declarations.
        :param root: If true, this statement lives in the root reference scope, in which case the in scope names are considered
            siblings and only promises for nested blocks should be emitted.
        """
        return []

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


class ExpressionStatement(DynamicStatement):
    def __init__(self) -> None:
        DynamicStatement.__init__(self)

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        target = ResultVariable()
        reqs = self.requires_emit(resolver, queue)
        ExecutionUnit(queue, resolver, target, reqs, self)

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        """
        returns a dict of the result variables required, names are an opaque identifier
        may emit statements to break execution is smaller segments
        """
        raise NotImplementedError()

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        """
        execute the expression, give the values provided in the requires dict.
        These values correspond to the values requested via requires_emit
        """
        raise NotImplementedError()

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector
    ) -> Dict[object, ResultVariable]:
        """
        Returns a dict of the result variables required for execution. Behaves like requires_emit, but additionally may attach
        resultcollector as a listener to result variables.
        """
        return self.requires_emit(resolver, queue)

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

    def schedule(self, resolver: Resolver, queue_scheduler: QueueScheduler) -> RawUnit:
        """
        Schedules this instance for execution. Waits for the variable's requirements before resuming.
        """
        return RawUnit(
            queue_scheduler,
            resolver,
            # TODO: instance could be None, why does this not fail test cases -> add tests for is defined on local var / implicit self?
            # TODO: shouldn't we do gradual execution on self.instance as well?
            self.instance.requires_emit(resolver, queue_scheduler) if self.instance is not None else {},
            self,
        )

    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        """
        Fetches the variable when it's available and calls variable resumer.
        """
        variable: ResultVariable[object]
        if self.instance is not None:
            # get the Instance
            instance: object = self.instance.execute({k: v.get_value() for k, v in requires.items()}, resolver, queue_scheduler)

            if isinstance(instance, list):
                raise RuntimeException(self, "can not get attribute %s, %s is not an entity but a list" % (self.name, instance))
            if not isinstance(instance, Instance):
                raise RuntimeException(
                    self,
                    "can not get attribute %s, %s is not an entity but a %s with value %s"
                    % (self.name, self.instance, type(instance), instance),
                )

            # get the attribute result variable
            variable = instance.get_attribute(self.name)
        else:
            obj: Typeorvalue = resolver.lookup(self.name)
            if not isinstance(obj, ResultVariable):
                raise RuntimeException(self, "can not get variable %s, it is a type" % self.name)
            variable = obj

        self.variable_resumer.resume(variable, resolver, queue_scheduler)

    # TODO: execute method implementation required -> return None? Don't implement? Why even is RawResumer(ExpressionStatement)?

    # TODO: str and repr


# TODO: is Locatable required?
class VariableResumer(Locatable):
    """
    Resume execution on a variable object when it becomes available (i.e. it exists).
    """

    def resume(
        self,
        variable: ResultVariable,
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        raise NotImplementedError()

    # TODO: str and repr


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
    instance: "Reference" = instance
    attribute: str = attribute
    statement: "SetAttribute" = statement

    def get_root_variable(self) -> str:
        """
        Returns the name of the variable at the start of the attribute traversal chain. e.g. for a.b.c.d, returns "a". Includes
        namespace information if specified in the original reference.
        """
        return self.assignment.instance.get_root_variable().name

    def schedule(self, responsible: Statement, resolver: Resolver, queue_scheduler: QueueScheduler) -> "EagerPromise":
        """
        Schedule the acquisition of this promise in a given dynamic context: set up a waiter to wait for the referenced
        ResultVariable to exist, then acquire the promise.

        :param responsible: The statement responsible for this eager promise, i.e. the statement that will fulfill it once it
            will make no further progression.
        """
        dynamic: "EagerPromise" = EagerPromise(self, responsible)
        hook: VariableReferenceHook = VariableReferenceHook(
            self.instance,
            self.attribute_name,
            variable_resumer=dynamic,
        )
        # TODO: clean up copy_location
        self.assignment.copy_location(dynamic)
        self.assignment.copy_location(hook)
        waiter: Waiter = hook.schedule(resolver, queue)
        dynamic.set_waiter(waiter)


class EagerPromise(VariableResumer):
    """
    Dynamic node for eager promising (stateful). Eagerly acquires a progression promise on a variable when it becomes available.
    Fulfilling this promise aborts the waiter if it has not finished yet, otherwise it fulfills the acquired progression
    promise.
    """

    def __init__(self, static: StaticEagerPromise, responsible: Statement) -> None:
        super().__init__()
        self.static: StaticEagerPromise = static
        self.responsible: Statement = responsible
        self._waiter: Optional[Waiter] = None
        self._promise: Optional[ProgressionPromise] = None
        self._fulfilled: bool = False

    def set_waiter(self, waiter: Waiter) -> None:
        self._waiter = waiter

    def _acquire(self, variable: ResultVariable) -> None:
        """
        Entry point for the ResultVariable waiter: actually acquire the promise
        """
        if self._fulfilled:
            # already fulfilled, no need to acquire progression promise anymore
            return
        assert self._promise is None
        self._promise = variable.get_progression_promise(self.provider)

    def fulfill(self) -> None:
        """
        If a promise was already acquired, fulfills it, otherwise cancels the waiter so no new promise is acquired when the
        variable becomes available.
        """
        if self._fulfilled:
            # already fulfilled, no need to continue
            return
        if self._waiter is not None:
            self._waiter.queue.remove_from_all(self._waiter)
        if self._promise is not None:
            self._promise.fulfill()
        self._fulfilled = True

    def resume(
        self,
        variable: ResultVariable,
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        self._acquire(variable)


class ReferenceStatement(ExpressionStatement):
    """
    This class models statements that refer to other statements
    """

    def __init__(self, children: List[ExpressionStatement]) -> None:
        ExpressionStatement.__init__(self)
        self.children = children
        self.anchors.extend((anchor for e in self.children for anchor in e.get_anchors()))

    def normalize(self) -> None:
        for c in self.children:
            c.normalize()

    def requires(self) -> List[str]:
        return [req for v in self.children for req in v.requires()]

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        return {rk: rv for i in self.children for (rk, rv) in i.requires_emit(resolver, queue).items()}


class AssignStatement(DynamicStatement):
    """
    This class models binary sts
    """

    def __init__(self, lhs: "Reference", rhs: ExpressionStatement) -> None:
        DynamicStatement.__init__(self)
        self.lhs = lhs
        self.rhs = rhs
        if lhs is not None:
            self.anchors.extend(lhs.get_anchors())
        self.anchors.extend(rhs.get_anchors())

    def normalize(self) -> None:
        self.rhs.normalize()

    def requires(self) -> List[str]:
        out = self.lhs.requires()  # type : List[str]
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

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        return {}

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
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
