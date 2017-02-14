"""
    Copyright 2017 Inmanta

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
from conftest import snippetcompiler


def test_id_mapping_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import exp

        exp::Test(name="a", agent="b")
        """)

    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 1)
    resource = list(json_value.values())[0]
    assert(resource.id.attribute_value == "test_value_a")


def test_unknown_agent(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        exp::Test(name="a", agent=tests::unknown())
        """)
    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 0)


def test_unknown_attribute_value(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        exp::Test(name=tests::unknown(), agent="b")
        """)
    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 0)


def test_ignore_resource(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import exp
        import tests

        exp::Test(name="a", agent="b", managed=false)
        """)
    _version, json_value = snippetcompiler.do_export()

    assert(len(json_value) == 0)
