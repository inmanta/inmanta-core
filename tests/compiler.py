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

    tools.assert_equals(len(stmt.types()), 5, "Statement should request 5 types")


def test_relation():
    """ Test definition of relations
    """
    statements = parse_code("""
Test tests [0:] -- [5:10] Foo bars
""")

    tools.assert_equals(len(statements), 1, "Should return four statements")
    rel = statements[0]

    tools.assert_equals(len(rel.left), 4)
    tools.assert_equals(len(rel.right), 4)

    tools.assert_is_instance(rel.left[0], Reference)
    tools.assert_equals(rel.left[0].name, "Test")
    tools.assert_is_instance(rel.right[0], Reference)
    tools.assert_equals(rel.right[0].name, "Foo")

    tools.assert_equals(rel.left[1], "tests")
    tools.assert_equals(rel.right[1], "bars")

    tools.assert_equals(rel.left[2], [0, None])
    tools.assert_equals(rel.right[2], [5, 10])
    tools.assert_equals(statements[0].requires, None)


def test_directional_relation():
    """ Test definition of relations
    """
    statements = parse_code("""
Test tests [0:] -> [5:10] Foo bars
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(statements[0].requires, ">")

    statements = parse_code("""
Test tests [0:] <- [5:10] Foo bars
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(statements[0].requires, "<")


def test_implementation():
    """ Test the definition of implementations
    """
    statements = parse_code("""
implementation test for Test:
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(len(statements[0].statements), 0)
    tools.assert_equals(statements[0].name, "test")
    tools.assert_is_instance(statements[0].entity, Reference)

    statements = parse_code("""
implementation test for Test:
    std::File(attr="a")
    var = hello::func("world")
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(len(statements[0].statements), 2)
    tools.assert_equals(len(statements[0].types()), 3, "Should require 3 types")


def test_implementation_with_for():
    """ Test the propagation of type requires when using a for
    """
    statements = parse_code("""
implementation test for Test:
    for v in data:
        std::template("template")
    end
end
""")

    tools.assert_equals(len(statements), 2, "Should return one statement")
    tools.assert_equals(len(statements[0].statements), 1)
