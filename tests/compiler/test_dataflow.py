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

from itertools import chain
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple, Type, cast, Iterable

import pytest

import inmanta.compiler as compiler
from inmanta.ast import DoubleSetException, Namespace, NotFoundException, RuntimeException
from inmanta.ast.entity import Entity
from inmanta.ast.statements import Literal, Statement
from inmanta.ast.statements.assign import Assign, SetAttribute
from inmanta.ast.variables import Reference
from inmanta.execute.dataflow import (
    AssignableNode,
    AssignableNodeReference,
    Assignment,
    AttributeNode,
    AttributeNodeReference,
    DataflowGraph,
    DirectNodeReference,
    InstanceNode,
    Node,
    NodeReference,
    ValueNode,
    ValueNodeReference,
    VariableNodeReference,
)
from inmanta.execute.runtime import Resolver


@pytest.fixture(scope="function")
def graph() -> Iterator[DataflowGraph]:
    dummy_resolver: Resolver = Resolver(Namespace("dummy_namespace"))
    yield DataflowGraph(dummy_resolver)


def instance_node(attributes: Optional[List[str]] = None) -> InstanceNode:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    return InstanceNode(attributes if attributes is not None else [], entity, Statement(), graph)


def register_instance(
    graph: DataflowGraph, entity: Optional[Entity] = None, statement: Optional[Statement] = None
) -> InstanceNode:
    responsible: Statement = statement if statement is not None else Statement()
    return graph.own_instance_node_for_responsible(
        responsible,
        lambda: InstanceNode(
            [], entity if entity is not None else Entity("DummyEntity", Namespace("dummy_namespace")), responsible, graph
        ),
    )


def test_dataflow_hierarchy(graph: DataflowGraph) -> None:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    dummy_resolver: Resolver = Resolver(Namespace("dummy_namespace"))
    child: DataflowGraph = DataflowGraph(dummy_resolver, graph)
    assert child.instances() == {}
    assert graph.instances() == {}
    statement1: Statement = Statement()
    statement2: Statement = Statement()

    node1: InstanceNode = register_instance(child, entity, statement1)
    child.register_bidirectional_attribute(entity, "this", "other")

    assert child.instances() == graph.instances()
    assert entity in child.instances()
    assert child.instances()[entity].instances == [node1.reference()]
    assert child.instances()[entity].bidirectional_attributes == {"this": "other"}

    node2: InstanceNode = register_instance(child, entity, statement1)
    node3: InstanceNode = register_instance(child, entity, statement2)
    assert node1 == node2
    assert node2 != node3

    assert child.get_named_node("x") != graph.get_named_node("x")


def test_dataflow_simple_lookup(graph: DataflowGraph) -> None:
    x1: AssignableNodeReference = graph.get_named_node("x")
    x2: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    assert isinstance(x1, VariableNodeReference)
    assert x1.node.name == "x"
    assert x1 == x2
    assert isinstance(y, VariableNodeReference)
    assert y.node.name == "y"


def test_dataflow_attribute_lookup(graph: DataflowGraph) -> None:
    x_a_n: AssignableNodeReference = graph.get_named_node("x.a.n")
    x: AssignableNodeReference = graph.get_named_node("x")
    assert x_a_n == AttributeNodeReference(AttributeNodeReference(x, "a"), "n")


def test_dataflow_reference_nodes(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    x_nodes: List[AssignableNode] = list(x.nodes())
    assert len(x_nodes) == 1
    assert isinstance(x, DirectNodeReference)
    assert x_nodes[0] == x.node


def test_dataflow_attribute_reference_nodes(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    x.assign(y, Statement(), graph)
    y.assign(instance_node(["n"]).reference(), Statement(), graph)

    assert isinstance(y, VariableNodeReference)
    assert len(y.node.instance_assignments) == 1

    y_n: AssignableNodeReference = graph.get_named_node("y.n")
    y_n.assign(ValueNode(42).reference(), Statement(), graph)

    x_n: AssignableNodeReference = graph.get_named_node("x.n")
    x_n_nodes: List[AssignableNode] = list(x_n.nodes())
    assert len(x_n_nodes) == 1
    assert x_n_nodes[0] == y.node.instance_assignments[0].rhs.node().get_attribute("n")


def test_dataflow_simple_leaf(graph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    leaves: List[AssignableNode] = list(x.leaves())
    assert isinstance(x, DirectNodeReference)
    assert leaves == [x.node]


def test_dataflow_variable_chain_leaf(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(z, DirectNodeReference)
    assert leaves == {z.node}


@pytest.mark.parametrize("value_node", [ValueNode(42), instance_node()])
def test_dataflow_variable_tree_leaves(graph: DataflowGraph, value_node: Node) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    y.assign(value_node.reference(), Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    assert leaves == {y.node, z.node}


def test_dataflow_variable_loop_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(x, DirectNodeReference)
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    assert leaves == {x.node, y.node, z.node}


def test_dataflow_variable_loop_with_external_assignment_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    u: AssignableNodeReference = graph.get_named_node("u")
    y.assign(u, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(u, DirectNodeReference)
    assert leaves == {u.node}


def test_dataflow_variable_loop_with_value_assignment_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    y.assign(ValueNode(42).reference(), Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(x, DirectNodeReference)
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    # TODO: is this the desired result? Shouldn't only y.node be in the set?
    assert leaves == {x.node, y.node, z.node}


def test_dataflow_assignment_node_simple(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")

    x.assign(y, Statement(), graph)

    assert isinstance(x, VariableNodeReference)
    assert x.assignment_node() == x.node


@pytest.mark.parametrize("instantiate", [True, False])
def test_dataflow_assignment_node_attribute(graph: DataflowGraph, instantiate: bool) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    if instantiate:
        y.assign(instance_node().reference(), Statement(), graph)

    x_n: AssignableNodeReference = graph.get_named_node("x.n")

    assignment_node: AssignableNode = x_n.assignment_node()
    instance: InstanceNode
    if instantiate:
        assert isinstance(y, VariableNodeReference)
        assert len(y.node.instance_assignments) == 1
        instance = y.node.instance_assignments[0].rhs.node()
    else:
        assert isinstance(z, VariableNodeReference)
        assert z.node.tentative_instance is not None
        instance = z.node.tentative_instance
        # verify tentative nodes only get created once
        assignment_node2: AssignableNode = x_n.assignment_node()
        assert assignment_node == assignment_node2
    assert assignment_node == instance.get_attribute("n")


def test_dataflow_assignment_node_nested_tentative(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")

    x_a_n: AssignableNodeReference = graph.get_named_node("x.a.n")
    assignment_node: AssignableNode = x_a_n.assignment_node()

    assert isinstance(x, VariableNodeReference)
    instance: Optional[InstanceNode] = x.node.tentative_instance
    assert instance is not None
    a: Optional[AttributeNode] = instance.get_attribute("a")
    assert a is not None
    instance2: Optional[InstanceNode] = a.tentative_instance
    assert instance2 is not None
    n: Optional[AttributeNode] = instance2.get_attribute("n")

    assert assignment_node == n


def test_dataflow_primitive_assignment(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    statement: Statement = Statement()
    x.assign(ValueNode(42).reference(), statement, graph)
    assert isinstance(x, DirectNodeReference)
    assert len(x.node.value_assignments) == 1
    assignment: Assignment[ValueNodeReference] = x.node.value_assignments[0]
    assert assignment.lhs == x
    assert assignment.rhs.node == ValueNode(42)
    assert assignment.responsible == statement
    assert assignment.context == graph


@pytest.mark.parametrize("instantiate", [True, False])
def test_attribute_assignment(graph: DataflowGraph, instantiate: bool) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    x_n: AssignableNodeReference = graph.get_named_node("x.n")

    if instantiate:
        x.assign(instance_node().reference(), Statement(), graph)
    x_n.assign(ValueNode(42).reference(), Statement(), graph)

    assert isinstance(x, VariableNodeReference)
    instance: InstanceNode
    if instantiate:
        assert x.node.tentative_instance is None
        assert len(x.node.instance_assignments) == 1
        instance = x.node.instance_assignments[0].rhs.node()
    else:
        assert x.node.tentative_instance is not None
        instance = x.node.tentative_instance

    n: Optional[AttributeNode] = instance.get_attribute("n")
    assert n is not None
    assert len(n.value_assignments) == 1
    assert n.value_assignments[0].rhs == ValueNode(42).reference()


def test_dataflow_tentative_attribute_propagation(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)

    x_a_n: AssignableNodeReference = graph.get_named_node("x.a.n")
    x_a_n.assign(ValueNode(42).reference(), Statement(), graph)

    def assert_tentative_a_n(var: AssignableNode) -> None:
        instance: Optional[InstanceNode] = var.tentative_instance
        assert instance is not None
        a: Optional[AttributeNode] = instance.get_attribute("a")
        assert a is not None
        instance2: Optional[InstanceNode] = a.tentative_instance
        assert instance2 is not None
        n: Optional[AttributeNode] = instance2.get_attribute("n")
        assert n is not None
        assert len(n.value_assignments) == 1
        assert n.value_assignments[0].rhs.node == ValueNode(42)

    assert isinstance(z, VariableNodeReference)
    assert_tentative_a_n(z.node)

    u: AssignableNodeReference = graph.get_named_node("u")
    v: AssignableNodeReference = graph.get_named_node("v")

    u.assign(v, Statement(), graph)
    z.assign(u, Statement(), graph)

    assert isinstance(z, VariableNodeReference)
    assert z.node.tentative_instance is None
    assert isinstance(v, VariableNodeReference)
    assert_tentative_a_n(v.node)


@pytest.mark.parametrize("register_both_dirs", [True, False])
@pytest.mark.parametrize("assign_first", [True, False])
def test_dataflow_bidirectional_attribute(graph: DataflowGraph, register_both_dirs: bool, assign_first: bool) -> None:
    namespace: Namespace = Namespace("dummy_namespace")
    left_entity: Entity = Entity("Left", namespace)
    right_entity: Entity = Entity("Right", namespace)

    def register_attributes() -> None:
        graph.register_bidirectional_attribute(left_entity, "right", "left")
        if register_both_dirs:
            graph.register_bidirectional_attribute(right_entity, "left", "right")

    def assign_attribute(left: InstanceNode, right: NodeReference) -> None:
        left.assign_attribute("right", right, Statement(), graph)

    left = register_instance(graph, left_entity)
    right = register_instance(graph, right_entity)
    right_indirect = register_instance(graph, right_entity)
    x: AssignableNodeReference = graph.get_named_node("x")
    x.assign(right_indirect.reference(), Statement(), graph)
    assert isinstance(x, VariableNodeReference)
    assert len(x.node.instance_assignments) == 1

    if assign_first:
        assign_attribute(left, right.reference())
        assign_attribute(left, x)
        register_attributes()
    else:
        register_attributes()
        assign_attribute(left, right.reference())
        assign_attribute(left, x)

    left_right: Optional[AttributeNode] = left.get_attribute("right")
    right_left: Optional[AttributeNode] = right.get_attribute("left")
    x_left: Optional[AttributeNode] = x.node.instance_assignments[0].rhs.node().get_attribute("left")
    assert left_right is not None
    assert right_left is not None
    assert x_left is not None
    assert len(left_right.instance_assignments) == 1
    assert len(left_right.assignable_assignments) == 1
    assert len(right_left.instance_assignments) == 1
    assert len(x_left.instance_assignments) == 1
    assert left_right.instance_assignments[0].rhs.node() == right
    assert left_right.assignable_assignments[0].rhs == x
    assert right_left.instance_assignments[0].rhs.node() == left
    assert x_left.instance_assignments[0].rhs.node() == left


def test_dataflow_index(graph: DataflowGraph) -> None:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    i1: InstanceNode = register_instance(graph, entity)
    i2: InstanceNode = register_instance(graph, entity)

    assert i1.get_self() is i1
    assert i2.get_self() is i2
    assert i1 is not i2

    graph.add_index_match([i.reference() for i in [i1, i2]])
    # make sure adding them again in another order does not cause issues
    graph.add_index_match([i.reference() for i in [i2, i1]])

    assert i1.get_self() is i1
    assert i2.get_self() is i1
    assert i2.reference().node() is i1
    assert i2.reference().top_node() is i2
    assert i1.get_self().get_all_index_nodes() == {i1, i2}


class DataflowTestHelper:
    def __init__(self, snippetcompiler) -> None:
        self.snippetcompiler = snippetcompiler
        self._namespace: Optional[Namespace] = None
        self._instances: Dict[str, InstanceNode] = {}
        self._tokens: List[str] = []

    def get_namespace(self) -> Namespace:
        assert self._namespace is not None, "Call compile before trying to access namespace"
        return self._namespace

    def get_graph(self) -> DataflowGraph:
        graph: Optional[DataflowGraph] = self.get_namespace().get_scope().dataflow_graph
        assert graph is not None
        return graph

    def compile(self, snippet: str, expected_error_type: Optional[Type[RuntimeException]] = None) -> None:
        def compile():
            print(snippet)
            self.snippetcompiler.setup_for_snippet(snippet)
            (_, root_ns) = compiler.do_compile()
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
            node_ref: AssignableNodeReference = self.get_graph().get_named_node(token)
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
                node_ref: AssignableNodeReference = self.get_graph().get_named_node(token)
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
        print(leaves)
        for key, value in leaves.items():
            lhs: AssignableNodeReference = self.get_graph().get_named_node(key)
            rhs: Set[AssignableNode] = set(chain.from_iterable(self.get_graph().get_named_node(v).nodes() for v in value))
            assert set(lhs.leaves()) == rhs


@pytest.fixture(scope="function")
def dataflow_test_helper(snippetcompiler):
    return DataflowTestHelper(snippetcompiler)


def test_dataflow_model_primitive_assignment_responsible(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = 42
        """,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = graph.get_named_node("x")
    assert isinstance(x, DirectNodeReference)
    assert len(x.node.value_assignments) == 1
    assignment: Assignment[ValueNodeReference] = x.node.value_assignments[0]
    assert isinstance(assignment.responsible, Assign)
    assert assignment.responsible.name == "x"
    assert isinstance(assignment.responsible.value, Literal)
    assert assignment.responsible.value.value == 42
    assert assignment.context == graph


def test_dataflow_model_primitive_double_assignment_responsible(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = 42
x = 0
        """,
        DoubleSetException,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = graph.get_named_node("x")
    assert isinstance(x, DirectNodeReference)
    assignments: List[Assignment] = x.node.value_assignments
    assert len(assignments) == 2
    zero_index: int = [assignment.rhs for assignment in assignments].index(ValueNode(0).reference())
    for i, assignment in enumerate(assignments):
        value: int = 0 if i == zero_index else 42
        assert assignment.context == graph
        assert isinstance(assignment.responsible, Assign)
        assert assignment.responsible.name == "x"
        assert isinstance(assignment.responsible.value, Literal)
        assert assignment.responsible.value.value == value


def test_dataflow_model_variable_assignment_responsible(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = 42
        """,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = graph.get_named_node("x")
    assert isinstance(x, DirectNodeReference)
    assert len(x.node.assignable_assignments) == 1
    assignment: Assignment[AssignableNodeReference] = x.node.assignable_assignments[0]
    assert isinstance(assignment.responsible, Assign)
    assert assignment.responsible.name == "x"
    assert isinstance(assignment.responsible.value, Reference)
    assert assignment.responsible.value.name == "y"
    assert assignment.context == graph


def test_dataflow_model_attribute_assignment_responsible(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity Test:
    number n
end
implement Test using std::none

x = Test()
x.n = 42
        """
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = graph.get_named_node("x")
    assert isinstance(x, VariableNodeReference)
    assert len(x.node.instance_assignments) == 1
    n: Optional[AttributeNode] = x.node.instance_assignments[0].rhs.node().get_attribute("n")
    assert n is not None
    assert len(n.value_assignments) == 1
    assignment: Assignment[ValueNodeReference] = n.value_assignments[0]
    assert isinstance(assignment.responsible, SetAttribute)
    assert assignment.responsible.instance.name == "x"
    assert assignment.responsible.attribute_name == "n"
    assert isinstance(assignment.responsible.value, Literal)
    assert assignment.responsible.value.value == 42
    assert assignment.context == graph


def test_dataflow_model_simple_assignment(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = 42
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> 42
        """,
    )
    dataflow_test_helper.verify_leaves({"x": {"x"}})


def test_dataflow_model_variable_assignment(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
x = y
y = 42
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> [ y y ]
y -> 42
        """,
    )
    dataflow_test_helper.verify_leaves({"x": {"y"}, "y": {"y"}})


@pytest.mark.parametrize("same_value", [True, False])
def test_dataflow_model_variable_assignment_double(dataflow_test_helper: DataflowTestHelper, same_value: bool) -> None:
    x_value: int = 42 if same_value else 0
    dataflow_test_helper.compile(
        """
x = y
x = y
y = 42
x = %d
        """
        % x_value,
        None if same_value else DoubleSetException,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> [ y y %s ]
y -> 42
        """
        % x_value,
    )
    dataflow_test_helper.verify_leaves({"x": {"x", "y"}, "y": {"y"}})


# TODO: fix this test. Fails because of faulty node lookup logic
def test_dataflow_model_unassigned_dependency_error(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
        """,
        NotFoundException,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> y
y -> z
        """,
    )
    dataflow_test_helper.verify_leaves({"x": {"z"}, "y": {"z"}})


@pytest.mark.parametrize("assign", [True, False])
def test_dataflow_model_dependency_loop(dataflow_test_helper: DataflowTestHelper, assign: bool) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
z = x
%s
        """
        % ("y = 42" if assign else ""),
        None if assign else RuntimeException,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> y
y -> [ z %s ]
z -> x
        """
        % ("42" if assign else ""),
    )
    all_vars: str = "xyz"
    dataflow_test_helper.verify_leaves({var: set(iter(all_vars)) for var in all_vars})


def test_dataflow_model_dependency_loop_with_var_assignment(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
z = x

y = v
v = w
w = 42
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> y
y -> [ z v ]
z -> x

v -> w
w -> 42
        """,
    )
    dataflow_test_helper.verify_leaves({var: {"w"} for var in "xyzvw"})


def test_dataflow_model_double_dependency_loop(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
z = x

x = v
v = w
w = x

y = 42
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> [ y v ]
y -> [ z 42 ]
z -> x

v -> w
w -> x
        """,
    )
    all_vars: str = "xyzvw"
    dataflow_test_helper.verify_leaves({var: set(iter(all_vars)) for var in all_vars})


@pytest.mark.parametrize("assign_loop0", [True, False])
def test_dataflow_model_chained_dependency_loops(dataflow_test_helper: DataflowTestHelper, assign_loop0: bool) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
z = x

u = v
v = w
w = u

y = v

u = 42
%s
        """ % ("z = 42" if assign_loop0 else ""),
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> y
y -> [ z v ]
z -> [ x %s ]

u -> [ v 42 ]
v -> w
w -> u
        """ % ("42" if assign_loop0 else ""),
    )
    # TODO: fix inconsistency: leaves for u are actually just "uvw"
    loop0_vars: str = "xyz"
    loop1_vars: str = "uvw"
    all_vars: str = loop0_vars + loop1_vars
    leaf_vars: str = all_vars if assign_loop0 else loop1_vars
    dataflow_test_helper.verify_leaves({var: set(iter(leaf_vars)) for var in all_vars})


@pytest.mark.parametrize("attr_init", [True, False])
def test_dataflow_model_assignment_from_attribute(dataflow_test_helper: DataflowTestHelper, attr_init: bool) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
end
implement A using std::none

n = 42
x = A(%s)

nn = x.n
        """ % ("n = n" if attr_init else ""),
        None if attr_init else RuntimeException,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> <instance> 0
n -> 42
nn -> x . n
%s
        """ % ("<instance> 0 . n -> n" if attr_init else ""),
    )
    dataflow_test_helper.verify_leaves({"nn": {"n"}} if attr_init else {"nn": {"x.n"}})


def test_dataflow_model_assignment_outside_constructor(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
end
implement A using std::none

n = 42

x = A()
x.n = n
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
n -> 42
x -> <instance> 0
<instance> 0 . n -> n
        """,
    )
    dataflow_test_helper.verify_leaves({"x.n": {"n"}})


# TODO tests:
#   relations
#   default attributes
#   dynamic scoping
#   FIX: dynamic scope referring to parent


# TODO:
#   add model tests
#   fix TODO's in inmanta.execute.dataflow
#   add toggle option to inmanta.app
