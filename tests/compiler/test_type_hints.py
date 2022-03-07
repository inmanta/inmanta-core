"""
    Copyright 2022 Inmanta

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
from typing import Set

import pytest

from inmanta.ast.attribute import RelationAttribute
from inmanta.execute.scheduler import CycleInRelationPrecedencePolicyError, RelationPrecedenceGraph


class DummyRelationAttribute(RelationAttribute):
    """
    A dummy RelationAttribute to prevent the need to instantiate a full
    normal RelationAttribute object.
    """

    def __init__(self, fq_attr_name: str) -> None:
        self.fq_attr_name = fq_attr_name
        self.type_hints: Set[RelationAttribute] = set()

    def __hash__(self) -> "int":
        return hash(self.fq_attr_name)

    def __str__(self):
        return self.fq_attr_name


@pytest.mark.parametrize("set_type_hints_twice", [True, False])
def test_type_precedence_graph_one_freeze_order(set_type_hints_twice) -> None:
    r"""
    A.one --> B.one
      |   \  /\   |
      |    \/     |
      |   / \     |
      | /    \    |
     \//      _\ \/
    A.two -->  B.two
    """
    a_one = DummyRelationAttribute(fq_attr_name="A.one")
    a_two = DummyRelationAttribute(fq_attr_name="A.two")
    b_one = DummyRelationAttribute(fq_attr_name="B.one")
    b_two = DummyRelationAttribute(fq_attr_name="B.two")

    graph = RelationPrecedenceGraph()
    for _ in range(1 + int(set_type_hints_twice)):
        graph.add_precedence_rule(first_attribute=a_one, then_attribute=a_two)
        graph.add_precedence_rule(first_attribute=a_one, then_attribute=b_one)
        graph.add_precedence_rule(first_attribute=a_one, then_attribute=b_two)
        graph.add_precedence_rule(first_attribute=a_two, then_attribute=b_one)
        graph.add_precedence_rule(first_attribute=a_two, then_attribute=b_two)
        graph.add_precedence_rule(first_attribute=b_one, then_attribute=b_two)

    assert graph.get_freeze_order() == [a_one, a_two, b_one, b_two]


def test_type_precedence_graph_two_valid_freeze_orders() -> None:
    r"""
    A.one  --> B.one
      |
     \/
    B.two
    """
    a_one = DummyRelationAttribute(fq_attr_name="A.one")
    b_one = DummyRelationAttribute(fq_attr_name="B.one")
    b_two = DummyRelationAttribute(fq_attr_name="B.two")

    graph = RelationPrecedenceGraph()
    graph.add_precedence_rule(first_attribute=a_one, then_attribute=b_one)
    graph.add_precedence_rule(first_attribute=a_one, then_attribute=b_two)

    freeze_order = graph.get_freeze_order()

    assert freeze_order == [a_one, b_one, b_two] or freeze_order == [a_one, b_two, b_one]


def test_type_precedence_graph_disjunct_graphs() -> None:
    r"""
    A.one  --> B.one   |     C.one ---> D.one
    """
    a_one = DummyRelationAttribute(fq_attr_name="A.one")
    b_one = DummyRelationAttribute(fq_attr_name="B.one")
    c_one = DummyRelationAttribute(fq_attr_name="C.one")
    d_one = DummyRelationAttribute(fq_attr_name="D.one")

    graph = RelationPrecedenceGraph()
    graph.add_precedence_rule(first_attribute=a_one, then_attribute=b_one)
    graph.add_precedence_rule(first_attribute=c_one, then_attribute=d_one)

    freeze_order = graph.get_freeze_order()

    valid_freeze_orders = [
        [a_one, b_one, c_one, d_one],
        [a_one, c_one, b_one, d_one],
        [a_one, c_one, d_one, b_one],
        [c_one, d_one, a_one, b_one],
        [c_one, a_one, b_one, d_one],
        [c_one, a_one, d_one, b_one],
    ]

    assert freeze_order in valid_freeze_orders


def test_type_precedence_graph_cycle_in_graph_without_root_nodes() -> None:
    r"""
        A.one --> B.one --> C.one
          /\    /            /\
          |    /             |
          |  |/_             |
        B.two ----------------
    """
    a_one = DummyRelationAttribute(fq_attr_name="A.one")
    b_one = DummyRelationAttribute(fq_attr_name="B.one")
    b_two = DummyRelationAttribute(fq_attr_name="B.two")
    c_one = DummyRelationAttribute(fq_attr_name="C.one")

    graph = RelationPrecedenceGraph()
    graph.add_precedence_rule(first_attribute=a_one, then_attribute=b_one)
    graph.add_precedence_rule(first_attribute=b_one, then_attribute=b_two)
    graph.add_precedence_rule(first_attribute=b_two, then_attribute=a_one)
    graph.add_precedence_rule(first_attribute=b_one, then_attribute=c_one)
    graph.add_precedence_rule(first_attribute=b_two, then_attribute=c_one)

    with pytest.raises(CycleInRelationPrecedencePolicyError, match="A cycle exists in the relation precedence policy"):
        graph.get_freeze_order()


def test_type_precedence_graph_cycle_in_graph_with_root_nodes() -> None:
    r"""
        A.one --> B.one --> C.one
                     /\    /
                     |    /
                     |  |/_
                    C.two
    """
    a_one = DummyRelationAttribute(fq_attr_name="A.one")
    b_one = DummyRelationAttribute(fq_attr_name="B.one")
    c_one = DummyRelationAttribute(fq_attr_name="C.one")
    c_two = DummyRelationAttribute(fq_attr_name="C.two")

    graph = RelationPrecedenceGraph()
    graph.add_precedence_rule(first_attribute=a_one, then_attribute=b_one)
    graph.add_precedence_rule(first_attribute=b_one, then_attribute=c_one)
    graph.add_precedence_rule(first_attribute=c_one, then_attribute=c_two)
    graph.add_precedence_rule(first_attribute=c_two, then_attribute=b_one)

    with pytest.raises(CycleInRelationPrecedencePolicyError, match="A cycle exists in the relation precedence policy"):
        graph.get_freeze_order()


def test_type_precedence_graph_cycle_disjunct_graphs() -> None:
    r"""
        A.one --> B.one --> C.one     |     D.one --> E.one
                    |                 |           <--
                    |                 |
                   \/                 |
                  C.two               |
    """
    a_one = DummyRelationAttribute(fq_attr_name="A.one")
    b_one = DummyRelationAttribute(fq_attr_name="B.one")
    c_one = DummyRelationAttribute(fq_attr_name="C.one")
    c_two = DummyRelationAttribute(fq_attr_name="C.two")
    d_one = DummyRelationAttribute(fq_attr_name="D_one")
    e_one = DummyRelationAttribute(fq_attr_name="E.one")

    graph = RelationPrecedenceGraph()
    graph.add_precedence_rule(first_attribute=a_one, then_attribute=b_one)
    graph.add_precedence_rule(first_attribute=b_one, then_attribute=c_one)
    graph.add_precedence_rule(first_attribute=b_one, then_attribute=c_two)

    graph.add_precedence_rule(first_attribute=d_one, then_attribute=e_one)
    graph.add_precedence_rule(first_attribute=e_one, then_attribute=d_one)

    with pytest.raises(CycleInRelationPrecedencePolicyError, match="A cycle exists in the relation precedence policy"):
        graph.get_freeze_order()
