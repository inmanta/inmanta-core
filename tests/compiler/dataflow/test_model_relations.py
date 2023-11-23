"""
    Copyright 2020 Inmanta

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

from compiler.dataflow.conftest import DataflowTestHelper


@pytest.mark.parametrize("bidirectional", [True, False])
@pytest.mark.parametrize("inherit_relation", [True, False])
@pytest.mark.parametrize("assign_first", [True, False])
def test_dataflow_model_relation(
    dataflow_test_helper: DataflowTestHelper, bidirectional: bool, inherit_relation: bool, assign_first: bool
) -> None:
    relation_stmt: str = "%s.b [1] -- B%s" % ("AParent" if inherit_relation else "A", ".a [1]" if bidirectional else "")
    dataflow_test_helper.compile(
        """
entity AParent:
end
implement AParent using std::none

entity A extends AParent:
end
implement A using std::none

entity B:
end
implement B using std::none

%s

a = A()
b = B()

a.b = b

%s
        """
        % ("" if assign_first else relation_stmt, relation_stmt if assign_first else "")
    )
    bidirectional_rule: str = "<instance> b . a -> <instance> a"
    dataflow_test_helper.verify_graphstring(
        """
a -> <instance> a
b -> <instance> b

<instance> a . b -> b
%s
        """
        % (bidirectional_rule if bidirectional else ""),
    )
    if not bidirectional:
        with pytest.raises(AssertionError):
            dataflow_test_helper.verify_graphstring(bidirectional_rule)
    dataflow_test_helper.verify_leaves({"a": {"a"}, "b": {"b"}, "a.b": {"b"}, "b.a": {"b.a"}})


def test_dataflow_model_assignment_to_relation(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity X:
end

entity U:
end

entity V:
    number n
end

X.u [1] -- U
U.v [1] -- V

implement X using std::none
implement U using std::none
implement V using std::none

n = 42

x = X()
x.u = U()
x.u.v = V()
x.u.v.n = n
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> <instance> x
<instance> x . u -> <instance> u
<instance> u . v -> <instance> v
<instance> v . n -> n
n -> 42
        """,
    )
    dataflow_test_helper.verify_leaves({"x.u.v.n": {"n"}})


def test_dataflow_model_assignment_from_relation(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity U:
end

entity V:
    number n
end

U.v [1] -- V

implement U using std::none
implement V using std::none

n = 42

u = U(v = v)
v = V(n = n)

uvn = u.v.n
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
n -> 42
u -> <instance> u
v -> <instance> v

<instance> u . v -> v
<instance> v . n -> n

uvn -> u . v . n
        """,
    )
    dataflow_test_helper.verify_leaves({"n": {"n"}, "u": {"u"}, "v": {"v"}, "u.v": {"v"}, "v.n": {"n"}, "uvn": {"n"}})


def test_dataflow_model_index(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
    number k
    number l
end

index A(n)

implement A using std::none

x = A(n = 42, k = 0)
y = A(n = 42, l = 1)
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> <instance> x
y -> <instance> y

<instance> x . n -> [ 42 42 ]
<instance> y . n -> [ 42 42 ]

<instance> x . k -> 0
<instance> y . k -> 0

<instance> x . l -> 1
<instance> y . l -> 1
        """,
    )


def test_dataflow_model_default_attribute(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n = 42
end

implement A using std::none

x = A()
y = A(n = 0)
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> <instance> x
y -> <instance> y

<instance> x . n -> 42
<instance> y . n -> 0
        """,
    )


@pytest.mark.parametrize("refer_out", [True, False])
def test_dataflow_model_implementation(dataflow_test_helper: DataflowTestHelper, refer_out: bool) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
end

implementation i for A:
    self.n = %s
end

implement A using i

nn = 42
x = A()
        """
        % ("nn" if refer_out else 42),
    )
    dataflow_test_helper.verify_graphstring(
        """
nn -> 42
x -> <instance> x
<instance> x . n -> %s
        """
        % ("nn" if refer_out else 42),
    )


def test_dataflow_model_unsupported_bidirectional_doesnt_crash(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
end

entity B:
end

implement A using std::none
implement B using std::none

A.b [0:] -- B.a [0:]

a = A()
# Lists are not supported yet. Mustn't crash on trying to model the other side of the bidirectional relation
a.b = [B(), B()]
        """,
    )
