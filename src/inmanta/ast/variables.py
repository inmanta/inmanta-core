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

import logging
from collections.abc import Mapping
from typing import Dict, Generic, List, Optional, TypeVar

import inmanta.execute.dataflow as dataflow
from inmanta.ast import LocatableString, Location, NotFoundException, OptionalValueException, Range, RuntimeException
from inmanta.ast.statements import (
    AssignStatement,
    ExpressionStatement,
    RawResumer,
    Statement,
    VariableReferenceHook,
    VariableResumer,
)
from inmanta.ast.statements.assign import Assign, SetAttribute
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import QueueScheduler, RawUnit, Resolver, ResultCollector, ResultVariable, VariableABC
from inmanta.execute.util import NoneValue
from inmanta.parser import ParserException
from inmanta.stable_api import stable_api

LOGGER = logging.getLogger(__name__)


R = TypeVar("R", bound="Reference")


@stable_api
class Reference(ExpressionStatement):
    """
    This class represents a reference to a value

    :ivar name: The name of the Reference as a string.
    """

    __slots__ = ("locatable_name", "name", "full_name")

    def __init__(self, name: LocatableString) -> None:
        ExpressionStatement.__init__(self)
        self.locatable_name = name
        self.name = str(name)
        self.full_name = str(name)

    def normalize(self) -> None:
        pass

    def requires(self) -> List[str]:
        return [self.full_name]

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, VariableABC]:
        parent_req: Mapping[object, VariableABC] = super().requires_emit(resolver, queue)
        # FIXME: may be done more efficient?
        out: Mapping[object, VariableABC] = {self.name: resolver.lookup(self.full_name)}
        return {**parent_req, **out}

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector
    ) -> Dict[object, VariableABC]:
        promises: Mapping[object, VariableABC] = self._requires_emit_promises(resolver, queue)
        var: ResultVariable = resolver.lookup(self.full_name)
        var.listener(resultcollector, self.location)
        out: Mapping[object, VariableABC] = {self.name: var}
        return {**promises, **out}

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        super().execute(requires, resolver, queue)
        return requires[self.name]

    def execute_direct(self, requires: Dict[object, object]) -> object:
        if self.name not in requires:
            raise NotFoundException(self, "Could not resolve the value %s in this static context" % self.name)
        return requires[self.name]

    def get_root_variable(self) -> "Reference":
        """
        Returns the root reference node. e.g. for a.b.c.d, returns the reference for a.
        """
        return self

    def fully_qualified(self: R) -> R:
        """
        If this reference is already fully qualified, returns it unchanged. Otherwise, returns a new fully qualified reference
        to this name in this reference's namespace.
        This fully qualified reference is not guaranteed to resolve to the same object. It is the caller's responsibility to
        only request a fully qualified name when appropriate.
        """
        if "::" in self.name:
            return self
        fully_qualified_name: str = f"{self.namespace.name}::{self.name}"
        locatable: LocatableString = LocatableString(
            fully_qualified_name, Range("__internal__", 1, 1, 1, 1), -1, self.namespace
        )
        result: R = self.__class__(locatable)
        result.location = locatable.location
        return result

    def as_assign(self, value: ExpressionStatement, list_only: bool = False) -> AssignStatement:
        if list_only:
            raise ParserException(self.location, "+=", "Can not perform += on variable %s" % self.name)
        return Assign(self.locatable_name, value)

    def root_in_self(self) -> "Reference":
        if self.name == "self":
            return self
        else:
            ref = Reference("self")
            self.copy_location(ref)
            attr_ref = AttributeReference(ref, self.locatable_name)
            self.copy_location(attr_ref)
            return attr_ref

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.AssignableNodeReference:
        return graph.resolver.get_dataflow_node(self.name)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


T = TypeVar("T")


class VariableReader(VariableResumer, RawResumer, Generic[T]):
    """
    Resumes execution on a variable when it becomes avaiable, then waits for its completeness and copies its value to a target
    variable. Optionally subscribes a result collector to intermediate values.
    """

    __slots__ = ("owner", "target", "resultcollector")

    def __init__(self, owner: Statement, target: ResultVariable[T], resultcollector: Optional[ResultCollector[T]]) -> None:
        super().__init__()
        self.owner: Statement = owner
        self.target: ResultVariable[T] = target
        self.resultcollector: Optional[ResultCollector[T]] = resultcollector

    def write_target(self, variable: VariableABC[object]) -> None:
        """
        Writes the target variable based on the complete variable's value.
        """
        self.target.set_value(self.target_value(variable), self.owner.location)

    def target_value(self, variable: VariableABC[object]) -> T:
        """
        Returns the target value based on the complete variable's value.
        """
        try:
            return variable.get_value()
        except OptionalValueException as e:
            e.set_statement(self.owner)
            e.location = self.owner.location
            raise e

    def variable_resume(
        self,
        variable: ResultVariable[T],
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        if self.resultcollector:
            variable.listener(self.resultcollector, self.owner.location)

        if variable.is_ready():
            self.write_target(variable)
        else:
            # reschedule on the variable's completeness
            RawUnit(queue_scheduler, resolver, {self: variable}, self, override_exception_location=False)

    def resume(self, requires: Dict[object, VariableABC], resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        self.write_target(requires[self])

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        raise RuntimeException(self, "%s is not an actual AST node, it should never be executed" % self.__class__.__name__)

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        raise RuntimeException(self, "%s is not an actual AST node, it should never be executed" % self.__class__.__name__)


class IsDefinedGradual(VariableReader[bool], ResultCollector[object]):
    """
    Fill target variable with is defined result as soon as it gets known.
    """

    __slots__ = ()

    def __init__(self, owner: Statement, target: ResultVariable) -> None:
        VariableReader.__init__(self, owner, target, resultcollector=self)

    def receive_result(self, value: object, location: Location) -> None:
        """
        Gradually receive an assignment to the referenced variable. Sets the target variable to True because to receive a single
        value implies that the variable is defined.
        """
        self.target.set_value(True, self.owner.location)

    def target_value(self, variable: ResultVariable[object]) -> bool:
        """
        Returns the target value based on the attribute variable's value or absence of a value.

        We don't override `resume` so this method is always called when `variable` gets frozen, even if the target variable has
        been set already. This shouldn't affect performance but the potential double set acts as a guard against inconsistent
        internal state (if `receive_result` receives a result the eventual result of this method must be True).
        """
        try:
            value = variable.get_value()
            if isinstance(value, list):
                return len(value) != 0
            elif isinstance(value, NoneValue):
                return False
            return True
        except OptionalValueException:
            return False


class AttributeReference(Reference):
    """
    This variable refers to an attribute. This is mostly used to refer to
    attributes of a class or class instance.
    """

    __slots__ = ("attribute", "instance")

    def __init__(self, instance: Reference, attribute: LocatableString) -> None:
        range: Range = Range(
            instance.locatable_name.location.file,
            instance.locatable_name.lnr,
            instance.locatable_name.start,
            attribute.elnr,
            attribute.end,
        )
        reference: LocatableString = LocatableString(
            "%s.%s" % (instance.full_name, attribute), range, instance.locatable_name.lexpos, instance.namespace
        )
        Reference.__init__(self, reference)
        self.attribute = attribute

        # a reference to the instance
        self.instance = instance

    def requires(self) -> List[str]:
        return self.instance.requires()

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, VariableABC]:
        return self.requires_emit_gradual(resolver, queue, None)

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: Optional[ResultCollector]
    ) -> Dict[object, VariableABC]:
        promises: Mapping[object, VariableABC] = self._requires_emit_promises(resolver, queue)

        # The tricky one!

        # introduce temp variable to contain the eventual result of this stmt
        temp = ResultVariable()

        # construct waiter
        reader: VariableReader = VariableReader(owner=self, target=temp, resultcollector=resultcollector)
        hook: VariableReferenceHook = VariableReferenceHook(
            self.instance,
            str(self.attribute),
            variable_resumer=reader,
        )
        self.copy_location(hook)
        hook.schedule(resolver, queue)

        # wait for the attribute value
        return {**promises, self: temp}

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        ExpressionStatement.execute(self, requires, resolver, queue)
        # helper returned: return result
        return requires[self]

    def get_root_variable(self) -> "Reference":
        """
        Returns the root reference node. e.g. for a.b.c.d, returns the reference for a.
        """
        return self.instance.get_root_variable()

    def as_assign(self, value: ExpressionStatement, list_only: bool = False) -> AssignStatement:
        return SetAttribute(self.instance, str(self.attribute), value, list_only)

    def root_in_self(self) -> Reference:
        out = AttributeReference(self.instance.root_in_self(), str(self.attribute))
        self.copy_location(out)
        return out

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.AttributeNodeReference:
        assert self.instance is not None
        return dataflow.AttributeNodeReference(self.instance.get_dataflow_node(graph), str(self.attribute))

    def __repr__(self) -> str:
        return "%s.%s" % (repr(self.instance), str(self.attribute))
