"""
    Copyright 2016 Inmanta

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


def test_plugin_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        import std
        std::template("/tet.tmpl")
""",
        "Exception in plugin std::template caused by TemplateNotFound: /tet.tmpl "
        "(reported in std::template('/tet.tmpl') ({dir}/main.cf:3))"
    )


def test_keyword_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       index = ""
""",
        "Syntax error invalid identifier, index is a reserved keyword ({dir}/main.cf:2:15)"
    )


def test_keyword_excn2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       implementation index for std::Entity:
       end
""",
        "Syntax error invalid identifier, index is a reserved keyword ({dir}/main.cf:2:24)"
    )


def test_keyword_excn3(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       implementation aaa for index::Entity:
       end
""",
        "Syntax error invalid identifier, index is a reserved keyword ({dir}/main.cf:2:32)"
    )


def test_cid_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       entity test:
       end
""",
        "Syntax error Invalid identifier: Entity names must start with a capital ({dir}/main.cf:2:16)"
    )


def test_cid_excn2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       entity Test extends test:
       end
""",
        "Syntax error Invalid identifier: Entity names must start with a capital ({dir}/main.cf:2:29)"
    )


def test_bad_var(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        a=b
""",
        "variable b not found (reported in Assign(a, b) ({dir}/main.cf:2))"
    )


def test_bad_type(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test1:
    string a
end

Test1(a=3)
""",
        "Could not set attribute `a` on instance `__config__::Test1 (instantiated at {dir}/main.cf:6)` caused by Invalid "
        "value '3', expected String (reported in Construct(Test1) ({dir}/main.cf:6))"
    )


def test_bad_type_2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import std

entity Test1:
    string a
end

implement Test1 using std::none

t1 = Test1()
t1.a=3
""",
        "Could not set attribute `a` on instance `__config__::Test1 (instantiated at {dir}/main.cf:10)` caused by Invalid "
        "value '3', expected String (reported in t1.a = 3 ({dir}/main.cf:11)) (reported in t1.a = 3 ({dir}/main.cf:11))"
    )


def test_incomplete(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import std

entity Test1:
    string a
end

implement Test1 using std::none

t1 = Test1()
""",
        "The object __config__::Test1 (instantiated at {dir}/main.cf:10) is not complete: "
        "attribute a ({dir}/main.cf:5) is not set"
    )


def test_bad_deref(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
h = std::Host(name="test", os=std::linux)
std::print(h.name.test)
""",
        "can not get a attribute test, test not an entity (reported in h.name.test ({dir}/main.cf:3))"
    )


def test_doubledefine(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity File:
end

entity File:
end
""",
        "Entity __config__::File is already defined (reported at ({dir}/main.cf:5)) (duplicate at ({dir}/main.cf:2))"
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
        "Implementation __config__::file for type File is already defined (reported at ({dir}/main.cf:8))" +
        " (duplicate at ({dir}/main.cf:5))"
    )


def test_400_typeloops(snippetcompiler):
    snippetcompiler.setup_for_error("""
    entity Test extends Test:

    end
    """, "Entity can not be its own parent __config__::Test (reported in Entity(Test) ({dir}/main.cf:2))")


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
        "Entity can not be its own parent __config__::Test[1-2],__config__::Test[1-2] " +
        "\(reported in Entity\(Test[1-2]\) \({dir}/main.cf:[59]\)\)")


def test_null(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity A:
            string a = null
        end
        implement A using std::none
        a = A()

    """,
        "Could not set attribute `a` on instance `__config__::A (instantiated at {dir}/main.cf:6)`" +
        " caused by Invalid value 'null', expected String (reported in Construct(A) ({dir}/main.cf:6))")


def test_null_on_list(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity A:
            string[] a = null
        end
        implement A using std::none
        a = A()
    """, "Could not set attribute `a` on instance `__config__::A (instantiated at {dir}/main.cf:6)`" +
        " caused by Invalid value 'null', expected list (reported in Construct(A) ({dir}/main.cf:6))")


def test_null_on_dict(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity A:
            dict a = null
        end
        implement A using std::none
        a = A()
    """, "Syntax error null can not be assigned to dict, did you mean \"dict? a = null\" ({dir}/main.cf:3:14)")


def test_unknown_type_in_relation(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        foo::Entity.test [1] -- std::Entity
        """, "could not find type foo::Entity in namespace __config__ (reported in None ({dir}/main.cf:2))")
