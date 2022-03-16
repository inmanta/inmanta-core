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

import logging
import warnings
from typing import Optional, Type, Union

import pytest

import inmanta.compiler as compiler
import inmanta.warnings as inmanta_warnings
from inmanta.ast import CompilerDeprecationWarning, CompilerRuntimeWarning, VariableShadowWarning
from inmanta.warnings import InmantaWarning, WarningsManager


@pytest.mark.parametrize(
    "option,expected_error,expected_warning",
    [(None, False, True), ("warn", False, True), ("ignore", False, False), ("error", True, False)],
)
@pytest.mark.parametrize("raise_external_warning", [True, False])
def test_warnings(option: Optional[str], expected_error: bool, expected_warning: bool, raise_external_warning: bool):
    message: str = "Some compiler runtime warning"
    internal_warning: InmantaWarning = CompilerRuntimeWarning(None, message)
    external_warning: Warning = Warning(None, "Some external warning")
    WarningsManager.apply_config({"default": option} if option is not None else None)
    with warnings.catch_warnings(record=True) as w:
        if expected_error:
            with pytest.raises(CompilerRuntimeWarning):
                if raise_external_warning:
                    # make sure external warnings are ignored (#1905)
                    warnings.warn(external_warning)
                inmanta_warnings.warn(internal_warning)
        else:
            inmanta_warnings.warn(internal_warning)
        if expected_warning:
            assert len(w) == 1
            assert issubclass(w[0].category, CompilerRuntimeWarning)
            assert str(w[0].message) == message
        else:
            assert len(w) == 0


@pytest.mark.parametrize(
    "warning,category,filename,lineno",
    [
        ("my non-inmanta warning", UserWarning, "/path/to/filename", 42),
        (CompilerRuntimeWarning(None, "my inmanta warning"), CompilerRuntimeWarning, "/path/to/filename", 42),
    ],
)
def test_warning_format(caplog, warning: Union[str, Warning], category: Type[Warning], filename: str, lineno: int):
    caplog.set_level(logging.WARNING)
    WarningsManager.apply_config({})
    warnings.resetwarnings()
    warnings.filterwarnings("default", category=Warning)
    warnings.warn_explicit(warning, category, filename, lineno)
    if isinstance(warning, InmantaWarning):
        assert caplog.record_tuples == [("inmanta.warnings", logging.WARNING, "%s: %s" % (category.__name__, warning))]
    else:
        assert caplog.record_tuples == [
            (
                "py.warnings",
                logging.WARNING,
                warnings.formatwarning(warning, category, filename, lineno),  # type: ignore
            )
        ]


def test_shadow_warning(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
x = 0
if true:
    x = 1
    if true:
        if true:
            x = 3
        end
    end
end
        """
    )
    message: str = "Variable `x` shadowed: originally declared at {dir}/main.cf:%d, shadowed at {dir}/main.cf:%d"
    message = message.format(dir=snippetcompiler.project_dir)
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 2
        w1 = w[0]
        w3 = w[1]
        assert issubclass(w1.category, VariableShadowWarning)
        assert str(w1.message) == message % (2, 4)
        assert issubclass(w3.category, VariableShadowWarning)
        assert str(w3.message) == message % (4, 7)


def test_shadow_warning_implementation(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
x = 0

entity A:
end

implementation i for A:
    x = 1
end

implement A using std::none
        """
    )
    message: str = "Variable `x` shadowed: originally declared at {dir}/main.cf:%d, shadowed at {dir}/main.cf:%d"
    message = message.format(dir=snippetcompiler.project_dir)
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 1
        w1 = w[0]
        assert issubclass(w1.category, VariableShadowWarning)
        assert str(w1.message) == message % (2, 8)


def test_1918_shadow_warning_for_loop(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
i = 0

for i in std::sequence(10):
end
        """
    )
    message: str = "Variable `i` shadowed: originally declared at {dir}/main.cf:%d, shadowed at {dir}/main.cf:%d"
    message = message.format(dir=snippetcompiler.project_dir)
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 1
        w1 = w[0]
        assert issubclass(w1.category, VariableShadowWarning)
        assert str(w1.message) == message % (2, 4)


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


@pytest.mark.parametrize("assign", [True, False])
def test_1950_deprecation_warning_nullable_diamond_inheritance(snippetcompiler, assign: bool):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    number? n%s
end

entity B extends A:
end

entity C extends A, B:
end


implement A using std::none
implement B using std::none
implement C using std::none

C()
        """
        % (" = null" if assign else ""),
    )
    message: str = "No value for attribute __config__::C.n. Assign null instead of leaving unassigned. ({dir}/main.cf:17)"
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 0 if assign else 1
        if not assign:
            assert issubclass(w[0].category, CompilerDeprecationWarning)
            assert str(w[0].message) == message.format(dir=snippetcompiler.project_dir)


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


def test_2030_type_overwrite_warning(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
typedef string as number matching self > 0
        """,
    )
    with warnings.catch_warnings(record=True) as w:
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerRuntimeWarning)
        assert str(w[0].message) == (
            f"Trying to override a built-in type: string (reported in Type(string) ({snippetcompiler.project_dir}/main.cf:2:9))"
        )
