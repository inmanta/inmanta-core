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
from utils import log_doesnt_contain


@pytest.mark.parametrize(
    "option,expected_error,expected_warning",
    [(None, False, True), ("warn", False, True), ("ignore", False, False), ("error", True, False)],
)
def test_warnings(option: Optional[str], expected_error: bool, expected_warning: bool) -> None:
    """
    Verify whether the setting to configure warnings works correctly.
    """
    message_compiler_warning: str = "Some compiler runtime warning"
    internal_warning: InmantaWarning = CompilerRuntimeWarning(None, message_compiler_warning)
    message_internal_warning: str = "Some external warning"
    external_warning: Warning = Warning(None, message_internal_warning)

    def contains_warning(caught_warnings, category: Type[Warning], message: str) -> bool:
        return any(issubclass(w.category, category) and str(w.message) == message for w in caught_warnings)

    # Apply config
    WarningsManager.apply_config({"default": option} if option is not None else None)
    with warnings.catch_warnings(record=True) as caught_warnings:
        # Log an external warning
        warnings.warn(external_warning)
        # Log an internal warning
        if expected_error:
            with pytest.raises(CompilerRuntimeWarning):
                inmanta_warnings.warn(internal_warning)
        else:
            inmanta_warnings.warn(internal_warning)
        # Verify that the CompilerWarnings are filtered correctly with respect to the provided config option.
        if expected_warning:
            assert len(caught_warnings) >= 1
            assert contains_warning(caught_warnings, category=CompilerRuntimeWarning, message=message_compiler_warning)
        else:
            assert not contains_warning(caught_warnings, category=CompilerRuntimeWarning, message=message_compiler_warning)
        # Verify that the external warning is not logged
        assert not contains_warning(caught_warnings, category=Warning, message=message_internal_warning)


def test_filter_external_warnings(caplog) -> None:
    """
    Verify that warnings triggered from non-inmanta code are not displayed to the user.
    """
    message = "test message"
    # Raising a warning from the test suite is considered an external exception.
    # The file is not part of an inmanta package.
    warnings.warn(message, category=DeprecationWarning)
    log_doesnt_contain(caplog, "py.warnings", logging.WARNING, message)


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
    with warnings.catch_warnings(record=True) as caught_warnings:
        compiler.do_compile()
        assert len(caught_warnings) >= 2

        shadow_warning_1: bool = False
        shadow_warning_2: bool = False

        for w in caught_warnings:
            if str(w.message) == message % (2, 4):
                assert issubclass(w.category, VariableShadowWarning)
                shadow_warning_1 = True
            elif str(w.message) == message % (4, 7):
                assert issubclass(w.category, VariableShadowWarning)
                shadow_warning_2 = True

        assert all([shadow_warning_1, shadow_warning_2])


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
    with warnings.catch_warnings(record=True) as caught_warnings:
        compiler.do_compile()

        assert len(caught_warnings) >= 1
        assert any(
            issubclass(w.category, VariableShadowWarning) and str(w.message) == message % (2, 8) for w in caught_warnings
        )


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
    with warnings.catch_warnings(record=True) as caught_warnings:
        compiler.do_compile()

        assert len(caught_warnings) >= 1
        assert any(
            issubclass(w.category, VariableShadowWarning) and str(w.message) == message % (2, 4) for w in caught_warnings
        )


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
    with warnings.catch_warnings(record=True) as caught_warnings:
        compiler.do_compile()

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerDeprecationWarning) and str(w.message) == message for w in caught_warnings)


def test_2030_type_overwrite_warning(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
        snippetcompiler.setup_for_snippet(
            """
typedef string as number matching self > 0
            """,
        )
        compiler.do_compile()
        message = (
            "Trying to override a built-in type: string (reported in Type(string) "
            f"({snippetcompiler.project_dir}/main.cf:2:9))"
        )

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerRuntimeWarning) and str(w.message) == message for w in caught_warnings)


def test_deprecation_minus_in_entity_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
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

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerDeprecationWarning) and str(w.message) == message for w in caught_warnings)


def test_deprecation_minus_in_attribute_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
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

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerDeprecationWarning) and str(w.message) == message for w in caught_warnings)


def test_deprecation_minus_in_implementation_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
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

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerDeprecationWarning) and str(w.message) == message for w in caught_warnings)


def test_deprecation_minus_in_typedef_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
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

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerDeprecationWarning) and str(w.message) == message for w in caught_warnings)


def test_deprecation_minus_in_typedef_default_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
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

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerDeprecationWarning) and str(w.message) == message for w in caught_warnings)


def test_deprecation_minus_in_assign_variable_name(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
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

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerDeprecationWarning) and str(w.message) == message for w in caught_warnings)


def test_deprecation_minus_import_as(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
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

        assert len(caught_warnings) >= 1
        assert any(issubclass(w.category, CompilerDeprecationWarning) and str(w.message) == message for w in caught_warnings)


def test_deprecation_minus_relation(snippetcompiler):
    with warnings.catch_warnings(record=True) as caught_warnings:
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

        compiler_warning_1: bool = False
        compiler_warning_2: bool = False

        for w in caught_warnings:
            if str(w.message) == message1:
                assert issubclass(w.category, CompilerDeprecationWarning)
                compiler_warning_1 = True
            elif str(w.message) == message2:
                assert issubclass(w.category, CompilerDeprecationWarning)
                compiler_warning_2 = True

        assert all([compiler_warning_1, compiler_warning_2])


def test_import_hypen_in_name(snippetcompiler):
    with pytest.raises(CompilerException) as e:
        snippetcompiler.setup_for_snippet(
            """
import st-d
            """
        )
        compiler.do_compile()

    assert "st-d is not a valid module name: hyphens are not allowed, please use underscores instead." == e.value.msg
