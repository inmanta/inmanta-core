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

from typing import FrozenSet, Iterable, List, Set

from inmanta.execute.dataflow import AssignableNode, AttributeNode, AttributeNodeReference, InstanceNode


class RootCauseAnalyzer:
    """
        Analyzes the root causes among a collection of attribute nodes. The main entrypoint for this class is the
        root_causes method.
    """

    def __init__(self, nodes: Iterable[AttributeNode]) -> None:
        self.nodes: FrozenSet[AttributeNode] = frozenset(nodes)

    def root_causes(self) -> Set[AttributeNode]:
        """
            Returns the root causes from this instances' set of attribute nodes. An attribute node c
            is defined as the cause for an other attribute node n iff c being unset leads to n
            being unset.
            Formally, the relation is_cause(c, x) is defined by three rules:
                1. is_cause(c, x) <- c in x.leaves()
                2. is_cause(c, x) <- exists i: is_index_attr(x, i) and is_cause(c, x.i)
                3. is_cause(c, x) <- exists a [AttributeNode]: refers_to(x, a) and is_cause(c, a.instance)
                    where
                        refers_to(x, y) <- `x = y` in graph
                        refers_to(x, z) <- exists y: refers_to(x, y) and refers_to(y, z)
                        refers_to(x, u) <- refers_to(x, u.v)

                        example: x = u.v.w.n
                            -> refers_to(x, u.v.w.n)
                                and refers_to(x, u.v.w)
                                and refers_to(x, u.v)
                                and refers_to(x, u)

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
                            <-(3)- refers_to(x.n, V.n) and is_cause(c.i, V)
                            <-(2)- is_index_attr(V, i) and is_cause(c.i, V.i)
                            <-(1)- c.i in V.i.leaves()
                            <- true
            These three rules are implemented as propagation steps by
            _assignment_step, _child_attribute_step and _parent_instance_step respectively.
        """
        to_do: Set[AttributeNode] = set(self.nodes)
        causes: Set[AttributeNode] = set(())
        for node in self.nodes:
            to_do.remove(node)
            if not self._caused_by(node, causes.union(to_do)):
                causes.add(node)
        return causes

    def _caused_by(self, node: AttributeNode, pos_causes: Set[AttributeNode]) -> bool:
        """
            Returns True iff node being unset is caused by any of pos_causes being unset.
        """
        checked: Set[AssignableNode] = set(())
        nodes: List[AssignableNode] = [node]

        def process_step(step_result: FrozenSet[AssignableNode]) -> None:
            new: Set[AssignableNode] = {n for n in step_result if n not in checked}
            nodes.extend(new)
            checked.update(new)

        while nodes:
            n: AssignableNode = nodes.pop()
            if isinstance(n, AttributeNode) and n in pos_causes:
                return True
            # TODO: skip node if it has a bound ResultVariable with a value
            process_step(self._assignment_step(n))
            process_step(self._parent_instance_step(n))
            process_step(self._child_attribute_step(n))
        return False

    def _parent_instance_step(self, node: AssignableNode) -> FrozenSet[AssignableNode]:
        return frozenset(
            node
            for assignment in node.assignable_assignments
            if isinstance(assignment.rhs, AttributeNodeReference)
            for node in assignment.rhs.instance_var_ref.nodes()
        )

    def _assignment_step(self, node: AssignableNode) -> FrozenSet[AssignableNode]:
        return frozenset(node for assignment in node.assignable_assignments for node in assignment.rhs.nodes())

    def _child_attribute_step(self, node: AssignableNode) -> FrozenSet[AssignableNode]:
        return frozenset(
            node
            for instance_assignment in node.instance_assignments
            for node in self._index_attributes(instance_assignment.rhs.node())
        )

    def _index_attributes(self, instance: InstanceNode) -> List[AttributeNode]:
        # TODO: return only index attributes. Investigating any attribute works just as well but is less efficient.
        return list(instance.attributes.values())
