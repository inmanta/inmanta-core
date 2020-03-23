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

from typing import Iterable, Set

from inmanta.execute.dataflow import AttributeNode, InstanceNode


class RootCauseAnalyzer:
    """
        Analyzes the root causes among a collection of attribute nodes. An attribute node c
        is defined as the cause for an other attribute node n iff c being unset leads to n
        being unset.
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

    def __init__(self, nodes: Iterable[AttributeNode]) -> None:
        self.nodes: Set[AttributeNode] = set(nodes)

    def root_causes(self) -> Set[AttributeNode]:
        raise NotImplementedError()

    def is_cause(self, cause: AttributeNode, node: AttributeNode) -> None:
        raise NotImplementedError()

    def _is_cause_leaves(self, cause: AttributeNode, node: AttributeNode) -> None:
        raise NotImplementedError()

    def _is_cause_any_attribute(self, cause: AttributeNode, instance: InstanceNode) -> None:
        raise NotImplementedError()

    def _is_cause_instance(self, cause: AttributeNode, node: AttributeNode) -> None:
        raise NotImplementedError()
