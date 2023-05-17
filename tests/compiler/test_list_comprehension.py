"""
    Copyright 2023 Inmanta

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
import textwrap

import pytest

from inmanta import compiler


def test_list_comprehension_basic(snippetcompiler) -> None:
    """
    Verify the basic workings of the list comprehension expression.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            base = [1, 2, 3, 4, 5]

            l1 = [x for x in base]
            l2 = ["x={{x}}" for x in base]
            l3 = [x > 2 ? x : 0 for x in base]

            # assertions
            l1 = base
            l2 = ["x=1", "x=2", "x=3", "x=4", "x=5"]
            l3 = [0, 0, 3, 4, 5]
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()

def test_list_comprehension_order(snippetcompiler) -> None:
    """
    Verify that the list comprehension expression preserves order on primitive lists.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            entity A: end
            A.others [0:] -- A
            implement A using std::none

            # take some measures to ensure this needs to be waited on: expression with multiple phases, requiring a result
            # variable to be frozen
            default = true ? std::count(a.others) : "unreachable"
            a = A()

            l = [chained for chained in [x > 2 ? x : default for x in [1, 2, 3, 4, 5]]]
            # a naive implementation could result in [3, 4, 5, 0, 0] because the zeros need to be waited on
            l = [0, 0, 3, 4, 5]
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_double_for(snippetcompiler) -> None:
    """
    Verify correct behavior of list comprehension expressions with more than one for.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            base1 = [1, 2]
            base2 = [10, 20]

            entity A: end implement A using std::none
            entity B: end implement B using std::none
            entity C:
                int n
            end
            implement C using std::none

            A.b [0:] -- B
            B.c [0:] -- C

            # cross product
            l1 = ["{{x}}-{{y}}" for x in base1 for y in base2]

            # nesting
            a = A(b=[B(c=[C(n=1), C(n=2)]), B(c=[C(n=3)]), B()])
            l2 = [c.n for b in a.b for c in b.c]
            # equivalent because of list flattening
            l2 = [[c.n for c in b.c] for b in a.b]
            # ensure variables are resolved correctly by introducing some with the same name
            b = 1
            c = 1
            # equivalent with even more name shadowing
            l2 = [a.n for a in a.b for a in a.c]

            # assertions
            l1 = ["1-10", "1-20", "2-10", "2-20"]
            l2 = [1, 2, 3]  # specific order doesn't matter but it should be consistent
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_constructor_trees(snippetcompiler) -> None:
    """
    Verify that list comprehensions play nicely with constructor trees. Concretely, a list comprehension whose value expressions
    are constructors (directly or indirectly) should get their left hand side auto-assigned in case of bidirectional relations
    with an index on rhs.lhs.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            entity Trunk:
                int height
            end

            entity Branch:
                int length
            end
            Trunk.branches [0:] -- Branch.trunk [1]
            index Branch(trunk, length)

            entity Twig:
                int length
            end
            Branch.twigs [0:] -- Twig.branch [1]
            index Twig(branch, length)

            implement Trunk using std::none
            implement Branch using std::none
            implement Twig using std::none

            # e.g. from lsm::all()
            raw_tree = {
                "height": 100,
                "branches": [
                    {
                        "length": 10,
                        "twigs": [1, 2, 3],
                    },
                    {
                        "length": 20,
                        "twigs": [4, 5, 6],
                    },
                    {
                        "length": 30,
                        "twigs": [7, 8, 9],
                    },
                ]
            }

            tree = Trunk(
                height=raw_tree["height"],
                branches = [
                    # value expression is constructor but indirectly
                    false ? "unreachable" : Branch(
                        length=raw_branch["length"],
                        twigs=[Twig(length=raw_twig) for raw_twig in raw_branch["twigs"]],
                    )
                    for raw_branch in raw_tree["branches"]
                ],
            )

            # assertions
            nb_branches = std::count(tree.branches)
            nb_branches = 3
            for raw_branch in raw_tree["branches"]:
                branch = Branch[trunk=tree, length=raw_branch["length"]]
                nb_twigs = std::count(branch.twigs)
                nb_twigs = 3
                for raw_twig in raw_branch["twigs"]:
                    Twig[branch=branch, length=raw_twig]
                end
            end
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_nested_tail(snippetcompiler) -> None:
    """
    Verify correct behavior of list comprehensions where the iterable is a list comprehension itself.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            x = 0
            l = [
                # shadow outer variable to verify the nested list comprehension doesn't see the shadow
                "{{x}}{{x}}"
                for x in [
                    "{{x}}{{y}}"
                    for y in [1, 2]
                ]
            ]

            # assert
            l = ["0101", "0202"]
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_gradual(snippetcompiler) -> None:
    """
    Verify that list comprehensions are executed gradually.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            entity A: end
            A.others [0:] -- A
            implement A using std::none

            a = A()
            b = A(others=[chained for chained in [other for other in a.others]])
            a.others += A()
            if b.others is defined:
                # this seems like bad practice, but it should work as long as the list comprehension is executed gradually.
                a.others += A()
            end

            count = 2
            count = std::count(a.others)
            count = std::count(b.others)
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_gradual_consistency(snippetcompiler, monkeypatch) -> None:
    """
    Verify that gradual execution produces results consistent with non-gradual execution.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            entity A: end
            A.others [0:] -- A
            A.self [1] -- A
            implementation a for A:
                self.self = self
            end
            implement A using a

            a = A()
            a.others = [A(), A(), A()]

            # gradual execution
            b = A()
            b.others = [chained for chained in [other for other in a.others]]
            # non-gradual execution
            c = A()
            c.others = std::select([chained for chained in [other for other in a.others]], "self")

            assert = true
            assert = b.others == c.others
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_gradual_mixed(snippetcompiler) -> None:
    """
    Verify that list comprehensions work as expected when the lhs supports gradual execution but the iterable does not or vice
    versa, when the iterable contains both a gradual and a non-gradual component.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            entity A: end
            A.others [0:] -- A
            implement A using std::none


            # iterable

            ## non-gradual component
            extra = {"a": [A()]}

            ## gradual component
            a = A()
            a.others += A()
            a.others += A()


            # lhs

            ## gradual lhs, non-gradual iterable
            b = A(others=[other for other in extra["a"]])

            ## gradual lhs, mixed iterable
            c = A(others=[other for other in [a.others, extra["a"]]])

            ## non-gradual lhs, gradual iterable
            u = [other for other in [a.others]]

            ## non-gradual lhs, non-gradual iterable
            v = [other for other in extra["a"]]

            ## non-gradual lhs, mixed iterable
            w = [other for other in [a.others, extra["a"]]]


            # assertions

            a_count = 2
            a_count = std::count(a.others)
            a_count = std::count(u)

            extra_count = 1
            no_extra_count = std::count(b.others)
            no_extra_count = std::count(v)

            sum_count = 3
            sum_count = std::count(c.others)
            sum_count = std::count(w)
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


# TODO: tests for error scenarios
# TODO: tests for guards
# TODO: test for shadowing + guard
# TODO: test with Unknowns: in list / list itself is unknown
# TODO: test with null values in list
# TODO: as = [[a, a] for x in xs] where a = [1,2,3]
