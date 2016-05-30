"""
    Copyright 2016 Inmanta

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

from impera.execute.runtime import ResultVariable, WaitUnit, ExecutionUnit
from impera.ast.statements.assign import Assign, SetAttribute
from impera.ast.statements import ExpressionStatement

LOGGER = logging.getLogger(__name__)


class Reference(ExpressionStatement):
    """
        This class represents a reference to a value
    """

    def __init__(self, name):
        self.name = name
        self.full_name = name

    def normalize(self):
        pass

    def requires(self):
        return [self.full_name]

    def requires_emit(self, resolver, queue):
        # FIXME: may be done more efficient?
        out = {self.name: resolver.lookup(self.full_name)}
        return out

    def execute(self, requires, resolver, queue):
        return requires[self.name]

    def get_containing_namespace(self,):
        return self.namespace

    def as_assign(self, value):
        return Assign(self.name, value)


class AttributeReferenceHelper(object):
    """
        Helper class for AttributeReference, reschedules itself
    """

    def __init__(self, target, instance, attribute):
        self.attribute = attribute
        self.target = target
        self.instance = instance

    def resume(self, requires, resolver, queue_scheduler):
        """
            Instance is ready to execute, do it and see if the attribute is already present
        """
        # get the Instance
        obj = self.instance.execute(requires, resolver, queue_scheduler)
        # get the attribute result variable
        attr = obj.get_attribute(self.attribute)
        # Cache it
        self.attr = attr

        if attr.is_ready():
            # go ahead
            # i.e. back to the AttributeReference itself
            self.target.set_value(attr.get_value())
        else:
            # reschedule on the attribute, XU will assign it to the target variable
            ExecutionUnit(queue_scheduler, resolver, self.target, {"x": attr}, self)

    def execute(self, requires, resolver, queue):
        # Attribute is ready, return it,
        return self.attr.get_value()


class AttributeReference(Reference):
    """
        This variable refers to an attribute. This is mostly used to refer to
        attributes of a class or class instance.
    """

    def __init__(self, instance, attribute):
        Reference.__init__(self, instance)
        self.attribute = attribute

        # a reference to the instance
        self.instance = instance

        # if the reference resolves, this attribute contains the instance
        self._instance_value = None

    def requires(self):
        return self.instance.requires()

    def requires_emit(self, resolver, queue):
        # The tricky one!

        # introduce temp variable to contain the eventual result of this stmt
        temp = ResultVariable()
        temp.set_provider(self)

        # construct waiter
        resumer = AttributeReferenceHelper(temp, self.instance, self.attribute)
        self.copy_location(resumer)

        # wait for the instance
        WaitUnit(queue, resolver, self.instance.requires_emit(resolver, queue), resumer)
        return {self: temp}

    def execute(self, requires, resolver, queue):
        # helper returned: return result
        return requires[self]

    def as_assign(self, value):
        return SetAttribute(self.instance, self.attribute, value)
