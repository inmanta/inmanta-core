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

import sys
from io import StringIO

import inmanta.compiler as compiler


def test_if_true(snippetcompiler):
    print_str: str = "Success!"
    snippetcompiler.setup_for_snippet(
        """
if true:
    std::print("%s")
end
        """
        % print_str
    )

    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        compiler.do_compile()
        output = out.getvalue().strip()
        assert output == print_str
    finally:
        sys.stdout = saved_stdout


def test_if_false(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
if false:
    std::print(1)
end
        """
    )

    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        compiler.do_compile()
        output = out.getvalue().strip()
        assert output == ""
    finally:
        sys.stdout = saved_stdout


def test_if_else_true(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
if true:
    std::print("It's true")
else:
    std::print("It's false")
end
        """
    )

    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        compiler.do_compile()
        output = out.getvalue().strip()
        assert output == "It's true"
    finally:
        sys.stdout = saved_stdout


def test_if_else_false(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
if false:
    std::print("It's true")
else:
    std::print("It's false")
end
        """
    )

    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        compiler.do_compile()
        output = out.getvalue().strip()
        assert output == "It's false"
    finally:
        sys.stdout = saved_stdout


def test_if_else_extended(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    string a = ""
end
implement A using std::none
a = A(a="a")
if a.a == "b":
    std::print("It's")
    std::print("true")
else:
    std::print("It's")
    std::print("false")
end
        """
    )

    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        compiler.do_compile()
        output = out.getvalue().strip()
        assert output == r"It's\nfalse"
    finally:
        sys.stdout = saved_stdout
