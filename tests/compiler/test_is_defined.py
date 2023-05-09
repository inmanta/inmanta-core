"""
    Copyright 2019 Inmanta

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

from inmanta import compiler
from inmanta.ast import OptionalValueException

# Parametized fixtures are used in some places to increase coverage, but not everywhere, to keep test time under control.


@pytest.fixture(params=[1, 2, 3], ids=["if", "implements", "if in implementation"])
def condition_block(request):
    mode = request.param

    def gen(var):
        if mode == 1:
            return f"""
if {var} is defined:
    std::print("true")
else:
    std::print("false")
end
"""
        if mode == 2:
            return f"""
implementation printt for A:
    std::print("true")
end

implementation printf for A:
    std::print("false")
end

implement A using printt when {var} is defined
implement A using printf when not ({var} is defined)
"""

        if mode == 3:
            return f"""
implementation print for A:
    if {var} is defined:
        std::print("true")
    else:
        std::print("false")
    end
end

implement A using print
"""

    return gen


@pytest.fixture(params=[1, 2, 3, 4], ids=["implements", "implements self", "if in implementation", "if in implementation self"])
def condition_block_with_self(request):
    mode = request.param

    def gen(var):
        if mode % 2 == 0:
            var = f"self.{var}"
        if mode == 1 or mode == 2:

            return f"""
implementation printt for A:
    std::print("true")
end

implementation printf for A:
    std::print("false")
end

implement A using printt when {var} is defined
implement A using printf when not ({var} is defined)
"""

        if mode == 3 or mode == 4:
            return f"""
implementation print for A:
    b = 3
    if {var} is defined:
        std::print("true")
    else:
        std::print("false")
    end
end

implement A using print
"""

    # attach meta data
    gen.shadows_b = mode == 3
    return gen


def test_is_defined_attribute(snippetcompiler, capsys, condition_block):
    snippetcompiler.setup_for_snippet(
        f"""

entity A:
    number? a
end

implement A using std::none

x = A(a = 1)

{condition_block("x.a")}
"""
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "true" in out


def test_is_defined_attribute_not(snippetcompiler, capsys, condition_block_with_self):
    snippetcompiler.setup_for_snippet(
        f"""

entity A:
    number? a
end

implement A using std::none

x = A()

{condition_block_with_self("a")}
"""
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "false" in out


def test_is_defined_attribute_not_2(snippetcompiler, capsys, condition_block):
    snippetcompiler.setup_for_snippet(
        f"""

    entity A:
        number? a
    end

    implement A using std::none

    x = A(a=null)

    {condition_block("x.a")}
    """
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "false" in out


def test_is_defined_attribute_not_3(snippetcompiler, capsys, condition_block):
    snippetcompiler.setup_for_snippet(
        f"""

    entity A:
        number[]? a
    end

    implement A using std::none

    x = A()

   {condition_block("x.a")}
    """
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "false" in out


def test_is_defined_attribute_2(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """

    entity A:
        number[]? a
    end

    implement A using std::none

    x = A(a=[1,2])

    if x.a is defined:
        std::print("true")
    else:
        std::print("false")
    end
    """
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "true" in out


def test_is_defined_relation(snippetcompiler, capsys, condition_block):
    snippetcompiler.setup_for_snippet(
        f"""

entity A:
end

implement A using std::none

A.a [0:1] -- A

x = A(a=A())

{condition_block("x.a")}
"""
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "true" in out


def test_is_defined_relation_not(snippetcompiler, capsys, condition_block):
    snippetcompiler.setup_for_snippet(
        f"""

entity A:
end

implement A using std::none

A.a [0:1] -- A

x = A()
{condition_block("x.a")}
"""
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "false" in out


def test_is_defined_relation_not_2(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """

entity A:
end

implement A using std::none

A.a [0:] -- A

x = A()

if x.a is defined:
    std::print("true")
else:
    std::print("false")
end
"""
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "false" in out


def test_is_defined_global(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """

entity A:
end

implement A using std::none

A.a [0:] -- A

x = A()

if x is defined:
    std::print("true")
else:
    std::print("false")
end
"""
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "true" in out


def test_is_defined_global_2(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
entity A:
end

implement A using std::none

A.a [0:1] -- A

y = A()
x = y.a

if x is defined:
    std::print("true")
else:
    std::print("false")
end
"""
    )
    with pytest.raises(OptionalValueException):
        compiler.do_compile()


def test_is_defined_implements_scoping(snippetcompiler, capsys, condition_block_with_self):
    snippetcompiler.setup_for_snippet(
        f"""
entity A:
end


A.a [0:1] -- A

a = 3 # shadowed
y = A()

{condition_block_with_self("a")}

"""
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "false" in out


def test_is_defined_block_scoping(snippetcompiler, capsys, condition_block_with_self):
    snippetcompiler.setup_for_snippet(
        f"""
entity A:
end

implement A using std::none

# b is defined in implements block
A.b [0:1] -- A

y = A()

{condition_block_with_self("b")}

"""
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    result = "true" if condition_block_with_self.shadows_b else "false"
    assert result in out


def test_3026_is_defined_gradual(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
entity A:
end

A.list [0:] -- A
A.optional [0:1] -- A

implementation a for A:
    self.optional = A()
end

implement A using std::none
implement A using a when self.list is defined

a = A(list=A())
test = a.optional
"""
    )
    # assert this does not fail:
    # A.list's upper arity is unbounded, therefore without gradual execution it needs to be frozen.
    # A.optional is a candidate for freezing as well. It has the same potential to be selected as A.list
    # (until #2793 has been implemented).
    # As a result this snippet is likely to fail without gradual execution for `is defined`.
    compiler.do_compile()
