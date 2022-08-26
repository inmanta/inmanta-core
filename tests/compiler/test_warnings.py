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
from inmanta.ast import CompilerDeprecationWarning, CompilerException, CompilerRuntimeWarning, VariableShadowWarning
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

    def match(warning) -> bool:
        return issubclass(warning.category, CompilerDeprecationWarning) and str(warning.message) == message.format(dir=snippetcompiler.project_dir)

    with warnings.catch_warnings(record=True) as ws:
        compiler.do_compile()
        warned: bool = any(match(w) for w in ws)
        assert warned != assign


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
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
typedef string as number matching self > 0
            """,
        )
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerRuntimeWarning)
        assert str(w[0].message) == (
            f"Trying to override a built-in type: string (reported in Type(string) ({snippetcompiler.project_dir}/main.cf:2:9))"
        )


def test_deprecation_minus_in_entity_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
    entity Entity-a:
    end
            """
        )
        message: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming Entity-a. "
            f"(reported in Entity-a ({snippetcompiler.project_dir}/main.cf:2:12))"
        )
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message


def test_deprecation_minus_in_attribute_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
    entity Entity:
        string attribute-a
    end
            """
        )
        message: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming attribute-a. "
            f"(reported in attribute-a ({snippetcompiler.project_dir}/main.cf:3:16))"
        )
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message


def test_deprecation_minus_in_implementation_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
entity Car:
   string brand
end

implementation vw-polo for Car:
    brand = "vw"
end
            """
        )
        message: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming vw-polo. "
            f"(reported in vw-polo ({snippetcompiler.project_dir}/main.cf:6:16))"
        )
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message


def test_deprecation_minus_in_typedef_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
typedef tcp-port as int matching self > 0 and self < 65535
            """
        )
        message: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming tcp-port. "
            f"(reported in tcp-port ({snippetcompiler.project_dir}/main.cf:2:9))"
        )
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message


def test_deprecation_minus_in_typedef_default_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
entity Car:
   string brand
end

typedef Corsa-opel as Car(brand="opel")
            """
        )
        message: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming Corsa-opel. "
            f"(reported in Corsa-opel ({snippetcompiler.project_dir}/main.cf:6:9))"
        )
        compiler.do_compile()
        assert len(w) == 2
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message


def test_deprecation_minus_in_assign_variable_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
var-hello = "hello"
            """
        )
        message: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming var-hello. "
            f"(reported in var-hello ({snippetcompiler.project_dir}/main.cf:2:1))"
        )
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message


def test_deprecation_minus_import_as(snippetcompiler):
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
import std as std-std
            """
        )
        message: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming std-std. "
            f"(reported in std-std ({snippetcompiler.project_dir}/main.cf:2:15))"
        )
        compiler.do_compile()
        assert len(w) == 1
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message


def test_deprecation_minus_relation(snippetcompiler):
    with warnings.catch_warnings(record=True) as w:
        snippetcompiler.setup_for_snippet(
            """
entity Host:
    string  name
end

entity File:
    string path
end

Host.files-hehe [0:] -- File.host-hoho [1]
            """
        )
        message1: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming files-hehe. "
            f"(reported in files-hehe ({snippetcompiler.project_dir}/main.cf:10:6))"
        )
        message2: str = (
            f"The use of '-' in identifiers is deprecated. Consider renaming host-hoho. "
            f"(reported in host-hoho ({snippetcompiler.project_dir}/main.cf:10:30))"
        )
        compiler.do_compile()
        assert len(w) == 2
        assert issubclass(w[0].category, CompilerDeprecationWarning)
        assert str(w[0].message) == message1
        assert str(w[1].message) == message2


def test_import_hypen_in_name(snippetcompiler):
    with pytest.raises(CompilerException) as e:
        snippetcompiler.setup_for_snippet(
            """
import st-d
            """
        )
        compiler.do_compile()
    assert "st-d is not a valid module name: hyphens are not allowed, please use underscores instead." == e.value.msg
