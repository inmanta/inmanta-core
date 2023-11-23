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

from typing import Optional, Type

import pytest

from compiler.dataflow.conftest import DataflowTestHelper
from inmanta.ast import AttributeException, CompilerException, DoubleSetException, NotFoundException
from inmanta.execute.dataflow import VariableNodeReference
from inmanta.execute.dataflow.datatrace import DataTraceRenderer
from inmanta.execute.proxy import UnsetException


@pytest.mark.parametrize(
    "description,model,trace,trace_root,exception",
    [
        (
            "simple assignment",
            """
x = 42
            """,
            """
x
└── 42
    SET BY `x = 42`
    AT {dir}/main.cf:2
            """,
            "x",
            None,
        ),
        (
            "uninitialized rhs",
            """
x = y
            """,
            """
x
└── y
    SET BY `x = y`
    AT {dir}/main.cf:2
            """,
            "x",
            NotFoundException,
        ),
        (
            "assignment chain",
            """
x = y
y = z
z = u
            """,
            """
x
└── y
    SET BY `x = y`
    AT {dir}/main.cf:2
    └── z
        SET BY `y = z`
        AT {dir}/main.cf:3
        └── u
            SET BY `z = u`
            AT {dir}/main.cf:4
            """,
            "x",
            NotFoundException,
        ),
        (
            "assignment chain with branching",
            """
x = y
y = z

y = k
k = l
l = 42

z = u
            """,
            """
x
└── y
    SET BY `x = y`
    AT {dir}/main.cf:2
    ├── z
    │   SET BY `y = z`
    │   AT {dir}/main.cf:3
    │   └── u
    │       SET BY `z = u`
    │       AT {dir}/main.cf:9
    └── k
        SET BY `y = k`
        AT {dir}/main.cf:5
        └── l
            SET BY `k = l`
            AT {dir}/main.cf:6
            └── 42
                SET BY `l = 42`
                AT {dir}/main.cf:7
            """,
            "x",
            NotFoundException,
        ),
        (
            "equivalence",
            """
x = y
y = z
z = x

y = u
            """,
            """
x
EQUIVALENT TO {{x, y, z}} DUE TO STATEMENTS:
    `x = y` AT {dir}/main.cf:2
    `y = z` AT {dir}/main.cf:3
    `z = x` AT {dir}/main.cf:4
└── u
    SET BY `y = u`
    AT {dir}/main.cf:6
            """,
            "x",
            NotFoundException,
        ),
        (
            "equivalence with attribute",
            """
entity A:
    number n
end
implement A using std::none

t = A()

x = y
y = t.n
t.n = x
            """,
            """
x
EQUIVALENT TO {{attribute n on __config__::A instance, x, y}} DUE TO STATEMENTS:
    `y = t.n` AT {dir}/main.cf:10
    `t.n = x` AT {dir}/main.cf:11
    `x = y` AT {dir}/main.cf:9
            """,
            "x",
            UnsetException,
        ),
        (
            "double set exception with tail",
            """
x = y
y = z
z = 42
y = 0
            """,
            """
x
└── y
    SET BY `x = y`
    AT {dir}/main.cf:2
    ├── z
    │   SET BY `y = z`
    │   AT {dir}/main.cf:3
    │   └── 42
    │       SET BY `z = 42`
    │       AT {dir}/main.cf:4
    └── 0
        SET BY `y = 0`
        AT {dir}/main.cf:5
            """,
            "x",
            DoubleSetException,
        ),
        (
            "implementation",
            """
entity A:
    number n
end

entity B:
    number n
end

implementation ia for A:
    b = B()
    self.n = b.n
end
implement A using ia

implementation ib for B:
    self.n = 42
end
implement B using ib


x = A()
x_n = x.n
            """,
            """
x_n
└── x.n
    SET BY `x_n = x.n`
    AT {dir}/main.cf:23
    SUBTREE for x:
        └── __config__::A instance
            SET BY `x = A()`
            AT {dir}/main.cf:22
            CONSTRUCTED BY `A()`
            AT {dir}/main.cf:22
    └── b.n
        SET BY `self.n = b.n`
        AT {dir}/main.cf:12
        IN IMPLEMENTATION WITH self = __config__::A instance
            CONSTRUCTED BY `A()`
            AT {dir}/main.cf:22
        SUBTREE for b:
            └── __config__::B instance
                SET BY `b = B()`
                AT {dir}/main.cf:11
                IN IMPLEMENTATION WITH self = __config__::A instance
                    CONSTRUCTED BY `A()`
                    AT {dir}/main.cf:22
                CONSTRUCTED BY `B()`
                AT {dir}/main.cf:11
                IN IMPLEMENTATION WITH self = __config__::A instance
                    CONSTRUCTED BY `A()`
                    AT {dir}/main.cf:22
        └── 42
            SET BY `self.n = 42`
            AT {dir}/main.cf:17
            IN IMPLEMENTATION WITH self = __config__::B instance
                CONSTRUCTED BY `B()`
                AT {dir}/main.cf:11
                IN IMPLEMENTATION WITH self = __config__::A instance
                    CONSTRUCTED BY `A()`
                    AT {dir}/main.cf:22
            """,
            "x_n",
            None,
        ),
        (
            "index match double assignment",
            """
entity A:
    number n
    number m
end

index A(n)

implement A using std::none


x = A(n = 42)
y = A(n = 42)

x.m = 0
y.m = 1

x_m = x.m
            """,
            """
x_m
└── x.m
    SET BY `x_m = x.m`
    AT {dir}/main.cf:18
    SUBTREE for x:
        └── __config__::A instance
            SET BY `x = A(n=42)`
            AT {dir}/main.cf:12
            CONSTRUCTED BY `A(n=42)`
            AT {dir}/main.cf:12

            INDEX MATCH: `__config__::A instance`
                CONSTRUCTED BY `A(n=42)`
                AT {dir}/main.cf:13
    ├── 1
    │   SET BY `y.m = 1`
    │   AT {dir}/main.cf:16
    └── 0
        SET BY `x.m = 0`
        AT {dir}/main.cf:15
            """,
            "x_m",
            AttributeException,
        ),
    ],
)
def test_dataflow_trace(
    dataflow_test_helper: DataflowTestHelper,
    description: str,
    model: str,
    trace: str,
    trace_root: str,
    exception: Optional[Type[CompilerException]],
) -> None:
    """
    Tests the data trace output.

    :param description: Description for this test.
    :param model: The model to compile.
    :param trace: The expected trace.
    :param trace_root: The root variable for the trace. No attribute lookup allowed.
    :param exception: The type of an expected compiler exception.
    """
    dataflow_test_helper.compile(model, exception)
    root = dataflow_test_helper.get_graph().resolver.get_dataflow_node(trace_root)
    assert isinstance(root, VariableNodeReference)
    assert DataTraceRenderer.render(root.node.reference()).rstrip() == trace.strip().format(
        dir=dataflow_test_helper.snippetcompiler.project_dir
    )
