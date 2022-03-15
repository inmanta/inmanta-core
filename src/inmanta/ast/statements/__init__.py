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
from typing import Dict, FrozenSet, Iterator, List, Optional, Tuple

import inmanta.execute.dataflow as dataflow
from inmanta.ast import Anchor, DirectExecuteException, Locatable, Location, Named, Namespace, Namespaced, RuntimeException
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import ExecutionUnit, QueueScheduler, Resolver, ResultCollector, ResultVariable

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

    # TODO: implement in If, For, SubConstructor
    # TODO: name
    def emit_nested_promises(self, resolver: Resolver, queue: QueueScheduler, *, out_of_scope: FrozenSet[str]) -> None:
        # TODO: double check docstring correctness when final
        """
        Emits any progression promises for nested blocks. Makes sure the promises get fulfilled as soon as certainty is
        reached on whether or not the block will be emitted. Promises are acquired on any attribute assignments on any variables
        that have not been declared out of scope. This allows to emit promises only relative to a certain parent context,
        excluding sibling and/or intermediate parent (shadowed) declarations.

        Expected to be called after normalization and before emit.

        :param resolver: Resolver for the parent context promises should be acquired on.
        :param out_of_scope: Set of variables that are considered out of scope. No promises will be acquired for these
            variables or their attributes.
        """
        pass

    def emit_progression_promise(
        self, resolver: Resolver, queue: QueueScheduler, *, out_of_scope: FrozenSet[str]
    ) -> Optional["variables.AttributeReferencePromise"]:
        # TODO: better to make AttributeReferencePromise a child of ProgressionPromise or something generic like that.
        """
        Emits a progression promise for this statement if emitting it would make progression towards a variable's completeness
        and returns it. If emitting this statement would make no such progression, returns None.

        :param resolver: Resolver for the parent context promises should be acquired on.
        :param out_of_scope: Set of variables that are considered out of scope. No promises will be acquired on their or their
            attribute's variables.
        """
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
    def resume(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler, target: ResultVariable) -> None:
        pass


class RawResumer(ExpressionStatement):
    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> None:
        pass


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
