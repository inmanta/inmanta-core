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

# pylint: disable-msg=W0613

from . import ReferenceStatement
from inmanta.ast.type import List, Dict
from inmanta.ast.statements import AssignStatement, ExpressionStatement
from inmanta.execute.runtime import ExecutionUnit, ResultVariable, HangUnit, Instance, Resolver, QueueScheduler
from inmanta.execute.util import Unknown
from inmanta.ast import RuntimeException, AttributeException, DuplicateException
import typing

if typing.TYPE_CHECKING:
    from inmanta.ast.variables import Reference  # noqa: F401


class CreateList(ReferenceStatement):
    """
        Create list of values
    """

    def __init__(self, items: typing.List[ExpressionStatement]) -> None:
        ReferenceStatement.__init__(self, items)
        self.items = items

    def execute(self,
                requires: typing.Dict[object, ResultVariable],
                resolver: Resolver,
                queue: QueueScheduler) -> object:
        """
            Create this list
        """
        qlist = List()

        for i in range(len(self.items)):
            value = self.items[i]
            qlist.append(value.execute(requires, resolver, queue))

        return qlist

    def __repr__(self) -> str:
        return "List()"


class CreateDict(ReferenceStatement):

    def __init__(self, items: typing.List[typing.Tuple[str, ReferenceStatement]]) -> None:
        ReferenceStatement.__init__(self, [x[1] for x in items])
        self.items = items
        seen = {}  # type: typing.Dict[str,ReferenceStatement]
        for x, v in items:
            if x in seen:
                raise DuplicateException(v, seen[x], "duplicate key in dict %s" % x)
            seen[x] = v

    def execute(self, requires: typing.Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        """
            Create this list
        """
        qlist = Dict()

        for i in range(len(self.items)):
            key, value = self.items[i]
            qlist[key] = value.execute(requires, resolver, queue)

        return qlist

    def __repr__(self) -> str:
        return "Dict()"


class SetAttribute(AssignStatement):
    """
        Set an attribute of a given instance to a given value
    """

    def __init__(self, instance: "Reference", attribute_name: str, value: ExpressionStatement) -> None:
        AssignStatement.__init__(self, instance, value)
        self.instance = instance
        self.attribute_name = attribute_name
        self.value = value

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        reqs = self.instance.requires_emit(resolver, queue)
        HangUnit(queue, resolver, reqs, None, self)

    def resume(self,
               requires: typing.Dict[object, ResultVariable],
               resolver: Resolver,
               queue: QueueScheduler,
               target: ResultVariable) -> None:
        instance = self.instance.execute(requires, resolver, queue)
        var = instance.get_attribute(self.attribute_name)
        reqs = self.value.requires_emit(resolver, queue)
        SetAttributeHelper(queue, resolver, var, reqs, self.value, self, instance)

    def __str__(self) -> str:
        return "%s.%s = %s" % (str(self.instance), self.attribute_name, str(self.value))


class SetAttributeHelper(ExecutionUnit):

    def __init__(self,
                 queue_scheduler: QueueScheduler,
                 resolver: Resolver,
                 result: ResultVariable,
                 requires: typing.Dict[object, ResultVariable],
                 expression: ExpressionStatement,
                 stmt: SetAttribute,
                 instance: Instance) -> None:
        ExecutionUnit.__init__(self, queue_scheduler, resolver, result, requires, expression)
        self.stmt = stmt
        self.instance = instance

    def execute(self) -> None:
        try:
            ExecutionUnit.execute(self)
        except RuntimeException as e:
            e.set_statement(self.stmt)
            raise AttributeException(self.stmt, self.instance, self.stmt.attribute_name, e)

    def __str__(self) -> str:
        return str(self.stmt)


class Assign(AssignStatement):
    """
        This class represents the assignment of a value to a variable -> alias

        @param name: The name of the value
        @param value: The value that is to be assigned to the variable

        uses:          value
        provides:      variable
    """

    def __init__(self, name: str, value: ExpressionStatement) -> None:
        AssignStatement.__init__(self, None, value)
        self.name = name
        self.value = value

    def requires(self) -> typing.List[str]:
        return self.value.requires()

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        target = resolver.lookup(self.name)
        reqs = self.value.requires_emit(resolver, queue)
        ExecutionUnit(queue, resolver, target, reqs, self.value)

    def __repr__(self) -> str:
        return "Assign(%s, %s)" % (self.name, self.value)


class IndexLookup(ReferenceStatement):
    """
        Lookup a value in a dictionary
    """

    def __init__(self, index_type: str, query: typing.List[typing.Tuple[str, ExpressionStatement]]) -> None:
        ReferenceStatement.__init__(self, [v for (k, v) in query])
        self.index_type = index_type
        self.query = query

    def normalize(self) -> None:
        ReferenceStatement.normalize(self)
        self.type = self.namespace.get_type(self.index_type)

    def requires_emit(self, resolver: Resolver, queue: QueueScheduler) -> typing.Dict[object, ResultVariable]:
        sub = ReferenceStatement.requires_emit(self, resolver, queue)
        temp = ResultVariable()
        temp.set_type(self.type)
        temp.set_provider(self)
        HangUnit(queue, resolver, sub, temp, self)
        return {self: temp}

    def resume(self,
               requires: typing.Dict[object, ResultVariable],
               resolver: Resolver,
               queue: QueueScheduler,
               target: ResultVariable) -> None:
        self.type.lookup_index([(k, v.execute(requires, resolver, queue)) for (k, v) in self.query], self, target)

    def execute(self, requires: typing.Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        return requires[self]

    def __repr__(self) -> str:
        """
            The representation of this statement
        """
        return "%s[%s]" % (self.index_type, self.query)


class StringFormat(ReferenceStatement):
    """
        Create a new string by doing a string interpolation
    """

    def __init__(self, format_string: str, variables: typing.List[typing.Tuple["Reference", str]]) -> None:
        ReferenceStatement.__init__(self, [k for (k, _) in variables])
        self._format_string = format_string
        self._variables = variables

    def execute(self, requires: typing.Dict[object, ResultVariable], resolver: Resolver, queue: QueueScheduler) -> object:
        result_string = self._format_string
        for _var, str_id in self._variables:
            value = _var.execute(requires, resolver, queue)
            if isinstance(value, Unknown):
                return Unknown(self)
            if isinstance(value, float) and (value - int(value)) == 0:
                value = int(value)

            result_string = result_string.replace(str_id, str(value))

        return result_string

    def __repr__(self) -> str:
        return "Format(%s)" % self._format_string
