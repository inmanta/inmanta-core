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

import numbers
from typing import Callable
from typing import List as PythonList
from typing import Optional, Sequence

from inmanta.ast import (
    DuplicateException,
    Locatable,
    Location,
    Named,
    Namespace,
    NotFoundException,
    RuntimeException,
    TypeNotFoundException,
)
from inmanta.execute.util import AnyType, NoneValue

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from inmanta.ast.statements import ExpressionStatement


class BasicResolver(object):
    def __init__(self, types):
        self.types = types

    def get_type(self, namespace, name):
        if not isinstance(name, str):
            raise Exception("Should Not Occur, bad AST construction")
        if "::" in name:
            if name in self.types:
                return self.types[name]
            else:
                raise TypeNotFoundException(name, namespace)
        elif name in TYPES:
            return self.types[name]
        else:
            cns = namespace
            while cns is not None:
                full_name = "%s::%s" % (cns.get_full_name(), name)
                if full_name in self.types:
                    return self.types[full_name]
                cns = cns.get_parent()
                raise TypeNotFoundException(name, namespace)


class NameSpacedResolver(object):
    def __init__(self, ns):
        self.ns = ns

    def get_type(self, name):
        return self.ns.get_type(name)

    def get_resolver_for(self, namespace: Namespace):
        return NameSpacedResolver(namespace)


class Type(Locatable):
    """
        This class is the base class for all types that represent basic data.
        These are types that are not relations.

        An instance of Type (or a subclass) represents an Inmanta type.
        Inmanta instances are represented by instances of other Python types.
    """

    def validate(self, value: Optional[object]) -> bool:
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        return True

    def type_string(self) -> Optional[str]:
        """
            Returns the type string as expressed in the inmanta DSL, if this type can be expressed in the DSL.
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
        return False


class NamedType(Type, Named):
    def get_double_defined_exception(self, other: "NamedType") -> "DuplicateException":
        """produce an error message for this type"""
        raise DuplicateException(self, other, "Type %s is already defined" % (self.get_full_name()))


class NullableType(Type):
    def __init__(self, basetype: Type) -> None:
        Type.__init__(self)
        self.basetype: Type = basetype

    def validate(self, value: Optional[object]) -> bool:
        """
            Validate the given value to check if it satisfies the constraint and
            the basetype.
        """
        if isinstance(value, NoneValue):
            return True

        return self.basetype.validate(value)

    def _wrap_type_string(self, string: str) -> str:
        return "%s?" % string

    def type_string(self) -> Optional[str]:
        base_type_string: Optional[str] = self.basetype.type_string()
        return None if base_type_string is None else self._wrap_type_string(base_type_string)

    def type_string_internal(self) -> str:
        return self._wrap_type_string(self.basetype.type_string_internal())

    def normalize(self) -> None:
        self.basetype.normalize()


class Primitive(Type):
    def __init__(self) -> None:
        Type.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], object]] = []

    def cast(self, value: Optional[object]) -> object:
        exception: RuntimeException = RuntimeException(None, "Failed to cast '%s' to %s" % (value, self))

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


class Number(Primitive):
    """
        This class represents an integer or float in the configuration model. On
        these integers the following operations are supported:

        +, -, /, *
    """

    def __init__(self) -> None:
        Primitive.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], numbers.Number]] = [int, float]

    def validate(self, value: Optional[object]) -> bool:
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if isinstance(value, AnyType):
            return True

        if not isinstance(value, numbers.Number):
            raise RuntimeException(None, "Invalid value '%s', expected Number" % value)

        return True  # allow this function to be called from a lambda function

    def is_primitive(self) -> bool:
        return True

    def get_location(self) -> Location:
        return None

    def type_string(self) -> str:
        return "number"

    def type_string_internal(self) -> str:
        return self.type_string()


class Integer(Number):
    """
        An innstance of this class represent the int type in the configuration model.
    """

    def __init__(self) -> None:
        Number.__init__(self)
        self.try_cast_functions: Sequence[Callable[[Optional[object]], object]] = [int]

    def validate(self, value: Optional[object]) -> bool:
        if not super().validate(value):
            return False
        if not isinstance(value, numbers.Integral):
            raise RuntimeException(None, "Invalid value '%s', expected %s" % (value, self.type_string()))
        return True

    def type_string(self) -> str:
        return "int"


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
        raise RuntimeException(None, "Invalid value '%s', expected Bool" % value)

    def type_string(self) -> str:
        return "bool"

    def type_string_internal(self) -> str:
        return self.type_string()

    def is_primitive(self) -> bool:
        return True

    def get_location(self) -> Location:
        return None


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
        if not isinstance(value, str):
            raise RuntimeException(None, "Invalid value '%s', expected String" % value)

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

    def get_location(self) -> Location:
        return None


class List(Type):
    """
        This class represents a list type in the configuration model. (instances represent instances)
    """

    def __init__(self):
        Type.__init__(self)

    def validate(self, value: Optional[object]) -> bool:
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if value is None:
            return True

        if isinstance(value, AnyType):
            return True

        if not isinstance(value, list):
            raise RuntimeException(None, "Invalid value '%s', expected %s" % (value, self.type_string()))

        return True

    def type_string_internal(self) -> str:
        return "List"

    def get_location(self) -> Location:
        return None


class TypedList(List):
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
        element_type_string: Optional[str] = self.element_type.type_string()
        return None if element_type_string is None else self._wrap_type_string(element_type_string)

    def type_string_internal(self) -> str:
        return self._wrap_type_string(self.element_type.type_string_internal())

    def get_location(self) -> Location:
        return None


class LiteralList(TypedList):
    """
    This class represents a list type containing only literals.
    (instances of the class represent the type)
    """

    def __init__(self) -> None:
        TypedList.__init__(self, Literal())

    def type_string(self) -> str:
        return "list"


class Dict(Type):
    """
        This class represents a list type in the configuration model. (instances represent instances)
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
            raise RuntimeException(None, "Invalid value '%s', expected dict" % value)

        return True

    def type_string_internal(self) -> str:
        return "Dict"

    def get_location(self) -> Location:
        return None


class TypedDict(Dict):
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

    def get_location(self) -> Location:
        return None


class LiteralDict(TypedDict):
    """
    This class represents a dict type containing only literals as values.
    (instances of the class represent the type)
    """

    def __init__(self) -> None:
        TypedDict.__init__(self, Literal())

    def type_string(self) -> str:
        return "dict"


class Union(Type):
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
        raise RuntimeException(None, "Invalid value '%s', expected %s" % (value, self))

    def type_string_internal(self) -> str:
        return "Union[%s]" % ",".join((t.type_string_internal() for t in self.types))


class Literal(Union):
    """
    This class represents a literal in the configuration model.
    (instances of the class represent the type)
    """

    def __init__(self) -> None:
        Union.__init__(self, [NullableType(Number()), Bool(), String(), TypedList(self), TypedDict(self)])

    def type_string_internal(self) -> str:
        return "Literal"


class ConstraintType(NamedType):
    """
        A type that is based on Number or String but defines additional constraint on this type.
        These constraints only apply on the value of the type.

        The constraint on this type is defined by a regular expression.
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
                self, "Invalid value %s, does not match constraint `%s`" % (repr(value), self.expression.pretty_print())
            )

        return True

    def type_string(self):
        return "%s::%s" % (self.namespace, self.name)

    def type_string_internal(self) -> str:
        return self.type_string()

    def get_full_name(self) -> str:
        return self.namespace.get_full_name() + "::" + self.name

    def get_namespace(self) -> "Namespace":
        return self.namespace

    def get_double_defined_exception(self, other: "NamedType") -> DuplicateException:
        return DuplicateException(self, other, "TypeConstraint %s is already defined" % (self.get_full_name()))


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


TYPES = {
    "string": String(),
    "number": Number(),
    "int": Integer(),
    "bool": Bool(),
    "list": LiteralList(),
    "dict": LiteralDict(),
}
