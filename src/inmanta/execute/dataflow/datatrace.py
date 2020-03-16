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
from typing import TYPE_CHECKING, List, Iterable, Optional

from inmanta.execute.dataflow import (
    Assignment,
    AssignableNode,
    AssignableNodeReference,
    VariableNodeReference,
    DataflowGraph,
    InstanceNode,
    InstanceNodeReference,
)
from inmanta.ast import NotFoundException, Locatable
from inmanta.execute.runtime import Instance

if TYPE_CHECKING:
    pass

class DataTraceRenderer:
    def __init__(self, node: AssignableNode, render_self: bool = True) -> None:
        self.node: AssignableNode = node
        self.render_self: bool = render_self

    def _prefix_line(self, prefix: str, line: str) -> str:
        return prefix + line

    def _prefix(self, prefix: str, lines: Iterable[str]) -> List[str]:
        return [self._prefix_line(prefix, line) for line in lines]

    def _branch(self, lines: List[str], last: Optional[bool] = False) -> List[str]:
        if len(lines) == 0:
            return []
        branch_prefix: str = ('└' if last else '├') + "── "
        block_prefix: str = (' ' if last else '│') + ' ' * 3
        result: List[str] = self._prefix(branch_prefix, lines[0:1])
        result += self._prefix(block_prefix, lines[1:])
        return result

    def _shift(self, lines: Iterable[str]) -> List[str]:
        return self._prefix(' ' * 4, lines)

    def _render_implementation_context(self, context: DataflowGraph) -> List[str]:
        try:
            result: List[str] = []
            # TODO: better detection of implementation -> based on __self__ node?
            context.resolver.lookup("self")
            var_node: AssignableNodeReference = context.resolver.get_dataflow_node("self")
            if isinstance(var_node, VariableNodeReference) \
                    and len(var_node.node.instance_assignments) == 1 \
                    and isinstance(var_node.node.instance_assignments[0].responsible, Instance):
                instance_node: "InstanceNode" = var_node.node.instance_assignments[0].rhs.top_node()
                assert instance_node.responsible is not None
                # TODO: don't pass reference but node itself
                result += [
                    "IN IMPLEMENTATION WITH self = %s" % instance_node,
                    *self._shift([
                        "CONSTRUCTED BY %s" % instance_node.responsible,
                        "AT %s" % instance_node.responsible.get_location(),
                    ]),
                ]
                assert instance_node.context is not None
                result += self._shift(self._render_implementation_context(instance_node.context))
            return result
        except NotFoundException:
            return []

    def _render_instance(self, instance: InstanceNode) -> List[str]:
        result: List[str] = []
        # TODO: pretty_print, str, repr, implicit?
        # TODO: handle Optionals
        result += [
            "CONSTRUCTED BY %s" % instance.responsible.pretty_print(),
            "AT %s" % instance.responsible.get_location(),
        ]
        assert instance.context is not None
        result += self._render_implementation_context(instance.context)
        for index_node in instance.get_all_index_nodes():
            if index_node is instance:
                continue
            assert index_node.responsible is not None
            assert index_node.context is not None
            result += [
                "",
                "INDEX MATCH: %s" % index_node,
            ]

            subblock: List[str] = []
            subblock += [
                "CONSTRUCTED BY %s" % index_node.responsible,
                "AT %s" % index_node.responsible.get_location(),
            ]
            subblock += self._render_implementation_context(index_node.context)

            result += self._shift(subblock)
        return result

    def _render_assignment(self, assignment: Assignment) -> List[str]:
        responsible: "Locatable" = assignment.responsible
        return [
            "%s" % assignment.rhs,
            "SET BY %s" % responsible,
            "AT %s" % responsible.get_location(),
        ]

    def render(self) -> str:
        # TODO: SUBTREE for instance if self.node is AttributeNode
        # TODO: show Equivalences instead of individual nodes. Also show internal assignments
        result: List[str] = []
        if self.render_self:
            result.append(repr(self.node))
        assignments: List[Assignment] = list(self.node.assignments())
        nb_assignments: int = len(assignments)
        for i, assignment in enumerate(assignments):
            last: bool = i == nb_assignments - 1
            subblock: List[str] = []

            subblock += self._render_assignment(assignment)
            subblock += self._render_implementation_context(assignment.context)

            if isinstance(assignment.rhs, InstanceNodeReference):
                subblock += self._render_instance(assignment.rhs.top_node())
            if isinstance(assignment.rhs, AssignableNodeReference):
                for node in assignment.rhs.nodes():
                    subblock += DataTraceRenderer(node, render_self=False).render().split("\n")

            result += self._branch(subblock, last)
        return "\n".join(result)
