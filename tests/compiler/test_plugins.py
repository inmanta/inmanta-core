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

import logging
import os
import re
import typing

import pytest

import inmanta.ast.statements.define
import inmanta.compiler as compiler
import inmanta.plugins
from inmanta.ast import (
    CompilerException,
    ExplicitPluginException,
    InvalidTypeAnnotation,
    Namespace,
    RuntimeException,
    WrappingRuntimeException,
)
from utils import log_contains

if typing.TYPE_CHECKING:
    from conftest import SnippetCompilationTest


def test_plugin_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        import std
        std::template("/tet.tmpl")
""",
        """Exception in plugin std::template (reported in std::template('/tet.tmpl') ({dir}/main.cf:3:9))
caused by:
  jinja2.exceptions.TemplateNotFound: /tet.tmpl
""",
    )


def test_1221_plugin_incorrect_type_annotation(snippetcompiler):
    modpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "modules", "test_1221")
    snippetcompiler.setup_for_error(
        """
import test_1221
        """,
        "could not find type std::WrongName in namespace std (%s/plugins/__init__.py:5:1)" % modpath,
    )


def test_kwargs_in_plugin_call(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
str = std::replace("Hello World!", new = "You", old = "World")
        """,
        autostd=True,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert root.lookup("str").get_value() == "Hello You!"


def test_wrapped_kwargs_in_plugin_call(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
dct = {
    "new": "You",
    "old": "World",
}
str = std::replace("Hello World!", **dct)
        """,
        autostd=True,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert root.lookup("str").get_value() == "Hello You!"


def test_kwargs_in_plugin_call_missing_arg(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
std::equals(42, desc="they differ")
        """,
        "std::equals() missing 1 required positional argument: 'arg2' "
        "(reported in std::equals(42,desc='they differ') ({dir}/main.cf:2:1))",
        autostd=True,
    )


def test_kwargs_in_plugin_call_double_arg(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
std::equals(42, 42, arg1=42)
        """,
        "std::equals() got multiple values for argument 'arg1' (reported in std::equals(42,42,arg1=42) ({dir}/main.cf:2:1))",
        autostd=True,
    )


def test_plugin_has_no_type_annotation(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import plugin_missing_type_annotation
plugin_missing_type_annotation::no_type_annotation(42)
        """,
        "All arguments of plugin 'plugin_missing_type_annotation::no_type_annotation' "
        "should be annotated: 'a' has no annotation",
    )


def test_kwargs_in_plugin_call_double_kwarg(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
std::equals(42, arg2=42, arg2=42)
        """,
        "Keyword argument arg2 repeated in function call std::equals()"
        " (reported in std::equals(42,arg2=42) ({dir}/main.cf:2:1))",
    )


def test_1774_plugin_returning_entity_in_list(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import test_1774

test_1774::test_list(test_1774::Test())
        """,
        autostd=True,
    )
    compiler.do_compile()


def test_1774_plugin_returning_entity_in_dict(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import test_1774

test_1774::test_dict(test_1774::Test())
        """,
        autostd=True,
    )
    compiler.do_compile()


def test_674_nullable_type_in_plugin_arguments(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import test_674

test_674::test_nullable("str")
test_674::test_nullable(null)
        """,
    )
    compiler.do_compile()


def test_674_not_nullable_type_in_plugin_arguments(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import test_674

test_674::test_not_nullable("Hello World!")
        """,
    )
    compiler.do_compile()


def test_674_not_nullable_type_in_plugin_arguments_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import test_674

test_674::test_not_nullable(null)
        """,
        "Value null for argument param of plugin test_674::test_not_nullable has incompatible type."
        " Expected type: string (reported in test_674::test_not_nullable(null) ({dir}/main.cf:4:1))"
        "\ncaused by:"
        "\n  Invalid value 'null', expected string (reported in test_674::test_not_nullable(null) ({dir}/main.cf:4:1))",
    )


def test_674_nullable_list_type_in_plugin_arguments(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import test_674

test_674::test_nullable_list([42, 12])
test_674::test_nullable_list(null)
        """,
    )
    compiler.do_compile()


def test_674_not_nullable_list_type_in_plugin_arguments(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import test_674

test_674::test_not_nullable_list([1,2])
        """,
    )
    compiler.do_compile()


def test_674_not_nullable_list_type_in_plugin_arguments_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import test_674

test_674::test_not_nullable_list(null)
        """,
        "Value null for argument param of plugin test_674::test_not_nullable_list has incompatible type."
        " Expected type: int[] (reported in test_674::test_not_nullable_list(null) ({dir}/main.cf:4:1))"
        "\ncaused by:"
        "\n  Invalid value 'null', expected int[] (reported in test_674::test_not_nullable_list(null) ({dir}/main.cf:4:1))",
    )


def test_674_nullable_type_in_plugin_return(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import test_674

x = test_674::test_returns_none()
x = null
        """,
    )
    compiler.do_compile()


def test_1778_context_as_kwarg_reject(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
std::generate_password("pw_id", 42, context=42)
        """,
        "std::generate_password() got an unexpected keyword argument: 'context' "
        "(reported in std::generate_password('pw_id',42,context=42) ({dir}/main.cf:2:1))",
        autostd=True,
    )


def test_1920_type_double_defined_plugin(snippetcompiler):
    modpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "modules", "test_1920")
    snippetcompiler.setup_for_error(
        """
import test_1920
        """,
        "Type test_1920::some_name is already defined"
        f" (original at ({modpath}/plugins/__init__.py:5))"
        f" (duplicate at ({modpath}/model/_init.cf:1:16))",
    )


def test_explicit_plugin_exception(snippetcompiler):
    msg: str = "my exception message"
    snippetcompiler.setup_for_snippet(
        """
import tests

tests::raise_exception("%s")
        """
        % msg,
    )
    try:
        compiler.do_compile()
        assert False, "Expected ExplicitPluginException"
    except ExplicitPluginException as e:
        assert e.__cause__.message == "Test: " + msg
    except Exception as e:
        assert False, "Expected ExplicitPluginException, got %s" % e


def test_plugin_load_exception(snippetcompiler):
    module: str = "test_plugin_load_error"
    snippetcompiler.setup_for_snippet(f"import {module}")
    modpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "modules", module)
    expected: str = (
        "Unable to load all plug-ins for module test_plugin_load_error:"
        "\n\tNameError while loading plugin module inmanta_plugins.test_plugin_load_error.invalid_code:"
        f" name 'invalid_token_at_line_42' is not defined ({modpath}/plugins/invalid_code.py:42)"
    )
    with pytest.raises(CompilerException, match=re.escape(expected)):
        compiler.do_compile()


def test_3457_helpful_string(snippetcompiler, caplog):
    with caplog.at_level(logging.DEBUG):
        snippetcompiler.setup_for_snippet(
            """
entity A:
end
A.other [0:] -- A
implement A using std::none
a = A()
std::attr(a, "other")
a.other = A()
            """,
            autostd=True,
        )
        compiler.do_compile()
    dir: str = snippetcompiler.project_dir
    message: str = (
        "Unset value in python code in plugin at call: std::attr " f"({dir}/main.cf:7:1) (Will be rescheduled by compiler)"
    )
    log_contains(caplog, "inmanta.ast.statements.call", logging.DEBUG, message)


def test_plugin_with_keyword_only_arguments(snippetcompiler) -> None:
    """
    Verify that keyword-only arguments in plugins are handled correctly by the compiler.
    """
    snippetcompiler.setup_for_snippet(
        """
import keyword_only_arguments

# Test regular case. All arguments are provided
std::equals(keyword_only_arguments::sum_all(1, 2, c=3, d=4), 10)

# Test handling of default values
std::equals(keyword_only_arguments::sum_all(1, c=3), 7)
        """,
        autostd=True,
    )
    compiler.do_compile()

    # Test required keyword-only argument is missing
    snippetcompiler.setup_for_snippet(
        """
import keyword_only_arguments

keyword_only_arguments::sum_all(1, 2)
        """,
    )
    with pytest.raises(RuntimeException) as exc_info:
        compiler.do_compile()
    assert "sum_all() missing 1 required keyword-only argument: 'c'" in exc_info.value.msg


def test_catch_all_arguments(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    Test that catch all positional and keyword arguments work as expected.
    """
    snippetcompiler.setup_for_snippet(
        """
import catch_all_arguments

# Test regular case.  No extra argument is provided
std::equals(catch_all_arguments::sum_all(1, b=2), 3)

# Test with extra values provided
std::equals(catch_all_arguments::sum_all(1, 2, 3, b=4, c=5, d=6), 21)
        """,
        autostd=True,
    )
    compiler.do_compile()


def test_signature(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    Test that the get_signature method of the plugins work as expected.
    """
    snippetcompiler.setup_for_snippet(
        """
# Import some modules which define plugins
import catch_all_arguments
import keyword_only_arguments
        """
    )
    statements, _ = compiler.do_compile()

    # Get all plugins objects, we get them from the statements, and recognize them
    # by their `get_signature` method.
    plugins: dict[str, inmanta.plugins.Plugin] = {
        name: stmt for name, stmt in statements.items() if hasattr(stmt, "get_signature")
    }
    assert (
        plugins["catch_all_arguments::sum_all"].get_signature()
        == "sum_all(a: 'int', *aa: 'int', b: 'int', **bb: 'int') -> 'int'"
    )
    assert plugins["catch_all_arguments::sum_all"].get_signature(use_dsl_types=True) == (
        "sum_all(a: int, *aa: int, b: int, **bb: int) -> int"
    )
    assert plugins["keyword_only_arguments::sum_all"].get_signature() == (
        "sum_all(a: 'int', b: 'int' = 1, *, c: 'int', d: 'int' = 2) -> 'int'"
    )
    assert plugins["keyword_only_arguments::sum_all"].get_signature(use_dsl_types=True) == (
        "sum_all(a: int, b: int, *, c: int, d: int) -> int"
    )


def test_returned_types(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    Test that the value returned from a plugin are validated correctly.
    """
    snippetcompiler.setup_for_snippet(
        """
import plugin_returned_type_validation

plugin_returned_type_validation::as_any_explicit({"a": "a"})
plugin_returned_type_validation::as_any_implicit({"a": "a"})
plugin_returned_type_validation::as_none(null)
plugin_returned_type_validation::as_null(null)
plugin_returned_type_validation::as_string("a")
        """
    )
    compiler.do_compile()


def test_context_and_defaults(snippetcompiler: "SnippetCompilationTest") -> None:
    """
    Test that the usage of the context argument together with default
    values doesn't cause any issue
    """
    snippetcompiler.setup_for_snippet(
        """
import plugin_context_and_defaults

plugin_context_and_defaults::func()
        """
    )
    compiler.do_compile()


def test_inferred_signatures_logging(snippetcompiler: "SnippetCompilationTest", caplog) -> None:
    """
    Test that the signature (using inferred Inmanta types)
    for each plugin is correctly logged
    """
    with caplog.at_level(logging.DEBUG):

        snippetcompiler.setup_for_snippet(
            """
import plugin_native_types
            """,
            ministd=True,
        )
        compiler.do_compile()

        expected_signatures = [
            "get_from_dict(value: dict[string, string], key: string) -> string?",
            "many_arguments(il: string[], idx: int) -> string",
            "as_none(value: string)",
            "var_args_test(value: string, *other: string[])",
            "var_kwargs_test(value: string, *other: string[], **more: dict[string, int])",
            (
                "all_args_types(positional_arg: string, *star_args_collector: string[], "
                "key_word_arg: string?, **star_star_args_collector: dict[string, string])"
            ),
            "positional_args_ordering_test(c: string, a: string, b: string) -> string",
            "no_collector(pos_arg_1: string, pos_arg_2: string, kw_only_123: string, kw_only_2: string, kw_only_3: string)",
            "only_kwargs(*, kw_only_1: string, kw_only_2: string, kw_only_3: int)",
            "optional_arg(a: int?)",
        ]
        for plugin_signature in expected_signatures:
            log_contains(
                caplog=caplog,
                loggerpart="inmanta.plugins",
                level=logging.DEBUG,
                msg=f"Found plugin plugin_native_types::{plugin_signature}",
            )


def test_native_types(snippetcompiler: "SnippetCompilationTest", caplog) -> None:
    """
    test the use of python types
    """
    with caplog.at_level(logging.DEBUG):

        snippetcompiler.setup_for_snippet(
            """
import plugin_native_types

test_entity = plugin_native_types::TestEntity(value=2)
a = "b"
a = plugin_native_types::get_from_dict({"a":"b"}, "a")

none = null
none = plugin_native_types::get_from_dict({"a":"b"}, "B")

a = plugin_native_types::many_arguments(["a","c","b"], 1)

none = plugin_native_types::as_none("a")

# Union types (input)
plugin_native_types::union_single_type(value="test")     # type value: Union[str]
plugin_native_types::union_multiple_types(value="test")  # type value: Union[int, str]
plugin_native_types::union_multiple_types(value=123)     # type value: Union[int, str]
for val in ["test", 123, null, test_entity]:
    plugin_native_types::union_optional_1(value=val)     # type value: Union[None, int, str, Entity]
    plugin_native_types::union_optional_2(value=val)     # type value: Optional[Union[int, str, Entity]]
    plugin_native_types::union_optional_3(value=val)     # type value: Union[int, str, Entity] | None
    plugin_native_types::union_optional_4(value=val)     # type value: None | Union[int, str, Entity]
end

# Union types (return value)
plugin_native_types::union_return_single_type(value="test")     # type return value: Union[str]
plugin_native_types::union_return_multiple_types(value="test")  # type return value: Union[str, int]
plugin_native_types::union_return_multiple_types(value=123)     # type return value: Union[str, int]
for val in ["test", 123, null, test_entity]:
    plugin_native_types::union_return_optional_1(value=val)     # type return value: Union[None, int, str, Entity]
    plugin_native_types::union_return_optional_2(value=val)     # type return value: Optional[Union[int, str, Entity]]
    plugin_native_types::union_return_optional_3(value=val)     # type return value: Union[int, str, Entity] | None
    plugin_native_types::union_return_optional_4(value=val)     # type return value: None | Union[int, str, Entity]
end

# Annotated types
plugin_native_types::annotated_arg_entity(test_entity)     # type value: Annotated[MyEntity, ModelType["TestEntity"]]
plugin_native_types::annotated_return_entity(test_entity)  # type return value: Annotated[MyEntity, ModelType["TestEntity"]]
# Entity: typing.TypeAlias = typing.Annotated[Any, ModelType["std::Entity"]]
plugin_native_types::type_entity_arg(test_entity)          # type value: Entity
plugin_native_types::type_entity_return(test_entity)       # type return value: Entity
plugin_native_types::type_entity_alias_arg(test_entity)          # type value: EntityAlias
plugin_native_types::type_entity_alias_return(test_entity)       # type return value: EntityAlias

for val in ["yes", "no"]:
    plugin_native_types::annotated_arg_literal(val)        # type value: Annotated[Literal["yes", "no"], ModelType["response"]]
    plugin_native_types::annotated_return_literal(val)   # type value: Annotated[Literal["yes", "no"], ModelType["response"]]
end
        """,
            ministd=True,
        )
    compiler.do_compile()

    cf_file = snippetcompiler.main
    # Parameter to plugin has incompatible type
    ns = "plugin_native_types"
    for plugin_name, plugin_value, error_message_re in [
        (
            "union_single_type",
            123,
            re.escape(
                f"Value 123 for argument value of plugin {ns}::union_single_type has incompatible type. Expected type: string"
                f" (reported in plugin_native_types::union_single_type(value=123) ({cf_file}:3:13))"
            ),
        ),
        (
            "union_multiple_types",
            "[1, 2, 3]",
            re.escape(
                f"Value [1, 2, 3] for argument value of plugin {ns}::union_multiple_types has incompatible type."
                " Expected type: Union[int,string]"
                f" (reported in plugin_native_types::union_multiple_types(value=[1, 2, 3]) ({cf_file}:3:13))"
            ),
        ),
        (
            "union_optional_1",
            1.2,
            re.escape(
                f"Value 1.2 for argument value of plugin {ns}::union_optional_1 has incompatible type."
                f" Expected type: Union[int,string,std::Entity]?"
                f" (reported in plugin_native_types::union_optional_1(value=1.2) ({cf_file}:3:13))"
            ),
        ),
        (
            "union_optional_2",
            1.2,
            re.escape(
                f"Value 1.2 for argument value of plugin {ns}::union_optional_2 has incompatible type."
                f" Expected type: Union[int,string,std::Entity]?"
                f" (reported in plugin_native_types::union_optional_2(value=1.2) ({cf_file}:3:13))"
            ),
        ),
        (
            "union_optional_3",
            1.2,
            re.escape(
                f"Value 1.2 for argument value of plugin {ns}::union_optional_3 has incompatible type."
                f" Expected type: Union[int,string,std::Entity]?"
                f" (reported in plugin_native_types::union_optional_3(value=1.2) ({cf_file}:3:13))"
            ),
        ),
        (
            "union_optional_4",
            1.2,
            re.escape(
                f"Value 1.2 for argument value of plugin {ns}::union_optional_4 has incompatible type."
                f" Expected type: Union[int,string,std::Entity]?"
                f" (reported in plugin_native_types::union_optional_4(value=1.2) ({cf_file}:3:13))"
            ),
        ),
        (
            "annotated_arg_entity",
            "plugin_native_types::AnotherEntity(another_value=1)",
            (
                rf"Value {ns}::AnotherEntity [0-9a-f]+ for argument value of plugin "
                + re.escape(
                    f"{ns}::annotated_arg_entity has incompatible type. Expected type: {ns}::TestEntity "
                    f"(reported in {ns}::annotated_arg_entity(value=Construct({ns}::AnotherEntity)) ({cf_file}:3:13))"
                )
            ),
        ),
        (
            "annotated_arg_literal",
            "'maybe'",
            re.escape(
                f"Value 'maybe' for argument value of plugin {ns}::annotated_arg_literal has incompatible type. "
                f"Expected type: {ns}::response (reported in plugin_native_types::annotated_arg_literal(value='maybe')"
                f" ({cf_file}:3:13))"
            ),
        ),
    ]:
        snippetcompiler.setup_for_snippet(
            f"""
            import plugin_native_types
            plugin_native_types::{plugin_name}(value={plugin_value})
            """,
            ministd=True,
        )
        with pytest.raises(RuntimeException) as exc_info:
            compiler.do_compile()
        message = str(exc_info.value)
        assert re.fullmatch(error_message_re, message), message

    # Return value of plugin has incompatible type
    for plugin_name, plugin_value, error_message in [
        (
            "union_return_single_type",
            123,
            f"Return value 123 of plugin {ns}::union_return_single_type has incompatible type. Expected type: string",
        ),
        (
            "union_return_multiple_types",
            "[1, 2, 3]",
            f"Return value [1, 2, 3] of plugin {ns}::union_return_multiple_types has incompatible type."
            " Expected type: Union[string,int]",
        ),
        (
            "union_return_optional_1",
            1.2,
            (
                f"Return value 1.2 of plugin {ns}::union_return_optional_1 has incompatible type."
                " Expected type: Union[int,string,std::Entity]?"
            ),
        ),
        (
            "union_return_optional_2",
            1.2,
            (
                f"Return value 1.2 of plugin {ns}::union_return_optional_2 has incompatible type."
                " Expected type: Union[int,string,std::Entity]?"
            ),
        ),
        (
            "union_return_optional_3",
            1.2,
            (
                f"Return value 1.2 of plugin {ns}::union_return_optional_3 has incompatible type."
                " Expected type: Union[int,string,std::Entity]?"
            ),
        ),
        (
            "union_return_optional_4",
            1.2,
            (
                f"Return value 1.2 of plugin {ns}::union_return_optional_4 has incompatible type."
                " Expected type: Union[int,string,std::Entity]?"
            ),
        ),
        (
            "annotated_return_entity",
            "plugin_native_types::AnotherEntity(another_value=1)",
            (
                f"Return value {ns}::AnotherEntity (instantiated at {cf_file}:3) of plugin {ns}::annotated_return_entity "
                f"has incompatible type. Expected type: {ns}::TestEntity"
            ),
        ),
        (
            "annotated_return_literal",
            "'maybe'",
            (
                f"Return value maybe of plugin {ns}::annotated_return_literal has incompatible type. "
                f"Expected type: {ns}::response"
            ),
        ),
    ]:
        snippetcompiler.setup_for_snippet(
            f"""
            import plugin_native_types
            plugin_native_types::{plugin_name}(value={plugin_value})
            """,
            ministd=True,
        )
        with pytest.raises(WrappingRuntimeException) as exc_info:
            compiler.do_compile()
        assert error_message in str(exc_info.value)

    snippetcompiler.setup_for_snippet(
        """
        import plugin_invalid_union_type
        """,
        ministd=True,
    )
    with pytest.raises(InvalidTypeAnnotation) as exc_info:
        compiler.do_compile()
    assert "Union type must be subscripted, got typing.Union" in str(exc_info.value)
