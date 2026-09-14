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

Differential test: parse a corpus of DSL snippets with both parser backends and
assert they produce equivalent ASTs (structure + top-level locations). This guards
the PLY/Lark parity: an unintended divergence in either backend fails here.

Both backend modules are imported directly (not via dispatch), so this runs
regardless of the active INMANTA_PARSER.

The corpus deliberately excludes the known, intentional divergences (tracked with
inline comments on the grammar in PR #10053 and issue #10600): `**` associativity,
`not`/`in` precedence, signed-number lexing (e.g. `a[0]-1`), `is defined` as a
comparison/`in` operand, and non-ASCII content in escaped double-quoted strings.
"""

import re

import pytest

from inmanta.ast import Namespace
from inmanta.ast.statements import Statement
from inmanta.parser import lark_parser, plyInmantaParser

# Some AST classes use the default object repr (with a memory address); strip it so
# those nodes compare by type + position while classes with a structural repr compare
# fully.
_ADDRESS = re.compile(r" at 0x[0-9a-fA-F]+")

CORPUS: list[str] = [
    # literals and assignments
    "x = 1",
    "x = 1.5",
    "x = -5",
    "x = -2.5",
    "x = true",
    "x = false",
    "x = null",
    'x = "hello"',
    "x = 'single'",
    'x = r"raw\\d+"',
    'x = f"v={a}"',
    'x = """multi\nline"""',
    "x = []",
    "x = [1, 2, 3]",
    'x = ["a", "b",]',
    "x = {}",
    'x = {"a": 1, "b": 2}',
    # arithmetic (spaced to avoid the signed-number lexing divergence)
    "x = 1 + 2",
    "x = 5 - 3",
    "x = 2 * 3",
    "x = 10 / 2",
    "x = 7 % 2",
    "x = 2 ** 3",
    "x = (1 + 2) * 3",
    "x = a + b - c",
    # comparison and boolean (avoid `not a == b` and `a in b + c`)
    "x = a > b",
    "x = a == b",
    "x = a != b",
    "x = a and b",
    "x = a or b",
    "x = not a",
    "x = not (a == b)",
    "x = a in b",
    "x = a in [1, 2]",
    "x = a not in b",
    'x = a > 0 ? "y" : "n"',
    # references and calls
    "x = a.b.c",
    "x = std::func(1, 2)",
    "x = std::func(a=1, b=2)",
    "x = std::func(**kw)",
    'x = Foo(name="a", count=1)',
    "x = things[key]",
    "x = Foo[id=1]",
    "x = a.b is defined",
    "x = a is defined",
    # comprehensions
    "x = [i for i in items]",
    "x = [i for i in items if i > 0]",
    # block statements
    "for i in items:\n y = i\nend",
    "if a > 0:\n x = 1\nelse:\n x = 2\nend",
    "if a:\n x = 1\nelif b:\n x = 2\nend",
    # definitions
    "entity Foo:\n string name\n number count = 5\n bool flag = true\nend",
    "entity Bar extends Foo:\n dict data\nend",
    'entity E:\n string? opt = null\n string[] items = ["a"]\nend',
    "Foo.bars [0:] -- Bar.foo [1]",
    "Foo.bars [0:] ann Bar.foo [1]",
    "implement Foo using std::none",
    "implement Foo using std::none when self.x > 0",
    'implementation impl for Foo:\n self.name = "x"\nend',
    "typedef pos as number matching self > 0",
    "typedef name as string matching /[a-z]+/",
    "index Foo(name)",
    "import std",
    "import std as s",
]


def _fresh_namespace() -> Namespace:
    return Namespace("__config__", Namespace("__root__"))


def _structure(statements: list[Statement]) -> list[str]:
    return [_ADDRESS.sub("", repr(s)) for s in statements]


def _lines(statements: list[Statement]) -> list[int]:
    return [s.location.lnr for s in statements]


@pytest.mark.parametrize("source", CORPUS)
def test_backends_produce_equivalent_ast(source: str) -> None:
    ply_statements = plyInmantaParser.base_parse(_fresh_namespace(), "test.cf", source)
    lark_statements = lark_parser.base_parse(_fresh_namespace(), "test.cf", source)

    assert _structure(lark_statements) == _structure(ply_statements), "AST structure differs between backends"
    assert _lines(lark_statements) == _lines(ply_statements), "top-level statement locations differ between backends"
