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
import os

import inmanta.compiler as compiler


def test_plugin_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        import std
        std::template("/tet.tmpl")
""",
        """Exception in plugin std::template (reported in std::template('/tet.tmpl') ({dir}/main.cf:3))
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
        "Invalid value 'null', expected String (reported in test_674::test_not_nullable(null) ({dir}/main.cf:4))",
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
        "Invalid value 'null', expected number[] (reported in test_674::test_not_nullable_list(null) ({dir}/main.cf:4))",
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
