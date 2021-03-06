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

import typing
from itertools import chain

import inmanta.execute.dataflow as dataflow
from inmanta.ast import (
    AttributeException,
    DuplicateException,
    KeyException,
    LocatableString,
    RuntimeException,
    TypeReferenceAnchor,
    TypingException,
)
from inmanta.ast.attribute import RelationAttribute
from inmanta.ast.statements import AssignStatement, ExpressionStatement, Resumer, Statement
from inmanta.execute.dataflow import DataflowGraph
from inmanta.execute.runtime import (
    ExecutionUnit,
    HangUnit,
    Instance,
    QueueScheduler,
    Resolver,
    ResultCollector,
    ResultVariable,
    TempListVariable,
)
from inmanta.execute.util import Unknown

from . import ReferenceStatement

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    from inmanta.ast.statements.generator import WrappedKwargs  # noqa: F401
    from inmanta.ast.variables import Reference  # noqa: F401


class CreateList(ReferenceStatement):
    """
    Create list of values
    """

    def __init__(self, items: typing.List[ExpressionStatement]) -> None:
        ReferenceStatement.__init__(self, items)
        self.items = items

    def requires_emit_gradual(
        self, resolver: Resolver, queue: QueueScheduler, resultcollector: ResultCollector
    ) -> typing.Dict[object, ResultVariable]:

        if resultcollector is None:
            return self.requires(resolver, queue)

        # if we are in gradual mode, transform to a list of assignments instead of assignment of a list
        # to get more accurate gradual execution
        # temp variable is required get all heuristics right

        # ListVariable to hold all the stuff
        temp = TempListVariable(queue)

        # add listener
        temp.listener(resultcollector, self.location)

        # Assignments, wired for gradual
        for expr in self.items:
            ExecutionUnit(queue, resolver, temp, expr.requires_emit_gradual(resolver, queue, temp), expr, self)

        if not self.items:
            # empty: just close
            temp.freeze()

        # pass temp
        return {self: temp}

    def execute(self, requires: typing.Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        """
        Create this list
        """

        # gradual case, everything is in placeholder
        if self in requires:
            return requires[self]

        qlist = []

        for i in range(len(self.items)):
            value = self.items[i].execute(requires, resolver, queue)
            if isinstance(value, list):
                qlist.extend(value)
            else:
                qlist.append(value)

        return qlist

    def execute_direct(self, requires):
        qlist = []

        for i in range(len(self.items)):
            value = self.items[i]
            qlist.append(value.execute_direct(requires))

        return qlist

    def as_constant(self) -> typing.List[object]:
        return [item.as_constant() for item in self.items]

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("CreateList.get_node() placeholder for %s" % self).reference()

    def pretty_print(self) -> str:
        return "[%s]" % ",".join(item.pretty_print() for item in self.items)

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

    def execute_direct(self, requires):
        qlist = {}

        for i in range(len(self.items)):
            key, value = self.items[i]
            qlist[key] = value.execute_direct(requires)

        return qlist

    def execute(self, requires: typing.Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        """
        Create this list
        """
        qlist = {}

        for i in range(len(self.items)):
            key, value = self.items[i]
            qlist[key] = value.execute(requires, resolver, queue)

        return qlist

    def as_constant(self) -> typing.Dict[str, object]:
        return {k: v.as_constant() for k, v in self.items}

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("CreateDict.get_node() placeholder for %s" % self).reference()

    def __repr__(self) -> str:
        return "Dict()"


class SetAttribute(AssignStatement, Resumer):
    """
    Set an attribute of a given instance to a given value
    """

    def __init__(self, instance: "Reference", attribute_name: str, value: ExpressionStatement, list_only: bool = False) -> None:
        AssignStatement.__init__(self, instance, value)
        self.instance = instance
        self.attribute_name = attribute_name
        self.value = value
        self.list_only = list_only

    def _add_to_dataflow_graph(self, graph: typing.Optional[DataflowGraph]) -> None:
        if graph is None:
            return
        node: dataflow.AttributeNodeReference = self.instance.get_dataflow_node(graph).get_attribute(self.attribute_name)
        node.assign(self.value.get_dataflow_node(graph), self, graph)

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        self._add_to_dataflow_graph(resolver.dataflow_graph)
        reqs = self.instance.requires_emit(resolver, queue)
        HangUnit(queue, resolver, reqs, ResultVariable(), self)

    def resume(
        self, requires: typing.Dict[object, object], resolver: Resolver, queue: QueueScheduler, target: ResultVariable
    ) -> None:
        instance = self.instance.execute(requires, resolver, queue)
        if not isinstance(instance, Instance):
            raise TypingException(
                self, "The object at %s is not an Entity but a %s with value %s" % (self.instance, type(instance), instance)
            )
        var = instance.get_attribute(self.attribute_name)
        if self.list_only and not var.is_multi():
            raise TypingException(self, "Can not use += on relations with multiplicity 1")

        if var.is_multi():
            # gradual only for multi
            # to preserve order on lists used in attributes
            # while allowing gradual execution on relations
            reqs = self.value.requires_emit_gradual(resolver, queue, var)
        else:
            reqs = self.value.requires_emit(resolver, queue)

        SetAttributeHelper(queue, resolver, var, reqs, self.value, self, instance, self.attribute_name)

    def pretty_print(self) -> str:
        return "%s.%s = %s" % (self.instance.pretty_print(), self.attribute_name, self.value.pretty_print())

    def __str__(self) -> str:
        return "%s.%s = %s" % (str(self.instance), self.attribute_name, str(self.value))


class SetAttributeHelper(ExecutionUnit):
    def __init__(
        self,
        queue_scheduler: QueueScheduler,
        resolver: Resolver,
        result: ResultVariable,
        requires: typing.Dict[object, ResultVariable],
        expression: ExpressionStatement,
        stmt: Statement,
        instance: Instance,
        attribute_name: str,
    ) -> None:
        ExecutionUnit.__init__(self, queue_scheduler, resolver, result, requires, expression)
        self.stmt = stmt
        self.instance = instance
        self.attribute_name = attribute_name

    def execute(self) -> None:
        try:
            ExecutionUnit._unsafe_execute(self)
        except RuntimeException as e:
            e.set_statement(self.stmt, False)
            raise AttributeException(self.stmt, self.instance, self.attribute_name, e)

    def __str__(self) -> str:
        return str(self.stmt)


class Assign(AssignStatement):
    """
    This class represents the assignment of a value to a variable -> alias

    :param name: The name of the value
    :param value: The value that is to be assigned to the variable

    uses:          value
    provides:      variable
    """

    def __init__(self, name: str, value: ExpressionStatement) -> None:
        AssignStatement.__init__(self, None, value)
        self.name = name
        self.value = value

    def _add_to_dataflow_graph(self, graph: typing.Optional[DataflowGraph]) -> None:
        if graph is None:
            return
        node: dataflow.AssignableNodeReference = graph.resolver.get_dataflow_node(self.name)
        node.assign(self.value.get_dataflow_node(graph), self, graph)

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        self._add_to_dataflow_graph(resolver.dataflow_graph)
        target = resolver.lookup(self.name)
        assert isinstance(target, ResultVariable)
        reqs = self.value.requires_emit(resolver, queue)
        ExecutionUnit(queue, resolver, target, reqs, self.value, owner=self)

    def declared_variables(self) -> typing.Iterator[str]:
        yield self.name

    def pretty_print(self) -> str:
        return f"{self.name} = {self.value.pretty_print()}"

    def __repr__(self) -> str:
        return "Assign(%s, %s)" % (self.name, self.value)

    def __str__(self) -> str:
        return f"{self.name} = {self.value}"


class MapLookup(ReferenceStatement):
    """
    Lookup a value in a dict
    """

    def __init__(self, themap: ExpressionStatement, key: ExpressionStatement):
        super(MapLookup, self).__init__([themap, key])
        self.themap = themap
        self.key = key
        self.location = themap.get_location().merge(key.location)

    def execute(self, requires: typing.Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        mapv = self.themap.execute(requires, resolver, queue)
        if not isinstance(mapv, dict):
            raise TypingException(self, "dict lookup is only possible on dicts, %s is not an object" % mapv)

        keyv = self.key.execute(requires, resolver, queue)
        if not isinstance(keyv, str):
            raise TypingException(self, "dict keys must be string, %s is not a string" % keyv)

        if keyv not in mapv:
            raise KeyException(self, "key %s not found in dict, options are [%s]" % (keyv, ",".join(mapv.keys())))

        return mapv[keyv]

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("MapLookup.get_node() placeholder for %s" % self).reference()

    def __repr__(self) -> str:
        return "%s[%s]" % (repr(self.themap), repr(self.key))


class IndexLookup(ReferenceStatement, Resumer):
    """
    Lookup a value in a dictionary
    """

    def __init__(
        self,
        index_type: LocatableString,
        query: typing.List[typing.Tuple[LocatableString, ExpressionStatement]],
        wrapped_query: typing.List["WrappedKwargs"],
    ) -> None:
        ReferenceStatement.__init__(self, list(chain((v for (_, v) in query), wrapped_query)))
        self.index_type = index_type
        self.anchors.append(TypeReferenceAnchor(index_type.namespace, index_type))
        self.query = [(str(n), e) for n, e in query]
        self.wrapped_query: typing.List["WrappedKwargs"] = wrapped_query

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

    def resume(
        self, requires: typing.Dict[object, object], resolver: Resolver, queue: QueueScheduler, target: ResultVariable
    ) -> None:
        self.type.lookup_index(
            list(
                chain(
                    ((k, v.execute(requires, resolver, queue)) for (k, v) in self.query),
                    ((k, v) for kwargs in self.wrapped_query for (k, v) in kwargs.execute(requires, resolver, queue)),
                )
            ),
            self,
            target,
        )

    def execute(self, requires: typing.Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        return requires[self]

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("IndexLookup.get_node() placeholder for %s" % self).reference()

    def __repr__(self) -> str:
        """
        The representation of this statement
        """
        return "%s[%s]" % (self.index_type, ",".join([repr(x) for x in chain([self.query], self.wrapped_query)]))


class ShortIndexLookup(IndexLookup):
    """lookup of the form
    vm = ip::Host(...)
    file = std::File(host=vm, path="/etc/motd", ...)

    vm.files[path="/etc/motd"]
    """

    def __init__(
        self,
        rootobject: ExpressionStatement,
        relation: LocatableString,
        query: typing.List[typing.Tuple[LocatableString, ExpressionStatement]],
        wrapped_query: typing.List["WrappedKwargs"],
    ):
        ReferenceStatement.__init__(self, list(chain((v for (_, v) in query), [rootobject], wrapped_query)))
        self.rootobject = rootobject
        self.relation = str(relation)
        self.querypart: typing.List[typing.Tuple[str, ExpressionStatement]] = [(str(n), e) for n, e in query]
        self.wrapped_querypart: typing.List["WrappedKwargs"] = wrapped_query

    def normalize(self) -> None:
        ReferenceStatement.normalize(self)
        # currently there is no way to get the type of an expression prior to evaluation
        self.type = None

    def resume(
        self, requires: typing.Dict[object, object], resolver: Resolver, queue: QueueScheduler, target: ResultVariable
    ) -> None:
        root_object = self.rootobject.execute(requires, resolver, queue)

        if not isinstance(root_object, Instance):
            raise TypingException(self, "short index lookup is only possible one objects, %s is not an object" % root_object)

        from_entity = root_object.get_type()

        relation = from_entity.get_attribute(self.relation)
        if not isinstance(relation, RelationAttribute):
            raise TypingException(self, "short index lookup is only possible on relations, %s is an attribute" % relation)

        if relation.end is None:
            raise TypingException(
                self, "short index lookup is only possible on bi-drectional relations, %s is unidirectional" % relation
            )

        self.type = relation.type

        self.type.lookup_index(
            list(
                chain(
                    [(relation.end.name, root_object)],
                    ((k, v.execute(requires, resolver, queue)) for (k, v) in self.querypart),
                    ((k, v) for kwargs in self.wrapped_querypart for (k, v) in kwargs.execute(requires, resolver, queue)),
                )
            ),
            self,
            target,
        )

    def __repr__(self) -> str:
        """
        The representation of this statement
        """
        return "%s.%s[%s]" % (
            self.rootobject,
            self.relation,
            ",".join(repr(part) for part in chain([self.querypart], self.wrapped_querypart)),
        )


class StringFormat(ReferenceStatement):
    """
    Create a new string by doing a string interpolation
    """

    def __init__(self, format_string: str, variables: typing.List[typing.Tuple["Reference", str]]) -> None:
        ReferenceStatement.__init__(self, [k for (k, _) in variables])
        self._format_string = format_string
        self._variables = variables

    def execute(self, requires: typing.Dict[object, object], resolver: Resolver, queue: QueueScheduler) -> object:
        result_string = self._format_string
        for _var, str_id in self._variables:
            value = _var.execute(requires, resolver, queue)
            if isinstance(value, Unknown):
                return Unknown(self)
            if isinstance(value, float) and (value - int(value)) == 0:
                value = int(value)

            result_string = result_string.replace(str_id, str(value))

        return result_string

    def get_dataflow_node(self, graph: DataflowGraph) -> dataflow.NodeReference:
        return dataflow.NodeStub("StringFormat.get_node() placeholder for %s" % self).reference()

    def __repr__(self) -> str:
        return "Format(%s)" % self._format_string
