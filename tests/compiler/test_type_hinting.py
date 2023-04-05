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

from inmanta import compiler


def test_basic_type_hint(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import elaboratev1module

entity One:

end

One.ref [1] -- elaboratev1module::A

One(ref=A())

implement elaboratev1module::A using std::none
implement One using std::none
        """,
    )
    (_, scopes) = compiler.do_compile()


def test_inheriting_type_hint(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import elaboratev1module
import elaboratev1module::submod

entity One:

end

One.ref [1] -- elaboratev1module::A

One(ref=B())

implement elaboratev1module::A using std::none
implement elaboratev1module::submod::B using std::none

implement One using std::none
        """,
    )
    (_, scopes) = compiler.do_compile()


def test_basic_type_hint_name_collision(snippetcompiler):
    """
    Verify that local types are preferred, even if they do not match the type, resulting in an appropriate exception.
    """
    snippetcompiler.setup_for_error(
        """
import elaboratev1module

entity A:

end

A.ref [1] -- elaboratev1module::A

A(ref=A())

implement elaboratev1module::A using std::none
implement A using std::none

        """,
        (
            "Can not assign a value of type __config__::A to a variable of type elaboratev1module::A"
            " (reported in Construct(A) ({dir}/main.cf:10))"
        ),
    )


def test_basic_type_hint_attribute_collision(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import elaboratev1module

entity One:
    int ref
end

One(ref=A())

implement elaboratev1module::A using std::none
implement One using std::none

        """,
        "Can not assign a value of type A to a variable of type int (reported in Construct(A) ({dir}/main.cf:8))",
    )

    snippetcompiler.reset()
    snippetcompiler.setup_for_error(
        """
import elaboratev1module

entity A:
    int ref
end

A(ref=A())

implement A using std::none

        """,
        "Can not assign a value of type A to a variable of type int (reported in Construct(A) ({dir}/main.cf:8))",
    )


def test_type_inference_is_subclass_right_direction_5790(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import test_5790

entity A extends test_5790::A:
end

entity B extends test_5790::B:
    int n = 1
end

implement A using std::none
implement B using std::none


a = A(b=B())
n = a.b.n
        """,
    )
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    assert 1 == root.lookup("n").get_value()


def test_advanced_type_hint_name_collision(snippetcompiler):
    """
    This test makes sure we detect name collisions during type inference by defining two non-local entities with the same
    name and an inheritance relation between them.
    """
    snippetcompiler.setup_for_error(
        """
import test_5790_follow_up_mod_a
import test_5790_follow_up_mod_b

a = test_5790_follow_up_mod_a::A(b=B())
# raises exception because B can be either `test_5790_follow_up_mod_b::B` or `test_5790_follow_up_mod_a::B`
# (both are in scope and of a compatible type)
        """,
        "Could not determine namespace for type B. 2 possible candidates exists: [test_5790_follow_up_mod_a::B, "
        "test_5790_follow_up_mod_b::B]. To resolve this, use the fully qualified name instead of the short name. "
        "(reported in a = Construct(test_5790_follow_up_mod_a::A) ({dir}/main.cf:5:36))",
    )
