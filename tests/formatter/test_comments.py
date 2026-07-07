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

from inmanta.formatter import format_string
from inmanta.formatter.comments import Comment, extract_comments


# ── Comment extraction ──────────────────────────────────────────────────

def test_extract_inline_comment():
    source = "x = 5  # inline\n"
    cm = extract_comments(source)
    assert len(cm) == 1
    c = cm._by_line[1]
    assert c.is_inline
    assert c.text == "# inline"


def test_extract_block_comment():
    source = "# block comment\nx = 5\n"
    cm = extract_comments(source)
    assert len(cm) == 1
    c = cm._by_line[1]
    assert not c.is_inline
    assert c.text == "# block comment"


def test_comment_in_string_not_extracted():
    source = 'x = "hello # world"\n'
    cm = extract_comments(source)
    assert len(cm) == 0


def test_comment_in_fstring_not_extracted():
    source = 'x = f"hello # world"\n'
    cm = extract_comments(source)
    assert len(cm) == 0


def test_comment_in_mls_not_extracted():
    source = '"""\nhello # world\n"""\n'
    cm = extract_comments(source)
    assert len(cm) == 0


def test_multiple_comments():
    source = "# first\n# second\nx = 5  # inline\n"
    cm = extract_comments(source)
    assert len(cm) == 3


def test_get_leading_comments():
    source = "# first\n# second\nx = 5\n"
    cm = extract_comments(source)
    leading = cm.get_leading(3)  # x = 5 is on line 3
    assert len(leading) == 2
    assert leading[0].text == "# first"
    assert leading[1].text == "# second"


def test_get_trailing_comment():
    source = "x = 5  # inline\n"
    cm = extract_comments(source)
    tc = cm.get_trailing(1)
    assert tc is not None
    assert tc.text == "# inline"


def test_get_orphan_comments():
    source = "x = 1\n# orphan\ny = 2\n"
    cm = extract_comments(source)
    orphans = cm.get_orphans(1, 3)
    assert len(orphans) == 1
    assert orphans[0].text == "# orphan"


# ── Comment preservation in formatting ──────────────────────────────────

def test_leading_comment_preserved():
    source = "# comment about x\nx = 5\n"
    result = format_string(source)
    assert "# comment about x\n" in result
    assert "x = 5\n" in result


def test_inline_comment_preserved():
    source = "x = 5  # inline comment\n"
    result = format_string(source)
    assert "# inline comment" in result


def test_comment_between_definitions():
    source = "entity A:\nend\n\n# about B\n\nentity B:\nend\n"
    result = format_string(source)
    assert "# about B\n" in result


def test_comment_inside_entity():
    source = "entity Foo:\n    # about name\n    string name\nend\n"
    result = format_string(source)
    assert "    # about name\n" in result


def test_trailing_file_comment():
    source = "x = 5\n# end of file\n"
    result = format_string(source)
    assert "# end of file\n" in result


def test_comment_in_empty_if_body():
    """Comments in empty if/elif blocks must not be lost."""
    source = "if x == 1:\n    # nothing to do\nend\n"
    result = format_string(source)
    assert "    # nothing to do\n" in result
    assert result.strip().endswith("end")


def test_comment_in_empty_elif_body():
    """Comments in empty elif blocks must not be lost."""
    source = "if x == 1:\n    a = 1\nelif x == 2:\n    # skip this case\nelse:\n    b = 2\nend\n"
    result = format_string(source)
    assert "    # skip this case\n" in result


def test_comment_in_empty_else_body():
    """Comments in empty else blocks must not be lost."""
    source = "if x == 1:\n    a = 1\nelse:\n    # nothing here\nend\n"
    result = format_string(source)
    assert "    # nothing here\n" in result


def test_comment_in_empty_for_body():
    """Comments in empty for blocks must not be lost."""
    source = "for x in items:\n    # placeholder\nend\n"
    result = format_string(source)
    assert "    # placeholder\n" in result


def test_comment_in_empty_implementation_body():
    """Comments in empty implementation blocks must not be lost."""
    source = "implementation none for Foo:\n    # no-op\nend\n"
    result = format_string(source)
    assert "    # no-op\n" in result


def test_comments_not_duplicated():
    """Comments must not appear more than once in the output."""
    source = "if x == 1:\n    # nothing to do\nend\n\nif y == 2:\n    # also nothing\nend\n"
    result = format_string(source)
    assert result.count("# nothing to do") == 1
    assert result.count("# also nothing") == 1


# ── # fmt: off / on / skip ─────────────────────────────────────────────

def test_fmt_off_on():
    """Statements inside # fmt: off / # fmt: on are not formatted."""
    source = 'x = Foo(a=1, b=2)\n# fmt: off\ny = Foo(  a =  1 , b   =2  )\n# fmt: on\nz = Bar(c=3)\n'
    result = format_string(source)
    assert "y = Foo(  a =  1 , b   =2  )" in result
    assert "z = Bar(c=3)" in result


def test_fmt_skip():
    """A line with # fmt: skip is not formatted."""
    source = 'x = Foo(  a =  1  )  # fmt: skip\ny = Bar(b=2)\n'
    result = format_string(source)
    assert "x = Foo(  a =  1  )  # fmt: skip" in result
    assert "y = Bar(b=2)" in result


def test_fmt_off_unclosed():
    """Unclosed # fmt: off extends to end of file."""
    source = 'x = Foo(a=1)\n# fmt: off\ny = Foo(  a =  1  )\nz = Bar(  b = 2  )\n'
    result = format_string(source)
    assert "y = Foo(  a =  1  )" in result
    assert "z = Bar(  b = 2  )" in result
