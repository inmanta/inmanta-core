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
from typing import Union

import pytest

import inmanta.compiler as compiler
from inmanta.ast import Namespace
from inmanta.ast.variables import AttributeReference, Reference
from test_parser import parse_code


def test_multiline_string_interpolation(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
var = 42
str = \"\"\"var == {{   var }}\"\"\"
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
        (r"f'{   arg }'", "123\n"),
        (r"f'{arg}'", "123\n"),
        (r"f'{arg}{arg}{arg}'", "123123123\n"),
        (r"f'{arg:@>5}'", "@@123\n"),
        (r"f'{arg:@>{width}}'", "@@@@@@@123\n"),
        (r"f'{arg:^5}'", " 123 \n"),
        (r"f' {  \t\narg  \n  } '", " 123 \n"),
    ],
)
def test_fstring_formatting(snippetcompiler, capsys, f_string, expected_output):
    snippetcompiler.setup_for_snippet(
        f"""
arg = 123
width = 10
z={f_string}
std::print(z)
        """,
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert out == expected_output


def test_fstring_expected_error(snippetcompiler, capsys):
    snippetcompiler.setup_for_error(
        'std::print(f"{unknown}")',
        "variable unknown not found (reported in '{{unknown}}' ({dir}/main.cf:1:12))",
    )

    snippetcompiler.setup_for_error(
        'f"hello {}"',
        (
            "f-strings do not support positional substitutions via '{{}}', use variable or attribute keys instead"
            " (reported in 'hello {{}}' ({dir}/main.cf:1:1))"
        ),
    )

    snippetcompiler.setup_for_error(
        'f"{}{}"',
        (
            "f-strings do not support positional substitutions via '{{}}', use variable or attribute keys instead"
            " (reported in '{{}}{{}}' ({dir}/main.cf:1:1))"
        ),
    )

    snippetcompiler.setup_for_error(
        """
        world = "myworld"
        f"hello { world:{} }"
        """,
        (
            "f-strings do not support positional substitutions via '{{}}', use variable or attribute keys instead"
            " (reported in 'hello {{ world:{{}} }}' ({dir}/main.cf:3:9))"
        ),
    )

    snippetcompiler.setup_for_error(
        """
        world = "myworld"
        f"hello {world:invalid_specifier}"
        """,
        "Invalid f-string: Invalid format specifier%s (reported in 'hello {{world:invalid_specifier}}' ({dir}/main.cf:3:9))"
        % (
            " 'invalid_specifier' for object of type 'str'" if (sys.version_info.major, sys.version_info.minor) > (3, 9) else ""
        ),
    )


def test_fstring_relations(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
entity A:
end

entity B:
end

entity C:
    int n_c = 3
end

implement A using std::none
implement B using std::none
implement C using std::none

A.b [1] -- B [1]
B.c [1] -- C [1]

a = A(b=b)
b = B(c=c)
c = C()

std::print(f"{  a .b . c . n_c }")
        """
    )

    compiler.do_compile()
    out, err = capsys.readouterr()
    expected_output = "3\n"
    assert out == expected_output


def check_range(variable: Union[Reference, AttributeReference], start: int, end: int):
    assert variable.location.start_char == start, f"{variable=} expected {start=} got {variable.location.start_char=}"
    assert variable.location.end_char == end, f"{variable=} expected {end=} got {variable.location.end_char=}"


def test_fstring_numbering_logic():
    """
    Check that variable ranges in f-strings are correctly computed
    """
    statements = parse_code(
        """
#        10        20        30        40        50        60        70        80
#        |         |         |         |         |         |         |         |
std::print(f"---{s}{mm} - {sub.attr} - {  padded  } - {  \tpadded.sub.attr   }")
#                |   |           |           |                          |
#               [-][--]       [----]     [------]                    [----]    <--- expected ranges
        """
    )

    # Ranges are 1-indexed [start:end[
    ranges = [
        (len('std::print(f"---{s'), len('std::print(f"---{s}')),
        (len('std::print(f"---{s}{m'), len('std::print(f"---{s}{mm}')),
        (len('std::print(f"---{s}{mm} - {sub.a'), len('std::print(f"---{s}{mm} - {sub.attr}')),
        (len('std::print(f"---{s}{mm} - {sub.attr} - {  p'), len('std::print(f"---{s}{mm} - {sub.attr} - {  padded ')),
        (
            len('std::print(f"---{s}{mm} - {sub.attr} - {  padded  } - {  \tpadded.sub.a'),
            len('std::print(f"---{s}{mm} - {sub.attr} - {  padded  } - {  \tpadded.sub.attr '),
        ),
    ]
    variables = statements[0].children[0]._variables

    for var, range in zip(variables, ranges):
        check_range(var, *range)


def test_fstring_numbering_logic_multiple_refs():
    """
    Check that variable ranges in f-strings are correctly computed
    """
    statements = parse_code(
        """
std::print(f"---{s}----{s}")
#                |      |
#               [-]    [-] <--- expected ranges
        """
    )

    # Ranges are 1-indexed [start:end[
    ranges = [
        (len('std::print(f"---{s'), len('std::print(f"---{s}')),
        (len('std::print(f"---{s}----{s'), len('std::print(f"---{s}----{s}')),
    ]
    variables = statements[0].children[0]._variables

    for var, range in zip(variables, ranges):
        check_range(var, *range)


def test_fstring_float_nested_formatting(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
width = 10
precision = 2
arg = 12.34567
z=f"result: {arg:{width}.{precision}f}"
std::print(z)
        """,
    )
    expected = "result:      12.35\n"

    compiler.do_compile()
    out, err = capsys.readouterr()
    assert out == expected


def test_fstring_double_brackets(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
z=f"not {{replaced}}"
std::print(z)
        """,
    )
    expected = "not {replaced}\n"
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert out == expected


def test_fstring_numbering_logic_complex():
    statements = parse_code(
        """
std::print(f"-{arg:{width}.{precision}}{other}-text-{a:{w}.{p}}-----{w}")
        """
    )

    # Ranges are 1-indexed [start:end[
    ranges = [
        (len('std::print(f"-{a'), len('std::print(f"-{arg:')),
        (len('std::print(f"-{arg:{w'), len('std::print(f"-{arg:{width}')),
        (len('std::print(f"-{arg:{width}.{p'), len('std::print(f"-{arg:{width}.{precision}')),
        (len('std::print(f"-{arg:{width}.{precision}}{o'), len('std::print(f"-{arg:{width}.{precision}}{other}')),
        (
            len('std::print(f"-{arg:{width}.{precision}}{other}-text-{a'),
            len('std::print(f"-{arg:{width}.{precision}}{other}-text-{a:'),
        ),
        (
            len('std::print(f"-{arg:{width}.{precision}}{other}-text-{a:{w'),
            len('std::print(f"-{arg:{width}.{precision}}{other}-text-{a:{w}'),
        ),
        (
            len('std::print(f"-{arg:{width}.{precision}}{other}-text-{a:{w}.{p'),
            len('std::print(f"-{arg:{width}.{precision}}{other}-text-{a:{w}.{p}'),
        ),
        (
            len('std::print(f"-{arg:{width}.{precision}}{other}-text-{a:{w}.{p}}-----{w'),
            len('std::print(f"-{arg:{width}.{precision}}{other}-text-{a:{w}.{p}}-----{w}'),
        ),
    ]
    variables = statements[0].children[0]._variables

    for var, range in zip(variables, ranges):
        check_range(var, *range)
