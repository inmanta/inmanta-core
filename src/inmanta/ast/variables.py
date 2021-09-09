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
from typing import Dict, Generic, List, Optional, TypeVar

import inmanta.execute.dataflow as dataflow
from inmanta.ast import LocatableString, Location, NotFoundException, OptionalValueException, RuntimeException
from inmanta.ast.statements import AssignStatement, ExpressionStatement, RawResumer
from inmanta.ast.statements.assign import Assign, SetAttribute
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import Instance, QueueScheduler, RawUnit, Resolver, ResultCollector, ResultVariable
from inmanta.execute.util import NoneValue
from inmanta.parser import ParserException

LOGGER = logging.getLogger(__name__)


class Reference(ExpressionStatement):
    """
    This class represents a reference to a value
    """

    def __init__(self, name: LocatableString) -> None:
        ExpressionStatement.__init__(self)
        self.name = str(name)
        self.full_name = str(name)

    def normalize(self) -> None:
        pass

    def requires(self) -> List[str]:
        return [self.full_name]

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        # FIXME: may be done more efficient?
        out = {self.name: resolver.lookup(self.full_name)}  # type : Dict[object, ResultVariable]
        return out

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector
    ) -> Dict[object, ResultVariable]:
        var = resolver.lookup(self.full_name)
        var.listener(resultcollector, self.location)
        out = {self.name: var}  # type : Dict[object, ResultVariable]
        return out

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        return requires[self.name]

    def execute_direct(self, requires: Dict[object, object]) -> object:
        if self.name not in requires:
            raise NotFoundException(self, "Could not resolve the value %s in this static context" % self.name)
        return requires[self.name]

    def as_assign(self, value: ExpressionStatement, list_only: bool = False) -> AssignStatement:
        if list_only:
            raise ParserException(self.location, "+=", "Can not perform += on variable %s" % self.name)
        return Assign(self.name, value)

    def root_in_self(self) -> "Reference":
        if self.name == "self":
            return self
        else:
            ref = Reference("self")
            self.copy_location(ref)
            attr_ref = AttributeReference(ref, self.name)
            self.copy_location(attr_ref)
            return attr_ref

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.AssignableNodeReference:
        return graph.resolver.get_dataflow_node(self.name)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


T = TypeVar("T")


class AbstractAttributeReferenceHelper(RawResumer, Generic[T]):
    """
    Generic helper class for setting a target variable based on a Reference. Reschedules itself
    """

    def __init__(
        self, target: ResultVariable, instance: Optional[Reference], attribute: str, resultcollector: Optional[ResultCollector]
    ) -> None:
        super().__init__()
        self.target: ResultVariable = target
        self.instance: Optional[Reference] = instance
        self.attribute: str = attribute
        self.resultcollector: Optional[ResultCollector] = resultcollector
        # attribute cache
        self.variable: Optional[ResultVariable] = None

    def fetch_variable(
        self, requires: Dict[object, ResultVariable], resolver: Resolver, queue_scheduler: QueueScheduler
    ) -> ResultVariable:
        """
        Fetches the referred variable
        """
        if self.instance:
            # get the Instance
            obj = self.instance.execute({k: v.get_value() for k, v in requires.items()}, resolver, queue_scheduler)

            if isinstance(obj, list):
                raise RuntimeException(self, "can not get a attribute %s, %s is a list" % (self.attribute, obj))
            if not isinstance(obj, Instance):
                raise RuntimeException(self, "can not get a attribute %s, %s not an entity" % (self.attribute, obj))

            # get the attribute result variable
            return obj.get_attribute(self.attribute)
        else:
            return resolver.lookup(self.attribute)

    def is_ready(self) -> bool:
        """
        Returns whether this instance is ready to set the target variable
        """
        return self.variable is not None and self.variable.is_ready()

    def target_value(self) -> T:
        """
        Returns the target value based on self.variable
        """
        raise NotImplementedError()

    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        """
        Instance is ready to execute, do it and see if the variable is already present
        """
        if not self.variable:
            # this is a first time we are called, variable is not cached yet
            self.variable = self.fetch_variable(requires, resolver, queue_scheduler)

        if self.resultcollector:
            self.variable.listener(self.resultcollector, self.location)

        if self.is_ready():
            self.target.set_value(self.target_value(), self.location)
        else:
            requires[self] = self.variable
            # reschedule on the variable, XU will assign it to the target variable
            RawUnit(queue_scheduler, resolver, requires, self)

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> T:
        assert self.is_ready()
        assert self.variable
        # Attribute is ready, return it,
        return self.variable.get_value()

    def __str__(self) -> str:
        if not self.instance:
            return self.attribute
        return "%s.%s" % (self.instance, self.attribute)

    def get_location(self) -> Location:
        return self.location


class IsDefinedReferenceHelper(AbstractAttributeReferenceHelper[bool], ResultCollector[object]):
    """
    Helper class for IsDefined, reschedules itself
    """

    def __init__(self, target: ResultVariable, instance: Optional[Reference], attribute: str) -> None:
        super().__init__(target, instance, attribute, None)
        self.resultcollector = self

    def receive_result(self, value: T, location: Location) -> None:
        self.target.set_value(True, self.location)

    def target_value(self) -> bool:
        """
        Returns the target value based on self.variable.

        We don't override `resume` so this method is always called when `variable` gets frozen, even if the target variable has
        been set already. This shouldn't affect performance but the potential double set acts as a guard against inconsistent
        internal state (if `receive_result` receives a result the eventual result of this method must be True).
        """
        assert self.is_ready()
        assert self.variable
        try:
            value = self.variable.get_value()
            if isinstance(value, list):
                return len(value) != 0
            elif isinstance(value, NoneValue):
                return False
            return True
        except OptionalValueException:
            return False


class AttributeReferenceHelper(AbstractAttributeReferenceHelper[object]):
    """
    Helper class for AttributeReference, reschedules itself
    """

    def __init__(
        self, target: ResultVariable, instance: Reference, attribute: str, resultcollector: Optional[ResultCollector]
    ) -> None:
        super().__init__(target, instance, attribute, resultcollector)

    def target_value(self) -> object:
        assert self.is_ready()
        assert self.variable
        return self.variable.get_value()


class AttributeReference(Reference):
    """
    This variable refers to an attribute. This is mostly used to refer to
    attributes of a class or class instance.
    """

    def __init__(self, instance: Reference, attribute: LocatableString) -> None:
        Reference.__init__(self, "%s.%s" % (instance.full_name, attribute))
        self.attribute = str(attribute)

        # a reference to the instance
        self.instance = instance

    def requires(self) -> List[str]:
        return self.instance.requires()

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        return self.requires_emit_gradual(resolver, queue, None)

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: Optional[ResultCollector]
    ) -> Dict[object, ResultVariable]:
        # The tricky one!

        # introduce temp variable to contain the eventual result of this stmt
        temp = ResultVariable()
        temp.set_provider(self)

        # construct waiter
        resumer = AttributeReferenceHelper(temp, self.instance, self.attribute, resultcollector)
        self.copy_location(resumer)

        # wait for the instance
        RawUnit(queue, resolver, self.instance.requires_emit(resolver, queue), resumer)
        return {self: temp}

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        # helper returned: return result
        return requires[self]

    def as_assign(self, value: ExpressionStatement, list_only: bool = False) -> AssignStatement:
        return SetAttribute(self.instance, self.attribute, value, list_only)

    def root_in_self(self) -> Reference:
        out = AttributeReference(self.instance.root_in_self(), self.attribute)
        self.copy_location(out)
        return out

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.AttributeNodeReference:
        assert self.instance is not None
        return dataflow.AttributeNodeReference(self.instance.get_dataflow_node(graph), self.attribute)

    def __repr__(self) -> str:
        return "%s.%s" % (repr(self.instance), self.attribute)
