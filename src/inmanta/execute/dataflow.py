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

from typing import TYPE_CHECKING, Dict, Iterable, Iterator, Optional

if TYPE_CHECKING:
    from inmanta.execute.runtime import Resolver
    from inmanta.ast.statements import Statement
    from inmanta.ast.entity import Entity


class DataflowGraph:
    """
        Graph representation of the data flow and declarative control flow of an Inmanta model.
    """

    # TODO: other slots
    __slots__ = ("resolver", "parent", "_own_instances")

    def __init__(self, resolver: "Resolver", parent: Optional["DataflowGraph"] = None) -> None:
        self.resolver: "Resolver" = resolver
        self.parent: Optional[DataflowGraph] = parent if parent is not None else None
        self._own_instances: Dict[Statement, InstanceNode] = {}
        # TODO: finish implementation

    def get_named_node(self, name: str) -> "AssignableNodeReference":
        """
            Returns a reference to a named node, by name.
        """
        # TODO: implement
        return AssignableNodeReference()

    def own_instance_node_for_responsible(self, responsible: "Statement", default: "InstanceNode") -> "InstanceNode":
        """
            Returns this graph's instance node tied to responsible if it exists.
            Otherwise, returns default and adds it to the graph.
        """
        if responsible not in self._own_instances:
            assert default.responsible == responsible
            self._own_instances[responsible] = default
            self._add_global_instance_node(default.reference())
        return self._own_instances[responsible]

    def _add_global_instance_node(self, node: "InstanceNodeReference") -> None:
        # TODO: implement
        pass

    def add_bidirectional_attribute(self, entity: "Entity", this: str, other: str) -> None:
        # TODO: implement
        pass

    def add_index_match(self, instances: Iterable["InstanceNodeReference"]) -> None:
        # TODO: implement
        pass

    # TODO: other methods


class Node:
    """
        A node in the data flow graph. Represents an attribute, variable, value or instance in the configuration model.
    """

    def __init__(self) -> None:
        pass

    def reference(self) -> "NodeReference":
        """
            Returns a reference to this node.
        """
        raise NotImplementedError()


class NodeReference:
    """
        Reference to a node.
    """

    def __init__(self) -> None:
        pass

    def nodes(self) -> Iterator["Node"]:
        """
            Returns all nodes this NodeReference refers to.
        """
        raise NotImplementedError()

    def ref_to_node(self, node: "Node") -> bool:
        """
            Returns true iff this NodeReference refers to node.
        """
        return node in self.nodes()


class AssignableNodeReference(NodeReference):
    """
        Reference to a node that can have values assigned to it.
    """

    def __init__(self) -> None:
        NodeReference.__init__(self)

    # TODO: all methods

    def assignment_node(self) -> "AssignableNode":
        """
            Returns the assignable node to which an assignment to this reference should be delegated.
        """
        raise NotImplementedError()

    def assign(self, node_ref: "NodeReference", responsible: "Statement", context: "DataflowGraph") -> None:
        """
            Assign another node to this reference's assignment node.
        """
        # TODO: implement
        self.assignment_node().assign(node_ref, responsible, context)

    def get_attribute(self, name: str) -> "AttributeNodeReference":
        """
            Returns a reference to an attribute of this reference's node, by name.
        """
        return AttributeNodeReference(self, name)


class AttributeNodeReference(AssignableNodeReference):
    """
        Reference to a node representing an attribute of another node.
    """

    def __init__(self, instance_var_ref: AssignableNodeReference, attribute: str) -> None:
        AssignableNodeReference.__init__(self)
        self.instance_var_ref: AssignableNodeReference = instance_var_ref
        self.attribute: str = attribute

    # TODO: all methods

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AttributeNodeReference):
            return NotImplemented
        return self.instance_var_ref == other.instance_var_ref and self.attribute == other.attribute

    def __repr__(self) -> str:
        return "%s.%s" % (repr(self.instance_var_ref), self.attribute)


class DirectNodeReference(NodeReference):
    """
        Direct reference to a Node.
    """

    def __init__(self, node: "Node") -> None:
        NodeReference.__init__(self)
        self.node: Node = node

    def nodes(self) -> Iterator["Node"]:
        yield self.node

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DirectNodeReference):
            return NotImplemented
        return self.node == other.node


class VariableNodeReference(AssignableNodeReference, DirectNodeReference):
    """
        Reference to a node representing a variable in the configuration model.
    """

    def __init__(self, node: "AssignableNode") -> None:
        AssignableNodeReference.__init__(self)
        DirectNodeReference.__init__(self, node)
        self.node: AssignableNode

    def nodes(self) -> Iterator["AssignableNode"]:
        yield self.node

    def assignment_node(self) -> "AssignableNode":
        return self.node

    def __repr__(self) -> str:
        return self.node.name


class ValueNodeReference(DirectNodeReference):
    """
        Reference to a node representing a value in the configuration model.
    """

    def __init__(self, node: "ValueNode") -> None:
        DirectNodeReference.__init__(self, node)
        self.node: ValueNode

    def __repr__(self) -> str:
        return repr(self.node.value)


class InstanceNodeReference(NodeReference):
    """
        Reference to a node representing an entity instance in the configuration model.
    """

    def __init__(self, node: "InstanceNode") -> None:
        NodeReference.__init__(self)
        self._node: InstanceNode = node

    def top_node(self) -> "InstanceNode":
        """
            Returns the node this reference refers to directly.
        """
        return self._node

    def node(self) -> "InstanceNode":
        """
            Returns the actual instance node in case of index matches.
        """
        return self.top_node().get_self()

    def nodes(self) -> Iterator["Node"]:
        yield self.node()

    def assign_attribute(
        self, attribute: str, node_ref: "NodeReference", responsible: "Statement", context: "DataflowGraph"
    ) -> None:
        """
            Assigns a node to an attribute of the instance this reference refers to.
        """
        self.node().assign_attribute(attribute, node_ref, responsible, context)

    def __repr__(self) -> str:
        return "%s instance" % self.top_node().entity

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InstanceNodeReference):
            return NotImplemented
        return self._node == other._node


class ValueNode(Node):
    """
        Node representing a value in the configuration model.
    """

    # TODO: this can be done more efficiently: make ValueNodes singletons
    def __init__(self, value: object) -> None:
        super().__init__()
        self.value: object = value

    def reference(self) -> "ValueNodeReference":
        return ValueNodeReference(self)


class NodeStub(ValueNode):
    """
        node that represents currently unsupported expressions.
    """

    def __init__(self, message: str) -> None:
        ValueNode.__init__(self, message)
        self.message = message

    def reference(self) -> "ValueNodeReference":
        return ValueNodeReference(self)


class AssignableNode(Node):
    """
        Node representing a variable or an attribute in the assignment graph model.
    """

    def __init__(self, name: str) -> None:
        Node.__init__(self)
        self.name: str = name
        # TODO: implement

    def reference(self) -> AssignableNodeReference:
        return VariableNodeReference(self)

    def assign(self, node_ref: "NodeReference", responsible: "Statement", context: "DataflowGraph") -> None:
        """
            Assigns another node to this one, by reference.
        """
        # TODO: implement
        pass

    # TODO: all methods


class AttributeNode(AssignableNode):
    """
        Node representing an entity's attribute.
    """

    def __init__(self, instance: "InstanceNode", name: str) -> None:
        AssignableNode.__init__(self, name)
        self.instance: InstanceNode = instance
        # TODO: implement

    def assign(self, node_ref: NodeReference, responsible: "Statement", context: "DataflowGraph") -> None:
        # TODO: implement
        pass

    # TODO: all methods


class InstanceNode(Node):
    """
        Node representing an entity instance.
    """

    def __init__(
        self, attributes: Iterable[str], entity: "Entity", responsible: "Statement", context: "DataflowGraph" = None,
    ) -> None:
        Node.__init__(self)
        self.attributes: Dict[str, AttributeNode] = {name: AttributeNode(self, name) for name in attributes}
        self.entity: "Entity" = entity
        self.index_node: Optional[InstanceNode] = None
        self.responsible: "Statement" = responsible
        self.context: "DataflowGraph" = context
        # TODO: finish implementation

    def get_self(self) -> "InstanceNode":
        """
            Returns the main instance node if this node acts as a proxy due to an index match.
            Otherwise returns itself.
        """
        return self if self.index_node is None else self.index_node.get_self()

    def reference(self) -> InstanceNodeReference:
        return InstanceNodeReference(self)

    def assign_attribute(
        self, attribute: str, node_ref: "NodeReference", responsible: "Statement", context: "DataflowGraph",
    ) -> None:
        """
            Assigns a node to one of this instance's attributes.
        """

    # TODO: all methods
