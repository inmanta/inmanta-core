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
