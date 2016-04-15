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
from nose import tools
from impera.ast import Namespace
from impera.ast.statements import define
from impera.parser.plyInmantaParser import parse


def parse_code(model_code: str):
    root_ns = Namespace("__root__")
    main_ns = Namespace("__config__")
    main_ns.parent = root_ns
    statements = parse(main_ns, "test", model_code)

    return statements


def test_define_entity():
    """Test the definition of entities
    """
    statements = parse_code("""
entity Test:
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")

    stmt = statements[0]
    tools.assert_is_instance(stmt, define.DefineEntity)
    tools.assert_equals(stmt.name, "Test")
    tools.assert_equals(stmt.parents, ["std::Entity"])
    tools.assert_equals(len(stmt.attributes), 0)


def test_extend_entity():
    """Test extending entities
    """
    statements = parse_code("""
entity Test extends Foo:
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")

    stmt = statements[0]
    tools.assert_equals(stmt.parents, ["Foo"])


def test_complex_entity():
    """Test definition of a complex entity
    """
    documentation = "This entity has documentation"
    statements = parse_code("""
entity Test extends Foo, foo::sub::Bar:
    \"\"\" %s
    \"\"\"
    string hello
    bool bar = true
    number ten=5
end
""" % documentation)

    tools.assert_equals(len(statements), 1, "Should return one statement")

    stmt = statements[0]
    tools.assert_equals(len(stmt.parents), 2)
    tools.assert_equals(stmt.parents, ["Foo", "foo::sub::Bar"])
    tools.assert_equals(stmt.comment.strip(), documentation)
    tools.assert_equals(len(stmt.attributes), 3)

    for ad in stmt.attributes:
        tools.assert_is_instance(ad.type, str)
        tools.assert_is_instance(ad.name, str)

    tools.assert_equals(stmt.attributes[0].name, "hello")
    tools.assert_equals(stmt.attributes[1].name, "bar")
    tools.assert_equals(stmt.attributes[2].name, "ten")

    tools.assert_equals(stmt.attributes[1].default.execute(None, None, None), True)

    tools.assert_equals(stmt.attributes[2].default.execute(None, None, None), 5)


def test_relation():
    """Test definition of relations
    """
    statements = parse_code("""
Test tests [0:] -- [5:10] Foo bars
""")

    tools.assert_equals(len(statements), 1, "Should return four statements")
    rel = statements[0]

    tools.assert_equals(len(rel.left), 3)
    tools.assert_equals(len(rel.right), 3)

    tools.assert_equals(rel.left[0], "Test")
    tools.assert_equals(rel.right[0], "Foo")

    tools.assert_equals(rel.left[1], "tests")
    tools.assert_equals(rel.right[1], "bars")

    tools.assert_equals(rel.left[2], (0, None))
    tools.assert_equals(rel.right[2], (5, 10))
    tools.assert_equals(statements[0].requires, None)


def test_directional_relation():
    """Test definition of relations
    """
    statements = parse_code("""
Test tests [0:] -> [5:10] Foo bars
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(statements[0].requires, None)

    statements = parse_code("""
Test tests [0:] <- [5:10] Foo bars
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(statements[0].requires, None)


def test_implementation():
    """Test the definition of implementations
    """
    statements = parse_code("""
implementation test for Test:
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(len(statements[0].block.get_stmts()), 0)
    tools.assert_equals(statements[0].name, "test")
    tools.assert_is_instance(statements[0].entity, str)

    statements = parse_code("""
implementation test for Test:
    std::File(attr="a")
    var = hello::func("world")
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(len(statements[0].block.get_stmts()), 2)


def test_implementation_with_for():
    """Test the propagation of type requires when using a for
    """
    statements = parse_code("""
implementation test for Test:
    for v in data:
        std::template("template")
    end
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(len(statements[0].block.get_stmts()), 1)
