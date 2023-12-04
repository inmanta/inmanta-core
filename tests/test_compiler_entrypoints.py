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
import os
from collections import defaultdict

import more_itertools

from inmanta import compiler
from inmanta.ast import Range
from inmanta.compiler import Compiler
from inmanta.execute import scheduler


def test_anchors_basic(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string a = "a"
    string b
end

entity Test2 extends Test:
    foo c
end

Test.relation [0:1] -- Test2.reverse [0:]

typedef foo as string matching /^a+$/

a = Test(b="xx")
z = a.relation
u = a.b

implementation a for Test:

end

implement Test using a
""",
        autostd=False,
    )
    anchormap = compiler.anchormap()

    assert len(anchormap) == 9

    checkmap = {(r.lnr, r.start_char, r.end_char): t.location.lnr for r, t in anchormap}

    def verify_anchor(flnr, s, e, tolnr):
        assert checkmap[(flnr, s, e)] == tolnr

    for f, t in sorted(anchormap, key=lambda x: x[0].lnr):
        print("%s:%d -> %s" % (f, f.end_char, t))
    verify_anchor(7, 22, 26, 2)
    verify_anchor(8, 5, 8, 13)
    verify_anchor(11, 1, 5, 2)
    verify_anchor(11, 24, 29, 7)
    verify_anchor(15, 5, 9, 2)
    verify_anchor(15, 10, 11, 4)
    verify_anchor(19, 22, 26, 2)
    verify_anchor(23, 11, 15, 2)
    verify_anchor(23, 22, 23, 19)


def test_anchors_basic_old(snippetcompiler):
    """
    this test verify that the old path to generate the Anchormap still works. This ensure that we remain
    backward compatible with old Language servers.
    """
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string a = "a"
    string b
end

entity Test2 extends Test:
    foo c
end

Test.relation [0:1] -- Test2.reverse [0:]

typedef foo as string matching /^a+$/

a = Test(b="xx")
z = a.relation
u = a.b

implementation a for Test:

end

implement Test using a
""",
        autostd=False,
    )
    compiler = Compiler()
    (statements, blocks) = compiler.compile()
    sched = scheduler.Scheduler()
    anchormap = sched.anchormap(compiler, statements, blocks)

    assert len(anchormap) == 9
    assert all(isinstance(item[0], Range) and isinstance(item[1], Range) for item in anchormap)

    checkmap = {(r.lnr, r.start_char, r.end_char): t.lnr for r, t in anchormap}

    def verify_anchor(flnr, s, e, tolnr):
        assert checkmap[(flnr, s, e)] == tolnr

    for f, t in sorted(anchormap, key=lambda x: x[0].lnr):
        print("%s:%d -> %s" % (f, f.end_char, t))
    verify_anchor(7, 22, 26, 2)
    verify_anchor(8, 5, 8, 13)
    verify_anchor(11, 1, 5, 2)
    verify_anchor(11, 24, 29, 7)
    verify_anchor(15, 5, 9, 2)
    verify_anchor(15, 10, 11, 4)
    verify_anchor(19, 22, 26, 2)
    verify_anchor(23, 11, 15, 2)
    verify_anchor(23, 22, 23, 19)


def test_anchors_two(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    list a = ["a"]
    dict b
end

a = Test(b={})
z = a.a
u = a.b

implementation a for Test:

end

implement Test using a
""",
        autostd=False,
    )
    anchormap = compiler.anchormap()

    assert len(anchormap) == 5

    checkmap = {(r.lnr, r.start_char, r.end_char): t.location.lnr for r, t in anchormap}

    def verify_anchor(flnr, s, e, tolnr):
        assert checkmap[(flnr, s, e)] == tolnr

    for f, t in anchormap:
        print("%s:%d -> %s" % (f, f.end_char, t))
    verify_anchor(7, 5, 9, 2)
    verify_anchor(7, 10, 11, 4)
    verify_anchor(11, 22, 26, 2)
    verify_anchor(15, 22, 23, 11)
    verify_anchor(15, 11, 15, 2)


def test_anchors_plugin(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import tests

l = tests::length("Hello World!")
        """
    )
    anchormap = compiler.anchormap()
    location: Range
    resolves_to: Range
    location, resolves_to = more_itertools.one(
        (location, resolves_to)
        for location, resolves_to in anchormap
        if location.file == os.path.join(snippetcompiler.project_dir, "main.cf")
    )
    assert location.lnr == 4
    assert location.start_char == 5
    assert location.end_lnr == 4
    assert location.end_char == 18
    assert resolves_to.location.file == os.path.join(snippetcompiler.modules_dir, "tests", "plugins", "__init__.py")
    assert resolves_to.location.lnr == 14


def test_get_types_and_scopes(snippetcompiler):
    """
    Test the get_types_and_scopes() entrypoint of the compiler.
    """
    snippetcompiler.setup_for_snippet(
        """
    entity Test:
        string a = "a"
        string b
    end

    entity Test2 extends Test:
        foo c
    end

    Test.relation [0:1] -- Test2.reverse [0:]

    typedef foo as string matching /^a+$/

    a = Test(b="xx")
    z = a.relation
    u = a.b

    implementation a for Test:

    end

    implement Test using a

    """
    )

    (types, scopes) = compiler.get_types_and_scopes()

    # Verify types
    namespace_to_type_name = defaultdict(list)
    for type_name in types.keys():
        namespace = type_name.split("::")[0]
        namespace_to_type_name[namespace].append(type_name)

    assert len(namespace_to_type_name) == 2
    assert "__config__" in namespace_to_type_name
    assert "std" in namespace_to_type_name

    # Assert types in namespace __config__
    expected_types_in_config_ns = [
        "__config__::Test",
        "__config__::Test2",
        "__config__::foo",
        "__config__::a",
    ]
    assert sorted(namespace_to_type_name["__config__"]) == sorted(expected_types_in_config_ns)

    # Assert types in namespace std
    types_in_std_ns = namespace_to_type_name["std"]
    assert len(types_in_std_ns) > 1
    assert "std::Entity" in types_in_std_ns

    # Verify scopes
    assert scopes.get_name() == "__root__"
    assert sorted([scope.get_name() for scope in scopes.children()]) == sorted(["__config__", "std"])


def test_anchors_with_docs(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import tests

l = tests::length("Hello World!") # has a docstring
m = tests::empty("Hello World!") # has no docstring

entity Test:
    \"\"\"this is a test entity\"\"\"
end

entity Test_no_doc:
end

a = Test()
b = Test_no_doc()

implementation a for Test:
end

implementation b for Test_no_doc:
end

implement Test using a
implement Test_no_doc using b
""",
        autostd=False,
    )
    anchormap = compiler.anchormap()

    assert len(anchormap) == 10

    checkmap = {(r.lnr, r.start_char, r.end_char): t.docstring for r, t in anchormap}

    def verify_anchor(flnr, s, e, docs):
        assert checkmap[(flnr, s, e)] == docs

    for f, t in sorted(anchormap, key=lambda x: x[0].lnr):
        print("%s:%d -> %s docstring: %s" % (f, f.end_char, t, t.docstring))
    verify_anchor(4, 5, 18, "returns the length of the string")
    verify_anchor(5, 5, 17, None)
    verify_anchor(14, 5, 9, "this is a test entity")
    verify_anchor(15, 5, 16, None)
    verify_anchor(17, 22, 26, "this is a test entity")
    verify_anchor(20, 22, 33, None)
    verify_anchor(23, 22, 23, None)
    verify_anchor(23, 11, 15, "this is a test entity")
    verify_anchor(24, 29, 30, None)
    verify_anchor(24, 11, 22, None)


def test_constructor_with_inferred_namespace(snippetcompiler):
    """
    Test that the anchor for a constructor for an entity with an inferred namespace is correctly added to the anchormap
    The test checks if the anchormap correctly reflects the relationship between the
    source range (where the entity is instantiated: line 9 in main.cf) and the target range (where the
    entity is defined: line 1 in the _init.cf file of the tests module)
    """

    module: str = "tests"
    target_path = os.path.join(os.path.dirname(__file__), "data", "modules", module, "model", "_init.cf")

    snippetcompiler.setup_for_snippet(
        """
    import mod1
    import tests
    entity A:
    end

    A.mytest [1] -- tests::Test [1]

    A(mytest = Test())
    """,
        autostd=False,
    )

    compiler = Compiler()
    (statements, blocks) = compiler.compile()
    sched = scheduler.Scheduler()

    anchormap = sched.anchormap(compiler, statements, blocks)
    assert len(anchormap) == 5
    range_source = Range(os.path.join(snippetcompiler.project_dir, "main.cf"), 9, 16, 9, 20)
    range_target = Range(target_path, 1, 8, 1, 12)

    assert (range_source, range_target) in anchormap
