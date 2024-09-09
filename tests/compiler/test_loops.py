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
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
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
            """
        )
    )
    compiler.do_compile()


def test_for_loop_unknown(snippetcompiler) -> None:
    """
    Verify the behavior of the for loop regarding unknowns.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
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
            """
        ),
        autostd=True,
    )
    compiler.do_compile()


def test_resultcollector_receive_result_flatten(snippetcompiler) -> None:
    """
    Verify the flattening behavior of ResultCollector.receive_result_flatten.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
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
            """
        )
    )
    compiler.do_compile()


def test_for_loop_fully_gradual(snippetcompiler):
    """
    Verify that the compiler does not produce progress potential for the for loop because it may cause it too freeze too
    eagerly.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
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
            """
        ),
        ministd=True,
    )
    compiler.do_compile()
