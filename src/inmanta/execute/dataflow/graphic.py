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
from typing import Iterable, Iterator, Optional, Set, cast

from inmanta.ast import RuntimeException
from inmanta.execute.dataflow import (
    AssignableNode,
    AssignableNodeReference,
    Assignment,
    AttributeNode,
    AttributeNodeReference,
    DirectNodeReference,
    InstanceNode,
    InstanceNodeReference,
    Node,
    ValueNode,
    VariableNodeReference,
)
from inmanta.execute.runtime import Instance, ResultVariable

try:
    import graphviz
    from graphviz import Digraph
except ModuleNotFoundError:
    raise RuntimeException(None, "Graphically visualizing the data flow graph requires the graphviz python package.")


class GraphicRenderer:
    """
    Renders the DataflowGraph as a graphic graph. This graphic representation does not show all
    information because that would make it too congested. It shows nodes and assignments but not
    responsibles or dynamic context. An assignment where the right hand side is an attribute
    x.y.z is shown as an edge to z with the label ".y.z".
    """

    @classmethod
    def view(cls, variables: Iterable[ResultVariable], instances: Iterable[Instance]) -> None:
        """
        Renders and visualizes supplied variables and instances and the paths originating in them.
        """
        cls.render(variables, instances).view()

    @classmethod
    def render(cls, variables: Iterable[ResultVariable], instances: Iterable[Instance]) -> "GraphicGraph":
        """
        Renders supplied variables and instances and the paths originating in them.
        """
        graphic: GraphicGraph = GraphicGraph()
        for instance in instances:
            assert instance.instance_node is not None
            graphic.add_node(instance.instance_node.top_node())
        for var in variables:
            for node in var.get_dataflow_node().nodes():
                graphic.add_node(node)
        return graphic


class GraphicGraph:
    """
    Graphic representation of a data flow graph. Stateful. Methods add_node and add_assignments have side effects.
    """

    def __init__(self) -> None:
        self.digraph: Digraph = Digraph(engine="fdp")
        self._nodes: Set[Node] = set(())
        self._assignments: Set[Assignment] = set(())

    def view(self) -> None:
        try:
            self.digraph.view()
        except graphviz.ExecutableNotFound:
            raise RuntimeException(
                None,
                "Graphically visualizing the data flow graph requires the fdp command"
                " from your distribution's graphviz package.",
            )

    def node_key(self, node: Node) -> str:
        """
        Returns a unique key for a node.
        node == other => node_key(node) == node_key(other)
        """
        key: str = str(hash(node))
        if isinstance(node, InstanceNode):
            # required for fdp compatibility
            return "cluster_" + key
        return key

    def add_node(self, node: Node) -> None:
        """
        Adds the node if it has not been added yet, recursing along dependencies (assignments, attributes, ...)
        """
        if node in self._nodes:
            return
        self._nodes.add(node)

        if isinstance(node, InstanceNode):
            self._add_node_instance(node)
        elif isinstance(node, AttributeNode):
            self._add_node_attribute(node)
            self.add_assignments(node.assignments())
        elif isinstance(node, AssignableNode):
            self._add_node_generic(node)
            self.add_assignments(node.assignments())
        else:
            self._add_node_generic(node)

    def _add_node_generic(self, node: Node) -> None:
        self.digraph.node(self.node_key(node), repr(node), shape="diamond" if isinstance(node, ValueNode) else "ellipse")

    def _add_node_attribute(self, node: AttributeNode) -> None:
        self.add_node(node.instance)
        # create a node in the attribute's instance's subgraph
        with self.digraph.subgraph(name=self.node_key(node.instance)) as subgraph:
            subgraph.node(self.node_key(node), node.name, shape="ellipse")

    def _add_node_instance(self, node: InstanceNode) -> None:
        # create subgraph to represent the instance node. Attribute nodes will be nodes in the subgraph
        with self.digraph.subgraph(name=self.node_key(node)) as subgraph:
            label: str = "?" if node.entity is None else node.entity.get_name()
            subgraph.attr(label=label)
        if node is node.get_self():
            for attribute in node.attributes.values():
                self.add_node(attribute)
            for index_node in node.get_all_index_nodes():
                self.add_node(index_node)
        else:
            self.add_node(node.get_self())
            self.digraph.edge(self.node_key(node), self.node_key(node.get_self()), label="index")

    def add_assignments(self, assignments: Iterable[Assignment]) -> None:
        """
        Adds the assignments if they have not been added yet, recursing on the rhs' assignments.
        """

        def unroll_attribute_reference(attr: AttributeNodeReference) -> Iterator[AttributeNodeReference]:
            """
            Unrolls a chain of attribute references. Returns the chain of references where a parent comes after its child.
            """
            yield attr
            if isinstance(attr.instance_var_ref, AttributeNodeReference):
                yield from unroll_attribute_reference(attr.instance_var_ref)

        for assignment in assignments:
            if assignment in self._assignments:
                continue
            self._assignments.add(assignment)
            rhs: Node
            label: Optional[str] = None

            if isinstance(assignment.rhs, InstanceNodeReference):
                rhs = assignment.rhs.top_node()
            elif isinstance(assignment.rhs, AttributeNodeReference):
                label = ""
                instance_var_ref: AssignableNodeReference
                (label, instance_var_ref) = reduce(
                    lambda acc, x: (".%s%s" % (x.attribute, acc[0]), x.instance_var_ref),
                    unroll_attribute_reference(assignment.rhs),
                    ("", cast(AssignableNodeReference, assignment.rhs)),
                )
                assert isinstance(instance_var_ref, VariableNodeReference)
                rhs = instance_var_ref.node
            elif isinstance(assignment.rhs, DirectNodeReference):
                rhs = assignment.rhs.node
            else:
                raise Exception("Unknown node reference %s of type %s" % (assignment.rhs, type(assignment.rhs)))

            self.add_node(rhs)
            self.digraph.edge(self.node_key(assignment.lhs), self.node_key(rhs), label=label)
