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
    snippetcompiler.setup_for_snippet(
        """
import elaboratev1module

entity A:

end

A.ref [1] -- elaboratev1module::A

One(ref=A())

implement elaboratev1module::A using std::none
implement One using std::none
        """,
    )
    (_, scopes) = compiler.do_compile()
