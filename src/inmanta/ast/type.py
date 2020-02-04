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
from typing import Any, Iterable
from typing import List as PythonList
from typing import Optional
from typing import Union as PythonUnion
from typing import cast

from inmanta.ast import DuplicateException, Locatable, Location, Named, Namespace, RuntimeException, TypeNotFoundException
from inmanta.execute.util import AnyType, NoneValue


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


class CastException(Exception):
    """
        This exception is thrown when a type is unable to cast a value to its
        representation.
    """


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
        raise NotImplementedError()

    def cast(self, value: Optional[object]) -> Optional[object]:
        """
            Cast the given value to this type. If this fails a CastException
            is thrown.

            :param value: The value to cast
        """
        raise NotImplementedError()

    def type_string(self):
        """get the name of the type """
        raise NotImplementedError()

    def __str__(self):
        """get the string representation of the instance of the type """
        raise NotImplementedError(type(self))

    def normalize(self):
        pass

    def is_primitive(self):
        return False


class NamedType(Type, Named):
    def get_double_defined_exception(self, other: "NamedType") -> DuplicateException:
        """produce a customized error message for this type"""
        raise NotImplementedError()


class NullableType(Type):
    def __init__(self, basetype):
        Type.__init__(self)
        self.basetype = basetype

    def cast(self, value):
        """
            Cast the value to the basetype of this constraint
        """
        return self.basetype.cast(value)

    def validate(self, value: Optional[object]) -> bool:
        """
            Validate the given value to check if it satisfies the constraint and
            the basetype.
        """
        if isinstance(value, NoneValue):
            return True

        return self.basetype.validate(value)

    def type_string(self):
        return "%s?" % (self.basetype.type_string())

    def __str__(self):
        return "%s" % (self.basetype)

    def normalize(self):
        self.basetype.normalize()


class Number(Type):
    """
        This class represents an integer or float in the configuration model. On
        these integers the following operations are supported:

        +, -, /, *
    """

    def __init__(self):
        Type.__init__(self)

    def validate(self, value):
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if isinstance(value, AnyType):
            return True

        if not isinstance(value, numbers.Number):
            raise RuntimeException(None, "Invalid value '%s', expected Number" % value)

        return True  # allow this function to be called from a lambda function

    def cast(self, value: Optional[object]) -> Optional[PythonUnion[int, float]]:
        """
            Cast the value to a number.

            :see CastableType#cast
        """
        if value is None:
            return value

        try:
            fl_value = float(cast(Any, value))
            try:
                int_value = int(cast(Any, value))
            except ValueError:
                int_value = 0

            if fl_value == int_value:
                return int_value

            return fl_value
        except ValueError:
            raise CastException()

    def __str__(self):
        return "number"

    def is_primitive(self):
        return True

    def get_location(self) -> Location:
        return None

    def type_string(self):
        return "number"


class Bool(Type):
    """
        This class represents a simple boolean that can hold true or false.
    """

    def __init__(self):
        Type.__init__(self)

    def validate(self, value):
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if isinstance(value, AnyType):
            return True
        if isinstance(value, bool):
            return True
        raise RuntimeException(None, "Invalid value '%s', expected Bool" % value)

    def cast(self, value: Optional[object]) -> bool:
        """
            Convert the given value to value that can be used by the operators
            defined on this type.
        """
        if value == "true" or value == "True" or value == 1 or value == "1" or value is True:
            return True

        if value == "false" or value == "False" or value == 0 or value == "0" or value is False:
            return False

        raise CastException()

    def type_string(self):
        return "bool"

    def is_primitive(self):
        return True

    def get_location(self) -> Location:
        return None


class String(Type):
    """
        This class represents a string type in the configuration model.
    """

    def __init__(self):
        Type.__init__(self)

    def cast(self, value: Optional[object]) -> str:
        """
            Cast the given value to a string

            :see CastableType#cast
        """
        return str(value)

    def validate(self, value):
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if isinstance(value, AnyType):
            return True
        if not isinstance(value, str):
            raise RuntimeException(None, "Invalid value '%s', expected String" % value)

        return True

    def type_string(self):
        return "string"

    def is_primitive(self):
        return True

    def get_location(self) -> Location:
        return None


class List(Type):
    """
        This class represents a list type in the configuration model. (instances represent instances)
    """

    def __init__(self):
        Type.__init__(self)

    def cast(self, value):
        """
            Cast the given value to a string

            :see CastableType#cast
        """
        return list(value)

    def validate(self, value):
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if value is None:
            return True

        if isinstance(value, AnyType):
            return True

        if not isinstance(value, list):
            raise RuntimeException(None, "Invalid value '%s', expected list" % value)

        return True

    #     @classmethod
    #     def __str__(cls):
    #         return "list"

    def type_string(self):
        return "list"

    def __str__(self):
        return self.type_string()

    def get_location(self) -> Location:
        return None


class TypedList(List):
    def __init__(self, element_type):
        List.__init__(self)
        self.element_type: Type = element_type

    def normalize(self):
        self.element_type.normalize()

    def cast(self, value):
        if not isinstance(value, Iterable):
            raise CastException()
        return list([self.element_type.cast(x) for x in value])

    def validate(self, value: Optional[object]) -> bool:
        if not List().validate(value):
            return False

        assert isinstance(value, list)
        for element in value:
            self.element_type.validate(element)

        return True

    def type_string(self):
        return "%s[]" % (self.element_type.type_string())

    def get_location(self) -> Location:
        return None

    def __str__(self):
        return self.type_string()


class LiteralList(TypedList):
    """
    This class represents a list type containing only literals.
    (instances of the class represent the type)
    """

    def __init__(self):
        TypedList.__init__(self, Literal())


class Dict(Type):
    """
        This class represents a list type in the configuration model. (instances represent instances)
    """

    def __init__(self):
        Type.__init__(self)

    def cast(self, value):
        """
            Cast the given value to a string

            :see CastableType#cast
        """
        return dict(value)

    def validate(self, value):
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

    def type_string(self):
        return "dict"

    def __str__(self):
        return self.type_string()

    def get_location(self) -> Location:
        return None


class TypedDict(Dict):
    def __init__(self, element_type):
        List.__init__(self)
        self.element_type: Type = element_type

    def normalize(self):
        self.element_type.normalize()

    def cast(self, value):
        if not isinstance(value, dict):
            raise CastException()
        return list({k: self.element_type.cast(v) for k, v in value.items()})

    def validate(self, value: Optional[object]) -> bool:
        if not Dict().validate(value):
            return False

        assert isinstance(value, dict)
        for element in value.values():
            self.element_type.validate(element)

        return True

    def type_string(self):
        return "dict[%s, %s]" % (String().type_string(), self.element_type.type_string())

    def get_location(self) -> Location:
        return None

    def __str__(self):
        return self.type_string()


class LiteralDict(TypedDict):
    """
    This class represents a dict type containing only literals as values.
    (instances of the class represent the type)
    """

    def __init__(self):
        TypedDict.__init__(self, Literal())


class Union(Type):
    def __init__(self, types: PythonList[Type]):
        Type.__init__(self)
        self.types: PythonList[Type] = types

    def cast(self, value: Any) -> Any:
        if self.validate(value):
            return value
        raise CastException()

    def validate(self, value: object) -> bool:
        for typ in self.types:
            try:
                if typ.validate(value):
                    return True
            except RuntimeException:
                pass
        raise RuntimeException(None, "Invalid value '%s', expected Literal" % value)

    def type_string(self) -> str:
        return "literal"

    def __str__(self) -> str:
        return self.type_string()


class Literal(Union):
    """
    This class represents a literal in the configuration model.
    (instances of the class represent the type)
    """

    def __init__(self):
        Union.__init__(self, [NullableType(Number()), Bool(), String(), TypedList(self), TypedDict(self)])


class ConstraintType(NamedType):
    """
        A type that is based on Number or String but defines additional constraint on this type.
        These constraints only apply on the value of the type.

        The constraint on this type is defined by a regular expression.
    """

    comment: Optional[str]

    def __init__(self, namespace, name):
        NamedType.__init__(self)

        self.basetype = None  # : ConstrainableType
        self._constraint = None
        self.name = name
        self.namespace = namespace
        self.comment = None
        self.expression = None

    def normalize(self):
        self.expression.normalize()

    def set_constraint(self, expression):
        """
            Set the constraint for this type. This baseclass for constraint
            types requires the constraint to be set as a regex that can be
            compiled.
        """
        self.expression = expression
        self._constraint = create_function(expression)

    def get_constaint(self):
        """
            Get the string representation of the constraint
        """
        return self._constraint

    constraint = property(get_constaint, set_constraint)

    def cast(self, value: Any) -> str:
        """
            Cast the value to the basetype of this constraint
        """
        self.__base_type.cast(value)

    def validate(self, value):
        """
            Validate the given value to check if it satisfies the constraint and
            the basetype.
        """
        if isinstance(value, AnyType):
            return True

        self.basetype.validate(value)

        if not self._constraint(value):
            raise RuntimeException(self, "Invalid value '%s', constraint does not match" % value)

        return True

    def type_string(self):
        return "%s::%s" % (self.namespace, self.name)

    def __str__(self):
        return self.type_string()

    def get_full_name(self) -> str:
        return self.namespace.get_full_name() + "::" + self.name

    def get_namespace(self) -> "Namespace":
        return self.namespace

    def get_double_defined_exception(self, other: "NamedType") -> DuplicateException:
        return DuplicateException(self, other, "TypeConstraint %s is already defined" % (self.get_full_name()))


def create_function(expression):
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

        return expression.execute_direct({"self": args[0]})

    return function


TYPES = {"string": String(), "number": Number(), "bool": Bool(), "list": LiteralList(), "dict": Dict()}
