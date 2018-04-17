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

from inmanta.ast import Namespace, LocatableString
from inmanta.ast.statements import define, Literal
from inmanta.parser.plyInmantaParser import parse
from inmanta.parser import ParserException
from inmanta.ast.statements.define import DefineImplement, DefineTypeConstraint, DefineTypeDefault, DefineIndex, DefineEntity,\
    DefineImplementInherits
from inmanta.ast.constraint.expression import GreaterThan, Regex, Not, And, IsDefined, In
from inmanta.ast.statements.generator import Constructor
from inmanta.ast.statements.call import FunctionCall
from inmanta.ast.statements.assign import Assign, CreateList, IndexLookup, StringFormat, CreateDict, ShortIndexLookup,\
    SetAttribute, MapLookup
from inmanta.ast.variables import Reference, AttributeReference
import pytest
from inmanta.execute.util import NoneValue


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

    assert len(statements) == 3

    stmt = statements[0]
    assert isinstance(stmt, define.DefineEntity)
    assert stmt.name == "Test"
    assert stmt.parents == ["std::Entity"]
    assert len(stmt.attributes) == 0
    assert stmt.comment is None


def test_undefine_default():
    statements = parse_code("""
entity Test extends Foo:
 string hello = undef
 string[] dinges = undef
end""")
    assert len(statements) == 1

    stmt = statements[0]
    assert isinstance(stmt, define.DefineEntity)
    assert stmt.name == "Test"
    assert stmt.parents == ["Foo"]
    assert len(stmt.attributes) == 2
    assert stmt.comment is None

    for ad in stmt.attributes:
        assert isinstance(ad.type, LocatableString)
        assert isinstance(ad.name, LocatableString)
        assert ad.default is None
        assert ad.remove_default

    assert str(stmt.attributes[0].name) == "hello"
    assert str(stmt.attributes[1].name) == "dinges"


def test_extend_entity():
    """Test extending entities
    """
    statements = parse_code("""
entity Test extends Foo:
end
""")

    assert len(statements) == 1

    stmt = statements[0]
    assert stmt.parents == ["Foo"]


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
    number? ten=5
end
""" % documentation)

    assert len(statements) == 1

    stmt = statements[0]
    assert len(stmt.parents) == 2
    assert stmt.parents == ["Foo", "foo::sub::Bar"]
    assert str(stmt.comment).strip() == documentation
    assert len(stmt.attributes) == 3

    for ad in stmt.attributes:
        assert isinstance(ad.type, LocatableString)
        assert isinstance(ad.name, LocatableString)

    assert str(stmt.attributes[0].name) == "hello"
    assert str(stmt.attributes[1].name) == "bar"
    assert str(stmt.attributes[2].name) == "ten"

    assert stmt.attributes[1].default.execute(None, None, None)

    assert stmt.attributes[2].default.execute(None, None, None) == 5


def test_relation():
    """Test definition of relations
    """
    statements = parse_code("""
Test tests [0:] -- [5:10] Foo bars
""")

    assert len(statements) == 1
    rel = statements[0]

    assert len(rel.left) == 3
    assert len(rel.right) == 3

    assert str(rel.left[0]) == "Test"
    assert str(rel.right[0]) == "Foo"

    assert str(rel.left[1]) == "tests"
    assert str(rel.right[1]) == "bars"

    assert rel.left[2] == (0, None)
    assert rel.right[2] == (5, 10)
    assert statements[0].requires is None


def test_relation_2():
    """Test definition of relations
    """
    statements = parse_code("""
Test tests [3] -- [:10] Foo bars
""")

    assert len(statements) == 1
    rel = statements[0]

    assert len(rel.left) == 3
    assert len(rel.right) == 3

    assert str(rel.left[0]) == "Test"
    assert str(rel.right[0]) == "Foo"

    assert str(rel.left[1]) == "tests"
    assert str(rel.right[1]) == "bars"

    assert rel.left[2] == (3, 3)
    assert rel.right[2] == (None, 10)
    assert statements[0].requires is None


def test_new_relation():
    """Test definition of relations
    """
    statements = parse_code("""
Test.bar [1] -- Foo.tests [5:10]
""")

    assert len(statements) == 1, "Should return four statements"
    rel = statements[0]

    assert len(rel.left) == 3
    assert len(rel.right) == 3

    assert str(rel.left[0]) == "Test"
    assert str(rel.right[0]) == "Foo"

    assert str(rel.left[1]) == "tests"
    assert str(rel.right[1]) == "bar"

    assert rel.left[2] == (5, 10)
    assert rel.right[2] == (1, 1)
    assert statements[0].requires is None


def test_new_relation_with_annotations():
    """Test definition of relations
    """
    statements = parse_code("""
Test.bar [1] foo,bar Foo.tests [5:10]
""")

    assert len(statements) == 1, "Should return four statements"
    rel = statements[0]

    assert len(rel.left) == 3
    assert len(rel.right) == 3

    assert str(rel.left[0]) == "Test"
    assert str(rel.right[0]) == "Foo"

    assert str(rel.left[1]) == "tests"
    assert str(rel.right[1]) == "bar"

    assert rel.left[2] == (5, 10)
    assert rel.right[2] == (1, 1)
    assert statements[0].requires is None
    assert len(rel.annotations) == 2
    assert rel.annotation_expression[0][1].name == "foo"
    assert rel.annotation_expression[1][1].name == "bar"


def test_new_relation_unidir():
    """Test definition of relations
    """
    statements = parse_code("""
Test.bar [1] -- Foo
""")

    assert len(statements) == 1, "Should return four statements"
    rel = statements[0]

    assert len(rel.left) == 3
    assert len(rel.right) == 3

    assert str(rel.left[0]) == "Test"
    assert str(rel.right[0]) == "Foo"

    assert (rel.left[1]) is None
    assert str(rel.right[1]) == "bar"

    assert rel.left[2] is None
    assert rel.right[2] == (1, 1)
    assert statements[0].requires is None


def test_new_relation_with_annotations_unidir():
    """Test definition of relations
    """
    statements = parse_code("""
Test.bar [1] foo,bar Foo
""")

    assert len(statements) == 1, "Should return four statements"
    rel = statements[0]

    assert len(rel.left) == 3
    assert len(rel.right) == 3

    assert str(rel.left[0]) == "Test"
    assert str(rel.right[0]) == "Foo"

    assert rel.left[1] is None
    assert str(rel.right[1]) == "bar"

    assert rel.left[2] is None
    assert rel.right[2] == (1, 1)
    assert statements[0].requires is None
    assert len(rel.annotations) == 2
    assert rel.annotation_expression[0][1].name == "foo"
    assert rel.annotation_expression[1][1].name == "bar"


def test_implementation():
    """Test the definition of implementations
    """
    statements = parse_code("""
implementation test for Test:
end
""")

    assert len(statements) == 1
    assert len(statements[0].block.get_stmts()) == 0
    assert statements[0].name == "test"
    assert isinstance(statements[0].entity, str)

    statements = parse_code("""
implementation test for Test:
    std::File(attr="a")
    var = hello::func("world")
end
""")

    assert len(statements) == 1
    assert len(statements[0].block.get_stmts()) == 2


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

    assert len(statements) == 1
    assert len(statements[0].block.get_stmts()) == 1


def test_implements():
    """Test implements with no selector
    """
    statements = parse_code("""
implement Test using test
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineImplement)
    assert str(stmt.entity) == "Test"
    assert stmt.implementations == ["test"]
    assert str(stmt.select) == "True"


def test_implements_2():
    """Test implements with selector
    """
    statements = parse_code("""
implement Test using test, blah when (self > 5)
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineImplement)
    assert str(stmt.entity) == "Test"
    assert stmt.implementations == ["test", "blah"]
    assert isinstance(stmt.select, GreaterThan)
    assert stmt.select.children[0].name == 'self'
    assert stmt.select.children[1].value == 5


def test_implements_parent():
    statements = parse_code("""
implement Test using parents  \""" testc \"""
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineImplementInherits)
    assert stmt.entity == "Test"


def test_implements_selector():
    """Test implements with selector
    """
    statements = parse_code("""
implement Test using test when not (fg(self) and false)
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineImplement)
    assert stmt.entity == "Test"
    assert stmt.implementations == ["test"]
    assert isinstance(stmt.select, Not)
    assert isinstance(stmt.select.children[0], And)
    assert isinstance(stmt.select.children[0].children[0], FunctionCall)
    assert isinstance(stmt.select.children[0].children[1], Literal)


def test_regex():
    statements = parse_code("""
a = /[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}/
""")

    assert len(statements) == 1
    stmt = statements[0].value
    assert isinstance(stmt, Regex)
    assert stmt.children[1].value == re.compile(r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}")


def test_regex_escape():
    statements = parse_code("""
a = /\/1/
""")

    assert len(statements) == 1
    stmt = statements[0].value
    assert isinstance(stmt, Regex)
    assert stmt.children[1].value == re.compile(r"\/1")


def test_regex_twice():
    statements = parse_code("""
a = /\/1/
b = "v"
c = /\/1/
""")

    assert len(statements) == 3
    stmt = statements[0].value
    assert isinstance(stmt, Regex)
    assert stmt.children[1].value == re.compile(r"\/1")


def test_typedef():
    statements = parse_code("""
typedef uuid as string matching /[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}/
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineTypeConstraint)
    assert str(stmt.name) == "uuid"
    assert stmt.basetype == "string"
    assert isinstance(stmt.get_expression(), Regex)
    assert (stmt.get_expression().children[1].value ==
            re.compile(r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"))


def test_typedef_in():
    statements = parse_code("""
typedef abc as string matching self in ["a","b","c"]
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineTypeConstraint)
    assert str(stmt.name) == "abc"
    assert stmt.basetype == "string"
    assert isinstance(stmt.get_expression(), In)
    assert ([x.value for x in stmt.get_expression().children[1].items] ==
            ["a", "b", "c"])


def test_typedef2():
    statements = parse_code("""
typedef ConfigFile as File(mode = 644, owner = "root", group = "root")
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineTypeDefault)
    assert stmt.name == "ConfigFile"
    assert isinstance(stmt.ctor, Constructor)


def test_index():
    statements = parse_code("""
index File(host, path)
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineIndex)
    assert stmt.type == "File"
    assert stmt.attributes == ["host", "path"]


def test_ctr():
    statements = parse_code("""
File(host = 5, path = "Jos")
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Constructor)
    assert str(stmt.class_type) == "File"
    assert {k: v.value for k, v in stmt.attributes.items()} == {"host": 5, "path": "Jos"}


def test_indexlookup():
    statements = parse_code("""
a=File[host = 5, path = "Jos"]
""")

    assert len(statements) == 1
    stmt = statements[0].value
    assert isinstance(stmt, IndexLookup)
    assert stmt.index_type == "File"
    assert {k: v.value for k, v in stmt.query} == {"host": 5, "path": "Jos"}


def test_short_index_lookup():
    statements = parse_code("""
a = vm.files[path="/etc/motd"]
""")

    assert len(statements) == 1
    stmt = statements[0].value
    assert isinstance(stmt, ShortIndexLookup)
    assert isinstance(stmt.rootobject, Reference)
    assert stmt.rootobject.name == "vm"
    assert stmt.relation == "files"
    assert {k: v.value for k, v in stmt.querypart} == {"path": "/etc/motd"}


def test_ctr_2():
    statements = parse_code("""
File( )
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Constructor)
    assert str(stmt.class_type) == "File"
    assert {k: v.value for k, v in stmt.attributes.items()} == {}


def test_function():
    statements = parse_code("""
file( )
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, FunctionCall)
    assert stmt.name == "file"


def test_function_2():
    statements = parse_code("""
file(b)
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, FunctionCall)
    assert stmt.name == "file"


def test_function_3():
    statements = parse_code("""
file(b,)
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, FunctionCall)
    assert stmt.name == "file"


def test_list_def():
    statements = parse_code("""
a=["a]","b"]
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, CreateList)
    assert [x.value for x in stmt.value.items] == ["a]", "b"]


def test_list_def_trailing_comma():
    statements = parse_code("""
a=["a]","b",]
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, CreateList)
    assert [x.value for x in stmt.value.items] == ["a]", "b"]


def test_map_def():
    statements = parse_code("""
a={ "a":"b", "b":1}
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, CreateDict)
    assert [(x[0], x[1].value) for x in stmt.value.items] == [("a", "b"), ("b", 1)]


def test_map_def_var():
    statements = parse_code("""a={ "b":b}""")
    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, CreateDict)
    assert isinstance(stmt.value.items[0][1], Reference)


def test_map_def_list():
    statements = parse_code("""a={ "a":["a"]}""")
    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, CreateDict)
    assert isinstance(stmt.value.items[0][1], CreateList)


def test_map_def_map():
    statements = parse_code("""a={ "a":{"a":"C"}}""")
    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, CreateDict)
    assert isinstance(stmt.value.items[0][1], CreateDict)


def test_booleans():
    statements = parse_code("""
a=true b=false
""")

    assert len(statements) == 2
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert stmt.value.value
    assert not statements[1].value.value


def test_none():
    statements = parse_code("""
a=null
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value.value, NoneValue)


def test_numbers():
    statements = parse_code("""
a=1
b=2.0
c=-5
d=-0.256
""")

    assert len(statements) == 4
    values = [1, 2.0, -5, -0.256]
    for i in range(4):
        stmt = statements[i]
        assert isinstance(stmt, Assign)
        assert stmt.value.value == values[i]


def test_string():
    statements = parse_code("""
a="jos"
""")
    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, Literal)
    assert stmt.value.value == "jos"


def test_string_2():
    statements = parse_code("""
a='jos'
""")
    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, Literal)
    assert stmt.value.value == "jos"


def test_empty():
    statements = parse_code("""
a=""
""")
    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, Literal)
    assert stmt.value.value == ""


def test_empty_2():
    statements = parse_code("""
a=''
""")
    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, Literal)
    assert stmt.value.value == ""


def test_string_format():
    statements = parse_code("""
a="j{{o}}s"
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, StringFormat)
    assert isinstance(stmt.value._variables[0][0], Reference)
    assert [x[0].name for x in stmt.value._variables] == ["o"]


def test_string_format_2():
    statements = parse_code("""
a="j{{c.d}}s"
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, StringFormat)
    assert len(stmt.value._variables) == 1
    assert len(stmt.value._variables[0]) == 2
    assert isinstance(stmt.value._variables[0][0], AttributeReference)
    assert stmt.value._variables[0][0].instance.name == "c"
    assert stmt.value._variables[0][0].attribute == "d"


def test_attribute_reference():
    statements = parse_code("""
a=a::b::c.d
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, AttributeReference)
    assert isinstance(stmt.value.instance, Reference)
    assert stmt.value.instance.full_name == "a::b::c"
    assert stmt.value.attribute == "d"


def test_is_defined():
    statements = parse_code("""
implement Test1 using tt when self.other is defined
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineImplement)
    assert isinstance(stmt.select, IsDefined)
    assert stmt.select.attr.name == 'self'
    assert stmt.select.name == 'other'


def test_is_defined_implicit_self():
    statements = parse_code("""
implement Test1 using tt when other is defined
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineImplement)
    assert isinstance(stmt.select, IsDefined)
    assert stmt.select.attr.name == 'self'
    assert stmt.select.name == 'other'


def test_is_defined_short():
    statements = parse_code("""
implement Test1 using tt when a.other is defined
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineImplement)
    assert isinstance(stmt.select, IsDefined)
    assert isinstance(stmt.select.attr, AttributeReference)
    assert stmt.select.attr.instance.name == 'self'
    assert stmt.select.attr.attribute == 'a'
    assert stmt.select.name == 'other'


def assert_is_non_value(x):
    assert isinstance(x, Literal)
    assert isinstance(x.value, NoneValue)


def compare_attr(attr, name, mytype, defs, multi=False, opt=False):
    assert str(attr.name) == name
    defs(attr.default)
    assert attr.multi == multi
    assert str(attr.type) == mytype
    assert attr.nullable == opt


def assert_is_none(x):
    assert x is None


def assert_equals(x, y):
    assert x == y


def test_define_list_attribute():
    statements = parse_code("""
entity Jos:
  bool[] bar
  ip::ip[] ips = ["a"]
  string[] floom = []
  string[] floomx = ["a", "b"]
  string[]? floomopt = null
end""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineEntity)
    assert len(stmt.attributes) == 5

    compare_attr(stmt.attributes[0], "bar", "bool", assert_is_none, multi=True)
    compare_attr(stmt.attributes[2], "floom", "string", lambda x: assert_equals([], x.items), multi=True)

    def compare_default(list):
        def comp(x):
            assert len(list) == len(x.items)
            for one, it in zip(list, x.items):
                assert isinstance(it, Literal)
                assert it.value == one
        return comp
    compare_attr(stmt.attributes[1], "ips", "ip::ip", compare_default(['a']), multi=True)
    compare_attr(stmt.attributes[3], "floomx", "string", compare_default(['a', 'b']), multi=True)
    compare_attr(stmt.attributes[4], "floomopt", "string", assert_is_non_value, opt=True, multi=True)


def test_define_dict_attribute():
    statements = parse_code("""
entity Jos:
  dict bar
  dict foo = {}
  dict blah = {"a":"a"}
  dict? xxx = {"a":"a"}
  dict? xxxx = null
end""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineEntity)
    assert len(stmt.attributes) == 5

    compare_attr(stmt.attributes[0], "bar", "dict", assert_is_none)
    compare_attr(stmt.attributes[1], "foo", "dict", lambda x: assert_equals([], x.items))

    def compare_default(list):
        def comp(x):
            assert len(list) == len(x.items)
            for (ok, ov), (k, v) in zip(list, x.items):
                assert k == ok
                assert ov == v.value
        return comp
    compare_attr(stmt.attributes[2], "blah", "dict", compare_default([('a', 'a')]))
    compare_attr(stmt.attributes[3], "xxx", "dict", compare_default([('a', 'a')]), opt=True)
    compare_attr(stmt.attributes[4], "xxxx", "dict", assert_is_non_value, opt=True)


def test_lexer():
    parse_code("""
#test
//test2
a=0.5
b=""
""")


def test_eol_comment():
    parse_code("""a="a"
    # valid_target_types: tosca.capabilities.network.Bindable""")


def test_mls():
    statements = parse_code("""
entity MANO:
    \"""
        This entity provides management, orchestration and monitoring

        More test
    \"""
end
""")
    assert len(statements) == 1
    stmt = statements[0]

    assert isinstance(stmt, DefineEntity)

    mls = stmt.comment

    print(mls)

    assert str(mls) == """
        This entity provides management, orchestration and monitoring

        More test
    """


def test_bad():
    with pytest.raises(ParserException):
        parse_code("""
a = b.c
a=a::b::c.
""")


def test_bad_2():
    with pytest.raises(ParserException):
        parse_code("""
a=|
""")


def test_error_on_relation():
    with pytest.raises(ParserException) as e:
        parse_code("""
Host.provider [1] -- Provider test""")
    assert e.value.location.file == "test"
    assert e.value.location.lnr == 3
    assert e.value.location.start_char == 2


def test_doc_string_on_new_relation():
    statements = parse_code("""
File.host [1] -- Host
\"""
Each file needs to be associated with a host
\"""
""")
    assert len(statements) == 1

    stmt = statements[0]
    assert str(stmt.comment).strip() == "Each file needs to be associated with a host"


def test_doc_string_on_relation():
    statements = parse_code("""
File file [1] -- [0:] Host host
\"""
Each file needs to be associated with a host
\"""
""")
    assert len(statements) == 1

    stmt = statements[0]
    assert str(stmt.comment).strip() == "Each file needs to be associated with a host"


def test_doc_string_on_typedef():
    statements = parse_code("""
typedef foo as string matching /^a+$/
\"""
    Foo is a stringtype that only allows "a"
\"""
""")
    assert len(statements) == 1

    stmt = statements[0]
    assert str(stmt.comment).strip() == "Foo is a stringtype that only allows \"a\""


def test_doc_string_on_typedefault():
    statements = parse_code("""
typedef Foo as File(x=5)
\"""
    Foo is a stringtype that only allows "a"
\"""
""")
    assert len(statements) == 1

    stmt = statements[0]
    assert str(stmt.comment).strip() == "Foo is a stringtype that only allows \"a\""


def test_doc_string_on_impl():
    statements = parse_code("""
implementation test for Host:
    \"""
        Bla bla
    \"""
end
""")
    assert len(statements) == 1

    stmt = statements[0]
    assert str(stmt.comment).strip() == "Bla bla"


def test_doc_string_on_implements():
    statements = parse_code("""
implement Host using test
\"""
    Always use test!
\"""
\"""
    Not a comment
\"""

""")
    assert len(statements) == 2

    stmt = statements[0]
    assert str(stmt.comment).strip() == "Always use test!"


def test_precise_lexer_positions():
    statements = parse_code("""
implement Test1 using tt when self.other is defined
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, DefineImplement)
    assert isinstance(stmt.select, IsDefined)
    assert stmt.select.attr.name == 'self'
    assert str(stmt.select.name) == 'other'


def test_list_extend_bad():
    with pytest.raises(ParserException):
        parse_code("""
    a+=b
    """)


def test_list_extend_good():
    statements = parse_code("""
z.a+=b
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, SetAttribute)
    assert stmt.list_only is True
    assert isinstance(stmt.value, Reference)
    assert stmt.value.name == "b"


def test_mapref():
    """Test extending entities
    """
    statements = parse_code("""
a = b.c["test"]
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, MapLookup)
    assert isinstance(stmt.value.themap, AttributeReference)
    assert stmt.value.themap.instance.name == "b"
    assert stmt.value.themap.attribute == "c"
    assert isinstance(stmt.value.key, Literal)
    assert stmt.value.key.value == "test"


def test_mapref_2():
    """Test extending entities
    """
    statements = parse_code("""
a = c["test"]
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, MapLookup)
    assert isinstance(stmt.value.themap, Reference)
    assert stmt.value.themap.name == "c"
    assert isinstance(stmt.value.key, Literal)
    assert stmt.value.key.value == "test"


def test_map_multi_ref():
    """Test extending entities
    """
    statements = parse_code("""
a = c["test"]["xx"]
""")

    assert len(statements) == 1
    stmt = statements[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, MapLookup)
    assert isinstance(stmt.value.themap, MapLookup)
    assert isinstance(stmt.value.themap.themap, Reference)
    assert stmt.value.themap.themap.name == "c"
    assert isinstance(stmt.value.key, Literal)
    assert stmt.value.key.value == "xx"
    assert isinstance(stmt.value.themap.key, Literal)
    assert stmt.value.themap.key.value == "test"
