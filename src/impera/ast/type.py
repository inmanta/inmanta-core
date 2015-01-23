"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

from impera.ast.constraint.expression import create_function
from impera.ast.variables import Variable


class CastException(Exception):
    """
        This exception is thrown when a type is unable to cast a value to its
        representation.
    """


class Type(object):
    """
        This class is the base class for all types that represent basic data.
        These are types that are not relations.
    """
    def __init__(self):
        pass

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
        try:
            float(value)
        except TypeError:
            raise ValueError("Invalid value '%s'" % value)
        except ValueError:
            raise ValueError("Invalid value '%s'" % value)

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
            return float(value)
        except ValueError:
            raise CastException()

    def __str__(self):
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
        return True  # allow this function to be called from a lambda function

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

    def __str__(self):
        return "bool"


class NoneType(Type):
    """
        This class represents an undefined value in the configuration model.
    """
    def __init__(self):
        Type.__init__(self)

    @classmethod
    def validate(cls, value):
        """
            Validate the value

            @see Type#validate
        """
        if value is not None:
            raise ValueError("Invalid value '%s'" % value)

        return True

    @classmethod
    def cast(cls, value):
        """
            Convert the given value to value that can be used by the operators
            defined on this type.
        """
        return None

    def __str__(self):
        return "none"


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
        if value is None:
            return True
        if not isinstance(value, str):
            raise ValueError("Invalid value '%s'" % value)

        return True

    def __str__(self):
        return "string"


class ConstraintType(Type):
    """
        A type that is based on Number or String but defines additional constraint on this type.
        These constraints only apply on the value of the type.

        The constraint on this type is defined by a regular expression.
    """
    def __init__(self, base_type, namespace, name):
        Type.__init__(self)

        self.__base_type = base_type  # : ConstrainableType
        self._constraint = None
        self.name = name
        self.namespace = namespace

    def get_base_type(self):
        """
            Returns the base that which is constraint by the constraint in this
            type.
        """
        return self.__base_type

    base_type = property(get_base_type)

    def set_constraint(self, expression):
        """
            Set the constraint for this type. This baseclass for constraint
            types requires the constraint to be set as a regex that can be
            compiled.
        """
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
        # throws an exception
        self.__base_type.validate(value)

        if not self._constraint(Variable(value)):
            raise ValueError("Invalid value '%s'" % value)

        return True

    def __str__(self):
        return "%s::%s" % (self.namespace, self.name)

TYPES = {"string": String, "number": Number, "bool": Bool, "list": list}
