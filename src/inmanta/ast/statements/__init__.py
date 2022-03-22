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
from itertools import chain
from typing import Dict, FrozenSet, Iterator, List, Optional, Sequence, Tuple

import inmanta.execute.dataflow as dataflow
from inmanta.ast import Anchor, DirectExecuteException, Locatable, Location, Named, Namespace, Namespaced, RuntimeException
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import (
    ExecutionUnit,
    ProgressionPromiseABC,
    QueueScheduler,
    Resolver,
    ResultCollector,
    ResultVariable,
    Typeorvalue,
)

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    from inmanta.ast.blocks import BasicBlock  # noqa: F401
    from inmanta.ast.type import NamedType, Type  # noqa: F401
    from inmanta.ast.variables import AttributeReferencePromise, Reference  # noqa: F401


class Statement(Namespaced):
    """
    An abstract baseclass representing a statement in the configuration policy.
    """

    def __init__(self) -> None:
        Namespaced.__init__(self)
        self.namespace = None  # type: Namespace
        self.anchors = []  # type: List[Anchor]

    def copy_location(self, statement: Locatable) -> None:
        """
        Copy the location of this statement in the given statement
        """
        statement.set_location(self.location)

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


# TODO: move up or down?
# TODO: inherit from ProgressionPromise. Requires new ProgressionPromise subclass for owner and provider
class ConditionalPromiseABC(ProgressionPromiseABC):
    """
    Promise for progression that might or might not be made depending on a condition. Can be either picked or dropped when the
    condition becomes known.
    """

    # TODO: docstring

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
    everything below it while picking a block means fulfilling the immediate promises of this block while leaving nested
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
        # TODO: document why this behavior
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

    # TODO: contract has changed: for nested blocks it no longer returns just the newly acquired promises but all promises that
    #       are held. This is required for deeply nested promises that are dropped by another scope than the one that acquired
    #       them
    # TODO: implement in If, For, SubConstructor
    # TODO: name: emit_eager_promises? emit_conditional_promises?
    # TODO: caller: set root appropriately
    def emit_progression_promises(
        self, resolver: Resolver, queue: QueueScheduler, *, in_scope: FrozenSet[str], root: bool = False
    ) -> Sequence[ConditionalPromiseABC]:
        # TODO: mention that this may be called multiple times with different scopes
        # TODO: double check docstring correctness when final
        # TODO: docstring is complete chaos now
        """
        Emits progression promises for this statement if emitting it would make progression towards any of the in scope
        variables' completeness and returns these promises. The caller is responsible for fulfilling each of these promises,
        either by picking them or by dropping them.

        :param root: If true, this statement lives in the root reference scope, in which case only promises for nested blocks
            should be emitted.

        reached on whether or not the block will be emitted. Promises are acquired on any attribute assignments on any variables
        that have not been declared out of scope. This allows to emit promises only relative to a certain parent context,
        excluding sibling and/or intermediate parent (shadowed) declarations.

        Expected to be called after normalization and before emit.

        :param resolver: Resolver for the parent context promises should be acquired on.
        :param out_of_scope: Set of variables that are considered out of scope. No promises will be acquired for these
            variables or their attributes.
        """
        # TODO: update docs out_of_scope -> in_scope
        return []

    # TODO: can be removed? Parts of docstring may have  to be moved to other method
    # TODO: can this be made 1 method? If not, add it to BasicBlock as well and/or clean up implementation in if statement.
    def emit_progression_promise(
        self, resolver: Resolver, queue: QueueScheduler, *, in_scope: FrozenSet[str]
    ) -> Optional[ConditionalPromiseABC]:
        # TODO: better to make AttributeReferencePromise a child of ProgressionPromise or something generic like that.
        """
        Emits a progression promise for this statement if emitting it would make progression towards a variable's completeness
        and returns it. If emitting this statement would make no such progression, returns None.

        :param resolver: Resolver for the parent context promises should be acquired on.
        :param out_of_scope: Set of variables that are considered out of scope. No promises will be acquired on their or their
            attribute's variables.
        """
        # TODO: update docs out_of_scope -> in_scope
        return None

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

    def requires(self) -> List[str]:
        """List of all variable names used by this statement"""
        raise NotImplementedError()

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
        instance: Optional[Reference],
        name: str,
        variable_resumer: "VariableResumer",
    ) -> None:
        super().__init__()
        self.instance: Optional[Reference] = instance
        self.name: str = name
        self.variable_resumer: "VariableResumer" = variable_resumer

    def schedule(self, resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        """
        Schedules this instance for execution. Waits for the variable's requirements before resuming.
        """
        RawUnit(
            queue_scheduler,
            resolver,
            # TODO: instance could be None, why does this not fail test cases -> add tests?
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
                raise RuntimeException(
                    self, "can not get a attribute %s, %s is not an entity but a list" % (self.name, instance)
                )
            if not isinstance(instance, Instance):
                raise RuntimeException(
                    self,
                    "can not get a attribute %s, %s is not an entity but a %s with value %s"
                    % (self.name, type(instance), instance),
                )

            # get the attribute result variable
            variable = instance.get_attribute(self.name)
        else:
            # TODO: what if this is not an RV?
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
        variable: ResultVariable[T],
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        raise NotImplementedError()

    # TODO: str and repr


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
