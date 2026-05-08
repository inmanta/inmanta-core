"""
Copyright 2026 Inmanta

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

import glob
import os

import pytest

from inmanta.formatter import FormatterError, format_string
from inmanta.formatter.config import FormatConfig

TESTS_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


# ── Collect all .cf files in tests/data ─────────────────────────────────

def _all_cf_files():
    return sorted(glob.glob(os.path.join(TESTS_DATA, "**", "*.cf"), recursive=True))


@pytest.fixture(params=_all_cf_files(), ids=lambda p: os.path.relpath(p, TESTS_DATA))
def cf_file(request):
    return request.param


# ── AST equivalence: parse(format(source)) == parse(source) ────────────

def test_ast_equivalence(cf_file):
    """Formatting must not change the AST — this is the core safety guarantee."""
    with open(cf_file) as f:
        source = f.read()
    if not source.strip():
        pytest.skip("empty file")
    # format_string internally runs _assert_ast_equivalent
    format_string(source, filename=cf_file)


# ── Idempotency: format(format(source)) == format(source) ──────────────

def test_idempotency(cf_file):
    """Formatting the same source twice must produce identical output."""
    with open(cf_file) as f:
        source = f.read()
    if not source.strip():
        pytest.skip("empty file")
    formatted = format_string(source, filename=cf_file)
    formatted2 = format_string(formatted, filename=cf_file)
    assert formatted == formatted2, f"Formatter is not idempotent for {cf_file}"


# ── Specific formatting rules ───────────────────────────────────────────

def test_trailing_newline():
    """Formatted output must end with exactly one newline."""
    result = format_string("import std\n")
    assert result.endswith("\n")
    assert not result.endswith("\n\n")


def test_no_trailing_blank_lines():
    """No trailing blank lines before the final newline."""
    result = format_string("import std\n\n\n\n")
    assert result == "import std\n"


def test_blank_lines_between_imports():
    """Consecutive imports should have no blank lines between them."""
    source = "import std\nimport foo\n"
    result = format_string(source)
    assert result == "import std\nimport foo\n"


def test_blank_lines_after_imports():
    """2 blank lines after import block before first definition."""
    source = "import std\nentity Foo:\nend\n"
    result = format_string(source)
    assert result == "import std\n\n\nentity Foo:\nend\n"


def test_no_blank_lines_between_relations():
    """Consecutive relations should have no blank lines between them."""
    source = "A.b [0:] -- B.a [1]\nC.d [1] -- D.c [0:]\n"
    result = format_string(source)
    assert result == "A.b [0:] -- B.a [1]\nC.d [1] -- D.c [0:]\n"


def test_no_blank_lines_between_implements():
    """Consecutive implement statements should have no blank lines between them."""
    source = "implement Foo using bar\nimplement Baz using qux\n"
    result = format_string(source)
    assert result == "implement Foo using bar\nimplement Baz using qux\n"


def test_indentation_entity():
    """Entity body must be indented 4 spaces."""
    source = "entity Foo:\n  string name\nend\n"
    result = format_string(source)
    assert "    string name\n" in result


def test_keyword_arg_no_spaces():
    """Constructor keyword args must have no spaces around =."""
    source = 'Foo(name = "bar", x = 5)\n'
    result = format_string(source)
    assert 'Foo(name="bar", x=5)\n' == result


def test_attribute_default_no_spaces():
    """Entity attribute defaults must have no spaces around = (like kwargs)."""
    source = 'entity Foo:\n    string name = "default"\nend\n'
    result = format_string(source)
    assert '    string name="default"\n' in result


def test_string_quote_normalization():
    """Single-quoted strings should be normalized to double-quoted."""
    source = "x = 'hello'\n"
    result = format_string(source)
    assert result == 'x = "hello"\n'


def test_string_no_normalize_when_has_double_quotes():
    """Don't normalize if content has double quotes."""
    source = """x = 'say "hello"'\n"""
    result = format_string(source)
    assert """x = 'say "hello"'\n""" == result


def test_spaces_around_operators():
    """Binary operators must have spaces around them."""
    source = "x = a+b\n"
    result = format_string(source)
    assert result == "x = a + b\n"


def test_relation_formatting():
    """Relations should be formatted with spaces around -- and before [."""
    source = "A.b [0:] -- B.a [1]\n"
    result = format_string(source)
    assert "A.b [0:] -- B.a [1]\n" == result


def test_for_loop_formatting():
    source = "for x in items:\nFoo(name=x)\nend\n"
    result = format_string(source)
    assert "for x in items:\n    Foo(name=x)\nend\n" == result


def test_if_elif_else():
    source = "if x == 1:\na = 1\nelif x == 2:\na = 2\nelse:\na = 3\nend\n"
    result = format_string(source)
    lines = result.strip().split("\n")
    assert lines[0] == "if x == 1:"
    assert lines[1] == "    a = 1"
    assert lines[2] == "elif x == 2:"
    assert lines[3] == "    a = 2"
    assert lines[4] == "else:"
    assert lines[5] == "    a = 3"
    assert lines[6] == "end"


def test_import_as():
    source = "import foo as bar\n"
    result = format_string(source)
    assert result == "import foo as bar\n"


def test_typedef_regex():
    source = "typedef hostname as string matching /^[a-z]+$/\n"
    result = format_string(source)
    assert result == "typedef hostname as string matching /^[a-z]+$/\n"


def test_index():
    source = "index Foo(name, id)\n"
    result = format_string(source)
    assert result == "index Foo(name, id)\n"


def test_list_literal():
    source = "x = [1, 2, 3]\n"
    result = format_string(source)
    assert result == "x = [1, 2, 3]\n"


def test_dict_literal():
    source = 'x = {"a": 1, "b": 2}\n'
    result = format_string(source)
    assert result == 'x = {"a": 1, "b": 2}\n'


def test_magic_trailing_comma_expands():
    """Trailing comma forces multi-line expansion (Black magic trailing comma)."""
    source = "x = [1, 2, 3,]\n"
    result = format_string(source)
    assert result == "x = [\n    1,\n    2,\n    3,\n]\n"


def test_no_trailing_comma_stays_compact():
    """Without trailing comma, list stays on one line if it fits."""
    source = "x = [1, 2, 3]\n"
    result = format_string(source)
    assert result == "x = [1, 2, 3]\n"


def test_ternary_expression():
    source = "x = a ? b : c\n"
    result = format_string(source)
    assert result == "x = a ? b : c\n"


def test_is_defined():
    source = "x = a is defined\n"
    result = format_string(source)
    assert result == "x = a is defined\n"


def test_implement_when():
    source = "implement Foo using bar when x == 1\n"
    result = format_string(source)
    assert result == "implement Foo using bar when x == 1\n"


def test_implement_parents():
    source = "implement Foo using parents\n"
    result = format_string(source)
    assert result == "implement Foo using parents\n"


def test_empty_entity():
    source = "entity Foo:\nend\n"
    result = format_string(source)
    assert result == "entity Foo:\nend\n"


def test_entity_with_docstring_only():
    source = 'entity Foo:\n    """\n    A foo.\n    """\nend\n'
    result = format_string(source)
    assert '"""\n' in result
    assert "end\n" in result


def test_empty_input():
    assert format_string("") == ""
    assert format_string("   \n\n  ") == "   \n\n  "


def test_blank_line_preserved_in_block():
    """Single blank lines between statements in blocks should be preserved."""
    source = "implementation foo for Foo:\n    self.x = 1\n\n    self.y = 2\nend\n"
    result = format_string(source)
    assert "\n    self.x = 1\n\n    self.y = 2\n" in result


def test_no_blank_line_not_added_in_block():
    """Don't add blank lines between block statements that had none."""
    source = "implementation foo for Foo:\n    self.x = 1\n    self.y = 2\nend\n"
    result = format_string(source)
    assert "\n    self.x = 1\n    self.y = 2\n" in result


def test_multiple_blank_lines_collapsed():
    """Multiple blank lines between statements collapse to 1."""
    source = "x = 1\n\n\n\ny = 2\n"
    result = format_string(source)
    assert result == "x = 1\n\ny = 2\n"


def test_blank_line_preserved_top_level():
    """Single blank lines between top-level statements should be preserved."""
    source = "x = 1\n\ny = 2\n"
    result = format_string(source)
    assert result == "x = 1\n\ny = 2\n"


def test_entity_annotation_grouping():
    """Attributes with __ suffixes (annotations) group with their base attribute,
    separated by blank lines from other groups."""
    source = (
        "entity Foo:\n"
        "    string name\n"
        "    lsm::attribute_modifier name__modifier=\"rw\"\n"
        "    string desc\n"
        "    lsm::attribute_modifier desc__modifier=\"rw\"\n"
        "end\n"
    )
    result = format_string(source)
    expected = (
        "entity Foo:\n"
        "    string name\n"
        "    lsm::attribute_modifier name__modifier=\"rw\"\n"
        "\n"
        "    string desc\n"
        "    lsm::attribute_modifier desc__modifier=\"rw\"\n"
        "end\n"
    )
    assert result == expected


def test_entity_no_annotations_no_blank_lines():
    """Entity with no __ annotations should not have blank lines between attrs."""
    source = "entity Foo:\n    string a\n    string b\n    string c\nend\n"
    result = format_string(source)
    assert result == "entity Foo:\n    string a\n    string b\n    string c\nend\n"


def test_format_config_line_length():
    """FormatConfig line_length should be customizable."""
    config = FormatConfig(line_length=80)
    assert config.line_length == 80


# ── Line splitting tests ────────────────────────────────────────────────

def test_long_constructor_splits():
    """Constructor calls exceeding line length should split one-arg-per-line."""
    source = 'x = Foo(aaa="very_long_value_1", bbb="very_long_value_2", ccc="very_long_value_3")\n'
    config = FormatConfig(line_length=60)
    result = format_string(source, config=config)
    assert "Foo(\n" in result
    assert '    aaa="very_long_value_1",\n' in result
    assert ")\n" in result


def test_long_function_call_splits():
    """Function calls exceeding line length should split."""
    source = 'std::validate_type("pydantic.constr", self, {"regex": "^[a-zA-Z]*$"})\n'
    config = FormatConfig(line_length=50)
    result = format_string(source, config=config)
    assert "std::validate_type(\n" in result


def test_nested_call_expansion():
    """Nested calls should expand recursively if needed."""
    source = 'x = Outer(name="test", inner=Inner(a="long_value_here", b="another_long_val", c="third"))\n'
    config = FormatConfig(line_length=40)
    result = format_string(source, config=config)
    assert "Outer(\n" in result
    assert "Inner(\n" in result


def test_magic_trailing_comma_constructor():
    """Trailing comma in constructor forces expansion."""
    source = "x = Foo(a=1,)\n"
    result = format_string(source)
    assert "Foo(\n" in result
    assert "    a=1,\n" in result
    assert ")\n" in result


def test_short_call_no_split():
    """Short calls should stay on one line."""
    source = "x = Foo(a=1)\n"
    result = format_string(source)
    assert result == "x = Foo(a=1)\n"


def test_trailing_comma_removed_on_compact():
    """Trailing commas in source are stripped when the call fits on one line.
    This cannot actually happen since trailing comma forces expansion,
    so this tests a call WITHOUT trailing comma stays compact."""
    source = "x = Foo(a=1, b=2)\n"
    result = format_string(source, config=FormatConfig(line_length=200))
    assert result == "x = Foo(a=1, b=2)\n"
