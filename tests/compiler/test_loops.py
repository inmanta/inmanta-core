"""
Copyright 2018 Inmanta

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
from collections import Counter

import inmanta.compiler as compiler


def test_order_of_execution(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
for i in std::sequence(10):
    std::print(i)
end
        """,
        autostd=True,
    )

    capsys.readouterr()
    compiler.do_compile()
    out, _ = capsys.readouterr()
    output = out.strip()
    assert output == "\n".join([str(x) for x in range(10)])


def test_for_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity A:
            string a = ""
        end
        implement A using none
        a = A()
        for i in a:
        end

        implementation none for std::Entity:
        end
    """,
        "A for loop can only be applied to lists and relations. Hint: 'a' resolves to "
        "'__config__::A (instantiated at {dir}/main.cf:6)'. (reported in "
        "For(i) ({dir}/main.cf:7))",
    )


def test_for_error_2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        for i in "foo":
        end
    """,
        "A for loop can only be applied to lists and relations. Hint: 'foo' is not a "
        "list. (reported in For(i) ({dir}/main.cf:2))",
    )


def test_for_error_nullable_list(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity A:
            string[]? elements=null
        end
        implement A using std::none

        a = A()
        for element in a.elements:
            std::print(element)
        end
    """,
        "A for loop can only be applied to lists and relations. "
        "Hint: 'a.elements' resolves to 'null'. (reported in For(element) ({dir}/main.cf:8))",
        ministd=True,
    )


def test_for_loop_on_list_attribute(snippetcompiler) -> None:
    """
    Verify the basic workings of the for loop statement when applied to a plain list attribute.
    """
    snippetcompiler.setup_for_snippet(textwrap.dedent("""\
            entity A:
                list l
            end

            implement A using none

            a = A(l=[1, 2])

            entity Assert:
                bool success  # no default -> trigger not-set exception if for loop is not executed
            end
            implement Assert using none
            assert = Assert()

            for x in a.l:
                assert.success = true
                if x != 1 and x != 2:
                    # trigger exception
                    assert.success = false
                end
            end

            implementation none for std::Entity:
            end
            """))
    compiler.do_compile()


def test_for_loop_unknown(snippetcompiler) -> None:
    """
    Verify the behavior of the for loop regarding unknowns.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent("""\
            import tests

            entity Assert:
                bool success = true
            end
            implement Assert using std::none
            assert = Assert()

            for x in tests::unknown():
                # body should not be executed at all if entire list is unknown
                assert.success = false
            end

            for x in [1, 2, tests::unknown()]:
                # unknowns in list should be skipped
                if x != 1 and x != 2:
                    assert.success = false
                end
                if std::is_unknown(x):
                    assert.success = false
                end
            end
            """),
        autostd=True,
    )
    compiler.do_compile()


def test_resultcollector_receive_result_flatten(snippetcompiler) -> None:
    """
    Verify the flattening behavior of ResultCollector.receive_result_flatten.
    """
    snippetcompiler.setup_for_snippet(textwrap.dedent("""\
            entity Assert:
                bool success = true
            end
            implement Assert using none
            assert = Assert()

            # nested list containing a string
            # => no flattening would result in `["test"]` in the list
            # => naive flattening might treat the string as a sequence and flatten to ["t", "e", "s", "t"]
            for x in [["test"]]:
                if x != "test":
                    assert.success = false
                end
            end

            # Test composed lists as well as constant lists
             a = "test"
             for x in [["test"], a, [a]]:
                if x != "test":
                    assert.success = false
                end
            end

            implementation none for std::Entity:
            end
            """))
    compiler.do_compile()


# TODO: created by Claude, needs review
def test_5720_for_loop_no_duplicate_trimming(snippetcompiler, capsys):
    """
    Verify that the for loop does not trim duplicate values, regardless of the type of value
    or whether the duplicates arise from literal list optimization, Python integer interning,
    or other implementation details. All 8 cases below iterate over a 2-element list and
    should each print twice.

    See: https://github.com/inmanta/inmanta-core/issues/5720
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent("""\
            one = 1
            entity Number: int n end implement Number using std::none

            # 1: for loop trims duplicate due to Python integer interning (low int -> same id())
            l = [42*one, 42*one]
            for n in l: std::print(n) end

            # 2: no trimming (high int, not interned by Python -> different id())
            ll = [420*one, 420*one]
            for n in ll: std::print(n) end

            # 3: list constructor trims duplicate due to Python integer interning
            for n in [421*one, 421*one]: std::print(n) end

            # 4: literal list, no trimming
            for n in [422, 422]: std::print(n) end

            # 5: two distinct instances with equal attribute value
            nums = [Number(n=43), Number(n=43)]
            for n in nums: std::print(n.n) end

            # 6: two distinct instances in a literal list
            for n in [Number(n=443), Number(n=443)]: std::print(n.n) end

            # 7: same instance referenced via the same list variable twice; list constructor trims the duplicate
            num = [Number(n=444)]
            for n in [num, num]: std::print(n.n) end

            # 8: same instance referenced directly twice; for loop trims the duplicate
            num2 = Number(n=445)
            nums2 = [num2, num2]
            for n in nums2: std::print(n.n) end
            """),
        autostd=True,
    )
    capsys.readouterr()
    compiler.do_compile()
    out, _ = capsys.readouterr()
    # The for loops are independent so execution order is not guaranteed.
    # Check that each value is printed exactly twice (i.e. no duplicate trimming occurred).
    assert Counter(out.split()) == Counter(
        {
            "42": 2,   # case 1
            "420": 2,  # case 2
            "421": 2,  # case 3
            "422": 2,  # case 4
            "43": 2,   # case 5
            "443": 2,  # case 6
            "444": 2,  # case 7
            "445": 2,  # case 8
        }
    )


def test_for_loop_fully_gradual(snippetcompiler):
    """
    Verify that the compiler does not produce progress potential for the for loop because it may cause it too freeze too
    eagerly.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent("""\
            entity A: end
            A.x [0:] -- A
            A.y [0:] -- A

            implement A using std::none


            a = A()
            if a.x is defined:
                # this is a nonsensical statement but it is a simple way to force the compiler to see the same progress
                # potential for a.x as it does for a.y, in a way that it can not trivially resolve without freezing something
                # (as would be the case with e.g. `if true`.
                a.x += a.x
            else:
                # a.x should clearly be frozen before a.x
                a.y += A()
            end
            # Pure gradual execution of the for loop ensures that this statement does produce progress potential for a.y.
            # If it did, it might cause the compiler to freeze a.y first.
            for y in a.y:
                std::print(y)
            end
            """),
        ministd=True,
    )
    compiler.do_compile()
