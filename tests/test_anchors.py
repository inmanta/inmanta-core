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

implementation a for Test:

end

implement Test using a
""", autostd=False)
    anchormap = compiler.anchormap()

    assert len(anchormap) == 9

    checkmap = {(r.lnr, r.start_char, r.end_char): t.lnr for r, t in anchormap}

    def verify_anchor(flnr, s, e, tolnr):
        assert checkmap[(flnr, s, e)] == tolnr

    for f, t in anchormap:
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
