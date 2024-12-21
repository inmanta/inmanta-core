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

import copy
import functools
import numbers
import typing
from collections.abc import Mapping, Sequence
from typing import Callable
from typing import List as PythonList
from typing import Optional

import typing_inspect

from inmanta import references
from inmanta.ast import DuplicateException, Locatable, LocatableString, Named, Namespace, NotFoundException, RuntimeException
from inmanta.execute.util import NoneValue, Unknown
from inmanta.stable_api import stable_api

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast.statements import ExpressionStatement

inmantaLiteral = typing.Union[str, int, float, bool, Sequence["inmantaLiteral"], dict[str, "inmantaLiteral"]]


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
        """
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

    def is_primitive(self) -> bool:
        """
        Returns true iff this type is a primitive type, i.e. number, string, bool.
        """
        return False

    def get_base_type(self) -> "Type":
        """
        Returns the base type for this type, i.e. the plain type without modifiers such as expressed by
        `[]` and `?` in the :term:`DSL`.
        """
        return self

    def with_base_type(self, base_type: "Type") -> "Type":
        """
        Returns the type formed by replacing this type's base type with the supplied type.
        """
        return base_type

    def corresponds_to(self, pytype: type[object]) -> bool:
        """
        Return if the python type corresponds to this inmanta type

        Used only on the plugin boundary
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

    def to_python(self, instance: object) -> "object":
        """
        Convert an instance of this type to its python form

        should only be called if has_custom_to_python is True
        """
        raise NotImplementedError(f"Not implemented for {self}")


class NamedType(Type, Named):
    def get_double_defined_exception(self, other: "NamedType") -> "DuplicateException":
        """produce an error message for this type"""
        raise DuplicateException(self, other, "Type %s is already defined" % (self.get_full_name()))

    def type_string(self) -> str:
        return self.get_full_name()


@stable_api
class NullableType(Type):
    """
    Represents a nullable type in the Inmanta :term:`DSL`. For example `NullableType(Number())` represents `number?`.
    """

    def __init__(self, element_type: Type) -> None:
        Type.__init__(self)
        self.element_type: Type = element_type

    def validate(self, value: Optional[object]) -> bool:
        if isinstance(value, NoneValue):
            return True

        return self.element_type.validate(value)

    def _wrap_type_string(self, string: str) -> str:
        return "%s?" % string

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

    def is_primitive(self) -> bool:
        return self.element_type.is_primitive()

    def corresponds_to(self, pytype: type[object]) -> bool:
        if not typing_inspect.is_optional_type(pytype):
            return False
        # remove options from union
        other_types = [tp for tp in typing_inspect.get_args(pytype) if not typing_inspect.is_optional_type(tp)]
        # Typing union conveniently returns the base type if that is the only element
        return self.element_type.corresponds_to(typing.Union[*other_types])

    def as_python_type_string(self) -> "str | None":
        return f"{self.element_type.as_python_type_string()} | None"

    def to_python(self, instance: object) -> "object":
        if isinstance(instance, NoneValue):
            return None
        return self.element_type.to_python(instance)

    def has_custom_to_python(self) -> bool:
        return self.element_type.has_custom_to_python()


class AnyType(Type):

    def corresponds_to(self, pytype: type[object]) -> bool:
        return True

    def as_python_type_string(self) -> "str | None":
        return "object"

    def has_custom_to_python(self) -> bool:
        return False


@stable_api
class Primitive(Type):
    """
    Abstract base class representing primitive types.
    """

    def __init__(self) -> None:
        Type.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], object]] = []

    def cast(self, value: Optional[object]) -> object:
        """
        Cast a value to this type. If the value can not be cast, raises a :py:class:`inmanta.ast.RuntimeException`.
        """
        exception: RuntimeException = RuntimeException(None, f"Failed to cast '{value}' to {self}")

        if isinstance(value, Unknown):
            # propagate unknowns
            return value

        for cast in self.try_cast_functions:
            try:
                return cast(value)
            except ValueError:
                continue
            except TypeError:
                raise exception
        raise exception

    def type_string_internal(self) -> str:
        return "Primitive"

    def __eq__(self, other: object) -> bool:
        if other.__class__ != self.__class__:
            return NotImplemented
        return True

    def has_custom_to_python(self) -> bool:
        # All primitives can be trivially converted
        return True


@stable_api
class Number(Primitive):
    """
    This class represents an integer or a float in the configuration model.
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], numbers.Number]] = [float]

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
        if isinstance(value, AnyType):
            return True
        if not isinstance(value, numbers.Number):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

        return True  # allow this function to be called from a lambda function

    def is_primitive(self) -> bool:
        return True

    def get_location(self) -> None:
        return None

    def type_string(self) -> str:
        return "number"

    def type_string_internal(self) -> str:
        return self.type_string()

    def corresponds_to(self, pytype: type[object]) -> bool:
        return pytype in [int, float, numbers.Number]

    def as_python_type_string(self) -> "str | None":
        return "numbers.Number"

    def to_python(self, instance: object) -> "object":
        return instance


@stable_api
class Float(Primitive):
    """
    This class is an alias for the Number class and represents a float in
    the configuration model.
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], object]] = [float]

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        if isinstance(value, AnyType):
            return True
        if references.is_reference_of(value, float):
            return True
        if not isinstance(value, float):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")
        return True  # allow this function to be called from a lambda function

    def is_primitive(self) -> bool:
        return True

    def get_location(self) -> None:
        return None

    def type_string(self) -> str:
        return "float"

    def type_string_internal(self) -> str:
        return self.type_string()

    def corresponds_to(self, pytype: type[object]) -> bool:
        return pytype is float

    def as_python_type_string(self) -> "str | None":
        return "float"

    def to_python(self, instance: object) -> "object":
        return instance


@stable_api
class Integer(Number):
    """
    An instance of this class represents the int type in the configuration model.
    """

    def __init__(self) -> None:
        Number.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], object]] = [int]

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        if isinstance(value, AnyType):
            return True
        if references.is_reference_of(value, int):
            return True
        if not isinstance(value, numbers.Integral):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")
        return True  # allow this function to be called from a lambda function

    def type_string(self) -> str:
        return "int"

    def corresponds_to(self, pytype: type[object]) -> bool:
        return pytype is int

    def as_python_type_string(self) -> "str | None":
        return "int"

    def to_python(self, instance: object) -> "object":
        return instance


@stable_api
class Bool(Primitive):
    """
    This class represents a simple boolean that can hold true or false.
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], object]] = [bool]

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        if isinstance(value, AnyType):
            return True
        if isinstance(value, bool):
            return True
        if references.is_reference_of(value, bool):
            return True
        raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

    def cast(self, value: Optional[object]) -> object:
        return super().cast(value if not isinstance(value, NoneValue) else None)

    def type_string(self) -> str:
        return "bool"

    def type_string_internal(self) -> str:
        return self.type_string()

    def is_primitive(self) -> bool:
        return True

    def get_location(self) -> None:
        return None

    def corresponds_to(self, pytype: type[object]) -> bool:
        return pytype is bool

    def as_python_type_string(self) -> "str | None":
        return "bool"

    def to_python(self, instance: object) -> "object":
        return instance


@stable_api
class String(Primitive):
    """
    This class represents a string type in the configuration model.
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], object]] = [str]

    def validate(self, value: Optional[object]) -> bool:
        """
        Validate the given value to check if it satisfies the constraints
        associated with this type
        """
        if isinstance(value, AnyType):
            return True
        if references.is_reference_of(value, str):
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

    def is_primitive(self) -> bool:
        return True

    def get_location(self) -> None:
        return None

    def corresponds_to(self, pytype: type[object]) -> bool:
        return pytype is str

    def as_python_type_string(self) -> "str | None":
        return "str"

    def to_python(self, instance: object) -> "object":
        return instance


@stable_api
class List(Type):
    """
    Instances of this class represent a list type containing any types of values.
    This class refers to the list type used in plugin annotations. For the list type in the Inmanta DSL, see `LiteralList`.
    """

    def __init__(self):
        Type.__init__(self)

    def validate(self, value: Optional[object]) -> bool:
        if value is None:
            return True

        if isinstance(value, AnyType):
            return True

        if not isinstance(value, list):
            raise RuntimeException(None, f"Invalid value '{value}', expected {self.type_string()}")

        return True

    def type_string(self) -> str:
        # This is not a type in the model, but it is used in plugin annotations, which are also part of the DSL.
        return "list"

    def type_string_internal(self) -> str:
        return "List"

    def get_location(self) -> None:
        return None

    def corresponds_to(self, pytype: type[object]) -> bool:
        if typing_inspect.is_union_type(pytype):
            return False

        if not typing_inspect.is_generic_type(pytype):
            return issubclass(pytype, Sequence)

        origin = typing_inspect.get_origin(pytype)
        return issubclass(origin, Sequence)

    def as_python_type_string(self) -> "str | None":
        return "list[object]"

    def has_custom_to_python(self) -> bool:
        # Any can not be converted
        return False


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
        if not List.validate(self, value):
            return False

        assert isinstance(value, list)
        for element in value:
            if not self.element_type.validate(element):
                return False

        return True

    def _wrap_type_string(self, string: str) -> str:
        return "%s[]" % string

    def type_string(self) -> Optional[str]:
        element_type_string = self.element_type.type_string()
        return None if element_type_string is None else self._wrap_type_string(element_type_string)

    def type_string_internal(self) -> str:
        return self._wrap_type_string(self.element_type.type_string_internal())

    def get_location(self) -> None:
        return None

    def get_base_type(self) -> Type:
        return self.element_type

    def with_base_type(self, base_type: Type) -> Type:
        return TypedList(base_type)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypedList):
            return NotImplemented
        return self.element_type == other.element_type

    def is_primitive(self) -> bool:
        return self.get_base_type().is_primitive()

    def corresponds_to(self, pytype: type[object]) -> bool:
        if typing_inspect.is_union_type(pytype):
            return False

        if not typing_inspect.is_generic_type(pytype):
            return issubclass(pytype, Sequence)

        origin = typing_inspect.get_origin(pytype)
        if not issubclass(origin, Sequence):
            return False

        args = typing_inspect.get_args(pytype, True)
        if len(args) != 1:
            return False
        return self.element_type.corresponds_to(args[0])

    def as_python_type_string(self) -> "str | None":
        return f"list[{self.element_type.as_python_type_string()}]"

    def to_python(self, instance: object) -> "object":
        assert isinstance(instance, Sequence), f"This method can only be called on iterables, not on {type(instance)}"
        return [self.element_type.to_python(element) for element in instance]

    def has_custom_to_python(self) -> bool:
        return self.element_type.has_custom_to_python()


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

    def get_location(self) -> None:
        return None

    def as_python_type_string(self) -> "str | None":
        return "dict"

    def corresponds_to(self, pytype: type[object]) -> bool:
        if typing_inspect.is_union_type(pytype):
            return False

        if not typing_inspect.is_generic_type(pytype):
            # None generic dict is fine
            return issubclass(pytype, Mapping)

        # Generic dict
        origin = typing_inspect.get_origin(pytype)
        if not issubclass(origin, Mapping):
            return False

        args = typing_inspect.get_args(pytype, True)
        if len(args) != 2:
            return False

        # always require dict[str,
        if args[0] != str:
            return False
        return True


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
        if not Dict.validate(self, value):
            return False

        assert isinstance(value, dict)
        for element in value.values():
            self.element_type.validate(element)

        return True

    def type_string_internal(self) -> str:
        return "dict[%s]" % self.element_type.type_string_internal()

    def get_location(self) -> None:
        return None

    def corresponds_to(self, pytype: type[object]) -> bool:
        if typing_inspect.is_union_type(pytype):
            return False

        if not typing_inspect.is_generic_type(pytype):
            # None generic dict is fine
            return issubclass(pytype, Mapping)

        # generic dict
        origin = typing_inspect.get_origin(pytype)
        if not issubclass(origin, Mapping):
            return False

        args = typing_inspect.get_args(pytype, True)
        if len(args) != 2:
            return False

        # first argument is always str
        if args[0] != str:
            return False

        # second is base type
        return self.element_type.corresponds_to(args[1])

    def as_python_type_string(self) -> "str | None":
        return f"dict[str, {self.element_type.as_python_type_string()}]"

    def has_custom_to_python(self) -> bool:
        return self.element_type.has_custom_to_python()

    def to_python(self, instance: object) -> "object":
        assert isinstance(instance, dict)
        base = self.get_base_type()
        return {k: base.to_python(v) for k, v in instance.items()}


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

    def is_primitive(self) -> bool:
        return True


@stable_api
class Union(Type):
    """
    Instances of this class represent a union of multiple types.
    """

    def __init__(self, types: PythonList[Type]) -> None:
        Type.__init__(self)
        self.types: PythonList[Type] = types

    def validate(self, value: object) -> bool:
        for typ in self.types:
            try:
                if typ.validate(value):
                    return True
            except RuntimeException:
                pass
        raise RuntimeException(None, f"Invalid value '{value}', expected {self}")

    def type_string_internal(self) -> str:
        return "Union[%s]" % ",".join(t.type_string_internal() for t in self.types)

    def as_python_type_string(self) -> "str | None":
        types = [tp.as_python_type_string() for tp in self.types]

        effective_types = [tp for tp in types if tp is not None]
        if len(types) != len(effective_types):
            # One is not converted
            return None
        return f" | ".join(effective_types)

    def has_custom_to_python(self) -> bool:
        # If we mix convertible and non convertible, it won't work, so we avoid it
        return False

    def corresponds_to(self, pytype: type[object]) -> bool:
        raise NotImplementedError("No unions can be specified on the plugin boundary")


@stable_api
class Literal(Union):
    """
    Instances of this class represent a literal in the configuration model. A literal is a primitive or a list or dict
    where all values are literals themselves.
    """

    def __init__(self) -> None:
        Union.__init__(self, [NullableType(Float()), Number(), Bool(), String(), TypedList(self), TypedDict(self)])

    def type_string_internal(self) -> str:
        return "Literal"

    def as_python_type_string(self) -> "str | None":
        # Keep it simple
        return "object"

    def corresponds_to(self, pytype: type[object]) -> bool:
        # Infinite recursive type, avoid the mess
        if pytype in [int, float, bool, str]:
            return True
        if List.corresponds_to(self, pytype):
            return True
        if Dict.corresponds_to(self, pytype):
            return True
        return False


@stable_api
class ConstraintType(NamedType):
    """
    A type that is based on a primitive type but defines additional constraints on this type.
    These constraints only apply on the value of the type.
    """

    def __init__(self, namespace: Namespace, name: str) -> None:
        NamedType.__init__(self)

        self.basetype: Optional[Type] = None  # : ConstrainableType
        self._constraint = None
        self.name: str = name
        self.namespace: Namespace = namespace
        self.comment: Optional[str] = None
        self.expression: Optional["ExpressionStatement"] = None

    def normalize(self) -> None:
        assert self.expression is not None
        self.expression.normalize()

    def set_constraint(self, expression) -> None:
        """
        Set the constraint for this type. This baseclass for constraint
        types requires the constraint to be set as a regex that can be
        compiled.
        """
        self.expression = expression
        self._constraint = create_function(self, expression)

    def get_constraint(self):
        """
        Get the string representation of the constraint
        """
        return self._constraint

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

    def get_base_type(self) -> "Type":
        assert self.basetype is not None
        return self.basetype

    def has_custom_to_python(self) -> bool:
        # Substitute for base type for now
        return self.get_base_type().has_custom_to_python()

    def corresponds_to(self, pytype: type[object]) -> bool:
        return self.get_base_type().corresponds_to(pytype)

    def as_python_type_string(self) -> "str | None":
        return self.get_base_type().as_python_type_string()

    def to_python(self, instance: object) -> "object":
        return self.get_base_type().to_python(instance)


def create_function(tp: ConstraintType, expression: "ExpressionStatement"):
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
    allowed_element_type: Type = Type()
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
