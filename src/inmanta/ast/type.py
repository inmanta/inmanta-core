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

from inmanta.ast import Namespace, TypeNotFoundException, RuntimeException, Locatable, Named, DuplicateException, Location
from inmanta.execute.util import AnyType, NoneValue
import numbers


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

        This code is rather tricky, as not all types are used in the same way

        1. types that are used as python types and inmanta types
            (i.e. an inmanta instance === python instance of the python class === the inmanta type)
            1. List
            2. Dict
        2. types for which the inmanta type == the python class and
            inmanta instances are python instances of a the corresponding python type
            1. Bool  => bool
            2. Number => float/int
            3. String => str
        3. types for which the inmanta type is an instance of the python type and
            inmanta instance is also an instance of the python type
            1. TypedList
        4. types for which the inmanta type is an instance of the python type and
            inmanta instance is an instance of a different python type
            1. ConstraintType
            2. NullableType

    """

    @classmethod
    def validate(cls, value):
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        raise NotImplementedError()

    @classmethod
    def cast(cls, value):
        """
            Cast the given value to this type. If this fails a CastException
            is thrown.

            @param value: The value to cast
        """
        raise NotImplementedError()

    def type_string(self):
        """get the name of the type """
        raise NotImplemented()

    def __str__(self):
        """get the string representation of the instance of the type """
        raise NotImplemented()

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

    def validate(self, value):
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


class Number(Type):
    """
        This class represents an integer or float in the configuration model. On
        these integers the following operations are supported:

        +, -, /, *
    """

    def __init__(self):
        Type.__init__(self)

    @classmethod
    def validate(cls, value):
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if isinstance(value, AnyType):
            return True

        if not isinstance(value, numbers.Number):
            raise RuntimeException(None, "Invalid value '%s'expected Number" % value)

        return True  # allow this function to be called from a lambda function

    @classmethod
    def cast(cls, value):
        """
            Cast the value to a number.

            :see CastableType#cast
        """
        if value is None:
            return value

        try:
            fl_value = float(value)
            try:
                int_value = int(value)
            except ValueError:
                int_value = 0

            if fl_value == int_value:
                return int_value

            return fl_value
        except ValueError:
            raise CastException()

    @classmethod
    def __str__(cls):
        return "number"

    @classmethod
    def is_primitive(cls):
        return True

    @classmethod
    def get_location(cls) -> Location:
        return None

    @classmethod
    def type_string(cls):
        return "number"


class Bool(Type):
    """
        This class represents a simple boolean that can hold true or false.
    """

    def __init__(self):
        Type.__init__(self)

    @classmethod
    def validate(cls, value):
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if isinstance(value, AnyType):
            return True
        if isinstance(value, bool):
            return True
        else:
            raise RuntimeException(None, "Invalid value '%s', expected Bool" % value)

    @classmethod
    def cast(cls, value):
        """
            Convert the given value to value that can be used by the operators
            defined on this type.
        """
        if (value == "true" or value == "True" or value == 1 or value == "1" or value is True):
            return True

        if (value == "false" or value == "False" or value == 0 or value == "0" or value is False):
            return False

        raise CastException()

    @classmethod
    def type_string(cls):
        return "bool"

    @classmethod
    def is_primitive(cls):
        return True

    @classmethod
    def get_location(cls) -> Location:
        return None


class String(Type, str):
    """
        This class represents a string type in the configuration model.
    """

    def __init__(self):
        Type.__init__(self)
        str.__init__(self)

    @classmethod
    def cast(cls, value):
        """
            Cast the given value to a string

            :see CastableType#cast
        """
        return str(value)

    @classmethod
    def validate(cls, value):
        """
            Validate the given value to check if it satisfies the constraints
            associated with this type
        """
        if isinstance(value, AnyType):
            return True
        if not isinstance(value, str):
            raise RuntimeException(None, "Invalid value '%s', expected String" % value)

        return True

    @classmethod
    def type_string(cls):
        return "string"

    @classmethod
    def is_primitive(cls):
        return True

    @classmethod
    def get_location(cls) -> Location:
        return None


class TypedList(Type):

    def __init__(self, basetype):
        Type.__init__(self)
        self.basetype = basetype

    def cast(self, value):
        """
            Cast the value to the basetype of this constraint
        """
        return list([self.basetype.cast(x) for x in value])

    def validate(self, value):
        """
            Validate the given value to check if it satisfies the constraint and
            the basetype.
        """
        if isinstance(value, AnyType):
            return True

        if value is None:
            return True

        if not isinstance(value, list):
            raise RuntimeException(None, "Invalid value '%s', expected list" % value)

        for x in value:
            self.basetype.validate(x)

        return True

    def type_string(self):
        return "%s[]" % (self.type_string())

    def __str__(self):
        return str(self.basetype)


class List(Type, list):
    """
        This class represents a list type in the configuration model. (instances represent instances)
    """

    def __init__(self):
        Type.__init__(self)
        list.__init__(self)

    @classmethod
    def cast(cls, value):
        """
            Cast the given value to a string

            :see CastableType#cast
        """
        return list(value)

    @classmethod
    def validate(cls, value):
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

    @classmethod
    def type_string(cls):
        return "list"

    def __str__(self):
        return list.__str__(self)


class Dict(Type, dict):
    """
        This class represents a list type in the configuration model. (instances represent instances)
    """

    def __init__(self):
        Type.__init__(self)
        dict.__init__(self)

    @classmethod
    def cast(cls, value):
        """
            Cast the given value to a string

            :see CastableType#cast
        """
        return dict(value)

    @classmethod
    def validate(cls, value):
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

    @classmethod
    def type_string(cls):
        return "dict"

    def __str__(self):
        return dict.__str__(self)


class ConstraintType(Type):
    """
        A type that is based on Number or String but defines additional constraint on this type.
        These constraints only apply on the value of the type.

        The constraint on this type is defined by a regular expression.
    """

    def __init__(self, namespace, name):
        Type.__init__(self)

        self.basetype = None  # : ConstrainableType
        self._constraint = None
        self.name = name
        self.namespace = namespace
        self.comment = None

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

    def cast(self, value):
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
            raise RuntimeException(None, "Invalid value '%s', constraint does not match" % value)

        return True

    def type_string(self):
        return "%s::%s" % (self.namespace, self.name)


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

        return expression.execute_direct({'self': args[0]})

    return function


TYPES = {"string": String, "number": Number, "bool": Bool, "list": List, "dict": Dict}
