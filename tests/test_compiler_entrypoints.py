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

    checkmap = {(r.lnr, r.start_char, r.end_char): t.lnr for r, t in anchormap}

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
    assert resolves_to.file == os.path.join(snippetcompiler.modules_dir, "tests", "plugins", "__init__.py")
    assert resolves_to.lnr == 13


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
