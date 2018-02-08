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
from inmanta import compiler
from inmanta.ast import Anchor


def test_anchors_basic(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
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
""", autostd=False)
    anchormap = compiler.anchormap()

    assert len(anchormap) == 6

    checkmap = {(r.lnr, r.start_char, r.end_char): t.lnr for r, t in anchormap}

    def verify_anchor(flnr, s, e, tolnr):
        assert checkmap[(flnr, s, e)] == tolnr

    for f, t in anchormap:
        print("%s -> %s" % (f, t))
    verify_anchor(7, 21, 25, 2)
    verify_anchor(8, 4, 7, 13)
    verify_anchor(11, 0, 4, 2)
    verify_anchor(11, 23, 28, 7)
    verify_anchor(15, 4, 8, 2)
    verify_anchor(15, 9, 10, 4)

