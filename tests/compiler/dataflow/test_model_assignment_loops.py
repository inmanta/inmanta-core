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

from typing import Set

import pytest

from compiler.dataflow.conftest import DataflowTestHelper
from inmanta.ast import RuntimeException


@pytest.mark.parametrize("assign", [True, False])
def test_dataflow_model_dependency_loop(dataflow_test_helper: DataflowTestHelper, assign: bool) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
z = x
%s
        """
        % ("y = 42" if assign else ""),
        None if assign else RuntimeException,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> y
y -> [ z %s ]
z -> x
        """
        % ("42" if assign else ""),
    )
    all_vars: str = "xyz"
    leaves: Set[str] = {"y"} if assign else set(iter(all_vars))
    dataflow_test_helper.verify_leaves({var: leaves for var in all_vars})


def test_dataflow_model_dependency_loop_with_var_assignment(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
z = x

y = v
v = w
w = 42
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> y
y -> [ z v ]
z -> x

v -> w
w -> 42
        """,
    )
    dataflow_test_helper.verify_leaves({var: {"w"} for var in "xyzvw"})


def test_dataflow_model_double_dependency_loop(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
z = x

x = v
v = w
w = x

y = 42
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> [ y v ]
y -> [ z 42 ]
z -> x

v -> w
w -> x
        """,
    )
    all_vars: str = "xyzvw"
    dataflow_test_helper.verify_leaves({var: {"y"} for var in all_vars})


@pytest.mark.parametrize("assign_loop0", [True, False])
def test_dataflow_model_chained_dependency_loops(dataflow_test_helper: DataflowTestHelper, assign_loop0: bool) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
z = x

u = v
v = w
w = u

y = v

u = 42
%s
        """
        % ("z = 42" if assign_loop0 else ""),
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> y
y -> [ z v ]
z -> [ x %s ]

u -> [ v 42 ]
v -> w
w -> u
        """
        % ("42" if assign_loop0 else ""),
    )
    loop0_vars: str = "xyz"
    loop1_vars: str = "uvw"
    dataflow_test_helper.verify_leaves({var: {"z", "u"} if assign_loop0 else {"u"} for var in loop0_vars})
    dataflow_test_helper.verify_leaves({var: {"u"} for var in loop1_vars})
