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

from inmanta import ast, compiler


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
            l4 = [1 for _ in base]

            # assertions
            l1 = base
            l2 = ["x=1", "x=2", "x=3", "x=4", "x=5"]
            l3 = [0, 0, 3, 4, 5]
            l4 = [1, 1, 1, 1, 1]
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

            # cross-product with same name for both loop vars (bad practice but valid)
            l3 = [x for x in base1 for x in base2]

            # assertions
            l1 = ["1-10", "1-20", "2-10", "2-20"]
            l2 = [1, 2, 3]  # specific order doesn't matter but it should be consistent
            l3 = [10, 20, 10, 20]
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_guards(snippetcompiler) -> None:
    """
    Verify the functionality of guards within a list comprehension.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            base = [1, 2, 3, 4, 5]

            # shadow loop variable to verify that neither the value expression nor the guard see it
            x = 0
            gt = 2
            lt = 5

            # single guard
            l1 = [x for x in base if x > gt]
            # multiple guards
            l2 = ["x={{x}}" for x in base if x > gt if x < lt if true and true if true or true]
            # nested expressions
            l3 = [y for y in [x for x in base if x > gt] if y < lt]
            l4 = [
                "{{x}}={{y}}"
                for x in base
                for y in base
                if x == 3
                if y == 5
            ]
            # cross-product with same name for both loop vars (bad practice but valid)
            l5 = [
                x
                for x in base
                for x in base
                if x > 3
            ]

            # assertions
            l1 = [3, 4, 5]
            l2 = ["x=3", "x=4"]
            l3 = [3, 4]
            l4 = ["3=5"]
            l5 = [4, 5, 4, 5, 4, 5, 4, 5, 4, 5]
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

            # use both plain variables (no gradual capability) and inline lists as iterable to verify identical behavior
            iterable1 = [1, 2, 3, 4, 5]
            iterable2 = [-1, 0, 1, 2, 3, 4, 5]

            # add an additional gradual-capable layer to collect out-of-order results if there are any
            l1 = [chained for chained in [x > 2 ? x : default for x in iterable1]]
            l1 = [chained for chained in [x > 2 ? x : default for x in [1, 2, 3, 4, 5]]]
            # a naive implementation could result in [3, 4, 5, 0, 0] because the zeros need to be waited on
            l1 = [0, 0, 3, 4, 5]

            # with a guard
            l1 = [chained for chained in [x > 2 ? x : default for x in iterable2 if x > default]]
            l1 = [chained for chained in [x > 2 ? x : default for x in [-1, 0, 1, 2, 3, 4, 5] if x > default]]
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

            # gradual execution of iterable
            a = A()
            b = A(others=[chained for chained in [other for other in a.others]])
            a.others += A()
            if b.others is defined:
                # this seems like bad practice, but it should work as long as the list comprehension is executed gradually.
                a.others += A()
            end

            # gradual execution of guard
            x = A()
            # again bad practice but asserts gradual execution of the `is defined`
            y = A(others=[A(), c.others])
            c = A(others=[candidate for candidate in [x, y] if candidate.others is defined])

            count = 2
            count = std::count(a.others)
            count = std::count(b.others)

            c_count = 1
            c_count = std::count(c.others)
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


def test_list_comprehension_duplicate_values(snippetcompiler) -> None:
    """
    Verify behavior of list comprehensions when the iterable contains duplicate values.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            l = [1, 2, 3]

            twice = [l, l]
            twice = [x for x in [l, l]]
            nested = [[l, l] for x in [l, l]]

            # assertions

            twice_count = 6
            twice_count = std::count(twice)

            nested_count = 36
            nested_count = std::count(nested)
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_empty_items(snippetcompiler, monkeypatch) -> None:
    """
    Verify that list comprehensions behave as expected when the iterable produces empty subitems, both for gradual and
    non-gradual execution.
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
            b.others = [chained for chained in [other for other in [[], [], a.others]]]
            # non-gradual execution
            c = A()
            c.others = std::select([chained for chained in [other for other in [a.others, [], [], [], []]]], "self")

            assert = true
            assert = a.others == b.others
            assert = b.others == c.others
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_unknown(snippetcompiler) -> None:
    """
    Verify that list comprehensions propagate Unknowns appropriately.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            import tests

            unknown = tests::unknown()

            # comprehensions

            ## unknown iterable makes result unknown
            l1 = [x for x in unknown]

            ## unknown in iterable becomes unknown in result
            l2 = [x for x in [1, 2, unknown]]
            l3 = [x for x in [1, unknown, 3] if true]

            ## unknown in guard expression becomes unknown in result
            l4 = [x for x in [1, 2, 3] if x > 1 or unknown]

            ## unknown in value expression becomes unknown in result
            l5 = [x < 2 ? x : unknown for x in [1, 2, 3]]
            l6 = [x == 2 ? x : unknown for x in [1, 2, 3] if true]

            ## nested for
            l7 = [
                x == 2 ? y : unknown
                for x in [1, 2, 3]
                for y in [1, 2, 3]
            ]
            l8 = [
                x == 2 ? y : unknown
                for y in [1, 2, 3]
                for x in [1, 2, 3]
            ]
            l9 = [
                y
                for x in [1, 2, 3]
                for y in [1, 2, 3]
                if x == 2 or unknown
            ]

            assert = true
            assert = tests::is_uknown(l1)
            assert = not tests::is_uknown(l2)
            assert = not tests::is_uknown(l3)
            assert = not tests::is_uknown(l4)
            assert = not tests::is_uknown(l5)
            assert = not tests::is_uknown(l6)

            l2_unknowns = [1, 2, "unknown"]
            l2_unknowns = [tests::is_uknown(element) ? "unknown" : element for element in l2]

            l3_unknowns = [1, "unknown", 3]
            l3_unknowns = [tests::is_uknown(element) ? "unknown" : element for element in l3]

            l4_unknowns = ["unknown", 2, 3]
            l4_unknowns = [tests::is_uknown(element) ? "unknown" : element for element in l4]

            l5_unknowns = [1, "unknown", "unknown"]
            l5_unknowns = [tests::is_uknown(element) ? "unknown" : element for element in l5]

            l6_unknowns = ["unknown", 2, "unknown"]
            l6_unknowns = [tests::is_uknown(element) ? "unknown" : element for element in l6]

            l7_unknowns = ["unknown", "unknown", "unknown", 1, 2, 3, "unknown", "unknown", "unknown"]
            l7_unknowns = [tests::is_uknown(element) ? "unknown" : element for element in l7]

            l8_unknowns = ["unknown", 1, "unknown", "unknown", 2, "unknown", "unknown", 3, "unknown"]
            l8_unknowns = [tests::is_uknown(element) ? "unknown" : element for element in l8]

            l9_unknowns = ["unknown", "unknown", "unknown", 1, 2, 3, "unknown", "unknown", "unknown"]
            l9_unknowns = [tests::is_uknown(element) ? "unknown" : element for element in l9]
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()


def test_list_comprehension_direct(snippetcompiler) -> None:
    """
    Verify that list comprehensions work in a direct execute context.
    """
    model_def: str = textwrap.dedent(
        """
        import tests

        typedef nineties as int matching self in [i == 2 ? 42 : tests::sum(i, 90) for i in std::sequence(10) if i != 5]

        entity A:
            nineties n
        end
        implement A using std::none
        """.strip(
            "\n"
        )
    )

    valid: str = textwrap.dedent(
        """
            for i in std::sequence(10, start=90):
                if i != 92 and i != 95:
                    A(n=i)
                end
            end
            A(n=42)
        """.strip(
            "\n"
        )
    )

    # verify some invalid values
    for i in [92, 95, 100, 89, 0, -1, 43]:
        snippetcompiler.setup_for_snippet(f"{model_def}\nA(n={i})")
        with pytest.raises(ast.AttributeException):
            compiler.do_compile()

    # verify valid values
    snippetcompiler.setup_for_snippet("\n".join((model_def, valid)))
    compiler.do_compile()


def test_list_comprehension_type_error(snippetcompiler) -> None:
    """
    Verify that a list comprehension applied to something other than a list raises a clear exception
    """
    snippetcompiler.setup_for_error(
        "[x for x in 'Hello World']",
        (
            "A list comprehension can only be applied to lists and relations, got str"
            " (reported in [x for x in 'Hello World'] ({dir}/main.cf:1))"
        ),
    )


def test_list_comprehension_type_error_direct_execute(snippetcompiler) -> None:
    """
    Verify that a list comprehension in a direct execute context applied to something other than a list raises a clear exception
    """
    snippetcompiler.setup_for_error(
        textwrap.dedent(
            """
            typedef mytype as int matching self in [x for x in 'Hello World']
            entity A:
                mytype n = 0
            end
            """.strip(
                "\n"
            )
        ),
        (
            "A list comprehension in a direct execute context can only be applied to lists, got str"
            " (reported in [x for x in 'Hello World'] ({dir}/main.cf:1))"
        ),
    )


def test_list_comprehension_type_error_direct_execute_guard(snippetcompiler) -> None:
    """
    Verify that a list comprehension in a direct execute context applied with a non-boolean guard raises a clear exception
    """
    snippetcompiler.setup_for_error(
        textwrap.dedent(
            """
            typedef mytype as int matching self in [x for x in [1, 2] if 42]
            entity A:
                mytype n = 0
            end
            """.strip(
                "\n"
            )
        ),
        (
            "Invalid value `42`: the guard condition for a list comprehension must be a boolean expression"
            " (reported in [x for x in [1,2] if 42] ({dir}/main.cf:1))"
        ),
    )
