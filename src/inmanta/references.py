"""
    Copyright 2024 Inmanta

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
# This file holds reference equivalents for primive types (excluding lists and dicts). Currently they are
# both a reference and a real value. For a string it is easy to provide a mock value, for a number it is not
# so much.

import abc
import typing
import uuid

import pydantic

# TODO: work out how reference can have secrets as well
# TODO: can we add the resolving logic and "relations" between the pydantic classes?
# TODO: should we introduce a distinction between normal values and secret references so that they are never sent back to the server?
#       this can also be used for binary values for example (like in files)


class ValueReferenceModel(pydantic.BaseModel):
    """A model class that defines the reference to the value. Values are always represented as an object
    with one or more attributes that can be referenced
    """

    @classmethod
    def get_all_reference_types(cls) -> list[type["ValueReferenceModel"]]:
        subclasses = []
        for subclass in cls.__subclasses__():
            subclasses.append(subclass)
            subclasses.extend(subclass.get_all_reference_types())
        return subclasses

    ref_id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    """ A uuid to be able to refere to this reference.
    """

    ref_type: str
    """ A type key that can be used to correctly select the correct pydantic resource

    # TODO: validate that it matches the name of an entity (for consistency)
    """

    def resolve_reference(self, values: list["ValueReferenceModel"]) -> object:
        """Resolve the reference.

        :param values: A list of all value reference
        """
        print(self.model_fields)


class ValueReference(str):
    """This object holds the information required to resolve references. This is currently represented as a string
    so that in the model it has a valid inmanta DSL value.

    The static create method is required because it is not possible to change the constructor of string without causing
    errors. When real references are support this is no longer required.
    """

    _value_reference: ValueReferenceModel

    @staticmethod
    def create(reference: ValueReferenceModel) -> "ValueReference":
        """This factory method creates the "magic" string with additional fields set."""
        obj = ValueReference(f"Placeholder string for secret {str(reference.ref_id)} of type {reference.reference_type}")
        obj._value_reference = reference
        return obj


class _ValueReferenceAttributeString(str):
    """A reference to an attribute of type string in a reference value"""

    _value_reference: ValueReference
    _attribute: str

    @staticmethod
    def create(reference: ValueReference, attribute: str) -> "_ValueReferenceAttributeString":
        obj = _ValueReferenceAttributeString(
            f"Placeholder string for reference to the value in attribute {attribute} of {reference}"
        )
        obj._value_reference: ValueReference = reference._value_reference
        obj._attribute: str = attribute
        return obj


ValueReferenceAttributeString = typing.Annotated[
    _ValueReferenceAttributeString,
    pydantic.PlainValidator(lambda x: x),  # make sure pydantic does not lose the custom string type
]


class ValueReferenceAttributeMap(pydantic.BaseModel):
    """A reference to the value in an attribute of a value."""

    attribute: str
    """ The attribute on the referenced value to use
    """

    value_reference_id: uuid.UUID
    """ The id of the value reference to use
    """

    path: str
    """ A dictpath expression where the value of the attribute should be stored in the resource

    TODO: add dictpath validation
    """


T = typing.TypeVar("T", bound=ValueReferenceModel)


class ValueReferencesField(pydantic.BaseModel, typing.Generic[T]):
    """The model for the value_references field of every resource"""

    values: dict[str, T] = []
    """ Each secrets gets an id so that the mapping can reference it. The key is a value reference id (uuid),
    but pydantic/json requires the keys to be str
    """

    mappings: list[ValueReferenceAttributeMap] = []


R = typing.TypeVar("R", bound=ValueReferenceModel)
S = typing.TypeVar("S")


class Resolver(typing.Generic[R, S]):
    @classmethod
    def get_all_reference_resolvers(cls) -> list[type["Resolver"]]:
        subclasses = []
        for subclass in cls.__subclasses__():
            subclasses.append(subclass)
            subclasses.extend(subclass.get_all_reference_resolvers())
        return subclasses

    @abc.abstractmethod
    def fetch(self) -> S:
        """Fetch the value"""
