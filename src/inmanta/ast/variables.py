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
from inmanta.ast import LocatableString, Location, NotFoundException, OptionalValueException, Range
from inmanta.ast.statements import AssignStatement, ExpressionStatement, RawResumer, VariableReferenceHook, VariableResumer
from inmanta.ast.statements.assign import Assign, SetAttribute
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import QueueScheduler, RawUnit, Resolver, ResultCollector, ResultVariable
from inmanta.execute.util import NoneValue
from inmanta.parser import ParserException
from inmanta.stable_api import stable_api

LOGGER = logging.getLogger(__name__)


@stable_api
class Reference(ExpressionStatement):
    """
    This class represents a reference to a value

    :ivar name: The name of the Reference as a string.
    """

    def __init__(self, name: LocatableString) -> None:
        ExpressionStatement.__init__(self)
        self.locatable_name = name
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

    def get_root_variable(self) -> "Reference":
        """
        Returns the root reference node. e.g. for a.b.c.d, returns the reference for a.
        """
        return self

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
    Resumes execution on a variable when it becomes avaiable, then waits for its completeness and copies its value to a target
    variable. Optionally subscribes a result collector to intermediate values.
    """

    def __init__(self, target: ResultVariable[T], resultcollector: Optional[ResultCollector[T]]) -> None:
        super().__init__()
        self.target: ResultVariable[T] = target
        self.resultcollector: Optional[ResultCollector[T]] = resultcollector

    def write_target(self, variable: ResultVariable[object]) -> None:
        """
        Writes the target variable based on the complete variable's value.
        """
        self.target.set_value(self.target_value(variable), self.location)

    def target_value(self, variable: ResultVariable[object]) -> T:
        """
        Returns the target value based on the complete variable's value.
        """
        return variable.get_value()

    def resume(
        self,
        variable: ResultVariable[T],
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        if self.resultcollector:
            variable.listener(self.resultcollector, self.location)

        if variable.is_ready():
            self.write_target(variable)
        else:
            # reschedule on the variable's completeness
            resumer: RawResumer = VariableReadResumer(self)
            self.copy_location(resumer)
            RawUnit(queue_scheduler, resolver, {self: variable}, resumer)


class VariableReadResumer(RawResumer):
    """
    Resumes execution when the variable is complete.
    """

    def __init__(self, reader: VariableReader) -> None:
        self.reader: VariableReader = reader

    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        self.reader.write_target(requires[self.reader])

    # TODO: does this ever get called? Can we get rid of it?
    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> T:
        return self.reader.target_value(requires[self.reader])


class IsDefinedGradual(VariableReader[bool], ResultCollector[object]):
    """
    Fill target variable with is defined result as soon as it gets known.
    """

    __slots__ = ("target", "resultcollector")

    def __init__(self, target: ResultVariable) -> None:
        VariableReader.__init__(self, target, resultcollector=self)

    def receive_result(self, value: object, location: Location) -> None:
        # TODO: docstring
        self.target.set_value(True, self.location)

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

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        return self.requires_emit_gradual(resolver, queue, None)

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: Optional[ResultCollector]
    ) -> Dict[object, ResultVariable]:
        # The tricky one!

        # introduce temp variable to contain the eventual result of this stmt
        temp = ResultVariable()

        # construct waiter
        reader: VariableReader = VariableReader(target=temp, resultcollector=resultcollector)
        hook: VariableReferenceHook = VariableReferenceHook(
            self.instance,
            str(self.attribute),
            variable_resumer=reader,
        )
        self.copy_location(reader)
        self.copy_location(hook)
        hook.schedule(resolver, queue)

        # wait for the attribute value
        return {self: temp}

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
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
