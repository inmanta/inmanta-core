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
import impera.ast.variables
from impera.ast import Namespace
from impera.execute.util import Unknown


class BasicResolver(object):

    def __init__(self, types):
        self.types = types

    def get_type(self, namespace, name):
        if isinstance(name, impera.ast.variables.Reference):
            raise Exception("Bad")
        if "::" in name:
            if name in self.types:
                return self.types[name]
            else:
                raise Exception("type not found " + name)
        elif name in TYPES:
            return self.types[name]
        else:
            cns = namespace
            while cns is not None:
                full_name = "%s::%s" % (cns.get_full_name(), name)
                if full_name in self.types:
                    return self.types[full_name]
                cns = cns.get_parent()
                raise Exception("type not found " + name + " " + namespace.get_full_name())


class NameSpacedResolver(object):

    def __init__(self, types, ns):
        self.types = types
        self.ns = ns

    def get_type(self, name):
        if "::" in name:
            if name in self.types:
                return self.types[name]
            else:
                raise Exception("type not found " + name)
        elif name in TYPES:
            return TYPES[name]
        else:
            cns = self.ns
            while cns is not None:
                full_name = "%s::%s" % (cns.get_full_name(), name)
                if full_name in self.types:
                    return self.types[full_name]
                cns = cns.get_parent()
            raise Exception("type not found " + name)

    def get_resolver_for(self, namespace: Namespace):
        return NameSpacedResolver(self.types, namespace)


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

    def __str__(self):
        return str(self.__class__)

    def normalize(self, resolver):
        pass


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
        except TypeError as t:
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

    @classmethod
    def __str__(cls):
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

    @classmethod
    def __str__(cls):
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
        if isinstance(value, Unknown):
            return True
        if not isinstance(value, str):
            raise ValueError("Invalid value '%s'" % value)

        return True

    @classmethod
    def __str__(cls):
        return "string"


class List(Type, list):
    """
        This class represents a string type in the configuration model.
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

        if not isinstance(value, list):
            raise ValueError("Invalid value '%s'" % value)

        return True

    @classmethod
    def __str__(cls):
        return "list"


class ConstraintType(Type):
    """
        A type that is based on Number or String but defines additional constraint on this type.
        These constraints only apply on the value of the type.

        The constraint on this type is defined by a regular expression.
    """

    def __init__(self, name):
        Type.__init__(self)

        self.basetype = None  # : ConstrainableType
        self._constraint = None
        self.name = name
        self.namespace = None

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
        if isinstance(value, Unknown):
            return True

        self.basetype.validate(value)

        if not self._constraint(value):
            raise ValueError("Invalid value '%s'" % value)

        return True

    def __str__(self):
        return "%s::%s" % (self.namespace, self.name)

TYPES = {"string": String, "number": Number, "bool": Bool, "list": List}
