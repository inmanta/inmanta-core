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
from inmanta.execute.runtime import ResultVariable, ExecutionUnit, Resolver, QueueScheduler
from inmanta.ast import Locatable, Location, Namespaced, Namespace, Named, Anchor
from typing import Any, Dict, List, Tuple  # noqa: F401

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    from inmanta.ast.variables import Reference  # noqa: F401
    from inmanta.ast.type import Type, NamedType  # noqa: F401


class Statement(Namespaced):
    """
        An abstract baseclass representing a statement in the configuration policy.
    """

    def __init__(self) -> None:
        Namespaced.__init__(self)
        self.namespace = None  # type: Namespace
        self.anchors = []

    def copy_location(self, statement: Locatable) -> None:
        """
            Copy the location of this statement in the given statement
        """
        statement.location = self.location

    def get_namespace(self) -> "Namespace":
        return self.namespace

    def pretty_print(self) -> str:
        return str(self)

    def get_location(self) -> Location:
        return self.location

    def get_anchors(self) -> List[Anchor]:
        return self.anchors


class DynamicStatement(Statement):
    """
        This class represents all statements that have dynamic properties.
        These are all statements that do not define typing.
    """

    def __init__(self) -> None:
        Statement.__init__(self)

    def normalize(self) -> None:
        raise Exception("Not Implemented" + str(type(self)))

    def requires(self) -> List[str]:
        """List of all variable names used by this statement"""
        raise Exception("Not Implemented" + str(type(self)))

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        """Emit new instructions to the queue, executing this instruction in the context of the resolver"""
        raise Exception("Not Implemented" + str(type(self)))


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
        raise Exception("Not Implemented" + str(type(self)))

    def execute(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        """
            execute the expression, give the values provided in the requires dict.
            These values correspond to the values requested via requires_emit
        """
        raise Exception("Not Implemented" + str(type(self)))

    def requires_emit_gradual(self, resolver: Resolver, queue: QueueScheduler, resultcollector) -> Dict[object, ResultVariable]:
        return self.requires_emit(resolver, queue)


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


class GeneratorStatement(ExpressionStatement):
    """
        This statement models a statement that generates new statements
    """

    def __init__(self) -> None:
        ExpressionStatement.__init__(self)


class Literal(ExpressionStatement):

    def __init__(self, value: object) -> None:
        ExpressionStatement.__init__(self)
        self.value = value

    def normalize(self) -> None:
        pass

    def __repr__(self) -> str:
        return repr(self.value)

    def requires(self) -> List[str]:
        return []

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        return {}

    def execute(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        return self.value

    def execute_direct(self, requires: Dict[object, object]) -> object:
        return self.value


class DefinitionStatement(Statement):
    """
        This statement defines a new entity in the configuration.
    """

    def __init__(self) -> None:
        Statement.__init__(self)


class TypeDefinitionStatement(DefinitionStatement, Named):

    def __init__(self, namespace: Namespace, name: str) -> None:
        DefinitionStatement.__init__(self)
        self.name = name
        self.namespace = namespace
        self.fullName = namespace.get_full_name() + "::" + str(name)
        self.type = None  # type: NamedType

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
