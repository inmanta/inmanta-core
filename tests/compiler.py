"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

from impera import app
from impera import parser
from impera.ast import Namespace

from nose import tools
from impera.ast.statements import define
from impera.ast.variables import Reference


def parse_code(model_code: str):
    model_parser = parser.Parser()
    ns_root = Namespace("__config__")
    statements = model_parser.parse(ns_root, content=model_code)

    return statements


def test_define_entity():
    """ Test the definition of entities
    """
    statements = parse_code("""
entity Test:
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")

    stmt = statements[0]
    tools.assert_is_instance(stmt, define.DefineEntity)
    tools.assert_equals(stmt.name, "Test")
    tools.assert_equals(len(stmt.parents), 0)
    tools.assert_equals(len(stmt.attributes), 0)


def test_extend_entity():
    """ Test extending entities
    """
    statements = parse_code("""
entity Test extends Foo:
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")

    stmt = statements[0]
    tools.assert_equals(len(stmt.parents), 1)
    tools.assert_is_instance(stmt.parents[0], Reference, "Parents should be references")


def test_complex_entity():
    """ Test definition of a complex entity
    """
    documentation = "This entity has documentation"
    statements = parse_code("""
entity Test extends Foo, foo::sub::Bar:
    \"\"\" %s
    \"\"\"
    string hello
    bool bar
    number ten=5
end
""" % documentation)

    tools.assert_equals(len(statements), 1, "Should return one statement")

    stmt = statements[0]
    tools.assert_equals(len(stmt.parents), 2)
    tools.assert_count_equal(stmt.parents[1].namespace, ["foo", "sub"])
    tools.assert_equals(stmt.comment.strip(), documentation)
    tools.assert_equals(len(stmt.attributes), 3)

    for attr_type, name, default in stmt.attributes:
        tools.assert_is_instance(attr_type, Reference)
        tools.assert_is_instance(name, str)

    tools.assert_equals(stmt.attributes[0][1], "hello")
    tools.assert_equals(stmt.attributes[1][1], "bar")
    tools.assert_equals(stmt.attributes[2][1], "ten")

    tools.assert_equals(stmt.attributes[2][2], 5)
    print(stmt.types())
