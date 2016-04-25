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

from impera.execute.util import Unknown
from impera.execute.runtime import ResultVariable, ListVariable, OptionVariable, AttributeVariable


class Attribute(object):
    """
        The attribute base class for entity attributes.

        @param entity: The entity this attribute belongs to
    """

    def __init__(self, entity, value_type, name):
        self.__name = name  # : String

        entity.add_attribute(self)
        self.__entity = entity
        self.__type = value_type

    def get_type(self):
        """
            Get the type of this data item
        """
        return self.__type

    type = property(get_type)

    def get_name(self):
        """
            Get the name of the attribute. This is the name this attribute
            is associated with in the entity.
        """
        return self.__name

    name = property(get_name)

    def __hash__(self):
        """
            The hash of this object is based on the name of the attribute
        """
        return hash(self.__name)

    def __repr__(self):
        return self.__name

    def get_entity(self):
        """
            Return the entity this attribute belongs to
        """
        return self.__entity

    entity = property(get_entity)

    def validate(self, value):
        """
            Validate a value that is going to be assigned to this attribute
        """
        if (not hasattr(value, "is_unknown") or not value.is_unknown()) and not isinstance(value, Unknown):
            self.type.validate(value)

    def get_new_Result_Variable(self, instance, queue):
        out = ResultVariable()
        out.set_type(self.__type)
        out.set_provider(instance)
        return out


class RelationAttribute(Attribute):
    """
        An attribute that is a relation
    """

    def __init__(self, entity, value_type, name):
        Attribute.__init__(self, entity, value_type, name)
        self.end = None
        self.low = 1
        self.high = 1
        self.depends = False

    def __repr__(self):
        return "[%s:%s] %s" % (self.low, self.high, self.name)

    def set_multiplicity(self, values):
        """
            Set the multiplicity of this end
        """
        self.low = values[0]
        self.high = values[1]

    def get_new_Result_Variable(self, instance, queue):
        if self.low == 1 and self.high == 1:
            out = AttributeVariable(self, instance)
        elif self.low == 0 and self.high == 1:
            out = OptionVariable(self, instance, queue)
        else:
            out = ListVariable(self, instance, queue)
        out.set_type(self.get_type())
        out.set_provider(self)
        return out
