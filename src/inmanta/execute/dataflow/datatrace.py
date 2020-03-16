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
from functools import reduce
from typing import TYPE_CHECKING, List, Iterable, Optional

from inmanta.execute.dataflow import (
    Assignment,
    AssignableNode,
    AttributeNode,
    AttributeNodeReference,
    AssignableNodeReference,
    Equivalence,
    VariableNodeReference,
    DataflowGraph,
    InstanceNode,
    InstanceNodeReference,
)
from inmanta.ast import NotFoundException, Locatable
from inmanta.execute.runtime import Instance

if TYPE_CHECKING:
    pass


# TODO: make all methods static-/classmethods?
# TODO: write tests
class DataTraceRenderer:
    def __init__(self, node: AssignableNode, render_self: bool = True) -> None:
        self.node: AssignableNode = node

    def _prefix_line(self, prefix: str, line: str) -> str:
        """
            Prefixes a line.
        """
        return prefix + line

    def _prefix(self, prefix: str, lines: Iterable[str]) -> List[str]:
        """
            Prefixes lines.
        """
        return [self._prefix_line(prefix, line) for line in lines]

    def _branch(self, lines: List[str], last: Optional[bool] = False) -> List[str]:
        """
            Renders a branch in the tree.

            :param last: True iff this is the last branch on this level.
        """
        if len(lines) == 0:
            return []
        branch_prefix: str = ('└' if last else '├') + "── "
        block_prefix: str = (' ' if last else '│') + ' ' * 3
        result: List[str] = self._prefix(branch_prefix, lines[0:1])
        result += self._prefix(block_prefix, lines[1:])
        return result

    def _indent(self, lines: Iterable[str]) -> List[str]:
        """
            Indents lines.
        """
        return self._prefix(' ' * 4, lines)

    def _render_implementation_context(self, context: DataflowGraph) -> List[str]:
        """
            Renders information about the dynamic implementation context, if it exists.
        """
        try:
            context.resolver.lookup("self")
        except NotFoundException:
            return []
        result: List[str] = []
        var_node: AssignableNodeReference = context.resolver.get_dataflow_node("self")
        if isinstance(var_node, VariableNodeReference) \
                and len(var_node.node.instance_assignments) == 1 \
                and isinstance(var_node.node.instance_assignments[0].responsible, Instance):
            instance_node: InstanceNode = var_node.node.instance_assignments[0].rhs.top_node()
            result.append("IN IMPLEMENTATION WITH self = %s" % instance_node)
            result += self._indent(self._render_constructor(instance_node))
        return result

    def _render_constructor(self, instance: InstanceNode) -> List[str]:
        """
            Renders information about the construction of an instance node:
                - constructor statement
                - lexical position
                - dynamic context it lives in, if any
        """
        result: List[str] = []
        if instance.responsible is not None:
            result += [
                "CONSTRUCTED BY `%s`" % instance.responsible.pretty_print(),
                "AT %s" % instance.responsible.get_location(),
            ]
        if instance.context is not None:
            result += self._render_implementation_context(instance.context)
        return result

    def _render_instance(self, instance: InstanceNode) -> List[str]:
        """
            Renders information about an instance node:
                - construction information
                - index matches and their construction information
        """
        result: List[str] = []
        result += self._render_constructor(instance)
        for index_node in instance.get_all_index_nodes():
            if index_node is instance:
                continue
            result += [
                "",
                "INDEX MATCH: `%s`" % index_node,
            ]

            subblock: List[str] = []
            subblock += self._render_constructor(index_node)

            result += self._indent(subblock)
        return result

    def _render_assignment(self, assignment: Assignment) -> List[str]:
        """
            Renders information about an assignment in the dataflow graph.
        """
        responsible: "Locatable" = assignment.responsible
        return [
            "%s" % assignment.rhs,
            "SET BY `%s`" % responsible,
            "AT %s" % responsible.get_location(),
        ]

    def _render_equivalence(self, equivalence: Equivalence) -> List[str]:
        """
            Renders information about an equivalence unless trivial. Shows the equivalence's members and the responsible
            assignments.
        """
        if len(equivalence.nodes) > 1:
            return [
                "EQUIVALENT TO %s DUE TO STATEMENTS:" % set(equivalence.nodes),
                *self._indent([
                    "`%s` AT %s" % (assignment.responsible, assignment.responsible.get_location())
                    for assignment in equivalence.interal_assignments()
                ]),
            ]
        return []

    def _render_reference(self, node_ref: AssignableNodeReference) -> List[str]:
        """
            Renders the data trace for all nodes a reference refers to.
        """
        result: List[str] = []
        if isinstance(node_ref, AttributeNodeReference):
            result.append("SUBTREE for %s:" % node_ref.instance_var_ref)
            result += self._indent(self._render_reference(node_ref.instance_var_ref))
        for node in node_ref.nodes():
            result += DataTraceRenderer(node).render(tree_root=False).split("\n")
        return result

    def render(self, tree_root: bool = True) -> str:
        """
            Renders the data trace for an assignable node. Shows information about:
                - the node's parent instance, if it is an attribute node
                - the node's equivalence
                - assignments to the node:
                    - right hand side
                    - responsible
                    - the dynamic context it lives in, if any
            Recurses on the assignment's right hand side.

            :param tree_root: indicates whether this node is the root of the data trace tree. Behaviour for non-root nodes is
                slightly different in order to prevent output duplication.
        """
        result: List[str] = []
        if tree_root:
            result.append(repr(self.node))
            if isinstance(self.node, AttributeNode):
                result.append("SUBTREE for %s:" % self.node.instance)
                result += self._indent(self._render_instance(self.node.instance))
        result += self._render_equivalence(self.node.equivalence)
        assignments: List[Assignment] = list(chain(
            self.node.equivalence.external_assignable_assignments(),
            self.node.equivalence.instance_assignments(),
            self.node.equivalence.value_assignments(),
        ))
        nb_assignments: int = len(assignments)
        for i, assignment in enumerate(assignments):
            last: bool = i == nb_assignments - 1
            subblock: List[str] = []

            subblock += self._render_assignment(assignment)
            subblock += self._render_implementation_context(assignment.context)

            if isinstance(assignment.rhs, InstanceNodeReference):
                subblock += self._render_instance(assignment.rhs.top_node())
            if isinstance(assignment.rhs, AssignableNodeReference):
                subblock += self._render_reference(assignment.rhs)

            result += self._branch(subblock, last)
        return "\n".join(result)
