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

from abc import ABCMeta, abstractmethod
import re

from impera.ast.variables import Variable, Reference, AttributeVariable
from impera.ast.statements import CallStatement
from impera.ast.statements.call import FunctionCall
from impera.execute.proxy import DynamicProxy


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
        return expression.eval(kwargs, args)

    return function


class InvalidNumberOfArgumentsException(Exception):
    """
        This exception is raised if an invalid amount of arguments is passed
        to an operator.
    """
    def __init__(self, msg):
        Exception.__init__(self, msg)


class UnboundVariableException(Exception):
    """
        This execption is raised if an expression is evaluated when not all
        variables have been resolved
    """
    def __init__(self, msg):
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


class Operator(CallStatement, metaclass=OpMetaClass):
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

    def __init__(self, name, num):
        CallStatement.__init__(self)

        self.__number_arguments = num
        self.__name = name
        # pylint: disable-msg=W0612
        self._arguments = [None for _x in range(self.__number_arguments)]
        # pylint: enable-msg=W0612

    def _add_operand(self, index, value):
        """
            Add an operand to this operator
        """
        if (index < self.__number_arguments):
            self._arguments[index] = value
        else:
            raise InvalidNumberOfArgumentsException(
                "The %s operator requires %d arguments" %
                (self.__name, self.__number_arguments))

    def types(self):
        """
            @see DynamicStatement#types
        """
        types = []
        for arg in self._arguments:
            if hasattr(arg, "types"):
                # it is an operator
                types.extend(arg.types())

        return types

    def references(self):
        """
            @see DynamicStatement#references
        """
        refs = []
        for i in range(len(self._arguments)):
            refs.append(("arg %d" % i, self._arguments[i]))

        return refs

    def actions(self, state):
        """
            What does this operation do
        """
        result = state.get_result_reference()
        actions = [("set", result)]

        for i in range(len(self._arguments)):
            value = state.get_ref("arg %d" % i)
            actions.append(("get", value))

        return actions

    def evaluate(self, state, _local_scope):
        """
            Evaluate this operator
        """
        arguments = []
        for i in range(len(self._arguments)):
            value = state.get_ref("arg %d" % i)
            arguments.append((value.value, value.value.__class__))

        return self._op(arguments)

    def get_variables(self):
        """
            Get the variables that need a value. If one of the operand is an operator itself, its variables will be merged.
        """
        variables = set()
        for arg in self._arguments:
            if hasattr(arg, "eval"):
                # it is an operator
                variables = variables.union(arg.get_variables())
            elif hasattr(arg, "arguments"):
                for fn_arg in arg.arguments:
                    if isinstance(fn_arg, Reference):
                        variables.add(fn_arg)
                    elif isinstance(fn_arg, AttributeVariable):
                        variables.add(fn_arg)

            elif isinstance(arg, Reference):
                variables.add(arg)
            elif isinstance(arg, AttributeVariable):
                variables.add(arg)

        return variables

    def eval(self, variables=None, var_list=None, state=None):
        """
            The call method implements the operator and returns the result of the operator

            @param variables: A dictionary that contains the values for the unresolved variables.
            @param var_list: An optional positional list of variables
        """
        positional = False
        if variables is None:
            variables = {}

        if var_list is not None:
            positional_list = list(var_list)
            positional = True

        if len(self._arguments) != self.__number_arguments:
            raise InvalidNumberOfArgumentsException(
                "The %s operator requires %d arguments" %
                (self.__name, self.__number_arguments))

        # unbox variables if required
        arg_list = []

        for arg in self._arguments:
            if hasattr(arg, "eval"):  # we have an operator
                value = arg.eval(variables, var_list, state)
                arg_list.append((value, value.__class__))
            else:
                if isinstance(arg, Reference) or isinstance(arg, AttributeVariable):
                    if positional and len(positional_list) > 0:
                        arg = positional_list.pop(0)
                    else:
                        if not hasattr(arg, "name") or arg.name not in variables:
                            raise UnboundVariableException("Unbound variable")
                        else:
                            arg = variables[arg.name]

                if hasattr(arg, "value"):
                    if hasattr(arg.type, "cast"):
                        arg_list.append((arg.type.cast(arg.value), arg.type))
                    else:
                        arg_list.append((arg.value, arg.type))

                elif isinstance(arg, FunctionCall):
                    if state is None:
                        raise Exception("The current state is required to evaluate %s in %s" % (arg, self))

                    fnc_arglist = []
                    for fn_arg in arg.arguments:
                        if str(fn_arg) in variables:
                            fnc_arglist.append(DynamicProxy.return_value(variables[str(fn_arg)].value))
                        elif isinstance(fn_arg, str):
                            fnc_arglist.append(fn_arg)
                        else:
                            raise UnboundVariableException("Unable to find %s for %s in expression %s" % (fn_arg, arg, self))

                    # get the object to call the function on
                    function = state.get_type("function_%d" % id(arg))
                    function.check_args(fnc_arglist)
                    result = function(*fnc_arglist)

                    arg_list.append((result, result.__class__))

                else:
                    arg_list.append((arg, arg.__class__))

        return self._op(arg_list)

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


class BinaryOperator(Operator):
    """
        This class represents a binary operator.
    """
    def __init__(self, name):
        Operator.__init__(self, name, 2)

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


class UnaryOperator(Operator):
    """
        This class represents a unary operator
    """
    def __init__(self, name):
        Operator.__init__(self, name, 1)

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


class Not(UnaryOperator):
    """
        The negation operator
    """
    __op = "not"

    def __init__(self, arg):
        UnaryOperator.__init__(self, "negation")
        self._add_operand(0, arg)

    def _un_op(self, arg):
        """
            Return the inverse of the argument

            @see Operator#_op
        """
        if arg[1] != bool:
            raise Exception("Unable to invert %s, a boolean argument is required." % arg[0])

        return (not arg[0])


class Regex(BinaryOperator):
    """
        An operator that does regex matching
    """
    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "regex")
        self._add_operand(0, op1)

        regex = re.compile(op2)
        self._add_operand(1, Variable(regex))

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        if not isinstance(arg1[0], str):
            raise Exception("Regex can only be match with strings. %s is of type %s" % arg1)

        return arg2[0].match(arg1[0]) is not None

    def __repr__(self):
        """
            Return a representation of the op
        """
        return "%s(%s, %s)" % (self.__class__.__name__, self._arguments[0],
                               self._arguments[1].value)


class Equals(BinaryOperator):
    """
        The equality operator
    """
    __op = "=="

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "equality")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        return arg1[0] == arg2[0]


class LessThan(BinaryOperator):
    """
        The less than operator
    """
    __op = "<"

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "less than")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        if not isinstance(arg1[0], (int, float)) or not isinstance(arg2[0], (int, float)):
            raise Exception("Can only compare numbers.")
        return arg1[0] < arg2[0]


class GreaterThan(BinaryOperator):
    """
        The more than operator
    """
    __op = ">"

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "greater than")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        if not isinstance(arg1[0], (int, float)) or not isinstance(arg2[0], (int, float)):
            raise Exception("Can only compare numbers.")
        return arg1[0] > arg2[0]


class LessThanOrEqual(BinaryOperator):
    """
        The less than or equal operator
    """
    __op = "<="

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "less than or equal")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        if not isinstance(arg1[0], (int, float)) or not isinstance(arg2[0], (int, float)):
            raise Exception("Can only compare numbers.")
        return arg1[0] <= arg2[0]


class GreaterThanOrEqual(BinaryOperator):
    """
        The more than or equal operator
    """
    __op = ">="

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "greater than or equal")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        if not isinstance(arg1[0], (int, float)) or not isinstance(arg2[0], (int, float)):
            raise Exception("Can only compare numbers.")
        return arg1[0] >= arg2[0]


class NotEqual(BinaryOperator):
    """
        The not equal operator
    """
    __op = "!="

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "not equal")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        return arg1[0] != arg2[0]


class And(BinaryOperator):
    """
        The and boolean operator
    """
    __op = "and"

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "and")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        if not isinstance(arg1[0], bool) or not isinstance(arg2[0], bool):
            raise Exception("Unable to 'and' two types that are not bool.")

        return arg1[0] and arg2[0]


class Or(BinaryOperator):
    """
        The or boolean operator
    """
    __op = "or"

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "or")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        if not isinstance(arg1[0], bool) or not isinstance(arg2[0], bool):
            raise Exception("Unable to 'or' two types that are not bool.")

        return arg1[0] or arg2[0]


class In(BinaryOperator):
    """
        The in operator for iterable types
    """
    __op = "in"

    def __init__(self, op1, op2):
        BinaryOperator.__init__(self, "in")
        self._add_operand(0, op1)
        self._add_operand(1, op2)

    def _bin_op(self, arg1, arg2):
        """
            @see Operator#_op
        """
        if not (isinstance(arg2[0], list) or (hasattr(arg2[0], "type") and arg2[0].type() == list)):
            raise Exception("Operand two of 'in' can only be a list (%s)" % arg2[0])

        for arg in arg2[0]:
            if arg == arg1[0]:
                return True

        return False
