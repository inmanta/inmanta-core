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

import builtins
import copy
import dataclasses
import functools
import numbers
import typing
from collections import defaultdict, deque
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Optional

from inmanta import references
from inmanta.ast import (
    DuplicateException,
    Locatable,
    LocatableString,
    Location,
    MultiUnsetException,
    Named,
    Namespace,
    NotFoundException,
    RuntimeException,
    TypingException,
    UnexpectedReference,
    UnsetException,
)
from inmanta.execute.proxy import DynamicProxy, ProxyContext
from inmanta.execute.util import AnyType, NoneValue, Unknown
from inmanta.stable_api import stable_api

if TYPE_CHECKING:
    from inmanta.ast.statements import ExpressionStatement


@stable_api
class Type(Locatable):
    """
    This class is the abstract base class for all types in the Inmanta :term:`DSL` that represent basic data. These are
    types that are not relations. Instances of subclasses represent a type in the Inmanta language.
    """

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints associated with this type. Returns true iff
        validation succeeds, otherwise raises a :py:class:`inmanta.ast.RuntimeException`.

        In advanced cases where this class has a custom ``to_python()``, translation-specific validation should be deferred
        to that stage. Translation-specific means that the value is definitely of this DSL type, but it can not be converted to
        the Python domain.
        """
        # Special DSL values like references require an explicit annotation so we don't leak them where they aren't expected.
        if isinstance(value, references.Reference):
            raise UnexpectedReference(
                reference=value,
                # keep message generic, since this method is used for many types' super() call.
                message=(
                    f"References are not allowed for values of type `{self.type_string_internal()}`. To work with references,"
                    " explicitly declare support with a `... | Reference[...]` annotation."
                ),
            )
        return True

    def type_string(self) -> Optional[str]:
        """
        Returns the type string as expressed in the Inmanta :term:`DSL`, if this type can be expressed in the :term:`DSL`.
        Otherwise returns None.
        """
        return None

    def type_string_internal(self) -> str:
        """
        Returns the internal string representation of the instance of the type. This is used by __str__
        when type_string() returns None.
        Use this method only when you explicitly need the internal string representation of the type.
        """
        return "Type"

    def __str__(self) -> str:
        """
        Returns the string representation of the type, to be used for informative reporting as in error messages.
        When a structured representation of the inmanta type is required, type_string() should be used instead.
        """
        type_string: Optional[str] = self.type_string()
        return type_string if type_string is not None else self.type_string_internal()

    def normalize(self) -> None:
        pass

    def is_attribute_type(self) -> bool:
        """
        Returns true iff this type is valid in the model as an attribute type
        """
        return False

    def is_entity(self) -> bool:
        """
        Returns true only for Entity
        """
        # Introduced to prevent import loops on isinstance checks
        return False

    def get_base_type(self) -> "Type":
        """
        Returns the base type for this type, i.e. the plain type without modifiers such as expressed by
        ``[]`` and ``?`` in the :term:`DSL` and ``Reference`` in the plugin domain.
        """
        return self

    def supports_references(self) -> bool:
        """
        Returns True iff this type accepts any sort of reference value. Nested references, e.g. inside a list, are not
        considered.
        """
        return False

    def with_base_type(self, base_type: "Type") -> "Type":
        """
        Returns the type formed by replacing this type's base type with the supplied type.
        """
        return base_type

    def corresponds_to(self, type: "Type") -> bool:
        """
        Determine if the given 'type' is a good approximation to `self` given that `type` is derived from a python type

        Intended specifically for type correspondence for dataclasses.
        This brings specific assumptions
        - `self` is the native inmanta type
        - `type` is translated form the python domain
        - 'Any' means: trust me, it will be fine (i.e. always corresponds)
        """
        raise NotImplementedError()

    def as_python_type_string(self) -> "str | None":
        """
        Return a python type that can capture the values of this inmanta type
        As a string

        Returns None if this is not possible.

        Used only on the plugin boundary
        """

    def has_custom_to_python(self) -> bool:
        """
        Indicates if a special to_python conversion should be used

        Used only on the plugin boundary
        """
        return False

    def to_python(self, instance: object, *, path: str) -> object:
        """
        Convert an instance of this type to its python form

        should only be called if has_custom_to_python is True
        the instance must be valid according to the validate method

        :param path: The path, relative to the plugin's namespace, where this object occurs.

        :raises RuntimeException: If there is a translation error.
        """
        return instance

    def issubtype(self, other: "Type") -> bool:
        """
        Returns True iff this DSL type is a subtype of the other type.

        Implementations may recurse but must do so in a way that progresses and will eventually terminate, i.e. one of:
            - narrow on the self type, e.g. recurse on each of the options in a union / intersection type
            - descend deeper into both types, e.g. if both are typed lists, check if their respective element types have a
                subtype relation.
        Implementations that do not return True or recurse, should fall back to calling issupertype with reversed arguments,
        to give the other type's specifics a chance to declare that it is a supertype.

        False negatives may be unavoidable in complex cases. Does not return false positives.
        """
        if self == other:
            return True
        return other.issupertype(self)

    def issupertype(self, other: "Type") -> bool:
        """
        Returns True iff this DSL type is a (non-strict) supertype of the other type due to specifics of this type,
        e.g. sum / union types.

        issubtype is always the entrypoint for any actual sub / super type check.

        Implementations must always narrow at least the self type when recursing (e.g. recurse on each of the options in a
        union type), and must do so by calling issubtype, never issupertype directly. Non-composed types should have no need
        to override the default implementation.
        """
        return False

    def __eq__(self, other: object) -> bool:
        if type(self) != Type:  # noqa: E721
            # Not for children
            return NotImplemented
        return type(self) == type(other)  # noqa: E721

    def __hash__(self) -> int:
        return hash(type(self))


class ReferenceType(Type):
    """
    The type of a reference to something of type element_type

    e.g ReferenceType(Integer()) represents a reference to an int
    """

    def __init__(self, element_type: Type) -> None:
        """
        :param element_type: the type we refer to
        """
        super().__init__()
        assert not element_type.supports_references()
        self.element_type = element_type
        self.is_dataclass = False
        if element_type.is_entity():
            # Can not be typed more strictly due to import loops
            # The root cause of the problem is the to_dsl method, which is required by entity and plugin
            # these are types, but to_dsl also constructs types.
            # i.e. we can't layer the type, entity and plugin domain any more
            if element_type.get_paired_dataclass() is None:
                raise TypingException(
                    None,
                    f"References to entities must always be references to dataclasses."
                    f" Got {element_type}, which is not a dataclass",
                )

            self.is_dataclass = True

    def supports_references(self) -> typing.Literal[True]:
        return True

    def validate(self, value: Optional[object]) -> bool:
        ref: Optional[references.Reference[references.RefValue]] = references.unwrap_reference(value)
        if ref is not None:
            assert ref._model_type is not None
            if ref._model_type.issubtype(self.element_type):
                return True

        raise TypingException(None, f"Invalid value: {value} is not a subtype of {self}")

    def has_custom_to_python(self) -> bool:
        return self.is_dataclass

    def to_python(self, instance: object, *, path: str) -> object:
        result: Optional[references.Reference[references.RefValue]] = references.unwrap_reference(instance)
        # wouldn't have passed validate otherwise
        assert result is not None
        return result

    def type_string_internal(self) -> str:
        return f"Reference[{self.element_type.type_string_internal()}]"

    def is_attribute_type(self) -> bool:
        return self.element_type.is_attribute_type()

    def get_base_type(self) -> "Type":
        return self.element_type

    def corresponds_to(self, type: "Type") -> bool:
        if builtins.type(type) != builtins.type(self):
            return False

        return self.element_type.corresponds_to(type.element_type)

    def as_python_type_string(self) -> "str | None":
        return f"Reference[{self.element_type.as_python_type_string()}]"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReferenceType):
            return False
        return other.element_type == self.element_type

    def __hash__(self) -> int:
        return hash((type(self), self.element_type))

    def issubtype(self, other: "Type") -> bool:
        if isinstance(other, ReferenceType):
            return other.element_type.issubtype(self.element_type)
        return other.issupertype(self)


class OrReferenceType(Type):
    """
    This class represents the shorthand for Reference[T] | T

    It produces a cleaner output for exceptions

    create_unions will compact unions to use this class when relevant
    """

    def __init__(self, element_type: Type) -> None:
        self.element_type: Type = element_type
        self.reference_type: ReferenceType = ReferenceType(element_type)

    def supports_references(self) -> typing.Literal[True]:
        return True

    def validate(self, value: Optional[object]) -> bool:
        # We validate that the value is either a reference of the base type or the base type
        if references.unwrap_reference(value) is not None:
            # Validate that we are the reference
            return self.reference_type.validate(value)
        else:
            # Validate that we are the base type
            return self.element_type.validate(value)

    def has_custom_to_python(self) -> bool:
        return self.reference_type.has_custom_to_python() or self.element_type.has_custom_to_python()

    def to_python(self, instance: object, *, path: str) -> object:
        try:
            self.reference_type.validate(instance)
        except RuntimeException:
            if self.element_type.has_custom_to_python():
                return self.element_type.to_python(instance, path=path)
            else:
                return DynamicProxy.return_value(instance, context=ProxyContext(path=path))
        else:
            return self.reference_type.to_python(instance, path=path)

    def type_string(self) -> Optional[str]:
        # unfortunately, this type is used (by necessity) for attribute types.
        return self.element_type.type_string()

    def type_string_internal(self) -> str:
        element = self.element_type.type_string_internal()
        return f"Reference[{element}] | {element}"

    def as_python_type_string(self) -> "str | None":
        # Can't be expressed in the model
        return f"Reference[{self.element_type.as_python_type_string()}] | {self.element_type.as_python_type_string()}"

    def __eq__(self, other):
        if not isinstance(other, OrReferenceType):
            return False
        return other.element_type == self.element_type

    def __hash__(self) -> int:
        return hash((type(self), self.element_type))

    def is_attribute_type(self) -> bool:
        return self.element_type.is_attribute_type()

    def get_base_type(self) -> "Type":
        return self.element_type

    def corresponds_to(self, type: "Type") -> bool:
        # The model always allow reference, we allow the type in the python domain to be tighter
        if isinstance(type, Any):
            return True
        if self.element_type.corresponds_to(type):
            return True
        if isinstance(type, OrReferenceType):
            return self.element_type.corresponds_to(type.element_type)
        return False

    # Due to the way unions with references are compacted to OrReference, it suffices to have a custom issupertype
    # implementation. The default issubtype suffices because it will delegate to issupertype, which will end up here
    # eventually, possibly by first going through Union.issupertype, in case of a wider union.
    def issupertype(self, other: "Type") -> bool:
        if not isinstance(other, (ReferenceType, OrReferenceType)):
            return other.issubtype(self.element_type)
        return other.element_type.issubtype(self.element_type)


class NamedType(Type, Named):
    def get_double_defined_exception(self, other: "NamedType") -> "DuplicateException":
        """produce an error message for this type"""
        raise DuplicateException(self, other, "Type %s is already defined" % (self.get_full_name()))

    def type_string(self) -> str:
        return self.get_full_name()

    def type_string_internal(self) -> str:
        return self.type_string()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NamedType):
            return False
        return self.get_full_name() == other.get_full_name()

    def __hash__(self) -> int:
        return hash((type(self), self.get_full_name()))


class Null(Type):
    """
    This custom type is used for the validation of plugins which only
    accept null as an argument or return value.
    """

    def validate(self, value: Optional[object]) -> bool:
        if isinstance(value, NoneValue):
            return True

        raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

    def type_string(self) -> str:
        return "null"

    def type_string_internal(self) -> str:
        return self.type_string()

    def as_python_type_string(self) -> "str | None":
        return "None"

    def corresponds_to(self, type: Type) -> bool:
        return isinstance(type, (Null, Any))

    def has_custom_to_python(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return type(self) == type(other)  # noqa: E721

    def get_location(self) -> Optional[Location]:
        return None

    def __hash__(self) -> int:
        return hash(self.type_string())


@stable_api
class NullableType(Type):
    """
    Represents a nullable type in the Inmanta :term:`DSL`. For example ``NullableType(Number())`` represents ``number?``.
    """

    def __init__(self, element_type: Type) -> None:
        Type.__init__(self)
        self.element_type: Type = element_type

    def validate(self, value: Optional[object]) -> bool:
        if isinstance(value, NoneValue):
            return True

        return self.element_type.validate(value)

    def _wrap_type_string(self, string: str) -> str:
        return f"({string})?" if " " in string else f"{string}?"

    def type_string(self) -> Optional[str]:
        base_type_string: Optional[str] = self.element_type.type_string()
        return None if base_type_string is None else self._wrap_type_string(base_type_string)

    def type_string_internal(self) -> str:
        return self._wrap_type_string(self.element_type.type_string_internal())

    def normalize(self) -> None:
        self.element_type.normalize()

    def get_base_type(self) -> Type:
        return self.element_type.get_base_type()

    def with_base_type(self, base_type: Type) -> Type:
        return NullableType(self.element_type.with_base_type(base_type))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NullableType):
            return NotImplemented
        return self.element_type == other.element_type

    def __hash__(self) -> int:
        return hash((type(self), self.element_type))

    def is_attribute_type(self) -> bool:
        return self.element_type.is_attribute_type()

    def corresponds_to(self, type: Type) -> bool:
        if isinstance(type, Any):
            return True
        if not isinstance(type, NullableType):
            return False
        return self.element_type.corresponds_to(type.element_type)

    def as_python_type_string(self) -> "str | None":
        return f"{self.element_type.as_python_type_string()} | None"

    def to_python(self, instance: object, *, path: str) -> object:
        if isinstance(instance, NoneValue):
            return None
        return self.element_type.to_python(instance, path=path)

    def has_custom_to_python(self) -> bool:
        return self.element_type.has_custom_to_python()

    def issubtype(self, other: "Type") -> bool:
        if isinstance(other, NullableType) and self.element_type.issubtype(other.element_type):
            return True
        return other.issupertype(self)

    def issupertype(self, other: "Type") -> bool:
        return isinstance(other, Null) or other.issubtype(self.element_type)

    def supports_references(self) -> bool:
        return self.element_type.supports_references()


class Any(Type):
    """
    this type represents the any type, similar to Python's

    the Any class itself is neither the top nor the bottom type in the type hierarchy.
    """

    def validate(self, value: Optional[object]) -> bool:
        try:
            return super().validate(value)
        except UnexpectedReference as e:
            raise UnexpectedReference(
                reference=e.reference,
                # custom error message for the "object" / "any" type
                message=(
                    "References are not allowed for values of type `object`. While the `object` Python type is technically"
                    " compatible with any value, references are considered special DSL values and are therefore guarded so"
                    " that they don't accidentally show up where they are not expected. To work with references,"
                    " explicitly declare support with a `object | Reference` annotation."
                ),
            )

    def corresponds_to(self, type: Type) -> bool:
        return True

    def as_python_type_string(self) -> "str | None":
        return "object"

    def has_custom_to_python(self) -> bool:
        return False

    def type_string_internal(self) -> str:
        return "any"

    def __eq__(self, other: object) -> bool:
        return type(self) == type(other)  # noqa: E721

    def issupertype(self, other: "Type") -> bool:
        return True

    def __hash__(self):
        # Could be any unique value
        return 3141156432848106867


def cast_not_implemented(value: Optional[object]) -> object:
    raise NotImplementedError("Can not cast to Primitive")


@stable_api
class Primitive(Type):
    """
    Abstract base class representing primitive types.
    """

    def __init__(self) -> None:
        Type.__init__(self)
        self.cast_function: Callable[[Optional[object]], object] = cast_not_implemented

    def cast(self, value: Optional[object]) -> object:
        """
        Cast a value to this type. If the value can not be cast, raises a :py:class:`inmanta.ast.RuntimeException`.
        """
        if isinstance(value, Unknown):
            # propagate unknowns
            return value

        try:
            return self.cast_function(value)
        except (ValueError, TypeError):
            raise RuntimeException(None, f"Failed to cast '{value}' to {self}")

    def type_string_internal(self) -> str:
        return "Primitive"

    def corresponds_to(self, type: "Type") -> bool:
        if isinstance(type, Any):
            return True
        return type == self

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other)

    def __hash__(self) -> int:
        return hash(self.type_string())

    def has_custom_to_python(self) -> bool:
        # All primitives can be trivially converted
        return False

    def is_attribute_type(self) -> bool:
        return True

    def get_location(self) -> Optional[Location]:
        # Override to skip the null check in the parent class
        return None


@stable_api
class Number(Primitive):
    """
    This class represents an integer or a float in the configuration model.
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.cast_function = float

    def cast(self, value: Optional[object]) -> object:
        """
        Attempts to cast a given value to an int or a float.
        """
        # Keep precision: cast to an int only if it already is an int
        if isinstance(value, int):
            return int(value)
        return super().cast(value)

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        super().validate(value)
        if isinstance(value, AnyType):
            return True

        if not isinstance(value, numbers.Number):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

        return True  # allow this function to be called from a lambda function

    def get_location(self) -> None:
        return None

    def type_string(self) -> str:
        return "number"

    def type_string_internal(self) -> str:
        return self.type_string()

    def as_python_type_string(self) -> "str | None":
        return "numbers.Number"

    def corresponds_to(self, type: "Type") -> bool:
        return isinstance(type, (Any, Float, Integer, Number))

    def issubtype(self, other: "Type") -> bool:
        return Float().issubtype(other) and Integer().issubtype(other)

    def issupertype(self, other: "Type") -> bool:
        return isinstance(other, (Float, Integer))


@stable_api
class Float(Primitive):
    """
    This class is an alias for the Number class and represents a float in
    the configuration model.
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.cast_function = float

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        super().validate(value)
        if isinstance(value, AnyType):
            return True

        if not isinstance(value, float):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")
        return True  # allow this function to be called from a lambda function

    def get_location(self) -> None:
        return None

    def type_string(self) -> str:
        return "float"

    def type_string_internal(self) -> str:
        return self.type_string()

    def as_python_type_string(self) -> "str | None":
        return "float"


@stable_api
class Integer(Primitive):
    """
    An instance of this class represents the int type in the configuration model.
    """

    def __init__(self) -> None:
        super().__init__()
        self.cast_function = int

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        super().validate(value)
        if isinstance(value, AnyType):
            return True

        if not isinstance(value, numbers.Integral):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")
        return True  # allow this function to be called from a lambda function

    def type_string(self) -> str:
        return "int"

    def type_string_internal(self) -> str:
        return "int"

    def as_python_type_string(self) -> "str | None":
        return "int"


@stable_api
class Bool(Primitive):
    """
    This class represents a simple boolean that can hold true or false.
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.cast_function = bool

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        super().validate(value)
        if isinstance(value, AnyType):
            return True
        if isinstance(value, bool):
            return True
        raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

    def cast(self, value: Optional[object]) -> object:
        # this is a bit odd, in that is accepts None, but it has always been so
        return super().cast(value if not isinstance(value, NoneValue) else None)

    def type_string(self) -> str:
        return "bool"

    def type_string_internal(self) -> str:
        return self.type_string()

    def get_location(self) -> None:
        return None

    def as_python_type_string(self) -> "str | None":
        return "bool"


@stable_api
class String(Primitive):
    """
    This class represents a string type in the configuration model.
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.cast_function = str

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        super().validate(value)
        if isinstance(value, AnyType):
            return True
        if not isinstance(value, str):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

        return True

    def cast(self, value: Optional[object]) -> object:
        if value is True:
            return "true"
        if value is False:
            return "false"
        return super().cast(value)

    def type_string(self) -> str:
        return "string"

    def type_string_internal(self) -> str:
        return self.type_string()

    def get_location(self) -> None:
        return None

    def as_python_type_string(self) -> "str | None":
        return "str"


@stable_api
class List(Type):
    """
    Instances of this class represent a list type containing any types of values.
    This class refers to the list type used in plugin annotations. For the list type in the Inmanta DSL, see `LiteralList`.
    """

    def __init__(self) -> None:
        Type.__init__(self)

    def validate(self, value: Optional[object]) -> bool:
        if value is None:
            return True

        if isinstance(value, AnyType):
            return True

        if not isinstance(value, list):
            raise TypingException(None, f"Invalid value '{value}', expected {self.type_string()}")

        return True

    def type_string(self) -> str:
        # This is not a type in the model, but it is used in plugin annotations, which are also part of the DSL.
        return "list"

    def type_string_internal(self) -> str:
        return "list"

    def get_location(self) -> None | Location:
        return None

    def corresponds_to(self, type: Type) -> bool:
        # Unreachable, the model can't specify this
        if isinstance(type, Any):
            return True

        return isinstance(type, List)

    def as_python_type_string(self) -> "str | None":
        return "list[object]"

    def __eq__(self, other: object) -> bool:
        return type(self) == type(other)  # noqa: E721

    def __hash__(self) -> int:
        return hash(type(self))

    def issubtype(self, other: "Type") -> bool:
        if isinstance(other, Any):
            return True
        return isinstance(other, List)


@stable_api
class TypedList(List):
    """
    Instances of this class represent a list type containing any values of type element_type.
    For example `TypedList(Number())` represents `number[]`.
    """

    def __init__(self, element_type: Type) -> None:
        List.__init__(self)
        self.element_type: Type = element_type

    def normalize(self) -> None:
        self.element_type.normalize()

    def validate(self, value: Optional[object]) -> bool:
        List.validate(self, value)

        assert isinstance(value, list)
        for element in value:
            self.element_type.validate(element)

        return True

    def _wrap_type_string(self, string: str) -> str:
        return f"({string})[]" if " " in string else f"{string}[]"

    def type_string(self) -> Optional[str]:
        element_type_string = self.element_type.type_string()
        return None if element_type_string is None else self._wrap_type_string(element_type_string)

    def type_string_internal(self) -> str:
        return self._wrap_type_string(self.element_type.type_string_internal())

    def get_location(self) -> Location | None:
        return self.element_type.get_location()

    def get_base_type(self) -> Type:
        return self.element_type

    def with_base_type(self, base_type: Type) -> Type:
        return TypedList(base_type)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypedList):
            return NotImplemented
        return self.element_type == other.element_type

    def __hash__(self) -> int:
        return hash((type(self), self.element_type))

    def is_attribute_type(self) -> bool:
        return self.element_type.is_attribute_type()

    def corresponds_to(self, type: Type) -> bool:
        if isinstance(type, Any):
            return True

        if not isinstance(type, TypedList):
            # The other list is untyped, so we are not equivalent
            return False

        return self.element_type.corresponds_to(type.element_type)

    def as_python_type_string(self) -> "str | None":
        return f"list[{self.element_type.as_python_type_string()}]"

    def to_python(self, instance: object, *, path: str) -> object:
        if not isinstance(instance, Sequence):
            # should not happen, pre-condition
            raise TypeError(f"This method can only be called on iterables, not on {type(instance)}")
        return [self.element_type.to_python(element, path=f"{path}[{i}]") for i, element in enumerate(instance)]

    def has_custom_to_python(self) -> bool:
        return self.element_type.has_custom_to_python()

    def issubtype(self, other: "Type") -> bool:
        if isinstance(other, TypedList):
            return self.element_type.issubtype(other.element_type)
        return other.issupertype(self)


@stable_api
class LiteralList(TypedList):
    """
    Instances of this class represent a list type containing only :py:class:`Literal` values.
    This is the `list` type in the :term:`DSL`
    """

    def __init__(self) -> None:
        TypedList.__init__(self, Literal())

    def type_string(self) -> str:
        return "list"

    def get_base_type(self) -> Type:
        # The `list` type is not multi, thus it is the base type itself
        return self

    def with_base_type(self, base_type: Type) -> Type:
        return self

    def has_custom_to_python(self) -> bool:
        return False

    def is_attribute_type(self) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LiteralList):
            return NotImplemented
        return True


@stable_api
class Dict(Type):
    """
    Instances of this class represent a dict type with any types of values.
    """

    def __init__(self) -> None:
        Type.__init__(self)

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        if isinstance(value, AnyType):
            return True

        if value is None:
            return True

        if not isinstance(value, dict):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

        return True

    def type_string_internal(self) -> str:
        return "Dict"

    def type_string(self) -> str:
        return "dict"

    def get_location(self) -> None | Location:
        return None

    def as_python_type_string(self) -> "str | None":
        return "dict"

    def corresponds_to(self, type: Type) -> bool:
        if isinstance(type, Any):
            return True
        return isinstance(type, Dict)

    def issubtype(self, other: "Type") -> bool:
        if isinstance(other, Any):
            return True
        return isinstance(other, Dict)

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other)

    def __hash__(self) -> int:
        return hash(type(self))


@stable_api
class TypedDict(Dict):
    """
    Instances of this class represent a dict type containing only values of type element_type.
    """

    def __init__(self, element_type: Type) -> None:
        Dict.__init__(self)
        self.element_type: Type = element_type

    def normalize(self) -> None:
        self.element_type.normalize()

    def validate(self, value: Optional[object]) -> bool:
        Dict.validate(self, value)

        assert isinstance(value, dict)
        for element in value.values():
            self.element_type.validate(element)

        return True

    def type_string_internal(self) -> str:
        return "dict[string, %s]" % self.element_type.type_string_internal()

    def get_location(self) -> Location | None:
        return self.element_type.get_location()

    def corresponds_to(self, type: Type) -> bool:
        if isinstance(type, Any):
            return True

        if not isinstance(type, Dict):
            return False

        if not isinstance(type, TypedDict):
            # Untyped dict is fine
            return True

        return self.element_type.corresponds_to(type.element_type)

    def as_python_type_string(self) -> "str | None":
        return f"dict[str, {self.element_type.as_python_type_string()}]"

    def has_custom_to_python(self) -> bool:
        return self.element_type.has_custom_to_python()

    def to_python(self, instance: object, *, path: str) -> object:
        assert isinstance(instance, dict)
        base = self.element_type
        return {k: base.to_python(v, path=f"{path}[{k}]") for k, v in instance.items()}

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypedDict):
            return NotImplemented
        return self.element_type == other.element_type

    def __hash__(self) -> int:
        return hash((type(self), self.element_type))

    def issubtype(self, other: "Type") -> bool:
        if isinstance(other, TypedDict):
            return self.element_type.issubtype(other.element_type)
        return other.issupertype(self)


@stable_api
class LiteralDict(TypedDict):
    """
    Instances of this class represent a dict type containing only :py:class:`Literal` values.
    This is the `dict` type in the :term:`DSL`
    """

    def __init__(self) -> None:
        TypedDict.__init__(self, Literal())

    def type_string(self) -> str:
        return "dict"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LiteralDict):
            return NotImplemented
        return True

    def has_custom_to_python(self) -> bool:
        return False

    def is_attribute_type(self) -> bool:
        return True


@dataclasses.dataclass
class BaseOrRef:
    """Small helper to sort types and their associated reference"""

    has_base: Type | None = None
    has_ref: ReferenceType | None = None

    def convert(self) -> Type:
        if self.has_ref is not None and self.has_base is not None:
            return OrReferenceType(self.has_base)
        if self.has_ref is not None:
            return self.has_ref
        assert self.has_base is not None
        return self.has_base


def create_union(types: Sequence[Type]) -> Type:
    """
    Normalize the union:
     - Nullable is the outer type if applicable
     - Nested unions are flattened
     - Reference[T] | T becomes OrReference[T] (for cleaner output)
     - Single item union return just the item
    """
    worklist = deque(types)
    sorted_types: dict[Type, BaseOrRef] = defaultdict(BaseOrRef)
    nullable = False
    seen: set[Type] = set()
    while worklist:
        current = worklist.popleft()
        if current in seen:
            continue
        seen.add(current)
        match current:
            case Union():
                worklist.extend(current.types)
            case NullableType():
                nullable = True
                worklist.append(current.element_type)
            case Null():
                nullable = True
            case ReferenceType():
                sorted_types[current.element_type].has_ref = current
            case _:
                sorted_types[current].has_base = current

    bases = [bor.convert() for bor in sorted_types.values()]
    if len(bases) == 1:
        base_union: Type = bases[0]
    else:
        base_union = Union(bases)

    if nullable:
        return NullableType(base_union)
    else:
        return base_union


@stable_api
class Union(Type):
    """
    Instances of this class represent a union of multiple types.
    """

    def __init__(self, types: Sequence[Type]) -> None:
        Type.__init__(self)
        self.types: Sequence[Type] = types

    def get_base_type(self) -> "Type":
        return self

    def validate(self, value: object) -> bool:
        for typ in self.types:
            try:
                if typ.validate(value):
                    return True
            except RuntimeException:
                pass
        raise TypingException(None, f"Invalid value '{value}', expected {self}")

    def type_string_internal(self) -> str:
        return "Union[%s]" % ",".join(t.type_string_internal() for t in self.types)

    def as_python_type_string(self) -> "str | None":
        types = [tp.as_python_type_string() for tp in self.types]

        effective_types = [tp for tp in types if tp is not None]
        if len(types) != len(effective_types):
            # One is not converted
            return None
        return " | ".join(effective_types)

    def has_custom_to_python(self) -> bool:
        return any(tp.has_custom_to_python() for tp in self.types)

    def to_python(self, instance: object, *, path: str) -> object:
        """
        Construct a python object for this instance
        """
        # At this point, we have two pre-conditions
        # 1. instance is an instance of one of our types
        # 2. one of our types has_custom_to_python set
        for tp in self.types:
            # For each of out types
            try:
                # Find if this instance is of that type
                if tp.validate(instance):
                    # It is of this type, does it require custom conversion?
                    if tp.has_custom_to_python():
                        # Custom conversion
                        return tp.to_python(instance, path=path)
                    else:
                        # Default conversion
                        return DynamicProxy.return_value(instance, context=ProxyContext(path=path))
            except (UnsetException, MultiUnsetException):
                # let these exceptions with special meaning through
                raise
            except RuntimeException:
                # Validate fails, up to the next one
                pass
        # Due to the invariants, this can't happen
        # One of the types HAS to match validate
        assert False

    def corresponds_to(self, type: Type) -> bool:
        if isinstance(type, Union):
            types = list(type.types)
        else:
            types = [type]

        unmatched = list(types)
        for type in self.types:
            for other_type in types:
                if type.corresponds_to(other_type):
                    unmatched.remove(other_type)
                    break
            else:
                # type did not match anything
                return False
        return not unmatched

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Union):
            return NotImplemented
        return self.types == other.types

    def is_attribute_type(self) -> bool:
        # It can not strictly speaking be used as an attribute type
        # But, if all member are is_attribute_type this is equivalent to either Nullable or Literal
        return all(tp.is_attribute_type() for tp in self.types)

    def get_location(self) -> Optional[Location]:
        # We don't know what location to use...
        return None

    def issubtype(self, other: "Type") -> bool:
        return self == other or all(element_type.issubtype(other) for element_type in self.types)

    def issupertype(self, other: "Type") -> bool:
        return any(other.issubtype(tp) for tp in self.types)

    def supports_references(self) -> bool:
        return any(tp.supports_references() for tp in self.types)

    def __hash__(self) -> int:
        return hash((3141156432848106868, *self.types))


@stable_api
class Literal(Union):
    """
    Instances of this class represent a literal in the configuration model. A literal is a primitive or a list or dict
    where all values are literals themselves.
    """

    def __init__(self) -> None:
        Union.__init__(
            self, [NullableType(Float()), Number(), Bool(), String(), TypedList(self), TypedDict(self), ReferenceType(self)]
        )

    def type_string_internal(self) -> str:
        return "Literal"

    def as_python_type_string(self) -> "str | None":
        # Keep it simple
        return "object"

    def is_attribute_type(self) -> bool:
        return True

    def corresponds_to(self, type: Type) -> bool:
        if isinstance(type, Any):
            return True

        # Infinite recursive type, avoid the mess
        # We allow any primitive
        return type.is_attribute_type()

    def issubtype(self, other: "Type") -> bool:
        # don't split this type in its union counterparts for performance reasons. It will always appear as Literal
        return Type.issubtype(self, other)

    def issupertype(self, other: "Type") -> bool:
        return other.is_attribute_type()

    def supports_references(self) -> bool:
        # prevent infinite loop for magic type
        return False

    def has_custom_to_python(self) -> bool:
        return False


@stable_api
class ConstraintType(NamedType):
    """
    A type that is based on a primitive type but defines additional constraints on this type.
    These constraints only apply on the value of the type.
    """

    def __init__(self, namespace: Namespace, name: str) -> None:
        NamedType.__init__(self)

        # It is easy to assume that get_base_type return self.basetype
        # It doesn't and shouldn't
        # This field would better be called element_type, but that would break backward compatibility
        # Is it also assumed to NEVER be a reference type
        self.basetype: Optional[Type] = None  # : ConstrainableType
        self._constraint: Callable[[object], object] | None = None
        self.name: str = name
        self.namespace: Namespace = namespace
        self.comment: Optional[str] = None
        self.expression: Optional["ExpressionStatement"] = None

    def normalize(self) -> None:
        assert self.expression is not None
        self.expression.normalize()

    def set_constraint(self, expression: "ExpressionStatement") -> None:
        """
        Set the constraint for this type. This baseclass for constraint
        types requires the constraint to be set as a regex that can be
        compiled.
        """
        self.expression = expression
        self._constraint = create_function(self, expression)

    def get_constraint(self) -> "ExpressionStatement | None":
        """
        Get the string representation of the constraint
        """
        return self.expression

    constraint = property(get_constraint, set_constraint)

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraint and
        the basetype.
        """
        if isinstance(value, AnyType):
            return True

        assert self.basetype is not None
        self.basetype.validate(value)

        assert self._constraint is not None
        assert self.expression is not None
        if not self._constraint(value):
            raise RuntimeException(
                self, f"Invalid value {repr(value)}, does not match constraint `{self.expression.pretty_print()}`"
            )

        return True

    def type_string(self) -> str:
        return f"{self.namespace}::{self.name}"

    def type_string_internal(self) -> str:
        return self.type_string()

    def get_full_name(self) -> str:
        return self.namespace.get_full_name() + "::" + self.name

    def get_namespace(self) -> "Namespace":
        return self.namespace

    def get_double_defined_exception(self, other: "NamedType") -> DuplicateException:
        return DuplicateException(self, other, "TypeConstraint %s is already defined" % (self.get_full_name()))

    def has_custom_to_python(self) -> bool:
        # Substitute for base type for now
        assert self.basetype is not None
        return self.basetype.has_custom_to_python()

    def corresponds_to(self, type: Type) -> bool:
        if self is type:
            # To avoid comparing the expression, we evaluate on exact equality, as typedefs are uniquely defined
            return True
        if isinstance(type, Any):
            return True
        assert self.basetype is not None
        # Same basetype is sufficiently close
        return self.basetype.corresponds_to(type)

    def as_python_type_string(self) -> "str | None":
        assert self.basetype is not None
        return self.basetype.as_python_type_string()

    def to_python(self, instance: object, *, path: str) -> object:
        assert self.basetype is not None
        return self.basetype.to_python(instance, path=path)

    def issubtype(self, other: "Type") -> bool:
        assert self.basetype is not None
        return self == other or self.basetype.issubtype(other)


def create_function(tp: ConstraintType, expression: "ExpressionStatement") -> Callable[[object], object]:
    """
    Function that returns a function that evaluates the given expression.
    The generated function accepts the unbound variables in the expression
    as arguments.
    """

    def function(*args, **kwargs):
        """
        A function that evaluates the expression
        """
        if len(args) != 1:
            raise NotImplementedError()

        try:
            return expression.execute_direct({"self": args[0]})
        except NotFoundException as e:
            e.msg = "Unable to resolve `%s`: a type constraint can not reference variables." % e.stmt.name
            raise e

    return function


TYPES: dict[str, Type] = {  # Part of the stable API
    "string": String(),
    "float": Float(),
    "number": Number(),
    "int": Integer(),
    "bool": Bool(),
    "list": LiteralList(),
    "dict": LiteralDict(),
}
"""
    Maps Inmanta :term:`DSL` types to their internal representation. For each key, value pair, `value.type_string()` is
    guaranteed to return key.
"""


@stable_api
def resolve_type(locatable_type: LocatableString, resolver: Namespace) -> Type:
    """
    Convert a locatable type string, into a real inmanta type, that can be used for validation.

    :param locatable_type: An object pointing to the type expression.
    :param resolver: The namespace that can be used to resolve the type expression
    """
    # quickfix issue #1774
    allowed_element_type: Type = Any()
    if locatable_type.value == "list":
        return List()
    if locatable_type.value == "dict":
        return TypedDict(allowed_element_type)

    # stack of transformations to be applied to the base inmanta_type.Type
    # transformations will be applied right to left
    transformation_stack: List[Callable[[Type], Type]] = []

    if locatable_type.value.endswith("?"):
        # We don't want to modify the object we received as argument
        locatable_type = copy.copy(locatable_type)
        locatable_type.value = locatable_type.value[0:-1]
        transformation_stack.append(NullableType)

    if locatable_type.value.endswith("[]"):
        # We don't want to modify the object we received as argument
        locatable_type = copy.copy(locatable_type)
        locatable_type.value = locatable_type.value[0:-2]
        transformation_stack.append(TypedList)

    return functools.reduce(
        lambda acc, transform: transform(acc), reversed(transformation_stack), resolver.get_type(locatable_type)
    )
