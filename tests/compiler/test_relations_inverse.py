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

import contextlib
import textwrap

import pytest

from inmanta import compiler
from inmanta.ast.statements.generator import IndexAttributeMissingInConstructorException


def test_relations_implicit_inverse_simple(snippetcompiler) -> None:
    """
    Verify that the basics of implicit inverse relations on index attributes work: if an index attribute is missing in a
    constructor call attempt to derive it from the left hand side.
    """
    snippetcompiler.setup_for_snippet(
        """
        entity A: end
        entity B: end
        implement A using std::none
        implement B using std::none

        A.b [0:1] -- B.a [1]

        index B(a)

        # nested constructors
        a1 = A(b=B())
        # attribute assignment
        a2 = A()
        a2.b = B()

        assert = true
        assert = a1.b.a == a1
        assert = a2.b.a == a2
        """
    )
    compiler.do_compile()


def test_relations_implicit_inverse_composite_index(snippetcompiler) -> None:
    """
    Verify that implicit inverse relations on index attributes work for an index consisting of multiple fields.
    """
    snippetcompiler.setup_for_snippet(
        """
        entity A: end
        entity B:
            int id
        end
        implement A using std::none
        implement B using std::none

        A.b [0:1] -- B.a [1]

        index B(id, a)

        # nested constructors
        a1 = A(b=B(id=0))
        # attribute assignment
        a2 = A()
        a2.b = B(id=0)

        assert = true
        assert = a1.b.a == a1
        assert = a2.b.a == a2
        """
    )
    compiler.do_compile()


def test_relations_implicit_inverse_composite_rhs(snippetcompiler) -> None:
    """
    Verify that implicit inverse relations on index attributes work if the constructor appears as an element in a composite
    statement, e.g. a list or a conditional expression.
    """
    snippetcompiler.setup_for_snippet(
        """
        entity A: end
        entity B:
            int id = 0
        end
        implement A using std::none
        implement B using std::none

        A.b [0:] -- B.a [1]

        # not very realistic model, but still a good case to check
        index B(id, a)

        # nested constructors
        a1 = A(b=[B(id=0), true ? B(id=1) : B(id=2)])
        # attribute assignment
        a2 = A()
        a2.b = false ? [B(id=10), B(id=20)] : [B(id=30), B(id=40), B(id=50)]

        assert = true
        assert = a1.b == [B[id=0, a=a1], B[id=1, a=a1]]
        assert = a2.b == [B[id=30, a=a2], B[id=40, a=a2], B[id=50, a=a2]]
        """
    )
    compiler.do_compile()


@pytest.mark.parametrize("double_index", (True, False))
def test_relations_implicit_inverse_left_index(snippetcompiler, double_index: bool) -> None:
    """
    Verify that the implementation for implicit inverse relations on index attributes does not choke on an index on the left
    hand side: a naive implementation might have this behavior.

    :param double_index: Iff True, include an index on the right side as well. This is expected to fail with a meaningful error
        message.
    """
    snippetcompiler.setup_for_snippet(
        """
        entity A: end
        entity B: end
        implement A using std::none
        implement B using std::none

        A.b [1] -- B.a [1]

        index A(b)
        %s

        A(b=B())
        """
        % ("index B(a)" if double_index else "")
    )
    with (
        pytest.raises(
            IndexAttributeMissingInConstructorException,
            match="Missing relation 'a'. The relation __config__::B.a is part of an index.",
        )
        if double_index
        else contextlib.nullcontext()
    ):
        compiler.do_compile()


def test_relation_implicit_inverse_deeply_nested_constructors(snippetcompiler) -> None:
    """
    Verify that implicit inverse relations on index attributes for deeply nested constructors work as expected.
    """
    snippetcompiler.setup_for_snippet(
        """
        entity A: end
        entity B: end
        entity C: end
        entity D: end
        implement A using std::none
        implement B using std::none
        implement C using std::none
        implement D using std::none

        A.b [1] -- B.a [1]
        B.c [1] -- C.b [1]
        C.d [1] -- D.c [1]

        index B(a)
        index C(b)
        index D(c)

        a = A(b=B(c=C(d=D())))

        assert = true
        assert = a.b.a == a
        assert = a.b.c.b == a.b
        assert = a.b.c.d.c == a.b.c
        """
    )
    compiler.do_compile()


def test_relation_implicit_inverse_nested_constructors_same_entity(snippetcompiler) -> None:
    """
    Verify that implicit inverse relations on index attributes for deeply nested constructors for the same entity type work as
    expected and that inverse relations are set to the immediate parent in the constructor tree.
    """
    snippetcompiler.setup_for_snippet(
        """
        entity LHS:
        end
        entity RHS extends LHS:
        end

        LHS.right [0:1] -- RHS.left [1]
        index RHS(left)

        implement LHS using std::none
        implement RHS using std::none

        x1 = LHS(
            right=RHS(    # x2: inverse relation x2.left should be set to x1
                right=RHS(    # x3: inverse relation x3.left should be set to x2
                    right=RHS()    # x4: inverse relation x4.left should be set to x3
                )
            )
        )

        assert = true
        assert = x1.right.left == x1
        assert = x1.right.right.left == x1.right
        assert = x1.right.right.right.left == x1.right.right
        assert = x1 != x1.right
        assert = x1.right != x1.right.right
        """
    )
    compiler.do_compile()


def test_relation_implicit_inverse_kwargs_conflict(snippetcompiler) -> None:
    """
    Verify that implicit inverse relations on index attributes don't hide conflicts with explicit assignments through kwargs.
    """
    snippetcompiler.setup_for_error(
        """
        entity A: end
        entity B: end
        implement A using std::none
        implement B using std::none

        A.b [0:1] -- B.a [1]

        index B(a)

        # nested constructors
        b_kwargs = {"a": A()}
        a1 = A(b=B(**b_kwargs))

        assert = true
        assert = a1.b.a == a1
        """,
        textwrap.dedent(
            """
            Could not set attribute `a` on instance `__config__::B (instantiated at {dir}/main.cf:13)` (reported in __config__::B (instantiated at {dir}/main.cf:13) ({dir}/main.cf:13))
            caused by:
              value set twice:
            \told value: __config__::A (instantiated at {dir}/main.cf:12)
            \t\tset at {dir}/main.cf:13
            \tnew value: __config__::A (instantiated at {dir}/main.cf:13)
            \t\tset at {dir}/main.cf:13
             (reported in Construct(A) ({dir}/main.cf:13))
            """.lstrip(  # noqa: E501
                "\n"
            ).rstrip()
        ),
    )


def test_relation_implicit_inverse_on_plain_attribute(snippetcompiler) -> None:
    """
    Verify that implicit inverse relations on index attributes don't hide errors due to relation assignment to a plain attribute
    """
    snippetcompiler.setup_for_error(
        """
        entity A:
            int b
        end
        entity B: end
        implement A using std::none
        implement B using std::none

        B.a [1] -- A
        index B(a)

        A(b=B())
        """,
        "Can not assign a value of type B to a variable of type int (reported in Construct(B) ({dir}/main.cf:12))",
    )


def test_relation_implicit_inverse_on_different_entity_type(snippetcompiler) -> None:
    """
    Verify that implicit inverse relations on index attributes don't hide errors due to relation assignment to a wrong
    entity type.
    """
    snippetcompiler.setup_for_error(
        """
        entity A: end
        entity B: end
        entity C: end
        implement A using std::none
        implement B using std::none
        implement C using std::none

        A.b [0:1] -- C.a [1]
        B.a [1] -- A
        index B(a)

        A(b=B())
        """,
        "Can not assign a value of type __config__::B to a variable "
        "of type __config__::C (reported in Construct(B) ({dir}/main.cf:13))",
    )


def test_relation_implicit_inverse_inheritance(snippetcompiler) -> None:
    """
    Verify that implicit inverse relations on index attributes work as expected when combined with inheritance: relations and
    indexes defined on parent entities should allow implicit inverses on their children.
    """
    snippetcompiler.setup_for_snippet(
        """
        entity AABC: end
        entity BABC: end
        entity ChildA extends AABC: end
        entity ChildB extends BABC: end
        implement ChildA using std::none
        implement ChildB using std::none

        # relation and index on ABC
        AABC.b [0:1] -- BABC.a [1]

        index BABC(a)

        # nested constructors
        a1 = ChildA(b=ChildB())
        # attribute assignment
        a2 = ChildA()
        a2.b = ChildB()

        assert = true
        assert = a1.b.a == a1
        assert = a2.b.a == a2
        """
    )
    compiler.do_compile()
