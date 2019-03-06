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


def test_str_on_instance_pos(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg = Hg()

for i in [1,2,3]:
 hg.hosts = std::Host(name="Test{{i}}", os=std::unix)
end


for i in hg.hosts:
    std::ConfigFile(host=i, path="/fx", content="")
end
"""
    )
    (types, _) = compiler.do_compile()
    files = types["std::File"].get_all_instances()
    assert len(files) == 3


def test_str_on_instance_neg(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg = Hg()

for i in [1,2,3]:
 hg.hosts = std::Host(name="Test", os=std::unix)
end


for i in hg.hosts:
    std::ConfigFile(host=i, path="/fx", content="")
end
"""
    )
    (types, _) = compiler.do_compile()
    files = types["std::File"].get_all_instances()
    assert len(files) == 1


def test_implements_inheritance(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string a
end

entity TestC extends Test:
end

implementation test for Test:
    self.a = "xx"
end



implement Test using test
implement TestC using parents

a = TestC()
"""
    )
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    assert "xx" == root.lookup("a").get_value().lookup("a").get_value()


def test_keyword_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       index = ""
""",
        "Syntax error invalid identifier, index is a reserved keyword ({dir}/main.cf:2:8)",
    )


def test_keyword_excn2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       implementation index for std::Entity:
       end
""",
        "Syntax error invalid identifier, index is a reserved keyword ({dir}/main.cf:2:23)",
    )


def test_keyword_excn3(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       implementation aaa for index::Entity:
       end
""",
        "Syntax error invalid identifier, index is a reserved keyword ({dir}/main.cf:2:31)",
    )


def test_cid_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       entity test:
       end
""",
        "Syntax error Invalid identifier: Entity names must start with a capital ({dir}/main.cf:2:15)",
    )


def test_cid_excn2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
       entity Test extends test:
       end
""",
        "Syntax error Invalid identifier: Entity names must start with a capital ({dir}/main.cf:2:28)",
    )


def test_bad_var(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        a=b
""",
        "variable b not found (reported in Assign(a, b) ({dir}/main.cf:2))",
    )


def test_bad_type(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test1:
    string a
end

Test1(a=3)
""",
        """Could not set attribute `a` on instance `__config__::Test1 (instantiated at {dir}/main.cf:6)` """
        """(reported in Construct(Test1) ({dir}/main.cf:6))
caused by:
  Invalid value '3', expected String (reported in Construct(Test1) ({dir}/main.cf:6))""",
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
        """Could not set attribute `a` on instance `__config__::Test1 (instantiated at {dir}/main.cf:10)` (reported in t1.a = 3 ({dir}/main.cf:11))
caused by:
  Invalid value '3', expected String (reported in t1.a = 3 ({dir}/main.cf:11))""",  # noqa: E501
    )


def test_typedef_in_non_constant(snippetcompiler):
    # noqa: E501
    snippetcompiler.setup_for_error(
        """
a = "A"
typedef abc as string matching self in [a,"b","c"]

entity Test:
    abc value
end

implement Test using std::none

Test(value="a")
""",
        """Could not set attribute `value` on instance `__config__::Test (instantiated at {dir}/main.cf:11)` (reported in Construct(Test) ({dir}/main.cf:11))
caused by:
  Could not resolve the value a in this static context (reported in a ({dir}/main.cf:3:41))""",  # noqa: E501
    )


def test_typedef_in_violates(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
typedef abc as string matching self in ["a","b","c"]

entity Test:
    abc value
end

implement Test using std::none

Test(value="ab")
""",
        """Could not set attribute `value` on instance `__config__::Test (instantiated at {dir}/main.cf:10)` (reported in Construct(Test) ({dir}/main.cf:10))
caused by:
  Invalid value 'ab', constraint does not match (reported in __config__::abc ({dir}/main.cf:2:9))""",  # noqa: E501
    )
