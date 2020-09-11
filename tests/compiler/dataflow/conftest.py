"""
    Copyright 2020 Inmanta

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

from functools import reduce
from itertools import chain
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple, Type

import pytest

import inmanta.ast.type as inmanta_type
import inmanta.compiler as compiler
from inmanta.ast import Namespace, RuntimeException
from inmanta.ast.blocks import BasicBlock
from inmanta.ast.entity import Entity
from inmanta.ast.statements import Statement
from inmanta.config import Config
from inmanta.execute.dataflow import (
    AssignableNode,
    AssignableNodeReference,
    AttributeNode,
    AttributeNodeReference,
    DataflowGraph,
    InstanceNode,
    NodeReference,
    ValueNode,
    VariableNodeReference,
)
from inmanta.execute.runtime import ExecutionContext, Resolver


def create_instance(
    graph: Optional[DataflowGraph] = None, entity: Optional[Entity] = None, statement: Optional[Statement] = None
) -> InstanceNode:
    responsible: Statement = statement if statement is not None else Statement()
    instance: InstanceNode = InstanceNode([])
    if graph is None:
        return instance
    return graph.own_instance_node_for_responsible(
        entity if entity is not None else Entity("DummyEntity", Namespace("dummy_namespace")),
        responsible,
        lambda: instance,
    )


@pytest.fixture(scope="function")
def graph() -> Iterator[DataflowGraph]:
    namespace: Namespace = Namespace("dummy_namespace")
    resolver: Resolver = Resolver(namespace, enable_dataflow_graph=True)
    block: BasicBlock = BasicBlock(namespace, [])
    xc: ExecutionContext = ExecutionContext(block, resolver)
    block.namespace.scope = xc

    yield DataflowGraph(resolver)


def get_dataflow_node(graph: DataflowGraph, name: str) -> AssignableNodeReference:
    """
    Returns a dataflow node for a graph by name. Name is allowed to have '.' for attribute nodes.
    """
    parts: List[str] = name.split(".")
    return reduce(lambda acc, part: AttributeNodeReference(acc, part), parts[1:], graph.resolver.get_dataflow_node(parts[0]))


class DataflowTestHelper:
    def __init__(self, snippetcompiler) -> None:
        self.snippetcompiler = snippetcompiler
        self._types: Dict[str, inmanta_type.Type] = {}
        self._namespace: Optional[Namespace] = None
        self._instances: Dict[str, InstanceNode] = {}
        self._tokens: List[str] = []

    def get_types(self) -> Dict[str, inmanta_type.Type]:
        return self._types

    def get_namespace(self) -> Namespace:
        assert self._namespace is not None, "Call compile before trying to access namespace"
        return self._namespace

    def get_graph(self) -> DataflowGraph:
        graph: Optional[DataflowGraph] = self.get_namespace().get_scope().dataflow_graph
        assert graph is not None
        return graph

    def compile(self, snippet: str, expected_error_type: Optional[Type[RuntimeException]] = None) -> None:
        def compile():
            self.snippetcompiler.setup_for_snippet(snippet)
            Config.set("compiler", "datatrace_enable", "true")
            (self._types, root_ns) = compiler.do_compile()
            self._namespace = root_ns.get_child("__config__")

        if expected_error_type is None:
            compile()
        else:
            try:
                compile()
                assert False, "Expected error: %s" % expected_error_type
            except expected_error_type as e:
                assert e.root_ns is not None
                root_ns = e.root_ns
                assert root_ns is not None
                self._namespace = root_ns.get_child("__config__")
            except Exception as e:
                if isinstance(e, AssertionError):
                    raise e
                assert False, "Expected %s, got %s" % (expected_error_type, e)

    def _consume_token_instance(self) -> Optional[str]:
        if self._tokens[0] != "<instance>":
            return None
        self._tokens.pop(0)
        instance_id: str = self._tokens.pop(0)
        if not instance_id.isalnum():
            raise Exception("Invalid syntax: expected instance identifier, got `%s`" % instance_id)
        return instance_id

    def _consume_token_attribute(self) -> Optional[str]:
        if len(self._tokens) == 0 or self._tokens[0] != ".":
            return None
        self._tokens.pop(0)
        attribute: str = self._tokens.pop(0)
        if not attribute.isalnum():
            raise Exception("Invalid syntax: expected attribute name, got `%s`" % attribute)
        return attribute

    def _consume_token_lhs(self) -> Callable[[List[NodeReference], Optional[str]], None]:
        node: AssignableNode
        instance_id: Optional[str] = self._consume_token_instance()
        if instance_id is not None:
            if instance_id not in self._instances:
                raise Exception("Parse error: bind instance_id `%s` to a n instance first by using it as a rhs." % instance_id)
            instance: InstanceNode = self._instances[instance_id]
            attribute_name: Optional[str] = self._consume_token_attribute()
            if attribute_name is None:
                raise Exception("Parse error: expected `. attribute_name`, got %s." % attribute_name)
            attribute: Optional[AttributeNode] = instance.get_attribute(attribute_name)
            assert attribute is not None
            node = attribute
        else:
            token: str = self._tokens.pop(0)
            if not token.isalnum():
                raise Exception("Invalid syntax: expected `variable_name` or `<instance> instance_id`, got `%s`" % token)
            node_ref: AssignableNodeReference = get_dataflow_node(self.get_graph(), token)
            assert isinstance(node_ref, VariableNodeReference)
            node = node_ref.node
        if self._consume_token_attribute() is not None:
            raise Exception("Syntax error: this simple language only supports attributes directly on instances in the lhs.")

        def continuation(rhs: List[NodeReference], instance_bind: Optional[str] = None) -> None:
            if instance_bind is not None:
                assert (
                    len(node.instance_assignments) == 1
                ), "This simple language only allows instance binding for a single instance in the rhs."
                instance_node: InstanceNode = node.instance_assignments[0].rhs.top_node()
                self._instances[instance_bind] = instance_node
                rhs.append(instance_node.reference())
            # test element equality: NodeReference does not define sort or hash so this is the only way
            actual_rhs: List[NodeReference] = [assignment.rhs for assignment in node.assignments()]
            for rhs_elem in rhs:
                assert rhs_elem in actual_rhs
                actual_rhs.remove(rhs_elem)
            assert len(actual_rhs) == 0

        return continuation

    def _consume_token_edge(self) -> None:
        token: str = self._tokens.pop(0)
        if token != "->":
            raise Exception("Invalid syntax: expected `->`, got `%s`" % token)

    def _consume_token_rhs_element(self) -> Tuple[Optional[NodeReference], Optional[str]]:
        instance_id: Optional[str] = self._consume_token_instance()
        if instance_id is not None:
            if self._consume_token_attribute() is not None:
                raise Exception("Syntax error: this simple language only supports attributes directly on instances in the lhs.")
            if instance_id not in self._instances:
                return (None, instance_id)
            return (self._instances[instance_id].reference(), None)
        else:
            token: str = self._tokens.pop(0)
            if not token.isalnum():
                raise Exception(
                    "Invalid syntax: expected `variable_name [. attr [...]]` or `<instance> instance_id`, got `%s`" % token
                )
            try:
                return (ValueNode(int(token)).reference(), None)
            except ValueError:
                node_ref: AssignableNodeReference = get_dataflow_node(self.get_graph(), token)
                assert isinstance(node_ref, VariableNodeReference)
                attribute_name: Optional[str] = self._consume_token_attribute()
                while attribute_name is not None:
                    node_ref = AttributeNodeReference(node_ref, attribute_name)
                    attribute_name = self._consume_token_attribute()
                return (node_ref, None)

    def _consume_token_rhs(self, continuation: Callable[[List[NodeReference], Optional[str]], None]) -> None:
        nodes: List[NodeReference] = []
        instance_bind: Optional[str] = None

        def consume_node(instance_bind: Optional[str] = None) -> Optional[str]:
            (node, instance_id) = self._consume_token_rhs_element()
            if instance_id is not None:
                if instance_bind is not None:
                    raise Exception("Parse error: this simple language only allows a single instance binding in the rhs.")
                instance_bind = instance_id
            if node is not None:
                nodes.append(node)
            return instance_bind

        if self._tokens[0] == "[":
            self._tokens.pop(0)
            while self._tokens[0] != "]":
                instance_bind = consume_node(instance_bind)
            self._tokens.pop(0)
        else:
            instance_bind = consume_node(instance_bind)
        continuation(nodes, instance_bind)

    def verify_graphstring(self, graphstring: str) -> None:
        """
        Verifies that the graphstring corresponds with the graph. Syntax for the graphstring:
            graph_string: empty
                | graphstring_rule graph_string
                ;
            graphstring_rule : lhs `->` rhs ;
            lhs : var_name
                | instance_ref
                | instance_ref `.` attr_name
                ;
            rhs : rhs_element
                | `[` rhs_list `]`
                ;
            rhs_list : empty
                | rhs_element rhs_list
                ;
            rhs_element : var_name
                | int
                | var_attr
                | `<instance>` instance_id
                ;
            var_attr : var_name `.` attr_name`
                | var_name `.` var_attr
                ;
        Where instance_id is a string that is bound when it occurs in the right. Once bound the same id can be used to refer
        to it in later rules.
        Spaces are required between all subsequent tokens.
        """
        self._tokens = graphstring.split()
        while len(self._tokens) > 0:
            continuation: Callable[[List[NodeReference], Optional[str]], None] = self._consume_token_lhs()
            self._consume_token_edge()
            self._consume_token_rhs(continuation)

    def verify_leaves(self, leaves: Dict[str, Set[str]]) -> None:
        """
        Verifies that the leaves correspond with the graph's leaves.
        :param leaves: dict with variable names as keys and a set of leaves for each variable as values.
            The variable and leaves are allowed to be attributes.
        """
        for key, value in leaves.items():
            lhs: AssignableNodeReference = get_dataflow_node(self.get_graph(), key)
            rhs: Set[AssignableNode] = set(chain.from_iterable(get_dataflow_node(self.get_graph(), v).nodes() for v in value))
            assert set(lhs.leaf_nodes()) == rhs


@pytest.fixture(scope="function")
def dataflow_test_helper(snippetcompiler):
    return DataflowTestHelper(snippetcompiler)
