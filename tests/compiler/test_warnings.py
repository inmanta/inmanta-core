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

import warnings
from typing import Optional

import pytest

import inmanta.compiler as compiler
import inmanta.warnings as inmanta_warnings
from inmanta.ast import CompilerDeprecationWarning, CompilerRuntimeWarning
from inmanta.warnings import WarningsManager


@pytest.mark.parametrize(
    "option,expected_error,expected_warning",
    [(None, False, True), ("warn", False, True), ("ignore", False, False), ("error", True, False)],
)
def test_warnings(option: Optional[str], expected_error: bool, expected_warning: bool):
    message: str = "Some compiler runtime warning"
    warning: Warning = CompilerRuntimeWarning(None, message)
    with warnings.catch_warnings(record=True) as w:
        WarningsManager.apply_config({"default": option} if option is not None else None)
        if expected_error:
            with pytest.raises(CompilerRuntimeWarning):
                inmanta_warnings.warn(warning)
        else:
            inmanta_warnings.warn(warning)
        if expected_warning:
            assert len(w) == 1
            assert issubclass(w[0].category, CompilerRuntimeWarning)
            assert str(w[0].message) == message
        else:
            assert len(w) == 0


def test_deprecation_warning_nullable(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    number? n
end

implement A using std::none

A()
A(n = null)
        """
    )
    message: str = "No value for attribute __config__::A.n. Assign null instead of leaving unassigned. ({dir}/main.cf:8)"
    message = message.format(dir=snippetcompiler.project_dir)
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message


def test_deprecation_warning_default_constructors(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
typedef MyType as A(n = 42)

entity A:
    number n
    number m
end

implement A using std::none
        """
    )
    message: str = (
        "Default constructors are deprecated."
        " Use inheritance instead. (reported in typedef MyType as A(n=42) ({dir}/main.cf:2))"
    )
    message = message.format(dir=snippetcompiler.project_dir)
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message
