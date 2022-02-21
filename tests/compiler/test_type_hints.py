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
import pytest

from inmanta.execute.scheduler import CycleInTypeHintsError, EntityRelationship, TypePrecedenceGraph


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
    a_one = EntityRelationship(fq_entity_name="A", relationship_name="one")
    a_two = EntityRelationship(fq_entity_name="A", relationship_name="two")
    b_one = EntityRelationship(fq_entity_name="B", relationship_name="one")
    b_two = EntityRelationship(fq_entity_name="B", relationship_name="two")

    graph = TypePrecedenceGraph()
    for _ in range(1 + int(set_type_hints_twice)):
        graph.add_precedence_rule(first_type=a_one, then_type=a_two)
        graph.add_precedence_rule(first_type=a_one, then_type=b_one)
        graph.add_precedence_rule(first_type=a_one, then_type=b_two)
        graph.add_precedence_rule(first_type=a_two, then_type=b_one)
        graph.add_precedence_rule(first_type=a_two, then_type=b_two)
        graph.add_precedence_rule(first_type=b_one, then_type=b_two)

    assert graph.get_freeze_order() == [a_one, a_two, b_one, b_two]


def test_type_precedence_graph_two_valid_freeze_orders() -> None:
    r"""
    A.one  --> B.one
      |
     \/
    B.two
    """
    a_one = EntityRelationship(fq_entity_name="A", relationship_name="one")
    b_one = EntityRelationship(fq_entity_name="B", relationship_name="one")
    b_two = EntityRelationship(fq_entity_name="B", relationship_name="two")

    graph = TypePrecedenceGraph()
    graph.add_precedence_rule(first_type=a_one, then_type=b_one)
    graph.add_precedence_rule(first_type=a_one, then_type=b_two)

    freeze_order = graph.get_freeze_order()

    assert freeze_order == [a_one, b_one, b_two] or freeze_order == [a_one, b_two, b_one]


def test_type_precedence_graph_cycle_in_graph() -> None:
    r"""
        A.one --> B.one --> C.one
          /\    /            /\
          |    /             |
          |  |/_             |
        B.two ----------------
    """
    a_one = EntityRelationship(fq_entity_name="A", relationship_name="one")
    b_one = EntityRelationship(fq_entity_name="B", relationship_name="one")
    b_two = EntityRelationship(fq_entity_name="B", relationship_name="two")
    c_one = EntityRelationship(fq_entity_name="C", relationship_name="one")

    graph = TypePrecedenceGraph()
    graph.add_precedence_rule(first_type=a_one, then_type=b_one)
    graph.add_precedence_rule(first_type=b_one, then_type=b_two)
    graph.add_precedence_rule(first_type=b_two, then_type=a_one)
    graph.add_precedence_rule(first_type=b_one, then_type=c_one)
    graph.add_precedence_rule(first_type=b_two, then_type=c_one)

    with pytest.raises(CycleInTypeHintsError, match="Cycle in type hints"):
        graph.get_freeze_order()
