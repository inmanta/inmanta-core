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

import pytest

import inmanta.compiler as compiler
from inmanta.ast import DuplicateException, TypingException
from inmanta.execute.proxy import UnsetException


def test_issue_127_default_overrides(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
f1=std::ConfigFile(host=std::Host(name="jos",os=std::linux), path="/tmp/test", owner="wouter", content="blabla")
        """
    )
    (types, _) = compiler.do_compile()
    instances = types["std::File"].get_all_instances()
    assert instances[0].get_attribute("owner").get_value() == "wouter"


def test_issue_135_duplo_relations(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2
Test1 test1 [0:1] -- [0:] Test2 test2
"""
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_224_default_over_inheritance(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:
    string a = "a"
end
entity Test2 extends Test1:
end
entity Test3 extends Test2:
end
implement Test3 using std::none

Test3()
"""
    )
    (types, _) = compiler.do_compile()
    instances = types["__config__::Test3"].get_all_instances()
    assert len(instances) == 1
    i = instances[0]
    assert i.get_attribute("a").get_value() == "a"


def test_275_default_override(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity A:
        bool at = true
    end
    implement A using std::none

    entity B extends A:
        bool at = false
    end
    implement B using std::none

    a = A()
    b = B()

    """
    )

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a")
    assert a.get_value().get_attribute("at").get_value() is True
    b = root.lookup("b")
    assert b.get_value().get_attribute("at").get_value() is False


def test_275_default_diamond(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity A:
        bool at = true
    end
    implement A using std::none

    entity B:
        bool at = false
    end
    implement B using std::none

    entity C extends A,B:
    end
    implement C using std::none

    entity D extends B,A:
    end
    implement D using std::none

    a = A()
    b = B()
    c = C()
    d = D()
    """
    )

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a")
    assert a.get_value().get_attribute("at").get_value() is True
    b = root.lookup("b")
    assert b.get_value().get_attribute("at").get_value() is False
    c = root.lookup("c")
    assert c.get_value().get_attribute("at").get_value() is True
    d = root.lookup("d")
    assert d.get_value().get_attribute("at").get_value() is False


def test_275_duplicate_parent(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity A:
        bool at = true
    end
    implement A using std::none

    entity B extends A,A:
        bool at = false
    end
    implement B using std::none
    """
    )
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_default_remove(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity A:
        bool at = true
    end
    implement A using std::none

    entity B extends A:
        bool at = undef
    end
    implement B using std::none

    a = A()
    b = B()
    """
    )
    with pytest.raises(UnsetException):
        compiler.do_compile()


def test_gradual_default(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Server:
    string a="a"
    string b
end

typedef Server2 as Server(b="b")

Server2()

implement Server using std::none
"""
    )
    compiler.do_compile()


def test_default_on_relation(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Server:
    string a="a"
    string b
end

entity Option:
end

Server.options [0:] -- Option

all = Option()

typedef Server2 as Server(b="b", options=all)

Server2()

implement Server using std::none
implement Option using std::none
"""
    )
    compiler.do_compile()


def test_1292_default_type_check(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    number t = "str"
end

Test(t=5)
        """,
        "Invalid value 'str', expected Number (reported in number t = 'str' ({dir}/main.cf:3:12))",
    )


def test_1292_default_type_check2(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    string[]? t = [1, "str"]
end

implement Test using std::none

Test(t = ["str"])
        """,
        "Invalid value '1', expected String (reported in string[]? t = List() ({dir}/main.cf:3:15))",
    )


def test_1292_default_type_check3(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    number? t = [1, 2]
end

implement Test using std::none

Test(t = 12)
        """,
        "Invalid value '[1, 2]', expected Number (reported in number? t = List() ({dir}/main.cf:3:13))",
    )


def test_1292_default_type_check4(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
typedef digit as number matching self > 0 and self < 10

entity Test:
    digit t = 12
end

implement Test using std::none

Test(t = 8)
        """,
        "Invalid value 12, does not match constraint `((self > 0) and (self < 10))`"
        " (reported in digit t = 12 ({dir}/main.cf:5:11))",
    )


def test_1292_default_type_check5(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    number t = "str"
end
        """,
        "Invalid value 'str', expected Number (reported in number t = 'str' ({dir}/main.cf:3:12))",
    )


def test_1725_default_type_check_with_plugin(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    std::date d = "2020-01-22"
end
        """,
    )
    compiler.do_compile()


def test_1725_default_type_check_with_plugin_incorrect(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    std::date d = "nodatevalue"
end
        """,
        "Invalid value 'nodatevalue', does not match constraint `(std::validate_type('datetime.date',self) == true)`"
        " (reported in std::date d = 'nodatevalue' ({dir}/main.cf:3:15))",
    )
