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

import re

import pytest

import inmanta.compiler as compiler
from inmanta.ast import DuplicateException, IndexException, NotFoundException, RuntimeException, TypeNotFoundException
from inmanta.ast.statements.generator import IndexAttributeMissingInConstructorException, IndexCollisionException
from inmanta.compiler.help.explainer import ExplainerFactory


def test_issue_121_non_matching_index(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
        a=std::Host[name="test"]
        """,
        autostd=True,
    )

    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except NotFoundException as e:
        assert e.location.lnr == 2


def test_issue_122_index_inheritance(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity TopResource:
    string name
end

index TopResource(name)

entity TestResource extends TopResource:
    bool enabled=true
end

implementation testRes for TestResource:
    self.name="test"
end

implement TestResource using testRes

TestResource()
        """
    )

    with pytest.raises(IndexAttributeMissingInConstructorException) as e:
        compiler.do_compile()
    assert e.value.location.lnr == 18


def test_issue_140_index_error(snippetcompiler):
    try:
        snippetcompiler.setup_for_snippet(
            """
        h = std::Host(name="test", os=std::linux)
        test = std::Service[host=h, path="test"]""",
            autostd=True,
        )
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except NotFoundException as e:
        assert re.match(".*No index defined on std::Service for this lookup:.*", str(e))


@pytest.mark.parametrize("explicit", [True, False])
def test_issue_745_2689_index_on_optional(snippetcompiler, explicit: bool):
    with pytest.raises(IndexException):
        snippetcompiler.setup_for_snippet(
            """
entity A:
    string name
end

A.opt [%s:1] -- A

index A(name,opt)
"""
            % ("0" if explicit else "")
        )
        compiler.do_compile()


def test_issue_745_index_on_multi(snippetcompiler):
    with pytest.raises(IndexException):
        snippetcompiler.setup_for_snippet(
            """
entity A:
    string name
end

A.opt [1:] -- A

index A(name,opt)
"""
        )
        compiler.do_compile()


def test_issue_index_on_not_existing(snippetcompiler):
    with pytest.raises(TypeNotFoundException):
        snippetcompiler.setup_for_snippet(
            """
index A(name)
"""
        )
        compiler.do_compile()


def test_issue_212_bad_index_defintion(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:
    string x
end
index Test1(x,y)
"""
    )
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_index_on_subtype(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
        host = std::Host(name="a",os=std::linux)
        a=std::DefaultDirectory(host=host,path="/etc")
        b=std::DefaultDirectory(host=host,path="/etc")
    """,
        autostd=True,
    )

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a")
    b = root.lookup("b")

    assert a.get_value() == b.get_value()


def test_index_on_subtype2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
        import std::testing

        entity NullResourceBis extends std::testing::NullResource:
        end

        a=std::testing::NullResource(name="test", agentname="agent1", fail=false)
        b=NullResourceBis(name="test", agentname="agent1")
    """
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


diamond = """
entity A:
    string at = "a"
end
implement A using none

entity B:
    string at = "a"
end
implement B using none


entity C extends A,B:
end
implement C using none

implementation none for std::Entity:
end
"""


def test_index_on_subtype_diamond(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        diamond
        + """
    index A(at)
    index B(at)

    a = A(at="a")
    b = C(at="a")
    """
    )

    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_index_on_subtype_diamond_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        diamond
        + """
    index A(at)
    index B(at)

    a = A(at="a")
    b = B(at="a")
    """
    )
    compiler.do_compile()


def test_index_on_subtype_diamond_3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        diamond
        + """
    index A(at)
    index B(at)

    a = A(at="a")
    b = B(at="ab")
    """
    )
    compiler.do_compile()


def test_index_on_subtype_diamond_4(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        diamond
        + """
    index A(at)
    index B(at)

    a = C(at="a")
    b = C(at="a")
    a=b
    """
    )
    (types, _) = compiler.do_compile()
    c = types["__config__::C"]
    assert len(c.get_indices()) == 1


def test_394_short_index(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """implementation none for std::Entity:

end

entity Host:
    string name
    string blurp
end

entity File:
    string name
end

implement Host using none
implement File using none

Host.files [0:] -- File.host [1]

index Host(name)
index File(host, name)

h1 = Host(name="h1", blurp="blurp1")
f1h1=File(host=h1,name="f1")
f2h1=File(host=h1,name="f2")

z = h1.files[name="f1"]
"""
    )
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    z = root.lookup("z").get_value()
    f1h1 = root.lookup("f1h1").get_value()
    assert z is f1h1


def test_394_short_index_bad(snippetcompiler):
    snippetcompiler.setup_for_error(
        """implementation none for std::Entity:

end

entity Host:
    string name
    string blurp
end

entity File:
    string name
end

implement Host using none
implement File using none

Host.files [0:] -- File
File.host [1] -- Host

index Host(name)
index File(host, name)

h1 = Host(name="h1", blurp="blurp1")

h1.files = f1h1
h1.files = f2h1

f1h1=File(host=h1,name="f1")
f2h1=File(host=h1,name="f2")

z = h1.files[name="f1"]
""",
        "short index lookup is only possible on bi-drectional relations, __config__::Host.files is unidirectional"
        " (reported in h1.files[[('name', 'f1')]] ({dir}/main.cf:31))",
    )


def test_511_index_on_default(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string a="a"
    string b
end

index Test(a, b)

implement Test using none

Test(b="b")

implementation none for std::Entity:
end
"""
    )
    compiler.do_compile()


def test_index_undefined_attribute(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        index std::Entity(foo, bar)
    """,
        "Attribute 'foo' referenced in index is not defined in entity std::Entity (reported in index "
        "std::Entity(foo, bar) ({dir}/main.cf:2))",
    )


def test_747_index_collisions(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity Test:
            string name
            string value
        end

        implementation none for Test:
        end

        implement Test using none

        index Test(name)
        Test(name="A", value="a")
        Test(name="A", value="b")

        """,
        """Could not set attribute `value` on instance `__config__::Test (instantiated at {dir}/main.cf:13,{dir}/main.cf:14)` (reported in Construct(Test) ({dir}/main.cf:14))
caused by:
  value set twice:
\told value: a
\t\tset at {dir}/main.cf:13
\tnew value: b
\t\tset at {dir}/main.cf:14
 (reported in Construct(Test) ({dir}/main.cf:14))""",  # noqa: E501
    )


def test_747_index_collisions_invisible(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity Test:
            string name
            string value
        end

        implementation none for Test:
        end

        implement Test using none

        index Test(name)

        for v in ["a","b"]:
            Test(name="A", value=v)
        end

        """,
        """Could not set attribute `value` on instance `__config__::Test (instantiated at {dir}/main.cf:15,{dir}/main.cf:15)` (reported in Construct(Test) ({dir}/main.cf:15))
caused by:
  value set twice:
\told value: a
\t\tset at {dir}/main.cf:15:34
\tnew value: b
\t\tset at {dir}/main.cf:15:34
 (reported in Construct(Test) ({dir}/main.cf:15))""",  # noqa: E501
    )


def test_index_collission_error_reporting(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Site:
end

entity Tier:
    string type
end

entity SubTier extends Tier:

end

index Tier(type)

Site.tier [1] -- Tier

implementation tiers for Site:
    # Only fails when assignment is inside the implementation
    # Does not fail when in ctor or s = Site(); s.tier = ...
    self.tier = Tier(type="api")
    self.tier = SubTier(type="api")
end

implement Site using tiers
implement Tier using none
implement SubTier using none

Site()

implementation none for std::Entity:
end
    """,
        """Could not set attribute `tier` on instance `__config__::Site (instantiated at {dir}/main.cf:28)` (reported in self.tier = Construct(Tier) ({dir}/main.cf:20))
caused by:
  Type found in index is not an exact match (original at ({dir}/main.cf:20)) (duplicate at ({dir}/main.cf:21))""",  # noqa: E501
    )


def test_index_lookup(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string a
end

index Test(a)

implement Test using none

b = Test(a="b")
a = Test(a="a")

ar = Test[a="a"]

implementation none for std::Entity:
end
        """
    )
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()
    ar = root.lookup("ar").get_value()
    assert a is ar


def test_index_lookup_double_argument(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    string a
end

index Test(a)

implement Test using none

b = Test(a="b")
a = Test(a="a")

ar = Test[a="a", a="b"]

implementation none for std::Entity:
end
        """,
        "Attribute a provided twice in index lookup (reported in Test[[('a', 'a'), ('a', 'b')]] ({dir}/main.cf:13))",
    )


def test_1652_index_on_missing_type_location(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test_A:
    string name
end

index TestA(name)
        """,
        "could not find type TestA in namespace __config__ ({dir}/main.cf:6:7)",
    )


@pytest.mark.parametrize("use_wrapped_kwargs", [True, False])
def test_index_attribute_missing_in_constructor_call(snippetcompiler, use_wrapped_kwargs: bool) -> None:
    """
    Assert correct error message when index attribute is not set in the constructor call.
    """
    model = f"""
entity Test_A:
    int id
    string name
end

index Test_A(name)

implement Test_A using none

Test_A({'id=1' if not use_wrapped_kwargs else '**{"id": 1}'})

implementation none for std::Entity:
end
    """

    snippetcompiler.setup_for_error_re(
        model,
        re.escape(
            "Invalid Constructor call:\n\t* Missing attribute 'name'. "
            "The attribute __config__::Test_A.name is part of an index."
        ),
    )


def test_index_collision_exception(snippetcompiler) -> None:
    """
    Test that an IndexCollisionException is raised when an index collision is detected and that the correct
    explanation is displayed.
    """
    snippetcompiler.setup_for_snippet(
        """
entity A:
    int id
    string left
    string right
    int other_id
end

implement A using none

index A(id)
index A(left, right)
index A(other_id)

A(id=1, left="L", right="R", other_id=1)
A(id=2, left="LL", right="RR", other_id=2)
A(id=3, left="LLL", right="RRR", other_id=3)
A(id=1, left="LL", right="RR", other_id=3)

implementation none for std::Entity:
end
"""
    )
    with pytest.raises(IndexCollisionException) as e:
        compiler.do_compile()

    print(ExplainerFactory().explain_and_format(e.value))
    assert (
        ExplainerFactory().explain_and_format(e.value)
        == f"""
Exception explanation
=====================
The constructor `A(id=1,left='LL',right='RR',other_id=3)` ({snippetcompiler.project_dir}/main.cf:18) matches different instances in different indexes:
- index A(id) matches __config__::A (instantiated at {snippetcompiler.project_dir}/main.cf:15)
- index A(left,right) matches __config__::A (instantiated at {snippetcompiler.project_dir}/main.cf:16)
- index A(other_id) matches __config__::A (instantiated at {snippetcompiler.project_dir}/main.cf:17)
"""  # noqa: E501
    )


def test_index_on_nullable(snippetcompiler) -> None:
    """
    Verify that indexes on nullable attributes are allowed and behave as expected.

    Indexes on optional relations are not supported and are tested in test_issue_745_2689_index_on_optional.
    """
    snippetcompiler.setup_for_snippet(
        """
        entity A:
            int? n = null
        end
        index A(n)

        entity B:
            int? m = null
            int? n = null
        end
        index B(m, n)

        entity C:
            string? s = null
        end
        index C(s)

        entity D:
            # this may be deprecated but best to make sure it behaves consistently nonetheless
            list? l = null
        end
        index D(l)

        implement A using none
        implement B using none
        implement C using none
        implement D using none
        implementation none for std::Entity:
        end

        assert = true

        a_default = A()
        a_null = A(n=null)
        a_zero = A(n=0)
        a_one = A(n=1)

        assert = (a_default == a_null)
        assert = (a_default == A())
        assert = (a_null == A(n=null))
        assert = (a_zero == A(n=0))
        assert = (a_one == A(n=1))
        assert = (a_null == A[n=null])
        assert = (a_zero == A[n=0])
        assert = (a_one == A[n=1])
        assert = (a_default != a_zero)
        assert = (a_default != a_one)
        assert = (a_zero != a_one)

        # concept is trivially the same: only test that basic behavior
        b_default = B()
        assert = (b_default == B[m=null,n=null])
        assert = (b_default == B(n=null))
        assert = (b_default != B(n=0))

        # guard against some plausible implementation errors, especially given that we use `repr` for index matching
        c_null = C()
        c_null_str = C(s="null")
        c_None = C(s="None")
        c_none = C(s="none")

        assert = (c_null != c_null_str)
        assert = (c_null != c_None)
        assert = (c_null != c_none)
        assert = (c_null == C[s=null])
        assert = (c_null_str == C[s="null"])

        d_default = D()
        d_null = D(l=null)
        d_empty = D(l=[])
        d_one = D(l=[1])

        assert = (d_null == d_default)
        assert = (d_null != d_empty)
        assert = (d_null != d_one)
        assert = (d_null == D[l=null])
        assert = (d_empty == D[l=[]])
        """
    )
    compiler.do_compile()


def test_lookup_on_float_with_int(snippetcompiler):
    """
    Verify that index lookups work as expected on float-type attributes, both with float and equivalent int lookups.
    """
    snippetcompiler.setup_for_snippet(
        """
entity A:
    float x
end
index A(x)

entity B:
    float? x
end
index B(x)

implement A using none
implement B using none

assert = true

a_one = A(x=1.0)

assert = (a_one == A[x=1.0])
assert = (a_one == A[x=1])

b_null = B(x=null)
b_one = B(x=1.0)

assert = (b_null != b_one)
assert = (b_null == B[x=null])
assert = (b_one == B[x=1.0])
assert = (b_one == B[x=1])

implementation none for std::Entity:
end
        """,
    )
    compiler.do_compile()
