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

import inmanta.compiler as compiler
from inmanta.execute.util import Unknown


def test_issue_219_unknows_in_template(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import tests

a = tests::unknown()
b = "abc{{a}}"
"""
    )
    (_, root) = compiler.do_compile()
    scope = root.get_child("__config__").scope

    assert isinstance(scope.lookup("a").get_value(), Unknown)
    assert isinstance(scope.lookup("b").get_value(), Unknown)


def test_749_is_unknown(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
        import tests

        a="a"
        b=tests::unknown()

        au = tests::is_uknown(a)
        bu = tests::is_uknown(b)

        ax = tests::do_uknown(a)
        bx = tests::do_uknown(b)
    """
    )

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")

    assert not root.lookup("au").get_value()
    assert root.lookup("bu").get_value()

    assert root.lookup("ax").get_value() == "XX"
    assert root.lookup("bx").get_value() == "XX"


def test_doubledefine(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity File:
end

entity File:
end
""",
        "Entity __config__::File is already defined (original at ({dir}/main.cf:5:8)) (duplicate at ({dir}/main.cf:2:8))",
    )


def test_double_define_implementation(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity File:
end

implementation file for File:
end

implementation file for File:
end
""",
        "Implementation __config__::file for type File is already defined (original at ({dir}/main.cf:8:16))"
        + " (duplicate at ({dir}/main.cf:5:16))",
    )


def test_400_typeloops(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
    entity Test extends Test:

    end
    """,
        "Entity can not be its own parent __config__::Test (reported in Entity(Test) ({dir}/main.cf:2))",
    )


def test_400_typeloops_2(snippetcompiler):
    snippetcompiler.setup_for_error_re(
        """
    entity Test3 extends Test2:
    end

    entity Test1 extends Test2:

    end

    entity Test2 extends Test1:

    end
    """,
        "Entity can not be its own parent __config__::Test[1-2],__config__::Test[1-2] "
        + r"\(reported in Entity\(Test[1-2]\) \({dir}/main.cf:[59]\)\)",
    )


def test_unknown_type_in_relation(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
foo::Entity.test [1] -- std::Entity
        """,
        "could not find type foo::Entity in namespace __config__ ({dir}/main.cf:2:1)",
    )
