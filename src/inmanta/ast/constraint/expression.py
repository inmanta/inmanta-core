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

import re
from abc import ABCMeta, abstractmethod
from typing import Dict, Optional

import inmanta.execute.dataflow as dataflow
from inmanta.ast import LocatableString, RuntimeException, TypingException
from inmanta.ast.statements import Literal, ReferenceStatement
from inmanta.ast.type import Bool, create_function
from inmanta.ast.variables import IsDefinedReferenceHelper, Reference
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import ExecutionUnit, HangUnit, QueueScheduler, RawUnit, Resolver, ResultVariable


class InvalidNumberOfArgumentsException(Exception):
    """
    This exception is raised if an invalid amount of arguments is passed
    to an operator.
    """

    def __init__(self, msg: str) -> None:
        Exception.__init__(self, msg)


class UnboundVariableException(Exception):
    """
    This execption is raised if an expression is evaluated when not all
    variables have been resolved
    """

    def __init__(self, msg: str) -> None:
        Exception.__init__(self, msg)


class OpMetaClass(ABCMeta):
    """
    This metaclass registers a class with the operator class if it contains
    a string that specifies the op it is able to handle. This metaclass
    only makes sense for subclasses of the Operator class.
    """

    def __init__(self, name, bases, attr_dict):
        attribute = "_%s__op" % name
        if attribute in attr_dict:
            Operator.register_operator(attr_dict[attribute], self)
        super(OpMetaClass, self).__init__(name, bases, attr_dict)


class IsDefined(ReferenceStatement):
    def __init__(self, attr: Optional[Reference], name: LocatableString) -> None:
        if attr:
            children = [attr]
        else:
            children = []
        super(IsDefined, self).__init__(children)
        self.attr = attr
        self.name = str(name)

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> Dict[object, ResultVariable]:
        # introduce temp variable to contain the eventual result of this stmt
        temp = ResultVariable()
        temp.set_provider(self)
        # construct waiter
        resumer = IsDefinedReferenceHelper(temp, self.attr, self.name)
        self.copy_location(resumer)

        # wait for the instance
        if self.requires():
            RawUnit(queue, resolver, super().requires_emit(resolver, queue), resumer)
        else:
            resumer.resume({}, resolver, queue)
        return {self: temp}

    def execute(self, requires: Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        # helper returned: return result
        return requires[self]

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("IsDefined.get_node() placeholder for %s" % self).reference()

    def pretty_print(self) -> str:
        if self.attr is not None:
            name = "%s.%s" % (self.attr.pretty_print(), self.name)
        else:
            name = self.name
        return "%s is defined" % name


class Operator(ReferenceStatement, metaclass=OpMetaClass):
    """
    This class is an abstract base class for all operators that can be used in expressions
    """

    # A hash to lookup each handler
    __operator = {}

    @classmethod
    def register_operator(cls, operator_string, operator_class):
        """
        Register a new operator
        """
        cls.__operator[operator_string] = operator_class

    @classmethod
    def get_operator_class(cls, oper):
        """
        Get the class that implements the given operator. Returns none of the operator does not exist
        """
        if oper in cls.__operator:
            return cls.__operator[oper]

        return None

    def __init__(self, name, children):
        self.__number_arguments = len(children)
        self._arguments = children
        ReferenceStatement.__init__(self, self._arguments)
        self.__name = name

    def get_name(self):
        return self.__name

    def execute(self, requires, resolver, queue):
        return self._op([x.execute(requires, resolver, queue) for x in self._arguments])

    def execute_direct(self, requires):
        return self._op([x.execute_direct(requires) for x in self._arguments])

    def get_op(self):
        attribute = "_%s__op" % type(self).__name__
        if hasattr(self, attribute):
            return getattr(self, attribute)
        return self.get_name()

    @abstractmethod
    def _op(self, args):
        """
        Abstract method that implements the operator
        """

    def __repr__(self):
        """
        Return a representation of the op
        """
        arg_list = []
        for arg in self._arguments:
            arg_list.append(str(arg))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(arg_list))

    def to_function(self):
        """
        Returns a function that represents this expression
        """
        return create_function(self)

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("Operator.get_node() placeholder for %s" % self).reference()

    def pretty_print(self):
        return repr(self)


class BinaryOperator(Operator):
    """
    This class represents a binary operator.
    """

    def __init__(self, name, op1, op2):
        Operator.__init__(self, name, [op1, op2])

    def _op(self, args):
        """
        The method that needs to be implemented for this operator
        """
        # pylint: disable-msg=W0142
        return self._bin_op(*args)

    @abstractmethod
    def _bin_op(self, arg1, arg2):
        """
        The implementation of the binary op
        """

    def pretty_print(self):
        return "(%s %s %s)" % (self._arguments[0].pretty_print(), self.get_op(), self._arguments[1].pretty_print())

    def __repr__(self) -> str:
        return self.pretty_print()


class LazyBooleanOperator(BinaryOperator):
    """
    This class represents a binary boolean operator.
    """

    def __init__(self, name, op1, op2):
        Operator.__init__(self, name, [op1, op2])

    def requires_emit(self, resolver, queue):
        # introduce temp variable to contain the eventual result of this stmt
        temp = ResultVariable()
        temp.set_type(Bool())

        temp.set_provider(self)

        # wait for the lhs
        HangUnit(queue, resolver, self.children[0].requires_emit(resolver, queue), temp, self)
        return {self: temp}

    def _validate_value(self, value: object, side: int) -> None:
        try:
            Bool().validate(value)
        except RuntimeException as e:
            e.set_statement(self)
            e.msg = "Invalid %s hand value `%s`: `%s` expects a boolean" % (
                "left" if side == 0 else "right",
                value,
                self.get_op(),
            )
            raise e

    def resume(self, requires, resolver, queue, target):
        result = self.children[0].execute(requires, resolver, queue)
        self._validate_value(result, 0)
        if self._is_final(result):
            target.set_value(result, self.location)
        else:
            ExecutionUnit(
                queue, resolver, target, self.children[1].requires_emit(resolver, queue), self.children[1], owner=self
            )

    def execute_direct(self, requires):
        lhs = self.children[0].execute_direct(requires)
        self._validate_value(lhs, 0)
        if self._is_final(lhs):
            return lhs
        else:
            rhs = self.children[1].execute_direct(requires)
            self._validate_value(rhs, 1)
            return rhs

    def execute(self, requires, resolver, queue):
        # helper returned: return result
        return requires[self]

    def _is_final(self, result):
        raise NotImplementedError()

    def _bin_op(self, arg1, arg2):
        """
        The implementation of the binary op
        """
        raise NotImplementedError()


class UnaryOperator(Operator):
    """
    This class represents a unary operator
    """

    def __init__(self, name, op1):
        Operator.__init__(self, name, [op1])

    def _op(self, args):
        """
        This method calls the implementation of the operator
        """
        # pylint: disable-msg=W0142
        return self._un_op(*args)

    @abstractmethod
    def _un_op(self, arg):
        """
        The implementation of the operator
        """

    def pretty_print(self):
        return "(%s %s)" % (self.get_op(), self._arguments[0].pretty_print())


class Not(UnaryOperator):
    """
    The negation operator
    """

    __op = "not"

    def __init__(self, arg):
        UnaryOperator.__init__(self, "negation", arg)

    def _un_op(self, arg):
        """
        Return the inverse of the argument

        @see Operator#_op
        """
        try:
            Bool().validate(arg)
        except RuntimeException as e:
            e.set_statement(self)
            e.msg = "Invalid value `%s`: `%s` expects a boolean" % (arg, self.get_op())
            raise e
        return not arg


class Regex(BinaryOperator):
    """
    An operator that does regex matching
    """

    def __init__(self, op1, op2):
        regex = re.compile(op2)
        BinaryOperator.__init__(self, "regex", op1, Literal(regex))

    def _bin_op(self, arg1, arg2):
        """
        @see Operator#_op
        """
        if not isinstance(arg1, str):
            raise TypingException(self, "Regex can only be match with strings. %s is of type %s" % arg1)

        return arg2.match(arg1) is not None

    def pretty_print(self) -> str:
        return "/%s/" % self._arguments[1].value.pattern

    def __repr__(self):
        """
        Return a representation of the op
        """
        return self.pretty_print()


class Equals(BinaryOperator):
    """
    The equality operator
    """

    __op = "=="

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "equality", op1, op2)

    def _bin_op(self, arg1, arg2):
        """
        @see Operator#_op
        """
        return arg1 == arg2


class LessThan(BinaryOperator):
    """
    The less than operator
    """

    __op = "<"

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "less than", op1, op2)

    def _bin_op(self, arg1, arg2):
        """
        @see Operator#_op
        """
        if not isinstance(arg1, (int, float)) or not isinstance(arg2, (int, float)):
            raise TypingException(self, "Can only compare numbers.")
        return arg1 < arg2


class GreaterThan(BinaryOperator):
    """
    The more than operator
    """

    __op = ">"

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "greater than", op1, op2)

    def _bin_op(self, arg1, arg2):
        """
        @see Operator#_op
        """
        if not isinstance(arg1, (int, float)) or not isinstance(arg2, (int, float)):
            raise TypingException(self, "Can only compare numbers.")
        return arg1 > arg2


class LessThanOrEqual(BinaryOperator):
    """
    The less than or equal operator
    """

    __op = "<="

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "less than or equal", op1, op2)

    def _bin_op(self, arg1, arg2):
        """
        @see Operator#_op
        """
        if not isinstance(arg1, (int, float)) or not isinstance(arg2, (int, float)):
            raise TypingException(self, "Can only compare numbers.")
        return arg1 <= arg2


class GreaterThanOrEqual(BinaryOperator):
    """
    The more than or equal operator
    """

    __op = ">="

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "greater than or equal", op1, op2)

    def _bin_op(self, arg1, arg2):
        """
        @see Operator#_op
        """
        if not isinstance(arg1, (int, float)) or not isinstance(arg2, (int, float)):
            raise TypingException(self, "Can only compare numbers.")
        return arg1 >= arg2


class NotEqual(BinaryOperator):
    """
    The not equal operator
    """

    __op = "!="

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "not equal", op1, op2)

    def _bin_op(self, arg1, arg2):
        """
        @see Operator#_op
        """
        return arg1 != arg2


class And(LazyBooleanOperator):
    """
    The and boolean operator
    """

    __op = "and"

    def __init__(self, op1, op2):
        LazyBooleanOperator.__init__(self, "and", op1, op2)

    def _is_final(self, result: bool):
        return not result


class Or(LazyBooleanOperator):
    """
    The or boolean operator
    """

    __op = "or"

    def __init__(self, op1, op2):
        LazyBooleanOperator.__init__(self, "or", op1, op2)

    def _is_final(self, result: bool):
        return result


class In(BinaryOperator):
    """
    The in operator for iterable types and dicts
    """

    __op = "in"

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "in", op1, op2)

    def _bin_op(self, arg1, arg2):
        """
        @see Operator#_op
        """
        if isinstance(arg2, dict):
            return arg1 in arg2
        elif isinstance(arg2, list):
            for arg in arg2:
                if arg == arg1:
                    return True
        else:
            raise TypingException(self, "Operand two of 'in' can only be a list or dict (%s)" % arg2[0])

        return False
