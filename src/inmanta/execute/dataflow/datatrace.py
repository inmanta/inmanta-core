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
from typing import Iterable, List, Optional

from inmanta.ast import Locatable, NotFoundException
from inmanta.ast.statements import Statement
from inmanta.execute.dataflow import (
    AssignableNode,
    AssignableNodeReference,
    Assignment,
    AttributeNodeReference,
    DataflowGraph,
    Equivalence,
    InstanceAttributeNodeReference,
    InstanceNode,
    InstanceNodeReference,
    VariableNodeReference,
)
from inmanta.execute.runtime import Instance


class DataTraceRenderer:
    """
    Renderer for the data trace of an assignable node. The data trace shows all data paths to the node as well as dynamic
    context (such as implementations) where applicable. The main entrypoint is the render() method.
    """

    @classmethod
    def render(cls, node_ref: AssignableNodeReference) -> str:
        return "\n".join(cls._render_reference(node_ref, tree_root=True)) + "\n"

    @classmethod
    def _render_reference(cls, node_ref: AssignableNodeReference, tree_root: bool = False) -> List[str]:
        """
        Renders the data trace for all nodes a reference refers to.
        """
        result: List[str] = []
        if tree_root:
            result.append(repr(node_ref))
        if isinstance(node_ref, AttributeNodeReference):
            result.append("SUBTREE for %s:" % node_ref.instance_var_ref)
            result += cls._indent(cls._render_reference(node_ref.instance_var_ref))
        if isinstance(node_ref, InstanceAttributeNodeReference):
            result.append("SUBTREE for %s:" % node_ref.instance)
            result += cls._indent(cls._render_instance(node_ref.instance))
        for node in node_ref.nodes():
            result += cls._render_node(node)
        return result

    @classmethod
    def _render_node(cls, node: AssignableNode) -> List[str]:
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
        result += cls._render_equivalence(node.equivalence)
        assignments: List[Assignment] = list(
            chain(
                node.equivalence.external_assignable_assignments(),
                node.equivalence.instance_assignments(),
                node.equivalence.value_assignments(),
            )
        )
        nb_assignments: int = len(assignments)
        for i, assignment in enumerate(assignments):
            last: bool = i == nb_assignments - 1
            subblock: List[str] = []

            subblock += cls._render_assignment(assignment)
            subblock += cls._render_implementation_context(assignment.context)

            if isinstance(assignment.rhs, InstanceNodeReference):
                subblock += cls._render_instance(assignment.rhs.top_node())
            if isinstance(assignment.rhs, AssignableNodeReference):
                subblock += cls._render_reference(assignment.rhs)

            result += cls._branch(subblock, last)
        return result

    @classmethod
    def _prefix_line(cls, prefix: str, line: str) -> str:
        """
        Prefixes a line.
        """
        if line == "":
            return prefix.rstrip()
        return prefix + line

    @classmethod
    def _prefix(cls, prefix: str, lines: Iterable[str]) -> List[str]:
        """
        Prefixes lines.
        """
        return [cls._prefix_line(prefix, line) for line in lines]

    @classmethod
    def _branch(cls, lines: List[str], last: Optional[bool] = False) -> List[str]:
        """
        Renders a branch in the tree.

        :param last: True iff this is the last branch on this level.
        """
        if len(lines) == 0:
            return []
        branch_prefix: str = ("└" if last else "├") + "── "
        block_prefix: str = (" " if last else "│") + " " * 3
        result: List[str] = cls._prefix(branch_prefix, lines[0:1])
        result += cls._prefix(block_prefix, lines[1:])
        return result

    @classmethod
    def _indent(cls, lines: Iterable[str]) -> List[str]:
        """
        Indents lines.
        """
        return cls._prefix(" " * 4, lines)

    @classmethod
    def _render_implementation_context(cls, context: DataflowGraph) -> List[str]:
        """
        Renders information about the dynamic implementation context, if it exists.
        """
        # roundabout way to detect encapsulating context, may lead to false positives, see #1937
        try:
            context.resolver.lookup("self")
        except NotFoundException:
            return []
        result: List[str] = []
        var_node: AssignableNodeReference = context.resolver.get_dataflow_node("self")
        if (
            isinstance(var_node, VariableNodeReference)
            and len(var_node.node.instance_assignments) == 1
            and isinstance(var_node.node.instance_assignments[0].responsible, Instance)
        ):
            instance_node: InstanceNode = var_node.node.instance_assignments[0].rhs.top_node()
            result.append("IN IMPLEMENTATION WITH self = %s" % instance_node)
            result += cls._indent(cls._render_constructor(instance_node))
        return result

    @classmethod
    def _render_constructor(cls, instance: InstanceNode) -> List[str]:
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
            result += cls._render_implementation_context(instance.context)
        return result

    @classmethod
    def _render_instance(cls, instance: InstanceNode) -> List[str]:
        """
        Renders information about an instance node:
            - construction information
            - index matches and their construction information
        """
        result: List[str] = []
        result += cls._render_constructor(instance)
        for index_node in instance.get_all_index_nodes():
            if index_node is instance:
                continue
            result += [
                "",
                "INDEX MATCH: `%s`" % index_node,
            ]

            subblock: List[str] = []
            subblock += cls._render_constructor(index_node)

            result += cls._indent(subblock)
        return result

    @classmethod
    def _render_assignment(cls, assignment: Assignment) -> List[str]:
        """
        Renders information about an assignment in the dataflow graph.
        """
        responsible: "Locatable" = assignment.responsible
        return [
            "%s" % assignment.rhs,
            "SET BY `%s`" % (responsible.pretty_print() if isinstance(responsible, Statement) else responsible),
            "AT %s" % responsible.get_location(),
        ]

    @classmethod
    def _render_equivalence(cls, equivalence: Equivalence) -> List[str]:
        """
        Renders information about an equivalence unless trivial. Shows the equivalence's members and the responsible
        assignments.
        """
        if len(equivalence.nodes) > 1:
            # sort output for consistency
            return [
                "EQUIVALENT TO {%s} DUE TO STATEMENTS:" % ", ".join(sorted(repr(n) for n in equivalence.nodes)),
                *cls._indent(
                    [
                        "`%s` AT %s" % resp_loc
                        for resp_loc in sorted(
                            (
                                (
                                    assignment.responsible.pretty_print()
                                    if isinstance(assignment.responsible, Statement)
                                    else str(assignment.responsible),
                                    str(assignment.responsible.get_location()),
                                )
                                for assignment in equivalence.interal_assignments()
                            ),
                            key=lambda t: tuple(reversed(t)),
                        )
                    ]
                ),
            ]
        return []
