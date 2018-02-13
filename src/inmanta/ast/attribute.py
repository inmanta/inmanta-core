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

from inmanta.ast import Locatable, RuntimeException, TypingException
from inmanta.ast.type import TypedList, NullableType
from inmanta.execute.runtime import ResultVariable, ListVariable, OptionVariable, AttributeVariable, QueueScheduler
from inmanta.execute.util import Unknown
from typing import List


try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast.type import Type  # noqa: F401
    from inmanta.execute.runtime import Instance  # noqa: F401
    from inmanta.ast.entity import Entity  # noqa: F401


class Attribute(Locatable):
    """
        The attribute base class for entity attributes.

        @param entity: The entity this attribute belongs to
    """

    def __init__(self, entity: "Entity", value_type: "Type", name: str, multi: bool=False, nullable=False) -> None:
        Locatable.__init__(self)
        self.__name = name
        entity.add_attribute(self)
        self.__entity = entity
        self.__type = value_type
        self.__multi = multi
        self.__nullallble = nullable
        self.comment = None  # type: str

    def get_type(self) -> "Type":
        """
            Get the type of this data item
        """
        return self.__type

    type = property(get_type)

    def get_name(self) -> str:
        """
            Get the name of the attribute. This is the name this attribute
            is associated with in the entity.
        """
        return self.__name

    name = property(get_name)

    def __hash__(self) -> "int":
        """
            The hash of this object is based on the name of the attribute
        """
        return hash(self.__name)

    def __repr__(self) -> str:
        return self.__name

    def get_entity(self) -> "Entity":
        """
            Return the entity this attribute belongs to
        """
        return self.__entity

    entity = property(get_entity)

    def validate(self, value: object) -> None:
        """
            Validate a value that is going to be assigned to this attribute
        """
        if not isinstance(value, Unknown):
            self.type.validate(value)

    def get_new_result_variable(self, instance: "Instance", queue: QueueScheduler) -> ResultVariable:
        if self.__multi:
            mytype = (TypedList(self.__type))
        else:
            mytype = (self.__type)

        if(self.__nullallble):
            # be a 0-1 relation
            self.end = None
            self.low = 0
            self.high = 1
            out = OptionVariable(self, instance, queue)
            mytype = NullableType(mytype)
        else:
            out = ResultVariable()

        out.set_type(mytype)
        out.set_provider(instance)
        return out

    def is_optional(self):
        return self.__nullallble

    def is_multi(self):
        return self.__multi

    def final(self, excns: List[Exception]) -> None:
        pass


class RelationAttribute(Attribute):
    """
        An attribute that is a relation
    """

    def __init__(self, entity: "Entity", value_type: "Type", name: str) -> None:
        Attribute.__init__(self, entity, value_type, name)
        self.end = None  # type: RelationAttribute
        self.low = 1
        self.high = 1
        self.depends = False
        self.source_annotations = []
        self.target_annotations = []

    def __repr__(self) -> str:
        return "[%d:%s] %s" % (self.low, self.high if self.high is not None else "", self.name)

    def set_multiplicity(self, values: "Tuple[int, int]") -> None:
        """
            Set the multiplicity of this end
        """
        self.low = values[0]
        self.high = values[1]

    def get_new_result_variable(self, instance: "Instance", queue: QueueScheduler) -> ResultVariable:
        if self.low == 1 and self.high == 1:
            out = AttributeVariable(self, instance)  # type: ResultVariable
        elif self.low == 0 and self.high == 1:
            out = OptionVariable(self, instance, queue)  # type: ResultVariable
        else:
            out = ListVariable(self, instance, queue)  # type: ResultVariable
        out.set_type(self.get_type())
        return out

    def is_optional(self):
        return self.low == 0

    def is_multi(self):
        return self.high != 1

    def final(self, excns: List[Exception]) -> None:
        for rv in self.source_annotations:
            try:
                if isinstance(rv.get_value(), Unknown):
                    excns.append(TypingException(self, "Relation annotation can not be Unknown"))
            except RuntimeException as e:
                excns.append(e)
        for rv in self.target_annotations:
            try:
                if isinstance(rv.get_value(), Unknown):
                    excns.append(TypingException(self, "Relation annotation can not be Unknown"))
            except RuntimeException as e:
                excns.append(e)
