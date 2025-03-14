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
from collections import abc
from itertools import chain
from typing import Optional, Type, TypeVar

import inmanta.execute.dataflow as dataflow
from inmanta import stable_api
from inmanta.ast import LocatableString, RuntimeException, TypingException
from inmanta.ast.statements import (
    AttributeAssignmentLHS,
    ExpressionStatement,
    Literal,
    ReferenceStatement,
    Resumer,
    StaticEagerPromise,
    VariableReferenceHook,
)
from inmanta.ast.type import Bool, create_function
from inmanta.ast.variables import IsDefinedGradual, Reference
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import ExecutionUnit, HangUnit, QueueScheduler, Resolver, ResultVariable, VariableABC
from inmanta.execute.util import Unknown


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

    def __init__(self, name, bases, attr_dict) -> None:
        attribute = "_%s__op" % name
        if attribute in attr_dict:
            Operator.register_operator(attr_dict[attribute], self)
        super().__init__(name, bases, attr_dict)


class IsDefined(ReferenceStatement):
    __slots__ = ("attr", "name")

    def __init__(self, attr: Optional[Reference], name: LocatableString) -> None:
        if attr:
            children = [attr]
        else:
            children = []
        super().__init__(children)
        self.attr = attr
        self.name = str(name)

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> dict[object, VariableABC]:
        requires: dict[object, VariableABC] = self._requires_emit_promises(resolver, queue)
        # introduce temp variable to contain the eventual result of this stmt
        temp = ResultVariable()
        # construct waiter
        gradual_helper: IsDefinedGradual = IsDefinedGradual(owner=self, target=temp)
        hook: VariableReferenceHook = VariableReferenceHook(
            instance=self.attr,
            name=self.name,
            variable_resumer=gradual_helper,
        )
        self.copy_location(hook)
        hook.schedule(resolver, queue)

        # wait for the attribute value
        requires[self] = temp
        return requires

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        # helper returned: return result
        return requires[self]

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("IsDefined.get_node() placeholder for %s" % self).reference()

    def pretty_print(self) -> str:
        if self.attr is not None:
            name = f"{self.attr.pretty_print()}.{self.name}"
        else:
            name = self.name
        return "%s is defined" % name


class Operator(ReferenceStatement, metaclass=OpMetaClass):
    """
    This class is an abstract base class for all operators that can be used in expressions
    """

    __slots__ = ("__number_arguments", "_arguments", "__name")

    # A hash to lookup each handler
    __operator: dict[str, "Type[Operator]"] = {}

    @classmethod
    def register_operator(cls, operator_string: str, operator_class: type["Operator"]) -> None:
        """
        Register a new operator
        """
        cls.__operator[operator_string] = operator_class

    @classmethod
    def get_operator_class(cls, oper: str) -> "Optional[Type[Operator]]":
        """
        Get the class that implements the given operator. Returns none of the operator does not exist
        """
        if oper in cls.__operator:
            return cls.__operator[oper]

        return None

    def __init__(self, name: str, children: list[ExpressionStatement]) -> None:
        self.__number_arguments = len(children)
        self._arguments = children
        ReferenceStatement.__init__(self, self._arguments)
        self.__name = name

    def get_name(self) -> str:
        return self.__name

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        return self._op([x.execute(requires, resolver, queue) for x in self._arguments])

    def execute_direct(self, requires: abc.Mapping[str, object]) -> object:
        return self._op([x.execute_direct(requires) for x in self._arguments])

    def get_op(self) -> str:
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
        return "{}({})".format(self.__class__.__name__, ", ".join(arg_list))

    def to_function(self):
        """
        Returns a function that represents this expression
        """
        return create_function(self)

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("Operator.get_node() placeholder for %s" % self).reference()

    def pretty_print(self) -> str:
        return repr(self)


class BinaryOperator(Operator):
    """
    This class represents a binary operator.
    """

    __slots__ = ()

    def __init__(self, name: str, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        Operator.__init__(self, name, [op1, op2])

    def _op(self, args):
        """
        The method that needs to be implemented for this operator
        """
        if any(isinstance(arg, Unknown) for arg in args):
            return Unknown(self)
        return self._bin_op(*args)

    @abstractmethod
    def _bin_op(self, arg1: object, arg2: object) -> object:
        """
        The implementation of the binary op
        """

    def pretty_print(self) -> str:
        return f"({self._arguments[0].pretty_print()} {self.get_op()} {self._arguments[1].pretty_print()})"

    def __repr__(self) -> str:
        return self.pretty_print()


class LazyBooleanOperator(BinaryOperator, Resumer):
    """
    This class represents a binary boolean operator.
    """

    __slots__ = ()

    def __init__(self, name: str, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        Operator.__init__(self, name, [op1, op2])

    def normalize(self, *, lhs_attribute: Optional[AttributeAssignmentLHS] = None) -> None:
        super().normalize()
        # lazy execution: we don't immediately emit the second operator so we need to hold its promises until we do
        self._own_eager_promises = list(self.children[1].get_all_eager_promises())

    def get_all_eager_promises(self) -> abc.Iterator["StaticEagerPromise"]:
        return chain(self._own_eager_promises, self.children[0].get_all_eager_promises())

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> dict[object, VariableABC]:
        requires: dict[object, VariableABC] = self._requires_emit_promises(resolver, queue)
        # introduce temp variable to contain the eventual result of this stmt
        temp: ResultVariable = ResultVariable()
        temp.set_type(Bool())

        # wait for the lhs
        requires.update(self.children[0].requires_emit(resolver, queue))
        HangUnit(queue, resolver, requires, temp, self)
        return {self: temp}

    def _validate_value(self, value: object, side: int) -> None:
        try:
            Bool().validate(value)
        except RuntimeException as e:
            e.set_statement(self)
            e.msg = "Invalid {} hand value `{}`: `{}` expects a boolean".format(
                "left" if side == 0 else "right",
                value,
                self.get_op(),
            )
            raise e

    def resume(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler, target: ResultVariable) -> None:
        result = self.children[0].execute(requires, resolver, queue)
        if isinstance(result, Unknown):
            target.set_value(result, self.location)
            return
        self._validate_value(result, 0)
        assert isinstance(result, bool)
        # second operand will get emitted now or never, no need to hold its promises any longer
        self._fulfill_promises(requires)
        if self._is_final(result):
            target.set_value(result, self.location)
        else:
            ExecutionUnit(
                queue, resolver, target, self.children[1].requires_emit(resolver, queue), self.children[1], owner=self
            )

    def execute_direct(self, requires: abc.Mapping[str, object]) -> object:
        lhs = self.children[0].execute_direct(requires)
        self._validate_value(lhs, 0)
        assert isinstance(lhs, bool)
        if self._is_final(lhs):
            return lhs
        else:
            rhs = self.children[1].execute_direct(requires)
            self._validate_value(rhs, 1)
            return rhs

    def _resolve(self, requires: dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        # helper returned: return result
        return requires[self]

    def _fulfill_promises(self, requires: dict[object, object]) -> None:
        # no need to fulfill promises, already done in resume
        pass

    def _is_final(self, result: bool) -> bool:
        raise NotImplementedError()

    def _bin_op(self, arg1: object, arg2: object) -> object:
        """
        The implementation of the binary op
        """
        raise NotImplementedError()


class UnaryOperator(Operator):
    """
    This class represents a unary operator
    """

    __slots__ = ()

    def __init__(self, name: str, op1: ExpressionStatement) -> None:
        Operator.__init__(self, name, [op1])

    def _op(self, args: abc.Sequence[object]) -> object:
        """
        This method calls the implementation of the operator
        """
        arg = args[0]
        if isinstance(arg, Unknown):
            return Unknown(self)
        return self._un_op(arg)

    @abstractmethod
    def _un_op(self, arg: object) -> object:
        """
        The implementation of the operator
        """

    def pretty_print(self) -> str:
        return f"({self.get_op()} {self._arguments[0].pretty_print()})"


class Not(UnaryOperator):
    """
    The negation operator
    """

    __slots__ = ()
    __op = "not"

    def __init__(self, arg):
        UnaryOperator.__init__(self, "negation", arg)

    def _un_op(self, arg: object) -> object:
        """
        Return the inverse of the argument

        @see Operator#_op
        """
        try:
            Bool().validate(arg)
        except RuntimeException as e:
            e.set_statement(self)
            e.msg = f"Invalid value `{arg}`: `{self.get_op()}` expects a boolean"
            raise e
        return not arg


@stable_api.stable_api
class Regex(BinaryOperator):
    """
    An operator that does regex matching
    """

    __slots__ = ("regex",)

    def __init__(self, op1: ExpressionStatement, op2: str):
        self.regex = re.compile(op2)
        super().__init__("regex", op1, Literal(self.regex))

    def _bin_op(self, arg1: object, arg2: object) -> object:
        """
        @see Operator#_op
        """
        assert arg2 == self.regex
        if not isinstance(arg1, str):
            raise TypingException(self, f"Regex can only be match with strings. {arg1} is of type {type(arg1)}")

        return self.regex.match(arg1) is not None

    def pretty_print(self) -> str:
        return "/%s/" % self.regex.pattern


class Equals(BinaryOperator):
    """
    The equality operator
    """

    __slots__ = ()
    __op = "=="

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        BinaryOperator.__init__(self, "equality", op1, op2)

    def _bin_op(self, arg1: object, arg2: object) -> object:
        """
        @see Operator#_op
        """
        return arg1 == arg2


class LessThan(BinaryOperator):
    """
    The less than operator
    """

    __slots__ = ()
    __op = "<"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        BinaryOperator.__init__(self, "less than", op1, op2)

    def _bin_op(self, arg1: object, arg2: object) -> object:
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

    __slots__ = ()
    __op = ">"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        BinaryOperator.__init__(self, "greater than", op1, op2)

    def _bin_op(self, arg1: object, arg2: object) -> object:
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

    __slots__ = ()
    __op = "<="

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        BinaryOperator.__init__(self, "less than or equal", op1, op2)

    def _bin_op(self, arg1: object, arg2: object) -> object:
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

    __slots__ = ()
    __op = ">="

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        BinaryOperator.__init__(self, "greater than or equal", op1, op2)

    def _bin_op(self, arg1: object, arg2: object) -> object:
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

    __slots__ = ()
    __op = "!="

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        BinaryOperator.__init__(self, "not equal", op1, op2)

    def _bin_op(self, arg1: object, arg2: object) -> object:
        """
        @see Operator#_op
        """
        return arg1 != arg2


class ArithmeticOperator(BinaryOperator):
    __slots__ = ()

    def _bin_op(self, arg1: object, arg2: object) -> object:
        result: object = self._execute_operator(arg1, arg2)
        if result is NotImplemented:
            raise TypingException(
                self,
                (
                    f"Unsupported operand type(s) for {self.get_name()}:"
                    f" '{type(arg1).__name__}' ({repr(arg1)}) and '{type(arg2).__name__}' ({repr(arg2)})"
                ),
            )
        return result

    def _execute_operator(self, arg1: object, arg2: object) -> object:
        """
        Validate and execute this operator given two operands. When validation fails, may raise its
        own custom TypingException or return the special value NotImplemented, which will result in a generic TypingException.

        This class adds an implementation for numbers. This may be extended by operators that support additional types.
        """
        if isinstance(arg1, (int, float)) and isinstance(arg2, (int, float)):
            return self._arithmetic_op(arg1, arg2)
        return NotImplemented

    @abstractmethod
    def _arithmetic_op(self, arg1: int | float, arg2: int | float) -> int | float:
        """
        The implementation for this ArithmeticOperator when applied to numbers, excluding the type validation.
        Type validation is done in the _execute_operator() method.
        Concrete implementations may widen the type signature.
        """
        raise NotImplementedError()


T = TypeVar("T", int | float, str)


class Plus(ArithmeticOperator):
    __slots__ = ()
    __op = "+"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        ArithmeticOperator.__init__(self, "plus", op1, op2)

    def _execute_operator(self, arg1: object, arg2: object) -> object:
        if isinstance(arg1, str):
            if isinstance(arg2, str):
                return self._arithmetic_op(arg1, arg2)
            # raise more representative error to override generic one from ArithmeticOperator
            raise TypingException(self, f"Can only concatenate str (not '{type(arg2).__name__}' ({repr(arg2)})) to str")
        return super()._execute_operator(arg1, arg2)

    def _arithmetic_op(self, arg1: T, arg2: T) -> T:
        return arg1 + arg2


class Minus(ArithmeticOperator):
    __slots__ = ()
    __op = "-"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        ArithmeticOperator.__init__(self, "minus", op1, op2)

    def _arithmetic_op(self, arg1: int | float, arg2: int | float) -> int | float:
        return arg1 - arg2


class Division(ArithmeticOperator):
    __slots__ = ()
    __op = "/"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        ArithmeticOperator.__init__(self, "division", op1, op2)

    def _arithmetic_op(self, arg1: int | float, arg2: int | float) -> int | float:
        return arg1 / arg2


class Multiplication(ArithmeticOperator):
    __slots__ = ()
    __op = "*"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        ArithmeticOperator.__init__(self, "multiplication", op1, op2)

    def _arithmetic_op(self, arg1: int | float, arg2: int | float) -> int | float:
        return arg1 * arg2


class Modulo(ArithmeticOperator):
    __slots__ = ()
    __op = "%"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        ArithmeticOperator.__init__(self, "modulo", op1, op2)

    def _arithmetic_op(self, arg1: int | float, arg2: int | float) -> int | float:
        return arg1 % arg2


class Exponentiation(ArithmeticOperator):
    __slots__ = ()
    __op = "**"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        ArithmeticOperator.__init__(self, "exponentiation", op1, op2)

    def _arithmetic_op(self, arg1: int | float, arg2: int | float) -> int | float:
        """
        @see Operator#_op
        """
        return arg1**arg2


class And(LazyBooleanOperator):
    """
    The and boolean operator
    """

    __slots__ = ()
    __op = "and"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        LazyBooleanOperator.__init__(self, "and", op1, op2)

    def _is_final(self, result: bool) -> bool:
        return not result


class Or(LazyBooleanOperator):
    """
    The or boolean operator
    """

    __slots__ = ()
    __op = "or"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        LazyBooleanOperator.__init__(self, "or", op1, op2)

    def _is_final(self, result: bool) -> bool:
        return result


class In(BinaryOperator):
    """
    The in operator for iterable types and dicts
    """

    __slots__ = ()
    __op = "in"

    def __init__(self, op1: ExpressionStatement, op2: ExpressionStatement) -> None:
        BinaryOperator.__init__(self, "in", op1, op2)

    def _op(self, args):
        # override parent implementation to not propagate unknowns eagerly
        return self._bin_op(*args)

    def _bin_op(self, arg1: object, arg2: object) -> object:
        """
        @see Operator#_op
        """
        if isinstance(arg1, Unknown):
            return Unknown(self)

        if isinstance(arg2, dict):
            return arg1 in arg2
        elif isinstance(arg2, list):
            any_unknown: bool = False
            for arg in arg2:
                if arg == arg1:
                    return True
                if isinstance(arg, Unknown):
                    any_unknown = True
            # if we did not find arg1 in arg2 but there are unknowns we can't be sure
            return Unknown(self) if any_unknown else False
        else:
            raise TypingException(self, "Operand two of 'in' can only be a list or dict (%s)" % arg2)
