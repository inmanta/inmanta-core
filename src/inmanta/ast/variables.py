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
from collections import abc
from typing import Generic, Optional, TypeVar

import inmanta.execute.dataflow as dataflow
from inmanta.ast import LocatableString, Location, NotFoundException, OptionalValueException, Range, RuntimeException
from inmanta.ast.statements import (
    AssignStatement,
    AttributeAssignmentLHS,
    ExpressionStatement,
    RawResumer,
    Statement,
    VariableReferenceHook,
    VariableResumer,
)
from inmanta.ast.statements.assign import Assign, SetAttribute
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import (
    QueueScheduler,
    RawUnit,
    Resolver,
    ResultCollector,
    ResultVariable,
    ResultVariableProxy,
    VariableABC,
    WrappedValueVariable,
)
from inmanta.execute.util import NoneValue, Unknown
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

    def normalize(self, *, lhs_attribute: Optional[AttributeAssignmentLHS] = None) -> None:
        split: abc.Sequence[str] = self.name.rsplit("::", maxsplit=1)
        if len(split) > 1:
            # fail-fast if namespace does not exist
            try:
                self.namespace.lookup_namespace(split[0])
            except NotFoundException as e:
                e.set_statement(self)
                raise

    def requires(self) -> list[str]:
        return [self.full_name]

    def requires_emit(
        self, resolver: Resolver, queue: QueueScheduler, *, propagate_unset: bool = False
    ) -> dict[object, VariableABC]:
        requires: dict[object, VariableABC] = super().requires_emit(resolver, queue)
        # FIXME: may be done more efficient?
        requires[self.name] = resolver.lookup(self.full_name)
        return requires

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector, *, propagate_unset: bool = False
    ) -> dict[object, VariableABC]:
        result: dict[object, VariableABC] = self.requires_emit(resolver, queue, propagate_unset=propagate_unset)
        var: VariableABC = result[self.name]
        assert isinstance(var, ResultVariable)
        listener_registered: bool = var.listener(resultcollector, self.location)
        if not listener_registered:
            # pass on resultcollector for explicit reporting in execute
            result[(self, ResultCollector)] = WrappedValueVariable(resultcollector)
        return result

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        return requires[self.name]

    def execute_direct(self, requires: abc.Mapping[str, object]) -> object:
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


class VariableReader(VariableResumer, Generic[T]):
    """
    Resumes execution on a variable when it becomes avaiable, then connects the target proxy variable to it.
    Optionally subscribes a result collector to intermediate values.
    """

    __slots__ = ("target",)

    def __init__(self, target: ResultVariableProxy[T]) -> None:
        super().__init__()
        self.target: ResultVariableProxy[T] = target

    def variable_resume(
        self,
        variable: VariableABC[T],
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        self.target.connect(variable)


class IsDefinedGradual(VariableResumer, RawResumer, ResultCollector[object]):
    """
    Fill target variable with is defined result as soon as it gets known.
    """

    __slots__ = ("owner", "target")

    def __init__(self, owner: Statement, target: ResultVariable[bool]) -> None:
        super().__init__()
        self.owner: Statement = owner
        self.target: ResultVariable[bool] = target

    def pure_gradual(self) -> bool:
        # freezing an empty variable causes progress
        return False

    def receive_result(self, value: object, location: Location) -> bool:
        """
        Gradually receive an assignment to the referenced variable. Sets the target variable to True because to receive a single
        value implies that the variable is defined.
        """
        if isinstance(value, Unknown):
            # value may or may not be defined, nothing can be decided yet
            return False
        self.target.set_value(True, self.owner.location)
        return True

    def variable_resume(
        self,
        variable: VariableABC[object],
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        if variable.is_ready():
            self.target.set_value(self._target_value(variable), self.owner.location)
        else:
            # gradual execution: as soon as a value comes in, the result is known
            variable.listener(self, self.owner.location)
            # wait for variable completeness in case no value comes in at all
            RawUnit(queue_scheduler, resolver, {self: variable}, self, override_exception_location=False)

    def resume(self, requires: dict[object, VariableABC], resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        self.target.set_value(self._target_value(requires[self]), self.owner.location)

    def _target_value(self, variable: VariableABC[object]) -> bool | Unknown:
        """
        Returns the target value based on the attribute variable's value or absence of a value.
        """
        try:
            value = variable.get_value()
            if isinstance(value, Unknown):
                return Unknown(self)
            if isinstance(value, list):
                if len(value) == 0:
                    return False
                elif all(isinstance(v, Unknown) for v in value):
                    return Unknown(self)
                else:
                    return True
            elif isinstance(value, NoneValue):
                return False
            return True
        except OptionalValueException:
            return False

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        raise RuntimeException(self, "%s is not an actual AST node, it should never be executed" % self.__class__.__name__)

    def execute(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        raise RuntimeException(self, "%s is not an actual AST node, it should never be executed" % self.__class__.__name__)


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
            f"{instance.full_name}.{attribute}", range, instance.locatable_name.lexpos, instance.namespace
        )
        Reference.__init__(self, reference)
        self.attribute = attribute

        # a reference to the instance
        self.instance = instance

    def requires(self) -> list[str]:
        return self.instance.requires()

    def requires_emit(
        self, resolver: Resolver, queue: QueueScheduler, *, propagate_unset: bool = False
    ) -> dict[object, VariableABC]:
        return self.requires_emit_gradual(resolver, queue, None, propagate_unset=propagate_unset)

    def requires_emit_gradual(
        self,
        resolver: Resolver,
        queue: QueueScheduler,
        resultcollector: Optional[ResultCollector],
        *,
        propagate_unset: bool = False,
    ) -> dict[object, VariableABC]:
        requires: dict[object, VariableABC] = self._requires_emit_promises(resolver, queue)

        # The tricky one!

        # introduce proxy variable to point to the eventual result of this stmt
        proxy: ResultVariableProxy[object] = ResultVariableProxy(
            listener=(resultcollector, self.location) if resultcollector is not None else None,
        )
        # construct waiter
        reader: VariableReader = VariableReader(target=proxy)
        hook: VariableReferenceHook = VariableReferenceHook(
            self.instance,
            str(self.attribute),
            variable_resumer=reader,
            propagate_unset=propagate_unset,
        )
        self.copy_location(hook)
        hook.schedule(resolver, queue)
        # wait for the attribute value
        requires[self] = proxy

        return requires

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
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
        return f"{repr(self.instance)}.{self.attribute}"
