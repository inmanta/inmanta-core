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
import pytest

import inmanta.compiler as compiler
from inmanta.ast import Namespace, NotFoundException
from inmanta.ast.variables import Reference
from test_parser import parse_code


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


def test_escaping_rules_single_vs_triple_quotes_2582(snippetcompiler, capsys):
    """
    Check that new line characters are correctly interpreted in multi-line strings
    """
    snippetcompiler.setup_for_snippet(
        r'''
test_string_1 = """trippel hello\nworld"""
test_string_2 = "single hello\nworld"
std::print(test_string_1)
std::print(test_string_2)
'''
    )
    expected = r"""trippel hello
world
single hello
world
"""
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert expected == out


def test_fstring_float_formatting(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
arg = 12.23455
z=f"{arg:.4f}"
std::print(z)
        """,
    )
    expected = "12.2346\n"

    compiler.do_compile()
    out, err = capsys.readouterr()
    assert out == expected


@pytest.mark.parametrize(
    "f_string,expected_output",
    [
        (r"f'{arg}'", "123\n"),
        (r"f'{arg}{arg}{arg}'", "123123123\n"),
        (r"f'{arg:@>5}'", "@@123\n"),
        (r"f'{arg:^5}'", " 123 \n"),
    ],
)
def test_fstring_formatting(snippetcompiler, capsys, f_string, expected_output):
    snippetcompiler.setup_for_snippet(
        f"""
arg = 123
z={f_string}
std::print(z)
        """,
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert out == expected_output


def test_fstring_expected_error(snippetcompiler, capsys):
    with pytest.raises(NotFoundException):
        snippetcompiler.setup_for_snippet(
            """
std::print(f"{unknown}")
            """,
        )
        compiler.do_compile()


def test_fstring_relations(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
entity Aaa:
end

entity Bbb:
end

entity Ccc:
    int n_c = 3
end

implement Aaa using std::none
implement Bbb using std::none
implement Ccc using std::none

Aaa.b [1] -- Bbb [1]
Bbb.c [1] -- Ccc [1]

a = Aaa(b=b)
b = Bbb(c=c)
c = Ccc()

std::print(f"{a.b.c.n_c}")
        """
    )

    compiler.do_compile()
    out, err = capsys.readouterr()
    expected_output = "3\n"
    assert out == expected_output


def test_fstring_numbering_logic():
    statements = parse_code(
        """
std::print(f"---{s}{mm} - {lll}")
"""
    )

    def check_range(variable: Reference, start: int, end: int):
        assert variable.location.start_char == start
        assert variable.location.end_char == end

    # Ranges are 1-indexed [start:end[
    ranges = [
        (
            len('std::print(f"---{s'),
            len('std::print(f"---{s}')
        ),
        (
            len('std::print(f"---{s}{m'),
            len('std::print(f"---{s}{mm}')),
        (
            len('std::print(f"---{s}{mm} - {l'),
            len('std::print(f"---{s}{mm} - {lll}')),
    ]
    variables = statements[0].children[0]._variables

    for var, range in zip(variables, ranges):
        check_range(var, *range)
