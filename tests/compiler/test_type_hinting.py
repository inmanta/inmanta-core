import pytest

from inmanta import compiler
from inmanta.ast import AmbiguousTypeException, TypeNotFoundException


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
    snippetcompiler.setup_for_snippet(
        """
import elaboratev1module

entity A:

end

A.ref [1] -- elaboratev1module::A

A(ref=A())

implement elaboratev1module::A using std::none
implement A using std::none

        """,
    )
    (_, scopes) = compiler.do_compile()


def test_advanced_type_hint_name_collision(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import elaboratev1module

entity A extends elaboratev1module::A:

end

A.ref [1] -- elaboratev1module::A

A(ref=A())

implement elaboratev1module::A using std::none
implement A using std::none

        """,
        "Could not determine namespace for type A. 2 possible candidates exists: [__config__::A, elaboratev1module::A]. "
        "To resolve this, use the fully qualified name instead of the short name. "
        "(reported in Construct(A) ({dir}/main.cf:10:7))",
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
        "Can not assign a value of type A to a variable of type int (reported in Construct(A) ({dir}/main.cf:8))"
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
    "Can not assign a value of type A to a variable of type int (reported in Construct(A) ({dir}/main.cf:8))"
    )
