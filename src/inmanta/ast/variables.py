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

from inmanta.execute.runtime import ResultVariable, ExecutionUnit, RawUnit, HangUnit, Instance, Resolver, QueueScheduler,\
    ResultCollector
from inmanta.ast.statements.assign import Assign, SetAttribute
from inmanta.ast.statements import ExpressionStatement, AssignStatement
from inmanta.ast import RuntimeException, Locatable, Location, LocatableString
from typing import List, Dict
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

    def execute(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        return requires[self.name]

    def execute_direct(self, requires: Dict[object, object]) -> object:
        if self.name not in requires:
            raise RuntimeException(self, "Could not resolve the value %s in this static context" % self.name)
        return requires[self.name]

    def as_assign(self, value: ExpressionStatement, list_only: bool=False) -> AssignStatement:
        if list_only:
            raise ParserException(self.location, "+=", "Can not perform += on variable %s" % self.name)
        return Assign(self.name, value)

    def root_in_self(self) -> "Reference":
        if self.name == 'self':
            return self
        else:
            ref = Reference('self')
            self.copy_location(ref)
            attr_ref = AttributeReference(ref, self.name)
            self.copy_location(attr_ref)
            return attr_ref

    def __str__(self) -> str:
        return self.name

    def __repr__(self, *args, **kwargs):
        return self.name


class AttributeReferenceHelper(Locatable):
    """
        Helper class for AttributeReference, reschedules itself
    """

    def __init__(self, target: ResultVariable, instance: Reference, attribute: str, resultcollector: ResultCollector) -> None:
        Locatable.__init__(self)
        self.attribute = attribute
        self.target = target
        self.instance = instance
        self.resultcollector = resultcollector

    def resume(self,
               requires: Dict[object, ResultVariable],
               resolver: Resolver,
               queue_scheduler: QueueScheduler,
               target: ResultVariable) -> None:
        """
            Instance is ready to execute, do it and see if the attribute is already present
        """
        # get the Instance
        obj = self.instance.execute(requires, resolver, queue_scheduler)

        if isinstance(obj, list):
            raise RuntimeException(self, "can not get a attribute %s, %s is a list" % (self.attribute, obj))

        if not isinstance(obj, Instance):
            raise RuntimeException(self, "can not get a attribute %s, %s not an entity" % (self.attribute, obj))

        # get the attribute result variable
        attr = obj.get_attribute(self.attribute)
        # Cache it
        self.attr = attr

        if attr.is_ready():
            # go ahead
            # i.e. back to the AttributeReference itself
            self.target.set_value(attr.get_value(), self.location)
        else:
            # reschedule on the attribute, XU will assign it to the target variable
            if self.resultcollector is not None:
                attr.listener(self.resultcollector, self.location)
            ExecutionUnit(queue_scheduler, resolver, self.target, {"x": attr}, self)

    def execute(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        # Attribute is ready, return it,
        return self.attr.get_value()

    def __str__(self) -> str:
        return "%s.%s" % (self.instance, self.attribute)

    def get_location(self) -> Location:
        return self.location


class IsDefinedReferenceHelper(Locatable):
    """
        Helper class for AttributeReference, reschedules itself
    """

    def __init__(self, target: ResultVariable, instance: Reference, attribute: str) -> None:
        Locatable.__init__(self)
        self.attribute = attribute
        self.target = target
        self.instance = instance

    def resume(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue_scheduler: QueueScheduler) -> None:
        """
            Instance is ready to execute, do it and see if the attribute is already present
        """
        try:
            # get the Instance
            obj = self.instance.execute({k: v.get_value() for k, v in requires.items()}, resolver, queue_scheduler)

            if isinstance(obj, list):
                raise RuntimeException(self, "can not get a attribute %s, %s is a list" % (self.attribute, obj))

            # get the attribute result variable
            attr = obj.get_attribute(self.attribute)
            # Cache it
            self.attr = attr

            if attr.is_ready():
                # go ahead
                # i.e. back to the AttributeReference itself
                attr.get_value()
                self.target.set_value(True, self.location)
            else:
                requires["x"] = attr
                # reschedule on the attribute, XU will assign it to the target variable
                RawUnit(queue_scheduler, resolver, requires, self)

        except RuntimeException:
            self.target.set_value(False, self.location)

    def execute(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue_scheduler: QueueScheduler) -> object:
        # Attribute is ready, return it,
        return self.attr.get_value()


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

    def requires_emit_gradual(self, resolver: Resolver, queue: QueueScheduler, resultcollector) -> Dict[object, ResultVariable]:
        # The tricky one!

        # introduce temp variable to contain the eventual result of this stmt
        temp = ResultVariable()
        temp.set_provider(self)

        # construct waiter
        resumer = AttributeReferenceHelper(temp, self.instance, self.attribute, resultcollector)
        self.copy_location(resumer)

        # wait for the instance
        HangUnit(queue, resolver, self.instance.requires_emit(resolver, queue), None, resumer)
        return {self: temp}

    def execute(self, requires: Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        # helper returned: return result
        return requires[self]

    def as_assign(self, value: ExpressionStatement, list_only: bool=False) -> AssignStatement:
        return SetAttribute(self.instance, self.attribute, value, list_only)

    def root_in_self(self) -> Reference:
        out = AttributeReference(self.instance.root_in_self(), self.attribute)
        self.copy_location(out)
        return out

    def __repr__(self, *args, **kwargs):
        return "%s.%s" % (repr(self.instance), self.attribute)
