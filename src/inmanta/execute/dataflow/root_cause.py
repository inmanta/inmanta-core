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
from typing import Iterable, Iterator, List, Optional, Set

from inmanta.execute.dataflow import AssignableNodeReference, AttributeNode, AttributeNodeReference, InstanceNode


class RootCauseAnalyzer:
    """
        Analyzes the root causes among a collection of attribute nodes. The main entrypoint for this class is the
        root_causes method.
    """

    def __init__(self, nodes: Iterable[AttributeNode]) -> None:
        self.nodes: Set[AttributeNode] = set(nodes)

    def root_causes(self) -> Set[AttributeNode]:
        """
            Returns the root causes from this instances' set of attribute nodes. An attribute node c
            is defined as the cause for an other attribute node n iff c being unset leads to n
            being unset. For a formal definition, see is_cause.
        """
        def caused_by(node: AttributeNode, others: Set[AttributeNode]) -> bool:
            return any(self.is_cause(other, node) for other in others)

        return set(node for node in self.nodes if not caused_by(node, self.nodes.difference({node})))

    def is_cause(self, cause: AttributeNode, node: AttributeNode) -> bool:
        """
            Returns True iff cause is a cause for node.
            Formally, is_cause(c, x) is defined by three rules:
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
            These three rules are implemented by _is_cause_leaves, _is_cause_any_attribute and _is_cause_instance respectively.
        """
        return self._is_cause_acc(set(()), cause, node)

    def _is_cause_acc(self, acc: Set[InstanceNode], cause: AttributeNode, node: AttributeNode) -> bool:
        return (
            self._is_cause_leaves(cause, node)
            or self._is_cause_any_attribute(acc, cause, self._instance_node(node))
            or self._is_cause_instance(acc, cause, node)
        )

    def _is_cause_leaves(self, cause: AttributeNode, node: AttributeNode) -> bool:
        """
            rule 1: is_cause(c, x) <- c in x.leaves()
        """
        return cause in chain.from_iterable(leaf.nodes() for leaf in node.leaves())

    def _is_cause_any_attribute(self, acc: Set[InstanceNode], cause: AttributeNode, instance: Optional[InstanceNode]) -> bool:
        """
            rule 2: is_cause(c, x) <- exists i: is_index_attr(x, i) and is_cause(c, x.i)
        """
        if instance is None or instance in acc:
            return False
        return any(
            self._is_cause_acc(acc.union({instance}), cause, index_attr) for index_attr in self._index_attributes(instance)
        )

    def _is_cause_instance(self, acc: Set[InstanceNode], cause: AttributeNode, node: AttributeNode) -> bool:
        """
            rule 3: is_cause(c, x) <- exists a [AttributeNode]: refers_to(x, a) and is_cause(c, a.instance)
        """
        return any(self._is_cause_any_attribute(acc, cause, attr.instance) for attr in self._referred_attrs(set(()), node))

    def _instance_node(self, node: AttributeNode) -> Optional[InstanceNode]:
        for leaf in node.leaves():
            for leaf_node in leaf.nodes():
                if len(leaf_node.instance_assignments) > 0:
                    return leaf_node.instance_assignments[0].rhs.top_node()
        return None

    def _index_attributes(self, instance: InstanceNode) -> List[AttributeNode]:
        # TODO: return only index attributes. Investigating any attribute works just as well but is less efficient.
        return list(instance.attributes.values())

    def _referred_attrs(self, acc: Set[AttributeNode], node: AttributeNode) -> Iterator[AttributeNode]:
        if node in acc:
            return iter(())
        for assignment in node.assignable_assignments:
            loop_ref: AssignableNodeReference = assignment.rhs
            while isinstance(loop_ref, AttributeNodeReference):
                for n in loop_ref.nodes():
                    yield n
                    yield from self._referred_attrs(acc.union({node}), n)
                loop_ref = loop_ref.instance_var_ref
