"""
Copyright 2018 Inmanta

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

from typing import Optional

from inmanta.types import JsonType

"""
    Objects defining the serialization format for type information.

    Types are exported as a Dict[str, :class:`.Entity` ]
"""


class Location:
    """
    Position in the source

    :param str file:  source file name
    :param int lnr: line in the source file
    """

    def __init__(self, file: str, lnr: int) -> None:
        self.file = file
        self.lnr = lnr

    def to_dict(self) -> JsonType:
        """
        Convert to serialized form:

        .. code-block:: python

            {
                "file": self.file,
                "lnr": self.lnr
            }
        """
        return {"file": self.file, "lnr": self.lnr}

    @staticmethod
    def from_dict(ctx: JsonType) -> "Location":
        return Location(**ctx)


class Attribute:
    """
    Attribute defined on an entity

    :param str mytype: fully qualified name of the type of this attribute
    :param bool nullable: can this attribute be null
    :param bool multi: is this attribute a list
    :param str comment: docstring for this attribute
    :param inmanta.model.Location location: source location where this attribute is defined
    """

    def __init__(self, mytype: str, nullable: bool, multi: bool, comment: str, location: Location) -> None:
        self.type = mytype
        self.nullable = nullable
        self.multi = multi
        self.comment = comment
        self.location = location

        if comment is None:
            self.comment = ""

    def to_dict(self) -> JsonType:
        """
        Convert to serialized form:

        .. code-block:: python

            {
                "type": self.type,
                "multi": self.multi,
                "nullable": self.nullable,
                "comment": self.comment,
                "location": self.location.to_dict()
            }
        """
        return {
            "type": self.type,
            "multi": self.multi,
            "nullable": self.nullable,
            "comment": self.comment,
            "location": self.location.to_dict(),
        }

    @staticmethod
    def from_dict(ctx: JsonType) -> None:
        return Attribute(
            mytype=ctx["type"],
            nullable=ctx["nullable"],
            multi=ctx["multi"],
            comment=ctx["comment"],
            location=Location.from_dict(ctx["location"]),
        )

    @staticmethod
    def from_list(lst: list[JsonType]) -> dict[str, "Attribute"]:
        return {n: Attribute.from_dict(x) for n, x in lst.items()}


class Value:
    """A value reference from a type either :class:`.DirectValue` or :class:`.ReferenceValue`"""

    @staticmethod
    def from_list(lst: list[JsonType]) -> list["Value"]:
        return [Value.from_dict(x) for x in lst]

    @staticmethod
    def from_dict(ctx: JsonType) -> "Value":
        if "value" in ctx:
            return DirectValue.from_dict(ctx)
        else:
            return ReferenceValue.from_dict(ctx)


class DirectValue(Value):
    """A primitive value, directly represented in the serialized form.

    :param value: the value itself, as string or number
    """

    def __init__(self, value: Value):
        self.value = value

    def to_dict(self) -> JsonType:
        """
        Convert to serialized form:

        .. code-block:: python

            {"value": self.value}
        """
        return {"value": self.value}

    @staticmethod
    def from_dict(ctx: JsonType) -> "DirectValue":
        return DirectValue(**ctx)


class ReferenceValue(Value):
    """
    A reference to an instance of an entity.

    :param str reference: the handle for the entity this value refers to
    """

    def __init__(self, reference):
        self.reference = reference

    def to_dict(self) -> JsonType:
        """
        Convert to serialized form:

        .. code-block:: python

            {"reference": self.reference}
        """
        return {"reference": self.reference}

    @staticmethod
    def from_dict(ctx: JsonType) -> "ReferenceValue":
        return ReferenceValue(**ctx)


class Relation:
    """
    A relation between two entities.

    :param str mytype: the type this relation refers to
    :param Tuple[int, int] multi: the multiplicity of this relation in the form (lower,upper), -1 for unbounded
    :param str reverse: the fully qualified name of the inverse relation
    :param inmanta.model.Location location: source location this relation was defined at
    :param List[Value] source_annotations: annotations on this relation on the source side
    :param List[Value] target_annotations: annotations on this relation on the target side
    """

    def __init__(
        self,
        mytype: str,
        multi: tuple[int, Optional[int]],
        reverse: str,
        comment: str,
        location: Location,
        source_annotations: list[Value],
        target_annotations: list[Value],
    ) -> None:
        self.type = mytype
        lower = multi[0]
        upper = multi[1]
        if upper is None:
            upper = -1
        self.multi = (lower, upper)
        self.reverse = reverse
        self.comment = comment
        self.location = location
        self.source_annotations = source_annotations
        self.target_annotations = target_annotations
        if comment is None:
            self.comment = ""

    def to_dict(self) -> JsonType:
        """
        Convert to serialized form:

        .. code-block:: python

           {
            "type": self.type,
            "multi": [self.multi[0], self.multi[1]],
            "reverse": self.reverse,
            "comment": self.comment,
            "location": self.location.to_dict(),
            "source_annotations": [x.to_dict() for x in self.source_annotations],
            "target_annotations": [x.to_dict() for x in self.target_annotations]
            }
        """
        return {
            "type": self.type,
            "multi": [self.multi[0], self.multi[1]],
            "reverse": self.reverse,
            "comment": self.comment,
            "location": self.location.to_dict(),
            "source_annotations": [x.to_dict() for x in self.source_annotations],
            "target_annotations": [x.to_dict() for x in self.target_annotations],
        }

    @staticmethod
    def from_dict(ctx: JsonType) -> "Relation":
        multi = ctx["multi"]
        return Relation(
            ctx["type"],
            (multi[0], multi[1]),
            ctx["reverse"],
            ctx["comment"],
            Location.from_dict(ctx["location"]),
            Value.from_list(ctx["source_annotations"]),
            Value.from_list(ctx["target_annotations"]),
        )

    @staticmethod
    def from_list(lst: JsonType) -> dict[str, "Relation"]:
        return {n: Relation.from_dict(x) for n, x in lst.items()}


class Entity:
    """
    An entity type

    :param List[str] parents: parent types
    :param  Dict[str, Attribute]: all attributes declared on this entity directly, by name
    :param  Dict[str, Relation]: all relations declared on this entity directly, by name
    :param inmanta.model.Location location: source location this entity was defined at
    """

    def __init__(
        self, parents: list[str], attributes: dict[str, Attribute], relations: dict[str, Relation], location: Location
    ) -> None:
        self.parents = parents
        self.attributes = attributes
        self.relations = relations
        self.location = location

    def to_dict(self) -> JsonType:
        """
        Convert to serialized form:

        .. code-block:: python

            {
            "parents": self.parents,
            "attributes": {n: a.to_dict() for n, a in self.attributes.items()},
            "relations": {n: r.to_dict() for n, r in self.relations.items()},
            "location": self.location.to_dict(),
            }
        """
        return {
            "parents": self.parents,
            "attributes": {n: a.to_dict() for n, a in self.attributes.items()},
            "relations": {n: r.to_dict() for n, r in self.relations.items()},
            "location": self.location.to_dict(),
        }

    @staticmethod
    def from_dict(ctx: JsonType) -> "Entity":
        return Entity(
            ctx["parents"],
            Attribute.from_list(ctx["attributes"]),
            Relation.from_list(ctx["relations"]),
            Location.from_dict(ctx["location"]),
        )
