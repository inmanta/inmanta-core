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

import re

from nose import tools
from impera.ast import Namespace
from impera.ast.statements import define, Literal
from impera.parser.plyInmantaParser import parse
from impera.parser import ParserException
from nose.tools.nontrivial import raises
from impera.ast.statements.define import DefineImplement, DefineTypeConstraint, DefineTypeDefault, DefineIndex, DefineImport
from impera.ast.constraint.expression import GreaterThan, Regex, Not, And
from impera.ast.statements.generator import Constructor
from impera.ast.statements.call import FunctionCall
from impera.ast.statements.assign import Assign, CreateList, IndexLookup, StringFormat
from impera.ast.variables import Reference, AttributeReference


def parse_code(model_code: str):
    root_ns = Namespace("__root__")
    main_ns = Namespace("__config__")
    main_ns.parent = root_ns
    statements = parse(main_ns, "test", model_code)

    return statements


def test_define_empty():
    parse_code("""""")


def test_define_entity():
    """Test the definition of entities
    """
    statements = parse_code("""
entity Test:
end
entity Other:
string hello
end
entity Other:
 \"\"\"XX
 \"\"\"
end
""")

    tools.assert_equals(len(statements), 3, "Should return two statement")

    stmt = statements[0]
    tools.assert_is_instance(stmt, define.DefineEntity)
    tools.assert_equals(stmt.name, "Test")
    tools.assert_equals(stmt.parents, ["std::Entity"])
    tools.assert_equals(len(stmt.attributes), 0)
    tools.assert_equals(stmt.comment, None)


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


def test_relation_2():
    """Test definition of relations
    """
    statements = parse_code("""
Test tests [3] -- [:10] Foo bars
""")

    tools.assert_equals(len(statements), 1, "Should return four statements")
    rel = statements[0]

    tools.assert_equals(len(rel.left), 3)
    tools.assert_equals(len(rel.right), 3)

    tools.assert_equals(rel.left[0], "Test")
    tools.assert_equals(rel.right[0], "Foo")

    tools.assert_equals(rel.left[1], "tests")
    tools.assert_equals(rel.right[1], "bars")

    tools.assert_equals(rel.left[2], (3, 3))
    tools.assert_equals(rel.right[2], (None, 10))
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
    \"\"\" test \"\"\"
    for v in data:
        std::template("template")
    end
end
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    tools.assert_equals(len(statements[0].block.get_stmts()), 1)


def test_implements():
    """Test implements with no selector
    """
    statements = parse_code("""
implement Test using test
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineImplement)
    tools.assert_equals(stmt.entity, "Test")
    tools.assert_equals(stmt.implementations, ["test"])
    tools.assert_equals(str(stmt.select), "True")


def test_implements_2():
    """Test implements with selector
    """
    statements = parse_code("""
implement Test using test, blah when (self > 5)
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineImplement)
    tools.assert_equals(stmt.entity, "Test")
    tools.assert_equals(stmt.implementations, ["test", "blah"])
    tools.assert_is_instance(stmt.select, GreaterThan)
    tools.assert_equals(stmt.select.children[0].name, 'self')
    tools.assert_equals(stmt.select.children[1].value, 5)


def test_implements_Selector():
    """Test implements with selector
    """
    statements = parse_code("""
implement Test using test when not (fg(self) and false)
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineImplement)
    tools.assert_equals(stmt.entity, "Test")
    tools.assert_equals(stmt.implementations, ["test"])
    tools.assert_is_instance(stmt.select, Not)
    tools.assert_is_instance(stmt.select.children[0], And)
    tools.assert_is_instance(stmt.select.children[0].children[0], FunctionCall)
    tools.assert_is_instance(stmt.select.children[0].children[1], Literal)


def test_regex():
    statements = parse_code("""
a = /[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}/
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0].value
    tools.assert_is_instance(stmt, Regex)
    tools.assert_equals(stmt.children[1].value, re.compile(
        r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"))


def test_typedef():
    statements = parse_code("""
typedef uuid as string matching /[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}/
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineTypeConstraint)
    tools.assert_equals(stmt.name, "uuid")
    tools.assert_equals(stmt.basetype, "string")
    tools.assert_is_instance(stmt.get_expression(), Regex)
    tools.assert_equals(stmt.get_expression().children[1].value, re.compile(
        r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"))


def test_typedef2():
    statements = parse_code("""
typedef ConfigFile as File(mode = 644, owner = "root", group = "root")
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineTypeDefault)
    tools.assert_equals(stmt.name, "ConfigFile")
    tools.assert_is_instance(stmt.ctor, Constructor)


def test_index():
    statements = parse_code("""
index File(host, path)
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineIndex)
    tools.assert_equals(stmt.type, "File")
    tools.assert_equals(stmt.attributes, ["host", "path"])


def test_ctr():
    statements = parse_code("""
File(host = 5, path = "Jos")
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, Constructor)
    tools.assert_equals(stmt.class_type, "File")
    tools.assert_equals({k: v.value for k, v in stmt.attributes.items()}, {"host": 5, "path": "Jos"})


def test_indexlookup():
    statements = parse_code("""
a=File[host = 5, path = "Jos"]
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0].value
    tools.assert_is_instance(stmt, IndexLookup)
    tools.assert_equals(stmt.index_type, "File")
    tools.assert_equals({k: v.value for k, v in stmt.query}, {"host": 5, "path": "Jos"})


def test_ctr_2():
    statements = parse_code("""
File( )
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, Constructor)
    tools.assert_equals(stmt.class_type, "File")
    tools.assert_equals({k: v.value for k, v in stmt.attributes.items()}, {})


def test_function():
    statements = parse_code("""
file( )
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, FunctionCall)
    tools.assert_equals(stmt.name, "file")


def test_list_Def():
    statements = parse_code("""
a=["a]","b"]
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, Assign)
    tools.assert_is_instance(stmt.value, CreateList)
    tools.assert_equals([x.value for x in stmt.value.items], ["a]", "b"])


def test_booleans():
    statements = parse_code("""
a=true b=false
""")

    tools.assert_equals(len(statements), 2, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, Assign)
    tools.assert_equals(stmt.value.value, True)
    tools.assert_equals(statements[1].value.value, False)


def test_StringFormat():
    statements = parse_code("""
a="j{{o}}s"
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, Assign)
    tools.assert_is_instance(stmt.value, StringFormat)
    tools.assert_is_instance(stmt.value._variables[0][0], Reference)
    tools.assert_equals([x[0].name for x in stmt.value._variables], ["o"])


def test_StringFormat_2():
    statements = parse_code("""
a="j{{c.d}}s"
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, Assign)
    tools.assert_is_instance(stmt.value, StringFormat)
    tools.assert_equals(len(stmt.value._variables), 1)
    tools.assert_equals(len(stmt.value._variables[0]), 2)
    tools.assert_is_instance(stmt.value._variables[0][0], AttributeReference)
    tools.assert_equals(stmt.value._variables[0][0].instance.name, "c")
    tools.assert_equals(stmt.value._variables[0][0].attribute, "d")


def test_AttributeReference():
    statements = parse_code("""
a=a::b::c.d
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, Assign)
    tools.assert_is_instance(stmt.value, AttributeReference)
    tools.assert_is_instance(stmt.value.instance, Reference)
    tools.assert_equals(stmt.value.instance.full_name, "a::b::c")
    tools.assert_equals(stmt.value.attribute, "d")


def test_import():
    statements = parse_code("""
import std
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineImport)
    tools.assert_equals(stmt.name, "std")


def test_import2():
    statements = parse_code("""
import std "2"
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineImport)
    tools.assert_equals(stmt.name, "std")
    tools.assert_equals(stmt.versionspec, "2")


def test_import3():
    statements = parse_code("""
import std ">2.0"
""")

    tools.assert_equals(len(statements), 1, "Should return one statement")
    stmt = statements[0]
    tools.assert_is_instance(stmt, DefineImport)
    tools.assert_equals(stmt.name, "std")
    tools.assert_equals(stmt.versionspec, ">2.0")


def test_Lexer():
    parse_code("""
#test
//test2
a=0.5
b=""
""")


@raises(ParserException)
def test_Bad():
    parse_code("""
    a = b.c
a=a::b::c.
""")


@raises(ParserException)
def test_Bad2():
    parse_code("""
a=|
""")
