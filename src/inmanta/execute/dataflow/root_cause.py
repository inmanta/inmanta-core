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
from typing import FrozenSet, Iterable, Set

from inmanta.execute.dataflow import AssignableNode, AttributeNode, AttributeNodeReference


class UnsetRootCauseAnalyzer:
    """
    Analyzes the root causes for attributes being unset among a collection of attribute nodes.
    The main entrypoint for this class is the root_causes method.
    """

    def __init__(self, nodes: Iterable[AttributeNode]) -> None:
        self.nodes: FrozenSet[AttributeNode] = frozenset(nodes)

    def root_causes(self) -> Set[AttributeNode]:
        """
        Returns the root causes from this instances' set of attribute nodes. An attribute node c
        is defined as the cause for an other attribute node n iff c being unset leads to n
        being unset.
        Formally, the relation is_cause(c, x) is defined by three rules:
            1. is_cause(c, x) <- c in `x = c` in graph
                (If `x = c` then c is responsible for x receiving a value)
            2. is_cause(c, x) <- exists y: is_cause(c, y) and is_cause(y, x)
                (Cause is transitive)
            3. is_cause(c, x) <- exists i : is_index_attr(x, i) and is_cause(c, x.i)
                (If an index attribute of x is unset this blocks execution. If c is the cause for the index
                    value being unset, it is the cause for x being unset)
            4. is_cause(c, x) <- exists y, z : `x = y.z` in graph and is_cause(c, y)
                (If x refers to y.z but y is unset, this blocks execution. If c is the cause for y being unset,
                    it is the cause for x being unset)

            example (entity definitions omitted for clarity):
                model:
                    index V(i)

                    c = C()
                    u = U()
                    x = X()

                    u.v = V(n = 42, i = c.i)
                    x.n = u.v.n

                root_cause_analysis (capital letters refer to the single instance of that entity, not the entity itself):
                    is_cause(c.i, x.n)
                        <-(4)- `x.n = u.v.n` in graph and is_cause(c.i, u.v)
                        <----- is_cause(c.i, u.v)
                        <-(2)- is_cause(V, u.v) and is_cause(c.i, V)
                        <-(1)- `u.v = V` in graph and is_cause(c.i, V)
                        <----- is_cause(c.i, V)
                        <-(3)- is_index_attr(V, i) and is_cause(c.i, V.i)
                        <----- is_cause(c.i, V.i)
                        <-(1)- `V.i = c.i` in graph
                        <----- true
        Rules 2 to 4 are implemented as propagation steps by
        _assignment_step, _child_attribute_step and _parent_instance_step respectively.
        """
        # Actual found roots
        roots: Set[AttributeNode] = set(())
        # Actual roots that we have to filter out
        ignore_roots: Set[AssignableNode] = set(())
        # Any node of which the roots are already in the roots set
        seen: Set[AssignableNode] = set(())

        def has_root(node: AssignableNode) -> bool:
            """
            Add underlying roots to roots

            :return: is there a valid root below this node
            """

            if node in seen:
                # Already processed, roots are already in roots
                # Unless is is an ignored_root
                return node not in ignore_roots

            if node.value_assignments:
                # Has a value, never has a root cause
                return False

            # Find any root for this equivalence
            n_has_root = any(
                (
                    has_root(subnode)
                    for peernode in node.equivalence.nodes
                    for subnode in chain(
                        self._assignment_step(peernode),
                        self._parent_instance_step(peernode),
                        self._child_attribute_step(peernode),
                    )
                    if subnode not in node.equivalence.nodes
                )
            )

            # This equivalence is done
            seen.update(node.equivalence.nodes)

            n_is_root = not n_has_root

            if n_is_root:
                # See if any of the equivalent nodes are a valid root
                anyroots = self.nodes.intersection(node.equivalence.nodes)
                if not anyroots:
                    # it is root, but not one we are looking for, ignore it
                    ignore_roots.update(node.equivalence.nodes)
                    return False
                else:
                    # Add valid roots
                    roots.update(anyroots)

            # We are a root or have seen an underlying root
            return True

        for node in self.nodes:
            has_root(node)

        return roots

    def _assignment_step(self, node: AssignableNode) -> FrozenSet[AssignableNode]:
        """
        Performs one propagation step according to rule 2:
            is_cause(c, x) <- exists y: is_cause(c, y) and is_cause(y, x)
            (Cause is transitive)
        """
        return frozenset(node for assignment in node.assignable_assignments for node in assignment.rhs.nodes())

    def _child_attribute_step(self, node: AssignableNode) -> FrozenSet[AssignableNode]:
        """
        Performs one propagation step according to rule 3:
            is_cause(c, x) <- exists i : is_index_attr(x, i) and is_cause(c, x.i)
            (If an index attribute of x is unset this blocks execution. If c is the cause for the index
                value being unset, it is the cause for x being unset)
        """
        return frozenset(
            index_attribute
            for instance_assignment in node.instance_assignments
            for index_attribute in instance_assignment.rhs.top_node().get_index_attributes()
        )

    def _parent_instance_step(self, node: AssignableNode) -> FrozenSet[AssignableNode]:
        """
        Performs one propagation step according to rule 4:
            is_cause(c, x) <- exists y, z : `x = y.z` in graph and is_cause(c, y)
            (If x refers to y.z but y is unset, this blocks execution. If c is the cause for y being unset,
                it is the cause for x being unset)
        """
        return frozenset(
            node
            for assignment in node.assignable_assignments
            if isinstance(assignment.rhs, AttributeNodeReference)
            for node in assignment.rhs.instance_var_ref.nodes()
        )
