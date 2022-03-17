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
from inmanta.ast import Locatable, LocatableString, Location, NotFoundException, OptionalValueException, Range, RuntimeException
from inmanta.ast.statements import AssignStatement, ConditionalPromiseABC, ExpressionStatement, RawResumer, Statement
from inmanta.ast.statements.assign import Assign, SetAttribute
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import Instance, ProgressionPromise, QueueScheduler, RawUnit, Resolver, ResultCollector, ResultVariable
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


# TODO: name
# TODO: generic?
class AttributeReferenceActionABC(Locatable):
    # TODO: docstring

    def __init__(self) -> None:
        super().__init__()

    # TODO: name
    def resolve(
        self,
        attribute: ResultVariable,
        requires: Dict[object, ResultVariable],
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        # TODO
        pass

    # TODO: str and repr


# TODO; is this even an ABC anymore? Looks pretty concrete to me
class AttributeReferenceHelperABC(RawResumer):
    # TODO: docstring
    """
    Generic helper class for accessing an instance attribute. Triggers action with the attribute's ResultVariable
    as soon as it's available.
    """
    # TODO: this might not work: different subscribers have different resolvers => single action

    def __init__(
        # TODO: can we make this non-optional?
        self, instance: Optional[Reference], attribute: str, action: AttributeReferenceActionABC,
    ) -> None:
        super().__init__()
        self.instance: Optional[Reference] = instance
        self.attribute: str = attribute
        # TODO: name
        self.action: AttributeReferenceActionABC = action

    def _fetch_variable(
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

    def schedule(self, resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        RawUnit(
            queue_scheduler,
            resolver,
            self.instance.requires_emit(resolver, queue_scheduler) if self.instance is not None else {},
            self,
        )

    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        # TODO: update docstring
        """
        Instance is ready to execute, do it and see if the variable is already present
        """
        self.action.resolve(self._fetch_variable(requires, resolver, queue_scheduler), requires, resolver, queue_scheduler)

    # TODO: execute method implementation required -> return None? Don't implement? Why even is RawResumer(ExpressionStatement)?

    # TODO: str and repr


class AttributeReferencePromise(AttributeReferenceActionABC, ConditionalPromiseABC):
    # TODO: docstring

    def __init__(self, provider: Statement) -> None:
        super().__init__()
        self.provider: Statement = provider
        self._promise: Optional[ProgressionPromise] = None
        # TODO: add single responsible per block for this?
        self._fulfilled: bool = False

    def resolve(
        self,
        attribute: ResultVariable,
        requires: Dict[object, ResultVariable],
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        # TODO: docstring
        if self._fulfilled:
            # already fulfilled, no need to acquire additional promises
            return
        # TODO: raise exception if self._promise already set?
        # TODO: get_progression_promise only exists on DRV
        self._promise = attribute.get_progression_promise(self.provider)

    def fulfill(self) -> None:
        # TODO: docstring
        if self._fulfilled:
            # already fulfilled, no need to continue
            return
        if self._promise is not None:
            self._promise.fulfill()
        self._fulfilled = True


T = TypeVar("T")


# TODO: name
class AttributeReferenceRead(AttributeReferenceActionABC, RawResumer, Generic[T]):
    # TODO: docstring (mention resultcollector)

    def __init__(
        self, target: ResultVariable[T], resultcollector: Optional[ResultCollector[T]]
    ) -> None:
        super().__init__()
        self.target: ResultVariable[T] = target
        self.resultcollector: Optional[ResultCollector[T]] = resultcollector
        # attribute cache
        self.attribute: Optional[ResultVariable[T]] = None

    def target_value(self) -> T:
        """
        Returns the target value based on the attribute variable's value
        """
        # TODO: can we get rid of these assertions?
        assert self.attribute
        assert self.attribute.is_ready()
        return self.attribute.get_value()

    def resolve(
        self,
        attribute: ResultVariable[T],
        requires: Dict[object, ResultVariable],
        resolver: Resolver,
        queue_scheduler: QueueScheduler,
    ) -> None:
        self.attribute = attribute

        if self.resultcollector:
            self.attribute.listener(self.resultcollector, self.location)

        if self.attribute.is_ready():
            self.target.set_value(self.target_value(), self.location)
        else:
            # reschedule on the attribute's completeness
            RawUnit(queue_scheduler, resolver, {self: self.attribute}, self)

    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        # TODO: docstring
        # TODO: assert / raise exception for self.attribute is None
        self.target.set_value(self.target_value(), self.location)

    # TODO: does this ever get called?
    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> T:
        assert self.attribute
        assert self.attribute.is_ready()
        # Attribute is ready, return it,
        return self.attribute.get_value()


class IsDefinedGradual(AttributeReferenceRead[bool], ResultCollector[object]):
    # TODO: docstring

    def __init__(self, target: ResultVariable) -> None:
        AttributeReferenceRead.__init__(self, target, resultcollector=self)

    def receive_result(self, value: object, location: Location) -> None:
        # TODO: docstring
        self.target.set_value(True, self.location)

    def target_value(self) -> bool:
        """
        Returns the target value based on the attribute variable's value or absence of a value.

        We don't override `resume` so this method is always called when `variable` gets frozen, even if the target variable has
        been set already. This shouldn't affect performance but the potential double set acts as a guard against inconsistent
        internal state (if `receive_result` receives a result the eventual result of this method must be True).
        """
        assert self.attribute
        assert self.attribute.is_ready()
        try:
            value = self.attribute.get_value()
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
        reader: AttributeReferenceRead = AttributeReferenceRead(target=temp, resultcollector=resultcollector)
        resumer: AttributeReferenceHelperABC = AttributeReferenceHelperABC(
            self.instance,
            str(self.attribute),
            action=reader,
        )
        self.copy_location(reader)
        self.copy_location(resumer)
        resumer.schedule(resolver, queue)

        # wait for the attribute value
        return {self: temp}

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        # helper returned: return result
        return requires[self]

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
