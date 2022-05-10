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

import inmanta.compiler as compiler
from inmanta.ast import Namespace


def test_multiline_string_interpolation(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
var = 42
str = \"\"\"var == {{var}}\"\"\"
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert root.lookup("str").get_value() == "var == 42"


def test_rstring(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
z=r"{{xxx}}"

entity X:
    string a
end

# Force typecheck
X(a=z)

implement X using none
implementation none for X:
end
        """,
    )
    compiler.do_compile()


def test_no_multiline_in_single_quoted_string_double_apostrophe(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
std::print(
  "test
  string"
)
        """,
        "Syntax error: Illegal character '\"' ({dir}/main.cf:3:3)",
    )


def test_no_multiline_in_single_quoted_string_simple_apostrophe(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
std::print(
  'test
  string'
)
        """,
        "Syntax error: Illegal character ''' ({dir}/main.cf:3:3)",
    )


def test_no_multiline_in_single_quoted_raw_string_double_apostrophe(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
std::print(
  r"test
  string"
)
        """,
        "Syntax error: Illegal character '\"' ({dir}/main.cf:3:4)",
    )


def test_no_multiline_in_single_quoted_raw_string_simple_apostrophe(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
std::print(
  r'test
  string'
)
        """,
        "Syntax error: Illegal character ''' ({dir}/main.cf:3:4)",
    )


def test_allowed_line_breaks(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        r'''
test_string_1 = "TESTSTRING"
test_string_2 = "TEST\nSTR\rING"
test_string_3 = r"TESTSTRING"
test_string_4 = r"TEST\nSTR\rING"

test_string_5 = 'TESTSTRING'
test_string_6 = 'TEST\nSTR\rING'
test_string_7 = r'TESTSTRING'
test_string_8 = r'TEST\nSTR\rING'


test_string_9 =  """TESTSTRING"""
test_string_10 = """TEST\nSTR\rING"""
test_string_11 = """TEST
STRING"""


std::print(test_string_1)
std::print(test_string_2)
std::print(test_string_3)
std::print(test_string_4)
std::print(test_string_5)
std::print(test_string_6)
std::print(test_string_7)
std::print(test_string_8)
std::print(test_string_9)
std::print(test_string_10)
std::print(test_string_11)

'''
    )
    compiler.do_compile()


def test_escaping_rules_single_vs_triple_quotes(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        r'''
test_string_1 = """trippel hello\nworld"""
test_string_2 = "single hello\nworld"
std::print(test_string_1)
std::print(test_string_2)
'''
    )
    compiler.do_compile()

