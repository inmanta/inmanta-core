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

import inmanta.compiler as compiler


def test_issue_261_tracing(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:
end

implementation test11 for Test1:
    Test2(name="test11")
end

implementation test12 for Test1:
    Test2(name="test12")
end

implement Test1 using test11
implement Test1 using test12

entity Test2:
    string name
end

implement Test2 using std::none

Test1()
        """
    )
    (types, _) = compiler.do_compile()

    t1s = types["__config__::Test1"].get_all_instances()
    assert len(t1s) == 1
    t1 = t1s[0]
    l3 = t1.trackers
    assert len(l3) == 1
    assert l3[0].namespace.name == "__config__"

    instances = types["__config__::Test2"].get_all_instances()
    assert len(instances) == 2
    for instance in instances:
        l1 = instance.trackers
        name = instance.get_attribute("name").get_value()
        assert len(l1) == 1
        implementations = l1[0].implements.implementations
        assert len(implementations) == 1
        implement = implementations[0]
        assert implement.name == name
        l2 = l1[0].instance
        assert l2 == t1

    for instance in instances:
        l1 = instance.trackers
        assert l1[0].get_next()[0].namespace.name == "__config__"


def test_trackingbug(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    bool z = true
end

entity B:
end

entity C:
end

entity E:
end

A.b [0:] -- B.a [0:]
A.b2 [0:] -- B.a2 [0:]
A.e [0:] -- E.a [0:]

C.a [0:] -- A.c [0:]

implement E using std::none
implement A using std::none



implementation c for C:
   E(a=self.a)
end
implement C using c

implementation b for B:
    C(a=self.a2)
end

implement B using b when std::count(self.a)>0

entity D:
end

implementation d for D:
    a = A()
    b = B()
    b.a = a
    b.a2 = a
end

implement D using d

D()
"""
    )
    (types, _) = compiler.do_compile()
    files = types["__config__::C"].get_all_instances()
    assert len(files) == 1


def test_747_entity_multi_location(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Alpha:
    string name
end

implementation none for Alpha:
end
implement Alpha using none

index Alpha(name)

a= Alpha(name="A")
b= Alpha(name="A")
c= Alpha(name="A")
""",
        autostd=False,
    )
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()
    assert len(a.get_locations()) == 3
    assert sorted([location.lnr for location in a.get_locations()]) == [12, 13, 14]
