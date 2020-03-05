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
from itertools import chain, filterfalse
from typing import TYPE_CHECKING, Callable, Dict, FrozenSet, Generic, Iterable, Iterator, List, Optional, Set, Tuple, TypeVar

if TYPE_CHECKING:
    from inmanta.execute.runtime import Resolver
    from inmanta.ast import Locatable
    from inmanta.ast.entity import Entity


class DataflowGraph:
    """
        Graph representation of the data flow and declarative control flow of an Inmanta model.
    """

    __slots__ = ("resolver", "parent", "named_nodes", "_instances", "_own_instances")

    def __init__(self, resolver: "Resolver", parent: Optional["DataflowGraph"] = None) -> None:
        self.resolver: "Resolver" = resolver
        self.parent: Optional[DataflowGraph] = parent if parent is not None else None
        self.named_nodes: Dict[str, AssignableNode] = {}
        self._instances: Dict["Entity", EntityData] = {}
        self._own_instances: Dict["Locatable", InstanceNode] = {}

    def instances(self) -> Dict["Entity", "EntityData"]:
        """
            Returns entity data for all registered entities.
            EntityData objects are stored in the root dataflow graph.
        """
        if self.parent is not None:
            return self.parent.instances()
        return self._instances

    def _entity_data(self, entity: "Entity") -> "EntityData":
        """
            Returns an EntityData object for an Entity. Registers the entity if it is not yet registered.
        """
        instances: Dict["Entity", "EntityData"] = self.instances()
        if entity not in instances:
            instances[entity] = EntityData(entity)
        return instances[entity]

    def get_named_node(self, name: str) -> "AssignableNodeReference":
        """
            Returns a reference to a named node, by name.
        """
        # TODO: temporary name lookup implementation. Will be replaced by #1879
        parts: List[str] = name.split(".")
        root: str = parts[0]
        if root not in self.named_nodes:
            self.named_nodes[root] = AssignableNode(root)
        root_ref: AssignableNodeReference = VariableNodeReference(self.named_nodes[root])
        return reduce(lambda acc, part: AttributeNodeReference(acc, part), parts[1:], root_ref)

    def own_instance_node_for_responsible(
        self, responsible: "Locatable", get_new: Callable[[], "InstanceNode"]
    ) -> "InstanceNode":
        """
            Returns this graph's instance node tied to responsible if it exists.
            Otherwise, creates a new one using get_new, returns it and adds it to the graph.
        """
        if responsible not in self._own_instances:
            new: InstanceNode = get_new()
            assert new.responsible == responsible
            self._own_instances[responsible] = new
            self._add_global_instance_node(new.reference())
        return self._own_instances[responsible]

    def _add_global_instance_node(self, node: "InstanceNodeReference") -> None:
        """
            Registers an instance.
        """
        entity: Optional["Entity"] = node.top_node().entity
        if entity is not None:
            self._entity_data(entity).add_instance(node)

    def register_bidirectional_attribute(self, entity: "Entity", this: str, other: str) -> None:
        """
            Registers a pair of bidirectional attributes.
        """
        self._entity_data(entity).register_bidirectional_attribute(this, other)

    def add_index_match(self, instances: Iterable["InstanceNodeReference"]) -> None:
        """
            Registers an index match between a set of instance nodes. Informs the nodes of the match.
        """
        iterator: Iterator[InstanceNodeReference] = iter(instances)
        try:
            first: InstanceNode = next(iter(iterator)).node()
            for instance in iterator:
                instance.node().index_match(first)
        except StopIteration:
            pass


class EntityData:
    """
        Data about an entity. Contains an entity's bidirectional attributes and a list of all instances.
        Enforces bidirectionality for all instances.
    """

    __slots__ = ("entity", "bidirectional_attributes", "instances")

    def __init__(self, entity: "Entity") -> None:
        self.entity: "Entity" = entity
        self.bidirectional_attributes: Dict[str, str] = {}
        self.instances: List[InstanceNodeReference] = []

    def register_bidirectional_attribute(self, this: str, other: str) -> None:
        self.bidirectional_attributes[this] = other
        for instance in self.instances:
            instance.node().register_bidirectional_attribute(this, other)

    def add_instance(self, instance: "InstanceNodeReference") -> None:
        self.instances.append(instance)
        for this, other in self.bidirectional_attributes.items():
            instance.node().register_bidirectional_attribute(this, other)


class Node:
    """
        A node in the data flow graph. Represents an attribute, variable, value or instance in the configuration model.
    """

    __slots__ = ()

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

    __slots__ = ()

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

    def assign_to(self, lhs: "AssignableNode", responsible: "Locatable", context: "DataflowGraph") -> None:
        """
            Assigns this node to the left hand side node.
        """
        raise NotImplementedError()

    def assign_attribute(
        self, attribute: str, rhs: "NodeReference", responsible: "Locatable", context: "DataflowGraph"
    ) -> None:
        raise NotImplementedError()


class AssignableNodeReference(NodeReference):
    """
        Reference to a node that can have values assigned to it.
    """

    __slots__ = ()

    def __init__(self) -> None:
        NodeReference.__init__(self)

    def nodes(self) -> Iterator["AssignableNode"]:
        raise NotImplementedError()

    def leaves(self) -> Iterator["AssignableNodeReference"]:
        """
            Returns an iterator over this reference's leaves. A leaf is defined as a node reference
            in the assignment tree which has either one or more value or instance assignments
            or no assignments at all. This reference's leaves are the leaves of the assignment
            subtrees originating from this reference's nodes.
        """
        child_leaves: Iterator["AssignableNodeReference"] = chain.from_iterable(n.leaves() for n in self.nodes())
        try:
            yield next(child_leaves)
            yield from child_leaves
        except StopIteration:
            yield self

    def leaf_nodes(self) -> Iterator["AssignableNode"]:
        """
            Returns an iterator over the nodes this reference's leaves refer to.
        """
        return chain.from_iterable(leaf.nodes() for leaf in self.leaves())

    def any_leaf_node(self) -> Optional["AssignableNode"]:
        """
            Returns a single leaf for this reference, if any exist.
        """
        try:
            return next(self.leaf_nodes())
        except StopIteration:
            return None

    def assignment_node(self) -> "AssignableNode":
        """
            Returns the assignable node to which an assignment to this reference should be delegated.
        """
        raise NotImplementedError()

    def assign(self, node_ref: "NodeReference", responsible: "Locatable", context: "DataflowGraph") -> None:
        """
            Assign another node to this reference's assignment node.
        """
        self.assignment_node().assign(node_ref, responsible, context)

    def assign_to(self, lhs: "AssignableNode", responsible: "Locatable", context: "DataflowGraph") -> None:
        lhs.assign_assignable(self, responsible, context)

    def get_attribute(self, name: str) -> "AttributeNodeReference":
        """
            Returns a reference to an attribute of this reference's node, by name.
        """
        return AttributeNodeReference(self, name)

    def assign_attribute(
        self, attribute: str, rhs: "NodeReference", responsible: "Locatable", context: "DataflowGraph"
    ) -> None:
        self.get_attribute(attribute).assign(rhs, responsible, context)


class AttributeNodeReference(AssignableNodeReference):
    """
        Reference to a node representing an attribute of another node.
    """

    __slots__ = ("instance_var_ref", "attribute")

    def __init__(self, instance_var_ref: AssignableNodeReference, attribute: str) -> None:
        AssignableNodeReference.__init__(self)
        self.instance_var_ref: AssignableNodeReference = instance_var_ref
        self.attribute: str = attribute

    def nodes(self) -> Iterator["AssignableNode"]:
        # yield all attribute nodes on instances assigned to this reference's leaves
        for node in self.instance_var_ref.leaf_nodes():
            for assignment in node.instance_assignments:
                yield assignment.rhs.node().register_attribute(self.attribute)

    def assignment_node(self) -> "AssignableNode":
        try:
            return next(self.nodes())
        except StopIteration:
            # If no attribute node can be found, create a tentative one on a leaf of the instance_var_ref.
            # Tentative attributes of a VariableNode will be propagated on assignment to that node.
            instance_leaf: Optional["AssignableNode"] = self.instance_var_ref.any_leaf_node()
            if instance_leaf is None:
                instance_leaf = self.instance_var_ref.assignment_node()
            return instance_leaf.equivalence.tentative_attribute(self.attribute)

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

    __slots__ = "node"

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

    __slots__ = ()

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

    __slots__ = ()

    def __init__(self, node: "ValueNode") -> None:
        DirectNodeReference.__init__(self, node)
        self.node: ValueNode

    def assign_to(self, lhs: "AssignableNode", responsible: "Locatable", context: "DataflowGraph") -> None:
        lhs.assign_value(self, responsible, context)

    def assign_attribute(
        self, attribute: str, rhs: "NodeReference", responsible: "Locatable", context: "DataflowGraph"
    ) -> None:
        if isinstance(self.node, NodeStub):
            return
        raise Exception("Can not assign attribute on a value node")

    def __repr__(self) -> str:
        return repr(self.node.value)


class InstanceNodeReference(NodeReference):
    """
        Reference to a node representing an entity instance in the configuration model.
    """

    __slots__ = "_node"

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
        self, attribute: str, rhs: "NodeReference", responsible: "Locatable", context: "DataflowGraph"
    ) -> None:
        """
            Assigns a node to an attribute of the instance this reference refers to.
        """
        self.node().assign_attribute(attribute, rhs, responsible, context)

    def __repr__(self) -> str:
        return "%s instance" % self.top_node().entity

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InstanceNodeReference):
            return NotImplemented
        return self._node == other._node

    def assign_to(self, lhs: "AssignableNode", responsible: "Locatable", context: "DataflowGraph") -> None:
        lhs.assign_instance(self, responsible, context)


RT = TypeVar("RT", bound=NodeReference, covariant=True)


class Assignment(Generic[RT]):
    """
        Assignment of one node to another, caused by a responsible
    """

    __slots__ = ("lhs", "rhs", "responsible", "context")

    def __init__(self, lhs: AssignableNodeReference, rhs: RT, responsible: "Locatable", context: "DataflowGraph") -> None:
        self.lhs: AssignableNodeReference = lhs
        self.rhs: RT = rhs
        self.responsible: "Locatable" = responsible
        self.context: "DataflowGraph" = context


class ValueNode(Node):
    """
        Node representing a value in the configuration model.
    """

    __slots__ = "value"

    def __init__(self, value: object) -> None:
        super().__init__()
        self.value: object = value

    def reference(self) -> "ValueNodeReference":
        return ValueNodeReference(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValueNode):
            return NotImplemented
        return self.value == other.value


class NodeStub(ValueNode):
    """
        Node that represents currently unsupported expressions.
    """

    __slots__ = "message"

    def __init__(self, message: str) -> None:
        ValueNode.__init__(self, message)
        self.message = message

    def reference(self) -> "ValueNodeReference":
        return ValueNodeReference(self)


class AssignableNode(Node):
    """
        Node representing a variable or an attribute in the assignment graph model.
    """

    __slots__ = ("name", "assignable_assignments", "value_assignments", "instance_assignments", "equivalence")

    def __init__(self, name: str) -> None:
        Node.__init__(self)
        self.name: str = name
        self.assignable_assignments: List[Assignment[AssignableNodeReference]] = []
        self.value_assignments: List[Assignment[ValueNodeReference]] = []
        self.instance_assignments: List[Assignment[InstanceNodeReference]] = []
        self.equivalence: Equivalence = Equivalence(frozenset([self]))

    def reference(self) -> AssignableNodeReference:
        return VariableNodeReference(self)

    def leaves(self) -> Iterator["AssignableNodeReference"]:
        """
            Returns an iterator over this node's leaves. A leaf is defined as a node
            in the assignment tree which has either one or more value or instance assignments
            or no assignments at all. This node's leaves are the leaves of the assignment
            subtree originating from this node.
        """
        return self.equivalence.leaves()

    def assignments(self) -> Iterator[Assignment]:
        """
            Returns an iterator over assignments to this node.
        """
        return chain(self.assignable_assignments, self.value_assignments, self.instance_assignments)

    def assign(self, node_ref: "NodeReference", responsible: "Locatable", context: "DataflowGraph") -> None:
        """
            Assigns another node to this one, by reference.
        """
        node_ref.assign_to(self, responsible, context)

    def assign_value(self, val_ref: ValueNodeReference, responsible: "Locatable", context: "DataflowGraph") -> None:
        """
            Assigns a value node to this node, by reference.
        """
        self.value_assignments.append(Assignment(self.reference(), val_ref, responsible, context))

    def assign_instance(self, instance_ref: InstanceNodeReference, responsible: "Locatable", context: "DataflowGraph") -> None:
        """
            Assigns an instance node to this node, by reference.
        """
        self.instance_assignments.append(Assignment(self.reference(), instance_ref, responsible, context))
        self.equivalence.propagate_tentative_instance()

    def assign_assignable(self, var_ref: AssignableNodeReference, responsible: "Locatable", context: "DataflowGraph") -> None:
        """
            Assigns an assignable node to this node, by reference.
        """
        # Gather all equivalences on the path between the rhs's leaves and this node.
        # The existence of such a trail indicates an assignment loop.
        equivalence_trail: Set[Equivalence] = reduce(
            set.union, (n.equivalence.equivalences_on_path(self) for n in var_ref.nodes()), set(),
        )
        # merge all equivalences on the trail
        new_equivalence: Equivalence = reduce(
            lambda acc, eq: acc.merge(eq), equivalence_trail, Equivalence(frozenset()),
        )
        self.assignable_assignments.append(Assignment(self.reference(), var_ref, responsible, context))
        # apply new equivalence to all it's nodes
        for node in new_equivalence.nodes:
            node.equivalence = new_equivalence
        # propagate this node's tentative instance to the new leaves, if it exists
        self.equivalence.propagate_tentative_instance()


class Equivalence:
    """
        Represents a collection of nodes that are equivalent because of one or more assignment loops.
    """

    __slots__ = ("nodes", "tentative_instance")

    def __init__(
        self, nodes: FrozenSet[AssignableNode] = frozenset(), tentative_instance: Optional["InstanceNode"] = None
    ) -> None:
        self.nodes: FrozenSet[AssignableNode] = nodes
        self.tentative_instance: Optional[InstanceNode] = tentative_instance

    def merge(self, other: "Equivalence") -> "Equivalence":
        """
            Returns the equivalence that is the union of this one and the one passed as an argument.
        """
        tentative_instance: Optional[InstanceNode] = self.tentative_instance
        if tentative_instance is not None:
            self.tentative_instance = None
            if other.tentative_instance is not None:
                tentative_instance.merge(other.tentative_instance)
        return Equivalence(self.nodes.union(other.nodes), tentative_instance)

    def is_leaf(self) -> bool:
        """
            Returns true iff this equivalence is a leaf. An equivalence is a leaf iff it has an instance
            or value assignment, or doesn't have any assignments at all.
        """
        return any(self.instance_assignments()) or any(self.value_assignments()) or not any(self.assignable_assignments())

    def leaves(self) -> Iterator[AssignableNodeReference]:
        """
            Returns an iterator over all leaves on assignment paths originating from this equivalence.
        """
        if self.is_leaf():
            explicit_leaves: Iterator[AssignableNodeReference] = (
                node.reference() for node in self.nodes if len(node.value_assignments) > 0 or len(node.instance_assignments) > 0
            )
            try:
                yield next(explicit_leaves)
                yield from explicit_leaves
            except StopIteration:
                yield from (node.reference() for node in self.nodes)
        yield from (node for assignment in self.assignable_assignments() for node in assignment.rhs.leaves())

    def equivalences_on_path(self, node: AssignableNode) -> Set["Equivalence"]:
        """
            Returns the set of all equivalences on the assignment path originating from this equivalence
            and terminating in the equivalence containing node.
            Returns the empty set if there is no such path.
        """
        if node in self.nodes:
            return {self}
        child_paths: Set[Equivalence] = reduce(
            set.union,
            (
                n.equivalence.equivalences_on_path(node)
                for n in set(chain.from_iterable(a.rhs.nodes() for a in self.assignable_assignments()))
            ),
            set(),
        )
        return child_paths.union({self}) if len(child_paths) > 0 else set(())

    def assignable_assignments(self) -> Iterator[Assignment[AssignableNodeReference]]:
        """
            Returns an iterator over external VariableNodes assigned to this Equivalence.
        """

        def is_internal(assignment: Assignment[AssignableNodeReference]) -> bool:
            filtered: Iterator[AssignableNode] = filter(assignment.rhs.ref_to_node, self.nodes)
            return any(filtered)

        return filterfalse(is_internal, chain.from_iterable(n.assignable_assignments for n in self.nodes))

    def instance_assignments(self) -> Iterator[Assignment[InstanceNodeReference]]:
        """
            Returns an iterator over InstanceNodes assigned to this Equivalence.
        """
        return chain.from_iterable(n.instance_assignments for n in self.nodes)

    def value_assignments(self) -> Iterator[Assignment[ValueNodeReference]]:
        """
            Returns an iterator over ValueNodes assigned to this Equivalence.
        """
        return chain.from_iterable(n.value_assignments for n in self.nodes)

    def propagate_tentative_instance(self) -> None:
        """
            Propagates this equivalence's tentative instance to one of it's leaves.
        """

        def propagate_tentative_assignments(source: Equivalence, target: AssignableNodeReference) -> None:
            """
                Recursively propagate tentative assignments.
                Makes sure tentative assignments over a relation get propageted as well.
            """
            if source.tentative_instance is None:
                return
            for tent_attr_name, tent_attr_node in source.tentative_instance.attributes.items():
                attr_node: AttributeNodeReference = target.get_attribute(tent_attr_name)
                for assignment in tent_attr_node.assignments():
                    attr_node.assign(assignment.rhs, assignment.responsible, assignment.context)
                propagate_tentative_assignments(tent_attr_node.equivalence, target.get_attribute(tent_attr_name))
            self.tentative_instance = None

        try:
            leaf: AssignableNodeReference = next(self.leaves())
            propagate_tentative_assignments(self, leaf)
        except StopIteration:
            raise Exception("Inconsistent state: an equivalence should always have at least one leaf")

    def tentative_attribute(self, attr: str) -> "AttributeNode":
        if self.tentative_instance is None:
            self.tentative_instance = InstanceNode([])
        attr_node: Optional[AttributeNode] = self.tentative_instance.get_attribute(attr)
        if attr_node is None:
            attr_node = self.tentative_instance.register_attribute(attr)
        return attr_node

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Equivalence):
            return NotImplemented
        return self.nodes == other.nodes and self.tentative_instance == other.tentative_instance

    def __hash__(self) -> int:
        return hash(self.nodes)


class AttributeNode(AssignableNode):
    """
        Node representing an entity's attribute.
    """

    __slots__ = ("instance", "responsibles")

    def __init__(self, instance: "InstanceNode", name: str) -> None:
        AssignableNode.__init__(self, name)
        self.instance: InstanceNode = instance
        self.responsibles: Set[Tuple["Locatable", DataflowGraph]] = set(())

    def assign(self, node_ref: NodeReference, responsible: "Locatable", context: "DataflowGraph") -> None:
        # only add assignment for each responsible once, this check is necessary for bidirectional attributes
        if (responsible, context) in self.responsibles:
            return
        super().assign(node_ref, responsible, context)
        self.responsibles.add((responsible, context))
        self.instance.assign_other_direction(self.name, node_ref, responsible, context)


class InstanceNode(Node):
    """
        Node representing an entity instance.
    """

    __slots__ = (
        "attributes",
        "entity",
        "responsible",
        "context",
        "bidirectional_attributes",
        "_index_node",
        "_all_index_nodes",
    )

    def __init__(
        self,
        attributes: Iterable[str],
        entity: Optional["Entity"] = None,
        responsible: Optional["Locatable"] = None,
        context: Optional["DataflowGraph"] = None,
    ) -> None:
        Node.__init__(self)
        self.attributes: Dict[str, AttributeNode] = {name: AttributeNode(self, name) for name in attributes}
        self.entity: Optional["Entity"] = entity
        self.responsible: Optional["Locatable"] = responsible
        self.context: Optional["DataflowGraph"] = context
        self.bidirectional_attributes: Dict[str, str] = {}
        self._index_node: Optional[InstanceNode] = None
        self._all_index_nodes: Set["InstanceNode"] = {self}

    def reference(self) -> InstanceNodeReference:
        return InstanceNodeReference(self)

    def get_self(self) -> "InstanceNode":
        """
            Returns the main instance node if this node acts as a proxy due to an index match.
            Otherwise returns itself.
        """
        return self if self._index_node is None else self._index_node.get_self()

    def merge(self, other: "InstanceNode") -> None:
        """
            Merge another instance into this one.
        """
        if self.get_self() is not self:
            return self.get_self().merge(other)
        for attr_name, attr_node in other.get_self().attributes.items():
            for assignment in attr_node.assignments():
                self.assign_attribute(attr_name, assignment.rhs, assignment.responsible, assignment.context)

    def index_match(self, index_node: "InstanceNode") -> None:
        """
            Registers index_node as this node's index node. Propagates all attribute assignments.
        """
        if index_node is self:
            return
        if self._index_node is not None:
            raise Exception("Trying to match index on node that already has an index match. Try calling get_self() first")
        assert self.entity == index_node.get_self().entity
        assert self.bidirectional_attributes == index_node.get_self().bidirectional_attributes
        index_node.get_self().merge(self)
        self._index_node = index_node
        self.attributes = {}
        index_node.get_self().update_all_index_nodes(self._all_index_nodes)
        self._all_index_nodes = set(())

    def update_all_index_nodes(self, index_nodes: Set["InstanceNode"]) -> None:
        """
            Adds a set of index nodes to this node's set of all index matches.
        """
        if self.get_self() is not self:
            return self.get_self().update_all_index_nodes(index_nodes)
        self._all_index_nodes.update(index_nodes)

    def get_all_index_nodes(self) -> Set["InstanceNode"]:
        """
            Returns all index matches for this node.
        """
        if self.get_self() is not self:
            return self.get_self().get_all_index_nodes()
        return self._all_index_nodes

    def assign_attribute(
        self, attribute: str, node_ref: "NodeReference", responsible: "Locatable", context: "DataflowGraph",
    ) -> None:
        """
            Assigns a node to one of this instance's attributes.
        """
        if self.get_self() is not self:
            return self.get_self().assign_attribute(attribute, node_ref, responsible, context)
        attr_node: AttributeNode = self.register_attribute(attribute)
        attr_node.assign(node_ref, responsible, context)

    def register_attribute(self, attribute: str) -> AttributeNode:
        """
            Registers an attribute to this instance node. Returns the attribute's node.
        """
        if self.get_self() is not self:
            return self.get_self().register_attribute(attribute)
        if attribute not in self.attributes:
            self.attributes[attribute] = AttributeNode(self, attribute)
        return self.attributes[attribute]

    def get_attribute(self, attribute: str) -> Optional[AttributeNode]:
        """
            Returns one of this instance's attributes by name, if it exists.
        """
        if self.get_self() is not self:
            return self.get_self().get_attribute(attribute)
        try:
            return self.attributes[attribute]
        except KeyError:
            return None

    def register_bidirectional_attribute(self, this: str, other: str) -> None:
        """
            Registers a pair of bidirectional attributes. Adds assignments for the other direction where required.
        """
        if self.get_self() is not self:
            return self.get_self().register_bidirectional_attribute(this, other)
        self.bidirectional_attributes[this] = other
        if this in self.attributes:
            attr_node: AttributeNode = self.attributes[this]
            for assignment in attr_node.assignments():
                self.assign_other_direction(this, assignment.rhs, assignment.responsible, assignment.context)

    def assign_other_direction(
        self, attribute: str, node_ref: "NodeReference", responsible: "Locatable", context: "DataflowGraph"
    ) -> None:
        """
            If attribute is a bidirectional attribute, assign the other direction.
            :param attribute: this node's attribute
            :param node_ref: the node assigned to the attribute
            :param responsible: the responsible for both assignments
            :param context: the context for both assignments
        """
        if self.get_self() is not self:
            return self.get_self().assign_other_direction(attribute, node_ref, responsible, context)
        if attribute in self.bidirectional_attributes:
            node_ref.assign_attribute(self.bidirectional_attributes[attribute], self.reference(), responsible, context)
